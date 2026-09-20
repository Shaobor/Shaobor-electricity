"""手机App（iOS 链路）登录流程（配置流 / 选项流共用）。

模块化设计：与 login_methods/ 下的网页版登录处理器（扫码/密码/短信）平级，
手机源的登录流程集中在本文件，由 ConfigFlow 与 OptionsFlowHandler 混入复用。

登录规则（由后端 /mobile/ios/profile 的登录档案决定）：
  - 已有登录档案（account.mobile 非空）且户号列表非空 → 免登录直接完成；
  - 无任何登录记录（首次） → 仅短信登录（新设备指纹必须短信验证后进信任名单）；
  - 有登录记录但会话失效/户号为空 → 短信 + 密码登录均可选；
  - 密码登录仅对已信任设备开放，被拒（设备验证/风控/滑块）时引导改走短信；
  - 手机源不提供扫码登录。

宿主钩子（混入方必须实现）：
  _mobile_auth_token() -> str | None            当前授权码
  _mobile_machine_id() -> str | None            当前 machineId（iOS 设备行键）
  _async_mobile_invalid_token() -> FlowResult   授权码无效时的展示
  _async_mobile_login_complete(account) -> FlowResult  登录成功/已有档案后的收尾
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol  # type: ignore[import-untyped]

try:
    from homeassistant.config_entries import ConfigFlowResult as FlowResult  # type: ignore[import-untyped]
except ImportError:
    from homeassistant.data_entry_flow import FlowResult  # type: ignore[import-untyped]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import-untyped]
from homeassistant.helpers.selector import (  # type: ignore[import-untyped]
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from ..const import LOGIN_METHOD_PASSWORD, LOGIN_METHOD_SMS

_LOGGER = logging.getLogger(__name__)


class MobileIosLoginMixin:
    """手机App源登录流程混入。

    提供以下表单步骤（step_id 同时适用于 config / options 流，strings.json 两处均已定义）：
      mobile_login_gate   内部闸门（非表单，直接转发）
      mobile_login_method 登录方式选择（sms / password，按登录记录放开）
      mobile_sms          短信登录第一步（手机号）
      mobile_sms_code     短信登录第二步（验证码）
      mobile_password     密码登录（仅限已信任设备）
    """

    # 流程状态（类级默认值，宿主无需在 __init__ 中初始化）
    _mobile_account: str | None = None
    _mobile_code_key: str | None = None
    _mobile_error: str | None = None
    _mobile_password_allowed: bool = False

    # ------------------------------------------------------------------
    # 宿主钩子（由 ConfigFlow / OptionsFlowHandler 实现）
    # ------------------------------------------------------------------

    def _mobile_auth_token(self) -> str | None:
        """返回当前授权码。"""
        raise NotImplementedError

    def _mobile_machine_id(self) -> str | None:
        """返回当前 machineId（后端 iOS 设备行键）。"""
        raise NotImplementedError

    async def _async_mobile_invalid_token(self) -> FlowResult:
        """授权码无效时的展示（配置流回授权码输入页，选项流回数据源页）。"""
        raise NotImplementedError

    async def _async_mobile_login_complete(self, account: str) -> FlowResult:
        """登录成功 / 已有档案后的收尾（配置流进入户号选择，选项流写库切换）。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 公共工具
    # ------------------------------------------------------------------

    async def _build_mobile_client(self):
        """构造手机App数据源的临时客户端（登录/档案操作）。"""
        from .client import MobileIosApiClient
        client = MobileIosApiClient(
            self._mobile_auth_token(),
            async_get_clientsession(self.hass),
            self.hass,
            machine_id=self._mobile_machine_id(),
        )
        # 必须挂本地库：登录会话真值在 HA 本地（shaobor_mobile_auth_store 表），
        # 否则每步新建的客户端互不相通——短信登录的 session 存不下来，
        # 下一步 _async_mobile_login_complete 查档案又是未登录状态。
        db = await self._mobile_flow_db()
        if db is not None:
            client.set_db(db)
        return client

    async def _mobile_flow_db(self):
        """配置/选项流共用的本地库（hass.data 缓存；首次安装需建表）。"""
        from ..const import DOMAIN

        store = self.hass.data.setdefault(DOMAIN, {})
        db = store.get("mobile_flow_db")
        if db is None:
            try:
                from ..helpers.database import StateGridDatabase

                db = StateGridDatabase(
                    self.hass,
                    self.hass.config.path(
                        ".storage", DOMAIN, "shaobor_electricity.db"
                    ),
                )
                await db.async_init()
                store["mobile_flow_db"] = db
            except Exception as err:  # noqa: BLE001 建库失败不阻断登录流程
                _LOGGER.warning("[手机源登录] 本地库不可用: %s", err)
                store["mobile_flow_db"] = False
                return None
        return db or None

    async def _mobile_client_with_session(self):
        """构造客户端并从本地库恢复会话（配置流跨步骤的会话载体）。"""
        client = await self._build_mobile_client()
        if getattr(client, "_db", None):
            try:
                await client._load_local_session()
            except Exception as err:  # noqa: BLE001 恢复失败按未登录处理
                _LOGGER.debug("[手机源登录] 本地会话恢复失败: %s", err)
        return client

    # ------------------------------------------------------------------
    # 登录闸门
    # ------------------------------------------------------------------

    async def async_step_mobile_login_gate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """手机源登录闸门：先查授权码对应 machineId 的登录档案。

        - 已有登录档案且户号列表非空 → 直接完成，无需登录；
        - 无登录档案（首次） → 仅短信登录；
        - 有档案但会话失效/户号为空 → 短信 + 密码登录均可选。
        手机源无扫码登录选项。
        """
        errors: dict[str, str] = {}
        client = await self._mobile_client_with_session()
        try:
            if not await client.validate_token():
                _LOGGER.warning("[手机源登录] 授权码校验失败")
                return await self._async_mobile_invalid_token()
            profile = await client.async_get_profile()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("[手机源登录] 中转后端不可达: %s", err)
            errors["base"] = "backend_unreachable"
            return await self.async_step_mobile_login_method(errors)

        account = profile.get("account") or {}
        users = [u for u in (account.get("powerUsers") or []) if isinstance(u, dict)]
        has_login_record = bool(account.get("mobile"))

        # 已有有效登录档案 → 免登录直接完成
        if has_login_record and users:
            return await self._async_mobile_login_complete(account.get("mobile") or "")

        # 未登录：首次（无任何记录）仅短信；有记录才放开密码登录
        self._mobile_password_allowed = has_login_record
        return await self.async_step_mobile_login_method(errors)

    # ------------------------------------------------------------------
    # 登录方式选择
    # ------------------------------------------------------------------

    async def async_step_mobile_login_method(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """手机源登录方式选择：短信登录始终可用；密码登录仅限已有登录记录的设备。"""
        errors = errors or {}
        # 注意：内部以 step(errors) 形式传错误字典，必须按键存在性判提交
        if isinstance(user_input, dict) and user_input.get("mobile_login_method"):
            method = user_input.get("mobile_login_method")
            if method == "password":
                return await self.async_step_mobile_password()
            return await self.async_step_mobile_sms()

        # 首次登录必须短信验证（设备指纹进信任名单后密码登录才可用）
        if self._mobile_password_allowed:
            options = [
                {"value": "sms", "label": "短信验证码登录"},
                {"value": "password", "label": "账号密码登录"},
            ]
            description = "手机App源登录。该设备已验证过，可直接使用账号密码或短信验证码登录。"
        else:
            options = [{"value": "sms", "label": "短信验证码登录"}]
            description = (
                "手机App源登录。首次登录必须使用短信验证码（验证通过后设备进入信任名单），"
                "之后才可直接使用账号密码登录。"
            )

        return self.async_show_form(
            step_id="mobile_login_method",
            data_schema=vol.Schema(
                {
                    vol.Required("mobile_login_method", default="sms"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={"description": description},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 短信登录（两步）
    # ------------------------------------------------------------------

    async def async_step_mobile_sms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """手机源短信登录第一步：输入手机号并发送验证码。"""
        from .client import StateGridAuthError, StateGridConnectionError

        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("back_to_login_method"):
                return await self.async_step_mobile_login_method()
            account = str(user_input.get("account", "")).strip()
            if account:
                client = await self._build_mobile_client()
                try:
                    self._mobile_account = account
                    self._mobile_code_key = await client.request_sms(account)
                    return await self.async_step_mobile_sms_code()
                except StateGridAuthError as err:
                    errors["base"] = "sms_send_failed"
                    self._mobile_error = str(err)
                except StateGridConnectionError as err:
                    errors["base"] = "backend_unreachable"
                    self._mobile_error = str(err)
            else:
                errors["base"] = "mobile_form_incomplete"
        return self.async_show_form(
            step_id="mobile_sms",
            data_schema=vol.Schema(
                {
                    # Optional：避免勾选"返回"时被前端必填校验拦截
                    vol.Optional("account", default=self._mobile_account or ""): str,
                    vol.Optional("back_to_login_method", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"error": self._mobile_error or ""},
        )

    async def async_step_mobile_sms_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """手机源短信登录第二步：输入验证码完成登录。"""
        from .client import StateGridAuthError, StateGridConnectionError

        errors: dict[str, str] = {}
        if user_input is not None:
            code = str(user_input.get("code", "")).strip()
            if code and self._mobile_account and self._mobile_code_key:
                client = await self._build_mobile_client()
                try:
                    await client.sms_login(
                        self._mobile_account, code, self._mobile_code_key
                    )
                    self._login_method = LOGIN_METHOD_SMS
                    return await self._async_mobile_login_complete(self._mobile_account)
                except StateGridAuthError as err:
                    errors["base"] = "sms_login_failed"
                    self._mobile_error = str(err)
                except StateGridConnectionError as err:
                    errors["base"] = "backend_unreachable"
                    self._mobile_error = str(err)
        return self.async_show_form(
            step_id="mobile_sms_code",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
            description_placeholders={
                "account": self._mobile_account or "",
                "error": self._mobile_error or "",
            },
        )

    # ------------------------------------------------------------------
    # 密码登录（仅限已信任设备）
    # ------------------------------------------------------------------

    async def async_step_mobile_password(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """手机源密码登录：仅限后端已有登录记录（设备已信任）的授权码使用。"""
        from .client import StateGridAuthError, StateGridConnectionError

        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("back_to_login_method"):
                return await self.async_step_mobile_login_method()
            account = str(user_input.get("account", "")).strip()
            password = str(user_input.get("password", "") or "")
            if account and password:
                client = await self._build_mobile_client()
                try:
                    await client.password_login(account, password)
                    self._login_method = LOGIN_METHOD_PASSWORD
                    return await self._async_mobile_login_complete(account)
                except StateGridAuthError as err:
                    msg = str(err)
                    if "验证" in msg or "风控" in msg or "滑块" in msg:
                        # 未信任设备密码登录被拒：提示改走短信
                        errors["base"] = "password_requires_sms"
                    else:
                        errors["base"] = "invalid_auth"
                    self._mobile_error = msg
                except StateGridConnectionError as err:
                    errors["base"] = "backend_unreachable"
                    self._mobile_error = str(err)
            else:
                errors["base"] = "mobile_form_incomplete"
        return self.async_show_form(
            step_id="mobile_password",
            data_schema=vol.Schema(
                {
                    # Optional：避免勾选"返回"时被前端必填校验拦截
                    vol.Optional("account", default=self._mobile_account or ""): str,
                    vol.Optional("password", default=""): str,
                    vol.Optional("back_to_login_method", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"error": self._mobile_error or ""},
        )

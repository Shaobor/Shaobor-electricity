"""Config flow for shaobor_electricity."""
import logging
from typing import Any

import voluptuous as vol  # type: ignore[import-untyped]

from homeassistant import config_entries  # type: ignore[import-untyped]
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry  # type: ignore[import-untyped]
from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]
from homeassistant.data_entry_flow import FlowResult  # type: ignore[import-untyped]

from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import-untyped]
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode  # type: ignore[import-untyped]

from .api import Shaobor95598ApiClient, StateGridAuthError, STORAGE_KEY, STORAGE_VERSION
from .storage import AuthStore
from .login_methods import QRCodeLoginHandler, PasswordLoginHandler, SMSLoginHandler

from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_LOGIN_METHOD,
    LOGIN_METHOD_PASSWORD,
    LOGIN_METHOD_QRCODE,
    LOGIN_METHOD_SMS,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_AUTO_RELOGIN,
    CONF_PHONE_NUMBER,
    CONF_SMS_CODE,
    CONF_USER_TOKEN,
    CONF_USER_ID,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_POWER_USER_LIST,
    CONF_SELECTED_ACCOUNT_INDEX,
    CONF_LOGIN_ACCOUNT,
    CONF_USER_INFO,
    CONF_BILLING_MODE,
    BILLING_STANDARD_YEAR_LADDER_TOU,
    BILLING_STANDARD_YEAR_LADDER,
    BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE,
    BILLING_STANDARD_MONTH_LADDER_TOU,
    BILLING_STANDARD_MONTH_LADDER,
    BILLING_STANDARD_AVERAGE,
    CONF_LADDER_LEVEL_1,
    CONF_LADDER_LEVEL_2,
    CONF_LADDER_PRICE_1,
    CONF_LADDER_PRICE_2,
    CONF_LADDER_PRICE_3,
    CONF_YEAR_LADDER_START,
    CONF_PRICE_TIP,
    CONF_PRICE_PEAK,
    CONF_PRICE_FLAT,
    CONF_PRICE_VALLEY,
    CONF_AVERAGE_PRICE,
    CONF_LADDER_PRICE_1_TIP,
    CONF_LADDER_PRICE_1_PEAK,
    CONF_LADDER_PRICE_1_FLAT,
    CONF_LADDER_PRICE_2_TIP,
    CONF_LADDER_PRICE_2_PEAK,
    CONF_LADDER_PRICE_2_FLAT,
    CONF_LADDER_PRICE_3_TIP,
    CONF_LADDER_PRICE_3_PEAK,
    CONF_LADDER_PRICE_3_FLAT,
)
try:
    import pyqrcode  # type: ignore[import-untyped]
    HAS_PYQRCODE = True
except ImportError:
    HAS_PYQRCODE = False
    pyqrcode = None  # type: ignore[assignment]
import io
import base64

_LOGGER = logging.getLogger(__name__)


class InvalidAuthToken(Exception):
    """Error to indicate we cannot authorize."""


async def validate_token(hass: HomeAssistant, token: str) -> None:
    """Validate the user input token."""
    session = async_get_clientsession(hass)
    api = Shaobor95598ApiClient(token=token, session=session)
    valid = await api.validate_token()
    if not valid:
        raise InvalidAuthToken

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shaobor_95598."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._auth_token: str | None = None
        self._login_method: str | None = None
        self._phone_number: str | None = None
        self._api: Shaobor95598ApiClient | None = None
        self._store: AuthStore | None = None
        self._qr_serial: str | None = None
        self._qr_image_md: str | None = None
        self._pending_entry_data: dict[str, Any] | None = None  # 登录成功后待创建 entry 的数据（户号选择前）
        self._skip_auto_load_token: bool = False  # 是否跳过自动加载 token（用于重新配置授权码）
        
        # 登录处理器（延迟初始化）
        self._qrcode_handler: QRCodeLoginHandler | None = None
        self._password_handler: PasswordLoginHandler | None = None
        self._sms_handler: SMSLoginHandler | None = None
        
        # 登录处理器（延迟初始化）
        self._qrcode_handler: QRCodeLoginHandler | None = None
        self._password_handler: PasswordLoginHandler | None = None
        self._sms_handler: SMSLoginHandler | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    def _get_store(self) -> AuthStore:
        """Get or create the auth Store."""
        if self._store is None:
            self._store = AuthStore(self.hass, STORAGE_VERSION, STORAGE_KEY)
        return self._store

    async def _get_stored_token(self) -> str | None:
        """Get token from persistent storage."""
        try:
            data = await self._get_store().async_load()
            return data.get("token") if isinstance(data, dict) else None
        except Exception:
            return None

    async def _get_stored_auth(self) -> dict[str, Any] | None:
        """Get full auth session from Store (Node-RED 全局变量 style)."""
        try:
            data = await self._get_store().async_load()
            return data if isinstance(data, dict) and data.get("token") else None
        except Exception:
            return None

    async def _save_token(self, token: str) -> None:
        """Save token to persistent storage."""
        await self._get_store().async_save({"token": token})

    async def _save_auth_store(
        self,
        *,
        token: str,
        user_token: str,
        user_id: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        power_user_list: list | None = None,
        login_account: str | None = None,
        user_info: Any = None,
        username: str | None = None,
        password: str | None = None,
        auto_relogin: bool = False,
    ) -> None:
        """Save all key values to Store when bizrt.token obtained (登录成功)."""
        payload: dict[str, Any] = {
            "token": token,
            "user_token": user_token,
            "user_id": user_id or "",
            "access_token": access_token or "",
            "refresh_token": refresh_token or "",
            "power_user_list": power_user_list or [],
            "login_account": login_account or "",
            "user_info": user_info,
            "username": username or "",
            "password": password or "",
            "auto_relogin": auto_relogin,
        }
        await self._get_store().async_save(payload)

    @staticmethod
    def _get_cons_no_from_entry_data(data: dict[str, Any]) -> str:
        """从 entry data 中取出当前所选户号（仅数字部分，用于条目标题与去重）."""
        pl = data.get(CONF_POWER_USER_LIST) or []
        idx = min(int(data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)), len(pl) - 1) if pl else -1
        if idx < 0 or not pl:
            return ""
        raw = pl[idx].get("consNo_dst") or pl[idx].get("consNoDst") or pl[idx].get("consNo") or ""
        return str(raw).split("-")[0].strip() if raw else ""

    async def _finish_entry(self, title: str, data: dict[str, Any]) -> FlowResult:
        """创建或更新配置项：条目名用户号；若该户号已添加则提示已添加."""        # 生成唯一 ID 和名称
        cons_no = self._get_cons_no_from_entry_data(data)
        entry_title = cons_no or title or "Shaobor_95598"
        if self.context.get("source") == SOURCE_REAUTH:
            entry_id = self.context.get("entry_id")
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                self.hass.config_entries.async_update_entry(entry, data=data)
                
                # 关键修复：强制保存最新认证信息到全局 Store，供其他联动户号读取
                await self._save_auth_store(
                    token=data.get(CONF_AUTH_TOKEN),
                    user_token=data.get(CONF_USER_TOKEN),
                    user_id=data.get(CONF_USER_ID),
                    access_token=data.get(CONF_ACCESS_TOKEN),
                    refresh_token=data.get(CONF_REFRESH_TOKEN),
                    power_user_list=data.get(CONF_POWER_USER_LIST),
                    login_account=data.get(CONF_LOGIN_ACCOUNT),
                    user_info=data.get(CONF_USER_INFO),
                )
                
                # 清除全局重连标志位，允许后续再次触发提醒
                auth_token = data.get(CONF_AUTH_TOKEN)
                if auth_token:
                    reauth_key = f"reauth_active_{auth_token}"
                    if DOMAIN in self.hass.data and reauth_key in self.hass.data[DOMAIN]:
                        self.hass.data[DOMAIN].pop(reauth_key)
                
                # 重新加载本项目下的所有集成条目，实现联动刷新
                # 这样用户只需要在一个条目上重新配置，其他同账号条目也会自动恢复
                login_account = data.get(CONF_LOGIN_ACCOUNT)
                for other_entry in self.hass.config_entries.async_entries(DOMAIN):
                    # 通过 auth_token 或 login_account (手机号) 匹配联动
                    if (auth_token and other_entry.data.get(CONF_AUTH_TOKEN) == auth_token) or \
                       (login_account and other_entry.data.get(CONF_LOGIN_ACCOUNT) == login_account):
                        if other_entry.entry_id != entry_id:
                            _LOGGER.info("检测到同账号条目，自动同步并刷新: %s", other_entry.title)
                            self.hass.async_create_task(
                                self.hass.config_entries.async_reload(other_entry.entry_id)
                            )
                
                return self.async_abort(reason="reauth_successful")
        # 检查该户号是否已被添加（含旧版未设 unique_id 的条目）
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_POWER_USER_LIST) and self._get_cons_no_from_entry_data(entry.data) == cons_no:
                return self.async_abort(reason="already_configured")
        
        # 新添加集成时，确保 Store 中保存的是最新的登录数据
        # 这样可以避免使用旧的、已失效的缓存数据
        await self._save_auth_store(
            token=data.get(CONF_AUTH_TOKEN, ""),
            user_token=data.get(CONF_USER_TOKEN, ""),
            user_id=data.get(CONF_USER_ID),
            access_token=data.get(CONF_ACCESS_TOKEN),
            refresh_token=data.get(CONF_REFRESH_TOKEN),
            power_user_list=data.get(CONF_POWER_USER_LIST),
            login_account=data.get(CONF_LOGIN_ACCOUNT),
            username=data.get(CONF_USERNAME),
            password=data.get(CONF_PASSWORD),
            auto_relogin=data.get(CONF_AUTO_RELOGIN, False),
        )
        
        await self.async_set_unique_id(cons_no or entry_title)
        return self.async_create_entry(title=entry_title, data=data)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Reauth 时先执行刷新 token：优先尝试从共享 Store 静默修复，失败才要求重新登录."""
        self._auth_token = entry_data.get(CONF_AUTH_TOKEN) or ""
        
        # 【静默修复】首先检查是否有其他同账号条目已经更新了全局 AuthStore
        store = AuthStore(self.hass, STORAGE_VERSION, STORAGE_KEY)
        stored = await store.async_load()
        if stored and isinstance(stored, dict) and stored.get("access_token"):
            current_login = entry_data.get(CONF_LOGIN_ACCOUNT)
            stored_login = stored.get("login_account")
            
            # 如果账号匹配，且存储的 token 看起来比现在的新（或至少存在）
            if current_login and stored_login == current_login:
                _LOGGER.info("检测到共享保险箱中有最新授权，尝试为 %s 执行静默修复", entry_data.get(CONF_AUTH_TOKEN))
                temp_api = Shaobor95598ApiClient(
                    token=self._auth_token,
                    session=async_get_clientsession(self.hass),
                )
                # 手动注入共享的 access_token 进行验证
                temp_api._access_token = stored.get("access_token")
                
                if await temp_api.validate_token():
                    _LOGGER.info("静默修复成功！已自动同步授权。")
                    # 直接合并数据并保存，跳过后续步骤
                    new_data = {
                        **entry_data,
                        CONF_USER_TOKEN: stored.get("user_token"),
                        CONF_USER_ID: stored.get("user_id"),
                        CONF_ACCESS_TOKEN: stored.get("access_token"),
                        CONF_REFRESH_TOKEN: stored.get("refresh_token"),
                        CONF_POWER_USER_LIST: stored.get("power_user_list"),
                    }
                    return await self._finish_entry(None, new_data)

        if not self._auth_token:
            return self.async_abort(reason="missing_token")
        self._api = Shaobor95598ApiClient(
            token=self._auth_token,
            session=async_get_clientsession(self.hass),
        )
        try:
            await self._api.initialize()
        except Exception:
            return self.async_abort(reason="invalid_token")
        # 先尝试刷新 token（authorize + getWebToken），能返回 access_token 即视为有效
        user_token = entry_data.get(CONF_USER_TOKEN) or ""
        if user_token:
            self._api.load_auth_state(
                user_token=user_token,
                user_id=entry_data.get(CONF_USER_ID),
                power_user_list=entry_data.get(CONF_POWER_USER_LIST),
                selected_account_index=entry_data.get(CONF_SELECTED_ACCOUNT_INDEX, 0),
                login_account=entry_data.get(CONF_LOGIN_ACCOUNT),
            )
            try:
                tokens = await self._api.refresh_access_token()
                if tokens.get("access_token"):
                    entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                    if entry:
                        # 保留原有的户号选择信息
                        new_data = {
                            **entry.data,
                            CONF_ACCESS_TOKEN: tokens["access_token"],
                            CONF_REFRESH_TOKEN: tokens.get("refresh_token") or entry.data.get(CONF_REFRESH_TOKEN) or "",
                            CONF_SELECTED_ACCOUNT_INDEX: entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0),
                        }
                        self.hass.config_entries.async_update_entry(entry, data=new_data)
                        
                        # 保存到 Store 时也保留户号选择信息
                        stored_auth = await self._get_stored_auth()
                        await self._save_auth_store(
                            token=self._auth_token,
                            user_token=user_token,
                            user_id=entry_data.get(CONF_USER_ID),
                            access_token=tokens["access_token"],
                            refresh_token=tokens.get("refresh_token"),
                            power_user_list=entry_data.get(CONF_POWER_USER_LIST),
                            login_account=entry_data.get(CONF_LOGIN_ACCOUNT),
                            username=stored_auth.get("username") if stored_auth else "",
                            password=stored_auth.get("password") if stored_auth else "",
                            auto_relogin=stored_auth.get("auto_relogin", False) if stored_auth else False,
                        )
                        # 重新加载集成以应用新的 token
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reauth_successful")
            except Exception:
                pass
        return await self.async_step_login_method()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Auth Token Verification."""
        errors: dict[str, str] = {}
        try:
            return await self._async_step_user_impl(user_input, errors)
        except Exception as err:  # pylint: disable=broad-except
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_AUTH_TOKEN): str}),
                errors=errors,
            )

    async def _async_step_user_impl(
        self, user_input: dict[str, Any] | None, errors: dict[str, str]
    ) -> FlowResult:
        """Implementation of user step to allow exception handling."""
        # 尝试从 Store 读取已保存的 token 用于预填充
        stored_token = await self._get_stored_token()
        # 预填逻辑：优先使用用户刚才输入的值，其次使用存储的值
        default_token = (user_input or {}).get(CONF_AUTH_TOKEN) or stored_token or ""

        # Try to auto-load token if user hasn't input anything yet
        if user_input is None:
            # 如果设置了跳过自动加载标志，则重置标志并直接显示表单（带预填充）
            if self._skip_auto_load_token:
                self._skip_auto_load_token = False
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(CONF_AUTH_TOKEN, default=default_token): str
                    }),
                    errors=errors,
                )
            
            if stored_token:
                try:
                    await validate_token(self.hass, stored_token)
                    self._auth_token = stored_token
                    self._api = Shaobor95598ApiClient(
                        token=self._auth_token,
                        session=async_get_clientsession(self.hass),
                    )
                    await self._api.initialize()
                    # 登录有效时，若 Store 中已有户号列表，尝试校验会话并进入选择户号（或仅一户则直接创建），跳过「选择登录方式」
                    stored_auth = await self._get_stored_auth()
                    if stored_auth and isinstance(stored_auth.get("power_user_list"), list) and len(stored_auth["power_user_list"]) > 0:
                        user_token = stored_auth.get("user_token")
                        if user_token:
                            self._api.load_auth_state(
                                user_token=user_token,
                                user_id=stored_auth.get("user_id"),
                                access_token=stored_auth.get("access_token"),
                                refresh_token=stored_auth.get("refresh_token"),
                                power_user_list=stored_auth.get("power_user_list"),
                                login_account=stored_auth.get("login_account"),
                            )
                            # 尝试验证会话是否依然有效
                            try:
                                await self._api.refresh_access_token()
                                # 验证成功，准备跳转
                                power_list = stored_auth["power_user_list"]
                                entry_data = {
                                    CONF_AUTH_TOKEN: self._auth_token,
                                    CONF_LOGIN_METHOD: self._login_method or LOGIN_METHOD_PASSWORD,
                                    CONF_USER_TOKEN: user_token,
                                    CONF_USER_ID: stored_auth.get("user_id") or "",
                                    CONF_ACCESS_TOKEN: self._api._access_token or "",
                                    CONF_REFRESH_TOKEN: self._api._refresh_token or "",
                                    CONF_POWER_USER_LIST: power_list,
                                    CONF_LOGIN_ACCOUNT: stored_auth.get("login_account") or "",
                                }
                                if len(power_list) == 1:
                                    entry_data[CONF_SELECTED_ACCOUNT_INDEX] = 0
                                    self._pending_entry_data = {**entry_data, "_title": "Shaobor_95598"}
                                    return await self.async_step_billing_mode()
                                self._pending_entry_data = {**entry_data, "_title": "Shaobor_95598"}
                                return await self.async_step_select_account()
                            except Exception as refresh_err:
                                # 刷新失败说明登录已过期，继续走常规流程（选择登录方式）
                                _LOGGER.debug("[配置流程] 自动跳转前校验失败，需要重新登录: %s", refresh_err)
                                pass
                        
                    return await self.async_step_login_method()
                except Exception:
                    pass

        if user_input is not None:
            try:
                # Validate the token
                token = user_input[CONF_AUTH_TOKEN]
                await validate_token(self.hass, token)
                
                # Store it globally for future setups
                await self._save_token(token)
                
                # Store the token safely and initialize instance API
                self._auth_token = token
                self._api = Shaobor95598ApiClient(
                    token=self._auth_token, 
                    session=async_get_clientsession(self.hass)
                )
                await self._api.initialize()
                
                # Validation successful, move to next step
                return await self.async_step_login_method()
                
            except InvalidAuthToken:
                errors["base"] = "invalid_token"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_TOKEN, default=default_token): str,
                }
            ),
            errors=errors,
        )

    async def async_step_login_method(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle choice of login method."""
        if user_input is not None:
            self._login_method = user_input[CONF_LOGIN_METHOD]
            if self._login_method == LOGIN_METHOD_PASSWORD:
                return await self.async_step_password()
            elif self._login_method == LOGIN_METHOD_QRCODE:
                return await self.async_step_qrcode()
            elif self._login_method == LOGIN_METHOD_SMS:
                return await self.async_step_sms()
            elif self._login_method == "reconfigure_token":
                # 重新配置授权码：清空当前 token 和 API，设置标志跳过自动加载，返回到输入 token 步骤
                self._auth_token = None
                self._api = None
                self._skip_auto_load_token = True  # 设置标志，跳过自动加载 token
                return await self.async_step_user()

        options = [{"value": LOGIN_METHOD_PASSWORD, "label": "password"}]
        if HAS_PYQRCODE:
            options.append({"value": LOGIN_METHOD_QRCODE, "label": "qrcode"})
        options.append({"value": LOGIN_METHOD_SMS, "label": "sms"})
        options.append({"value": "reconfigure_token", "label": "reconfigure_token"})
        default = LOGIN_METHOD_PASSWORD
        return self.async_show_form(
            step_id="login_method",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN_METHOD, default=default): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            translation_key="login_method",
                        )
                    )
                }
            ),
        )

    def _get_existing_cons_nos(self) -> set[str]:
        """Return set of cons_nos already configured in existing entries."""
        existing: set[str] = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            cons_no = self._get_cons_no_from_entry_data(entry.data)
            if cons_no:
                existing.add(cons_no)
        return existing

    def _build_account_options(self, power_user_list: list) -> list[dict[str, str]]:
        """Build options for 户号 selector：只显示户号（前面的数字），已添加户号追加标记."""
        existing = self._get_existing_cons_nos()
        options = []
        for i, item in enumerate(power_user_list or []):
            if not isinstance(item, dict):
                continue
            raw = item.get("consNo_dst") or item.get("consNoDst") or item.get("consNo") or ""
            # 只取第一个 “-” 前面的户号部分，后面的加密串不显示
            cons_no = str(raw).split("-")[0].strip() if raw else ""
            label = cons_no if cons_no else f"户号 #{i+1}"
            if cons_no and cons_no in existing:
                label = f"{label}（已添加）"
            options.append({"value": str(i), "label": label})
        if not options:
            options.append({"value": "0", "label": "默认户号"})
        return options

    async def async_step_select_account(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle 户号选择 - 登录成功后选择要监控的户号."""
        errors: dict[str, str] = {}
        if self._pending_entry_data is None:
            return self.async_abort(reason="unknown")
        pending = self._pending_entry_data
        power_list = pending.get(CONF_POWER_USER_LIST) or []
        if user_input is not None:
            idx = int(user_input.get(CONF_SELECTED_ACCOUNT_INDEX, "0"))
            idx = max(0, min(idx, len(power_list) - 1)) if power_list else 0
            # 计算当前选择的户号，禁止选择已添加过的户号
            raw = ""
            if power_list and 0 <= idx < len(power_list) and isinstance(power_list[idx], dict):
                raw = (
                    power_list[idx].get("consNo_dst")
                    or power_list[idx].get("consNoDst")
                    or power_list[idx].get("consNo")
                    or ""
                )
            cons_no = str(raw).split("-")[0].strip() if raw else ""
            if cons_no and cons_no in self._get_existing_cons_nos():
                errors["base"] = "already_configured"
            else:
                entry_data = {k: v for k, v in pending.items() if k != "_title"}
                entry_data[CONF_SELECTED_ACCOUNT_INDEX] = idx
                # 选择户号后，进入计费模式配置
                self._pending_entry_data = {**entry_data, "_title": pending.get("_title", "Shaobor_95598")}
                return await self.async_step_billing_mode()
        options = self._build_account_options(power_list)
        return self.async_show_form(
            step_id="select_account",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SELECTED_ACCOUNT_INDEX,
                        default="0",
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            translation_key="select_account",
                        )
                    )
                },
            ),
            errors=errors,
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle password login."""
        errors: dict[str, str] = {}
        
        # 在 reauth 流程中，尝试从 Store 预填充账号密码和自动重新登录状态
        default_username = ""
        default_password = ""
        default_auto_relogin = False
        
        if user_input is None and self.context.get("source") == SOURCE_REAUTH:
            try:
                stored_auth = await self._get_stored_auth()
                if stored_auth:
                    default_username = stored_auth.get("username", "")
                    default_password = stored_auth.get("password", "")
                    default_auto_relogin = stored_auth.get("auto_relogin", False)
            except Exception:
                pass
        
        if user_input is not None:
            # 检查是否点击了「返回选择登录方式」
            if user_input.get("back_to_login_method"):
                return await self.async_step_login_method()
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            if not username or not password:
                if not username: errors[CONF_USERNAME] = "required"
                if not password: errors[CONF_PASSWORD] = "required"
            else:
                auto_relogin = user_input.get(CONF_AUTO_RELOGIN, False)
                try:
                    result = await self._api.login_with_password(username, password)
                    # 确保 result 是字典类型
                    if not isinstance(result, dict):
                        _LOGGER.error("[配置流程] login_with_password 返回了非字典类型: %s (类型: %s)", result, type(result))
                        errors["base"] = "login_error"
                        errors["error"] = f"Unexpected result type: {type(result).__name__}"
                    elif result.get("success"):
                        data = result.get("data", {})
                        # 验证能否成功获取电费数据，成功才创建配置
                        try:
                            await self._api.get_electricity_data()
                        except StateGridAuthError:
                            errors["base"] = "login_verify_failed"
                        except Exception:
                            errors["base"] = "login_verify_failed"
                        else:
                            # 登录成功(bizrt.token已获取)，保存所有关键值到 Store(全局变量方式)
                            await self._save_auth_store(
                                token=self._auth_token,
                                user_token=data.get("user_token", ""),
                                user_id=data.get("user_id"),
                                access_token=data.get("access_token"),
                                refresh_token=data.get("refresh_token"),
                                power_user_list=data.get("power_user_list"),
                                login_account=data.get("login_account"),
                                user_info=data.get("user_info"),
                                username=username if auto_relogin else "",
                                password=password if auto_relogin else "",
                                auto_relogin=auto_relogin,
                            )
                            entry_data = {
                                CONF_AUTH_TOKEN: self._auth_token,
                                CONF_LOGIN_METHOD: self._login_method,
                                CONF_USERNAME: username,
                                CONF_PASSWORD: password if auto_relogin else "",  # 只有勾选自动登录才保存密码
                                CONF_AUTO_RELOGIN: auto_relogin,
                                CONF_USER_TOKEN: data.get("user_token"),
                                CONF_USER_ID: data.get("user_id"),
                                CONF_ACCESS_TOKEN: data.get("access_token"),
                                CONF_REFRESH_TOKEN: data.get("refresh_token"),
                                CONF_POWER_USER_LIST: data.get("power_user_list"),
                                CONF_LOGIN_ACCOUNT: data.get("login_account"),
                            }
                            power_list = data.get("power_user_list") or []
                            
                            # 如果是 reauth 流程,使用原有的户号选择
                            if self.context.get("source") == SOURCE_REAUTH:
                                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                                if entry:
                                    selected_index = entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)
                                    entry_data[CONF_SELECTED_ACCOUNT_INDEX] = selected_index
                                    
                                    # 保留原有的计费配置
                                    for key in [CONF_BILLING_MODE, CONF_LADDER_LEVEL_1, CONF_LADDER_LEVEL_2,
                                               CONF_LADDER_PRICE_1, CONF_LADDER_PRICE_2, CONF_LADDER_PRICE_3,
                                               CONF_PRICE_TIP, CONF_PRICE_PEAK, CONF_PRICE_FLAT, CONF_PRICE_VALLEY,
                                               CONF_AVERAGE_PRICE, CONF_YEAR_LADDER_START]:
                                        if key in entry.data:
                                            entry_data[key] = entry.data[key]
                                    
                                    self.hass.config_entries.async_update_entry(entry, data=entry_data)
                                    
                                    # 重新加载集成以应用新的认证信息
                                    await self.hass.config_entries.async_reload(entry.entry_id)
                                    
                                    return self.async_abort(reason="reauth_successful")
                            
                            # 新配置流程:进入户号选择或计费模式配置
                            if len(power_list) > 1:
                                self._pending_entry_data = {**entry_data, "_title": f"Shaobor_95598 ({username})"}
                                return await self.async_step_select_account()
                            entry_data[CONF_SELECTED_ACCOUNT_INDEX] = 0
                            self._pending_entry_data = {**entry_data, "_title": f"Shaobor_95598 ({username})"}
                            return await self.async_step_billing_mode()
                    else:
                        if "captcha" in str(result.get("message", "")).lower():
                            errors["base"] = "password_not_supported"
                        else:
                            errors["base"] = "invalid_auth"
                            errors["reason"] = result.get("message", "unknown")
                except Exception as err:
                    # 记录完整的异常信息到日志
                    _LOGGER.error("[配置流程] 登录异常: %s", err, exc_info=True)
                    err_str = str(err)
                    if "Slider API" in err_str or "x coordinate" in err_str:
                        errors["base"] = "slider_failed"
                    elif "Captcha missing" in err_str or "canvasSrc" in err_str:
                        errors["base"] = "captcha_parse_failed"
                    elif "c44/f06" in err_str or "c44/f05" in err_str:
                        errors["base"] = "login_verify_failed"
                    else:
                        errors["base"] = "login_error"
                        errors["error"] = err_str

        placeholders = {}
        if errors.get("error"):
            placeholders["error"] = errors["error"]

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME, default=default_username): str,
                    vol.Optional(CONF_PASSWORD, default=default_password): str,
                    vol.Optional(CONF_AUTO_RELOGIN, default=default_auto_relogin): bool,
                    vol.Optional("back_to_login_method", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_billing_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle 计费模式选择."""
        if user_input is not None:
            billing_mode = user_input[CONF_BILLING_MODE]
            if self._pending_entry_data:
                self._pending_entry_data[CONF_BILLING_MODE] = billing_mode
            # 根据计费模式跳转到对应的价格配置页面
            if billing_mode == BILLING_STANDARD_YEAR_LADDER_TOU:
                return await self.async_step_year_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_YEAR_LADDER:
                return await self.async_step_year_ladder_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE:
                return await self.async_step_month_ladder_tou_variable_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU:
                return await self.async_step_month_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER:
                return await self.async_step_month_ladder_config()
            elif billing_mode == BILLING_STANDARD_AVERAGE:
                return await self.async_step_average_config()

        billing_options = [
            {"value": BILLING_STANDARD_YEAR_LADDER_TOU, "label": "年阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_YEAR_LADDER, "label": "年阶梯计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE, "label": "月阶梯峰平谷变动价格计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU, "label": "月阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER, "label": "月阶梯计费"},
            {"value": BILLING_STANDARD_AVERAGE, "label": "平均单价计费"},
        ]
        
        return self.async_show_form(
            step_id="billing_mode",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BILLING_MODE, default=BILLING_STANDARD_YEAR_LADDER): SelectSelector(
                        SelectSelectorConfig(
                            options=billing_options,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_year_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯峰平谷计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        # 根据户号自动获取地区电价配置
        from .regional_prices import get_region_price_config, get_region_name
        
        cons_no = ""
        if self._pending_entry_data:
            power_list = self._pending_entry_data.get(CONF_POWER_USER_LIST) or []
            idx = self._pending_entry_data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)
            if power_list and 0 <= idx < len(power_list) and isinstance(power_list[idx], dict):
                raw = (
                    power_list[idx].get("consNo_dst")
                    or power_list[idx].get("consNoDst")
                    or power_list[idx].get("consNo")
                    or ""
                )
                cons_no = str(raw).split("-")[0].strip() if raw else ""
        
        # 获取地区配置
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        # 设置默认值
        if regional_config:
            default_level_1 = regional_config["ladder_level_1"]
            default_level_2 = regional_config["ladder_level_2"]
            
            # 通用默认电价：使用该地区的第一档基础电价作为默认值，用户在此基础上自行微调
            base_price = regional_config.get("ladder_price_1", 0.51)
            default_price_tip = base_price
            default_price_peak = base_price
            default_price_flat = base_price
            default_price_valley = base_price
            
            description = f"已自动识别地区：{region_name}\n以下为该地区的默认标准，请根据您的实际电费账单微调电价。"
        else:
            default_level_1 = 0
            default_level_2 = 0
            default_price_tip = 0.0
            default_price_peak = 0.0
            default_price_flat = 0.0
            default_price_valley = 0.0
            description = "【注意】无法自动识别您的地区，默认值已重置为 0。请手动输入或联系管理员添加您的地区电价数据。"

        return self.async_show_form(
            step_id="year_ladder_tou_config",
            description_placeholders={"description": description},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=default_level_1): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=default_level_2): int,
                    vol.Required(CONF_PRICE_TIP, default=default_price_tip): vol.Coerce(float),
                    vol.Required(CONF_PRICE_PEAK, default=default_price_peak): vol.Coerce(float),
                    vol.Required(CONF_PRICE_FLAT, default=default_price_flat): vol.Coerce(float),
                    vol.Required(CONF_PRICE_VALLEY, default=default_price_valley): vol.Coerce(float),
                    vol.Optional(CONF_YEAR_LADDER_START, default="0101"): str,
                }
            ),
        )

    async def async_step_year_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        # 根据户号自动获取地区电价配置
        from .regional_prices import get_region_price_config, get_region_name
        
        cons_no = ""
        if self._pending_entry_data:
            power_list = self._pending_entry_data.get(CONF_POWER_USER_LIST) or []
            idx = self._pending_entry_data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)
            if power_list and 0 <= idx < len(power_list) and isinstance(power_list[idx], dict):
                raw = (
                    power_list[idx].get("consNo_dst")
                    or power_list[idx].get("consNoDst")
                    or power_list[idx].get("consNo")
                    or ""
                )
                cons_no = str(raw).split("-")[0].strip() if raw else ""
        
        # 获取地区配置
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        # 设置默认值
        if regional_config:
            default_level_1 = regional_config["ladder_level_1"]
            default_level_2 = regional_config["ladder_level_2"]
            default_price_1 = regional_config["ladder_price_1"]
            default_price_2 = regional_config["ladder_price_2"]
            default_price_3 = regional_config["ladder_price_3"]
            description = f"已自动识别地区：{region_name}\n以下为该地区的默认电价标准，您可以根据需要修改。"
        else:
            # 默认值清零
            default_level_1 = 0
            default_level_2 = 0
            default_price_1 = 0.0
            default_price_2 = 0.0
            default_price_3 = 0.0
            description = "【注意】无法自动识别您的地区，默认值已重置为 0。请手动输入或联系管理员添加您的地区电费阶梯数据。"

        return self.async_show_form(
            step_id="year_ladder_config",
            description_placeholders={"description": description},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=default_level_1): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=default_level_2): int,
                    vol.Required(CONF_LADDER_PRICE_1, default=default_price_1): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_2, default=default_price_2): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_3, default=default_price_3): vol.Coerce(float),
                    vol.Optional(CONF_YEAR_LADDER_START, default="0101"): str,
                }
            ),
        )

    async def async_step_month_ladder_tou_variable_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷变动价格计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        current_month = __import__('datetime').datetime.now().month
        schema_dict = {
            vol.Required(CONF_LADDER_LEVEL_1, default=200): int,
            vol.Required(CONF_LADDER_LEVEL_2, default=400): int,
        }
        # 每月每档电价（1-12月，每档4个：尖、峰、平、谷）
        for month in range(1, 13):
            # 第1档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_tip", default=0.81)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_peak", default=0.56)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_flat", default=0.51)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_valley", default=0.31)] = vol.Coerce(float)
            # 第2档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_tip", default=0.91)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_peak", default=0.66)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_flat", default=0.61)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_valley", default=0.41)] = vol.Coerce(float)
            # 第3档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_tip", default=1.01)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_peak", default=0.76)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_flat", default=0.71)] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_valley", default=0.51)] = vol.Coerce(float)

        return self.async_show_form(
            step_id="month_ladder_tou_variable_config",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_month_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        return self.async_show_form(
            step_id="month_ladder_tou_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=200): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=400): int,
                    vol.Required(CONF_PRICE_TIP, default=0.81): vol.Coerce(float),
                    vol.Required(CONF_PRICE_PEAK, default=0.56): vol.Coerce(float),
                    vol.Required(CONF_PRICE_FLAT, default=0.51): vol.Coerce(float),
                    vol.Required(CONF_PRICE_VALLEY, default=0.51): vol.Coerce(float),
                }
            ),
        )

    async def async_step_month_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        return self.async_show_form(
            step_id="month_ladder_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=200): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=400): int,
                    vol.Required(CONF_LADDER_PRICE_1, default=0.51): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_2, default=0.56): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_3, default=0.81): vol.Coerce(float),
                }
            ),
        )

    async def async_step_average_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置平均单价计费."""
        if user_input is not None:
            if self._pending_entry_data:
                self._pending_entry_data.update(user_input)
                entry_data = {k: v for k, v in self._pending_entry_data.items() if k != "_title"}
                title = self._pending_entry_data.get("_title", "Shaobor_95598")
                self._pending_entry_data = None
                return await self._finish_entry(title=title, data=entry_data)

        return self.async_show_form(
            step_id="average_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AVERAGE_PRICE, default=0.51): vol.Coerce(float),
                }
            ),
        )

    async def async_step_qrcode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle QR code login."""
        errors: dict[str, str] = {}
        if not HAS_PYQRCODE:
            errors["base"] = "qr_dependency_missing"
            return self.async_show_form(
                step_id="qrcode",
                data_schema=vol.Schema({}),
                errors=errors,
                description_placeholders={"qr_code_image": ""},
            )
        if user_input is not None:
            if user_input.get("back_to_login_method"):
                return await self.async_step_login_method()
            if not self._qr_serial:
                errors["base"] = "unknown"
            else:
                try:
                    res = await self._api.check_qrcode_status(self._qr_serial)
                    _LOGGER.warning("[扫码登录] ===== check_qrcode_status 返回: status=%s =====", res.get("status"))
                    
                    if res.get("status") == "SUCCESS":
                        user_token = res.get("user_token")
                        bizrt = res.get("bizrt", {})
                        
                        _LOGGER.warning("[扫码登录] 扫码成功! user_token: %s..., bizrt keys: %s", 
                                     user_token[:20] if user_token else None, 
                                     list(bizrt.keys()) if isinstance(bizrt, dict) else type(bizrt))
                        
                        if not user_token:
                            errors["base"] = "unknown"
                        else:
                            # 步骤1: 从 bizrt 中提取 userInfo，设置 _user_id 和 _login_account
                            if isinstance(bizrt, dict):
                                user_info = bizrt.get("userInfo")
                                _LOGGER.debug("[扫码登录] userInfo type: %s", type(user_info))
                                
                                if isinstance(user_info, list) and user_info and isinstance(user_info[0], dict):
                                    first_ui = user_info[0]
                                    self._api._user_id = str(first_ui.get("userId", ""))
                                    if first_ui.get("loginAccount"):
                                        self._api._login_account = str(first_ui["loginAccount"])
                                    _LOGGER.debug("[扫码登录] 从 list 提取: user_id=%s, login_account=%s", 
                                                 self._api._user_id, self._api._login_account)
                                elif isinstance(user_info, dict):
                                    if user_info.get("loginAccount"):
                                        self._api._login_account = str(user_info["loginAccount"])
                                    if user_info.get("userId"):
                                        self._api._user_id = str(user_info["userId"])
                                    _LOGGER.debug("[扫码登录] 从 dict 提取: user_id=%s, login_account=%s", 
                                                 self._api._user_id, self._api._login_account)
                            
                            # 步骤2: 设置 user_token（c50/f02 返回的 bizrt.token）
                            self._api._user_token = str(user_token)
                            self._api._token = str(user_token)
                            _LOGGER.warning("[扫码登录] 步骤2: 已设置 user_token: %s...", user_token[:20] if user_token else None)
                            
                            # 步骤3: 用 user_token 换取 access_token（调用 authorize + getWebToken）
                            _LOGGER.warning("[扫码登录] 步骤3: 开始换取 access_token")
                            try:
                                tokens = await self._api.exchange_user_token_for_access_token(str(user_token))
                                _LOGGER.warning("[扫码登录] 步骤3: 成功获取 access_token: %s...", 
                                             tokens.get("access_token")[:20] if tokens.get("access_token") else None)
                            except Exception as ex:
                                _LOGGER.error("[扫码登录] 获取 access_token 失败: %s", ex, exc_info=True)
                                errors["base"] = "token_exchange_failed"
                                raise
                            
                            # 验证必要的参数是否已设置
                            if not self._api._access_token:
                                _LOGGER.error("[扫码登录] 步骤3: access_token 未设置")
                                errors["base"] = "token_exchange_failed"
                                raise StateGridAuthError("access_token not set after exchange")
                            
                            _LOGGER.warning("[扫码登录] 步骤3: API 状态检查: user_token=%s..., access_token=%s..., user_id=%s",
                                         self._api._user_token[:20] if self._api._user_token else None,
                                         self._api._access_token[:20] if self._api._access_token else None,
                                         self._api._user_id)
                            
                            # 步骤4: 获取户号列表（需要 access_token）
                            _LOGGER.warning("[扫码登录] 步骤4: 开始获取户号列表")
                            power_user_list = None
                            try:
                                power_user_list = await self._api.fetch_power_user_list()
                            except Exception as ex:
                                _LOGGER.error("[扫码登录] 获取户号列表失败: %s", ex, exc_info=True)
                                errors["base"] = "power_user_list_failed"
                            else:
                                # 扫码登录:获取到户号列表就算成功,不需要验证 get_electricity_data
                                # 因为在选择户号之前,无法调用需要户号信息的接口
                                _LOGGER.warning("[扫码登录] 成功获取 %d 个户号,跳过电费数据验证", len(power_user_list or []))
                                
                                # 登录成功(bizrt.token已获取)，保存所有关键值到 Store(全局变量方式)
                                await self._save_auth_store(
                                    token=self._auth_token,
                                    user_token=str(user_token),
                                    user_id=self._api.user_id,
                                    access_token=tokens.get("access_token"),
                                    refresh_token=tokens.get("refresh_token"),
                                    power_user_list=power_user_list,
                                    login_account=getattr(self._api, "_login_account", None),
                                    user_info=getattr(self._api, "_user_info", None),
                                )
                                entry_data = {
                                    CONF_AUTH_TOKEN: self._auth_token,
                                    CONF_LOGIN_METHOD: self._login_method,
                                    CONF_USER_TOKEN: str(user_token),
                                    CONF_USER_ID: self._api.user_id,
                                    CONF_ACCESS_TOKEN: tokens.get("access_token"),
                                    CONF_REFRESH_TOKEN: tokens.get("refresh_token"),
                                    CONF_POWER_USER_LIST: power_user_list,
                                    CONF_LOGIN_ACCOUNT: getattr(self._api, "_login_account", None),
                                }
                                
                                # 如果是 reauth 流程,使用原有的户号选择
                                if self.context.get("source") == SOURCE_REAUTH:
                                    entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                                    if entry:
                                        selected_index = entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)
                                        entry_data[CONF_SELECTED_ACCOUNT_INDEX] = selected_index
                                        
                                        # 保留原有的计费配置
                                        for key in [CONF_BILLING_MODE, CONF_LADDER_LEVEL_1, CONF_LADDER_LEVEL_2,
                                                   CONF_LADDER_PRICE_1, CONF_LADDER_PRICE_2, CONF_LADDER_PRICE_3,
                                                   CONF_PRICE_TIP, CONF_PRICE_PEAK, CONF_PRICE_FLAT, CONF_PRICE_VALLEY,
                                                   CONF_AVERAGE_PRICE, CONF_YEAR_LADDER_START]:
                                            if key in entry.data:
                                                entry_data[key] = entry.data[key]
                                        
                                        self.hass.config_entries.async_update_entry(entry, data=entry_data)
                                        
                                        # 重新加载集成以应用新的认证信息
                                        await self.hass.config_entries.async_reload(entry.entry_id)
                                        
                                        return self.async_abort(reason="reauth_successful")
                                
                                # 新配置流程:进入户号选择或计费模式配置
                                if len(power_user_list or []) > 1:
                                    self._pending_entry_data = {**entry_data, "_title": "Shaobor_95598 (QR)"}
                                    return await self.async_step_select_account()
                                entry_data[CONF_SELECTED_ACCOUNT_INDEX] = 0
                                self._pending_entry_data = {**entry_data, "_title": "Shaobor_95598 (QR)"}
                                return await self.async_step_billing_mode()
                    elif res.get("status") == "WAITING":
                        errors["base"] = "qr_not_scanned"
                    else:
                        errors["base"] = "unknown"
                except Exception as ex:
                    _LOGGER.error("[扫码登录] 异常: %s", ex, exc_info=True)
                    errors["base"] = "unknown"

        # Get QR data from API if not already present or if we need to refresh
        if not self._qr_image_md or "qr_not_scanned" not in errors.values():
            try:
                qr_result = await self._api.get_login_qrcode()
                qr_data = qr_result.get("qr_code", "")
                self._qr_serial = qr_result.get("serial_no")
                
                if qr_data.startswith("iVBOR"):
                    self._qr_image_md = f"![QR Code](data:image/png;base64,{qr_data})"
                elif HAS_PYQRCODE and pyqrcode:
                    try:
                        qr = pyqrcode.create(qr_data)
                        buffer = io.BytesIO()
                        qr.png(buffer, scale=5)
                        image_base64 = base64.b64encode(buffer.getvalue()).decode()
                        self._qr_image_md = f"![QR Code](data:image/png;base64,{image_base64})"
                    except Exception:
                        self._qr_image_md = "QR Code generation failed"
                else:
                    self._qr_image_md = "QR code display requires PyQRCode package"
                
            except Exception:
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="qrcode", 
                    errors=errors,
                    description_placeholders={"qr_code_image": ""}
                )

        return self.async_show_form(
            step_id="qrcode",
            data_schema=vol.Schema({vol.Optional("back_to_login_method", default=False): bool}),
            description_placeholders={
                "qr_code_image": self._qr_image_md
            },
            errors=errors,
        )

    async def async_step_sms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle SMS login - phase 1 (Input Phone Number)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("back_to_login_method"):
                return await self.async_step_login_method()
            self._phone_number = user_input.get(CONF_PHONE_NUMBER)
            if not self._phone_number:
                errors[CONF_PHONE_NUMBER] = "required"
            else:
                try:
                    _LOGGER.info("[配置流程] 短信登录步骤1: 发送验证码到 %s", self._phone_number)
                    await self._api.login_with_sms_step1(self._phone_number)
                    _LOGGER.info("[配置流程] 短信登录步骤1: 验证码发送成功")
                    return await self.async_step_sms_verify()
                except StateGridAuthError as err:
                    _LOGGER.error("[配置流程] 短信登录失败: %s", err)
                    errors["base"] = "login_error"
                except Exception as err:
                    _LOGGER.error("[配置流程] 短信登录异常: %s", err, exc_info=True)
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="sms",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PHONE_NUMBER): str,
                    vol.Optional("back_to_login_method", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_sms_verify(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle SMS login - phase 2 (Input Code)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("back_to_sms"):
                return await self.async_step_sms()
            code = user_input.get(CONF_SMS_CODE)
            if not code:
                errors[CONF_SMS_CODE] = "required"
            else:
                try:
                    result = await self._api.login_with_sms_step2(self._phone_number, code)
                    if result and result.get("success"):
                        tokens = result.get("tokens", {})
                        power_user_list = None
                        try:
                            power_user_list = await self._api.fetch_power_user_list()
                        except Exception:
                            errors["base"] = "power_user_list_failed"
                        else:
                            try:
                                await self._api.get_electricity_data()
                            except StateGridAuthError:
                                errors["base"] = "login_verify_failed"
                            except Exception:
                                errors["base"] = "login_verify_failed"
                            else:
                                # 登录成功(bizrt.token已获取)，保存所有关键值到 Store(全局变量方式)
                                await self._save_auth_store(
                                    token=self._auth_token,
                                    user_token=tokens.get("user_token", ""),
                                    user_id=self._api.user_id,
                                    access_token=tokens.get("access_token"),
                                    refresh_token=tokens.get("refresh_token"),
                                    power_user_list=power_user_list,
                                    login_account=getattr(self._api, "_login_account", None),
                                    user_info=getattr(self._api, "_user_info", None),
                                )
                                entry_data = {
                                    CONF_AUTH_TOKEN: self._auth_token,
                                    CONF_LOGIN_METHOD: self._login_method,
                                    CONF_USER_TOKEN: tokens.get("user_token"),
                                    CONF_USER_ID: self._api.user_id,
                                    CONF_ACCESS_TOKEN: tokens.get("access_token"),
                                    CONF_REFRESH_TOKEN: tokens.get("refresh_token"),
                                    CONF_POWER_USER_LIST: power_user_list,
                                    CONF_LOGIN_ACCOUNT: getattr(self._api, "_login_account", None),
                                }
                                
                                # 如果是 reauth 流程,使用原有的户号选择
                                if self.context.get("source") == SOURCE_REAUTH:
                                    entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                                    if entry:
                                        selected_index = entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0)
                                        entry_data[CONF_SELECTED_ACCOUNT_INDEX] = selected_index
                                        
                                        # 保留原有的计费配置
                                        for key in [CONF_BILLING_MODE, CONF_LADDER_LEVEL_1, CONF_LADDER_LEVEL_2,
                                                   CONF_LADDER_PRICE_1, CONF_LADDER_PRICE_2, CONF_LADDER_PRICE_3,
                                                   CONF_PRICE_TIP, CONF_PRICE_PEAK, CONF_PRICE_FLAT, CONF_PRICE_VALLEY,
                                                   CONF_AVERAGE_PRICE, CONF_YEAR_LADDER_START]:
                                            if key in entry.data:
                                                entry_data[key] = entry.data[key]
                                        
                                        self.hass.config_entries.async_update_entry(entry, data=entry_data)
                                        
                                        # 重新加载集成以应用新的认证信息
                                        await self.hass.config_entries.async_reload(entry.entry_id)
                                        
                                        return self.async_abort(reason="reauth_successful")
                                
                                # 新配置流程:进入户号选择或计费模式配置
                                if len(power_user_list or []) > 1:
                                    self._pending_entry_data = {**entry_data, "_title": f"Shaobor_95598 ({self._phone_number})"}
                                    return await self.async_step_select_account()
                                entry_data[CONF_SELECTED_ACCOUNT_INDEX] = 0
                                self._pending_entry_data = {**entry_data, "_title": f"Shaobor_95598 ({self._phone_number})"}
                                return await self.async_step_billing_mode()
                except StateGridAuthError as err:
                    _LOGGER.error("[配置流程] 短信验证失败: %s", err)
                    errors["base"] = "invalid_code"
                except Exception as err:
                    _LOGGER.error("[配置流程] 短信验证异常: %s", err, exc_info=True)
                    errors["base"] = "unknown"
                if not errors:
                    errors["base"] = "invalid_code"

        return self.async_show_form(
            step_id="sms_verify",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SMS_CODE): str,
                    vol.Optional("back_to_sms", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"phone_number": self._phone_number},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Shaobor_95598."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            billing_mode = user_input[CONF_BILLING_MODE]
            # 根据计费模式跳转到对应的价格配置页面
            if billing_mode == BILLING_STANDARD_YEAR_LADDER_TOU:
                return await self.async_step_year_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_YEAR_LADDER:
                return await self.async_step_year_ladder_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE:
                return await self.async_step_month_ladder_tou_variable_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU:
                return await self.async_step_month_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER:
                return await self.async_step_month_ladder_config()
            elif billing_mode == BILLING_STANDARD_AVERAGE:
                return await self.async_step_average_config()

        # 获取当前配置的计费模式
        current_billing_mode = self.config_entry.data.get(CONF_BILLING_MODE, BILLING_STANDARD_YEAR_LADDER)
        
        billing_options = [
            {"value": BILLING_STANDARD_YEAR_LADDER_TOU, "label": "年阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_YEAR_LADDER, "label": "年阶梯计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE, "label": "月阶梯峰平谷变动价格计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU, "label": "月阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER, "label": "月阶梯计费"},
            {"value": BILLING_STANDARD_AVERAGE, "label": "平均单价计费"},
        ]
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BILLING_MODE, default=current_billing_mode): SelectSelector(
                        SelectSelectorConfig(
                            options=billing_options,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_year_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯峰平谷计费."""
        if user_input is not None:
            # 更新配置，确保包含 billing_mode
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_YEAR_LADDER_TOU}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        # 获取当前配置值
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="year_ladder_tou_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=current_data.get(CONF_LADDER_LEVEL_1, 2040)): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=current_data.get(CONF_LADDER_LEVEL_2, 3240)): int,
                    vol.Required(CONF_PRICE_TIP, default=current_data.get(CONF_PRICE_TIP, 0.81)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_PEAK, default=current_data.get(CONF_PRICE_PEAK, 0.56)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_FLAT, default=current_data.get(CONF_PRICE_FLAT, 0.51)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_VALLEY, default=current_data.get(CONF_PRICE_VALLEY, 0.51)): vol.Coerce(float),
                    vol.Optional(CONF_YEAR_LADDER_START, default=current_data.get(CONF_YEAR_LADDER_START, "0101")): str,
                }
            ),
        )

    async def async_step_year_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_YEAR_LADDER}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        # 根据户号自动获取地区电价配置
        from .regional_prices import get_region_price_config, get_region_name
        
        current_data = self.config_entry.data
        
        # 尝试从coordinator获取户号
        cons_no = ""
        if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
            if coordinator and coordinator.data:
                cons_no = coordinator.data.get("selected_cons_no", "")
        
        # 获取地区配置
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        # 设置默认值
        if regional_config:
            default_level_1 = regional_config["ladder_level_1"]
            default_level_2 = regional_config["ladder_level_2"]
            default_price_1 = regional_config["ladder_price_1"]
            default_price_2 = regional_config["ladder_price_2"]
            default_price_3 = regional_config["ladder_price_3"]
            description = f"已自动识别地区：{region_name}\n当前配置的电价标准，您可以根据需要修改。"
        else:
            default_level_1 = 2040
            default_level_2 = 3240
            default_price_1 = 0.51
            default_price_2 = 0.56
            default_price_3 = 0.81
            description = "当前配置的电价标准，您可以根据实际情况修改。"
        
        return self.async_show_form(
            step_id="year_ladder_config",
            description_placeholders={"description": description},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=current_data.get(CONF_LADDER_LEVEL_1, default_level_1)): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=current_data.get(CONF_LADDER_LEVEL_2, default_level_2)): int,
                    vol.Required(CONF_LADDER_PRICE_1, default=current_data.get(CONF_LADDER_PRICE_1, default_price_1)): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_2, default=current_data.get(CONF_LADDER_PRICE_2, default_price_2)): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_3, default=current_data.get(CONF_LADDER_PRICE_3, default_price_3)): vol.Coerce(float),
                    vol.Optional(CONF_YEAR_LADDER_START, default=current_data.get(CONF_YEAR_LADDER_START, "0101")): str,
                }
            ),
        )

    async def async_step_month_ladder_tou_variable_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷变动价格计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        schema_dict = {
            vol.Required(CONF_LADDER_LEVEL_1, default=current_data.get(CONF_LADDER_LEVEL_1, 200)): int,
            vol.Required(CONF_LADDER_LEVEL_2, default=current_data.get(CONF_LADDER_LEVEL_2, 400)): int,
        }
        # 每月每档电价（1-12月，每档4个：尖、峰、平、谷）
        for month in range(1, 13):
            # 第1档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_tip", default=current_data.get(f"month_{month:02d}_ladder_1_tip", 0.81))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_peak", default=current_data.get(f"month_{month:02d}_ladder_1_peak", 0.56))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_flat", default=current_data.get(f"month_{month:02d}_ladder_1_flat", 0.51))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_1_valley", default=current_data.get(f"month_{month:02d}_ladder_1_valley", 0.31))] = vol.Coerce(float)
            # 第2档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_tip", default=current_data.get(f"month_{month:02d}_ladder_2_tip", 0.91))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_peak", default=current_data.get(f"month_{month:02d}_ladder_2_peak", 0.66))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_flat", default=current_data.get(f"month_{month:02d}_ladder_2_flat", 0.61))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_2_valley", default=current_data.get(f"month_{month:02d}_ladder_2_valley", 0.41))] = vol.Coerce(float)
            # 第3档
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_tip", default=current_data.get(f"month_{month:02d}_ladder_3_tip", 1.01))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_peak", default=current_data.get(f"month_{month:02d}_ladder_3_peak", 0.76))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_flat", default=current_data.get(f"month_{month:02d}_ladder_3_flat", 0.71))] = vol.Coerce(float)
            schema_dict[vol.Required(f"month_{month:02d}_ladder_3_valley", default=current_data.get(f"month_{month:02d}_ladder_3_valley", 0.51))] = vol.Coerce(float)

        return self.async_show_form(
            step_id="month_ladder_tou_variable_config",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_month_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER_TOU}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="month_ladder_tou_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=current_data.get(CONF_LADDER_LEVEL_1, 200)): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=current_data.get(CONF_LADDER_LEVEL_2, 400)): int,
                    vol.Required(CONF_PRICE_TIP, default=current_data.get(CONF_PRICE_TIP, 0.81)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_PEAK, default=current_data.get(CONF_PRICE_PEAK, 0.56)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_FLAT, default=current_data.get(CONF_PRICE_FLAT, 0.51)): vol.Coerce(float),
                    vol.Required(CONF_PRICE_VALLEY, default=current_data.get(CONF_PRICE_VALLEY, 0.51)): vol.Coerce(float),
                }
            ),
        )

    async def async_step_month_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="month_ladder_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LADDER_LEVEL_1, default=current_data.get(CONF_LADDER_LEVEL_1, 200)): int,
                    vol.Required(CONF_LADDER_LEVEL_2, default=current_data.get(CONF_LADDER_LEVEL_2, 400)): int,
                    vol.Required(CONF_LADDER_PRICE_1, default=current_data.get(CONF_LADDER_PRICE_1, 0.51)): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_2, default=current_data.get(CONF_LADDER_PRICE_2, 0.56)): vol.Coerce(float),
                    vol.Required(CONF_LADDER_PRICE_3, default=current_data.get(CONF_LADDER_PRICE_3, 0.81)): vol.Coerce(float),
                }
            ),
        )

    async def async_step_average_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置平均单价计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_AVERAGE}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="average_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AVERAGE_PRICE, default=current_data.get(CONF_AVERAGE_PRICE, 0.51)): vol.Coerce(float),
                }
            ),
        )

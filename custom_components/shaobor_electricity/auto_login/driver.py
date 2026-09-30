"""掉线短信自动登录：登录驱动（屏蔽网页源 / 手机 App 源链路差异）。

两条链路的短信登录形状不同：
  网页源（web）  client/login.py  login_with_sms_step1 / login_with_sms_step2
  手机源（mobile）mobile/client.py request_sms / sms_login（codeKey 由驱动实例持有）

驱动只负责「发码」与「校验 + 拉户号 + 产出热生效所需数据」，
ConfigEntry 写回与刷新由 AutoLoginManager 统一处理。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..client.exceptions import StateGridAuthError
from ..const import (
    CONF_ACCESS_TOKEN,
    CONF_LOGIN_ACCOUNT,
    CONF_POWER_USER_LIST,
    CONF_REFRESH_TOKEN,
    CONF_SELECTED_ACCOUNT_INDEX,
    CONF_USER_ID,
    CONF_USER_TOKEN,
)
from .const import CONF_SMS_PHONE


@dataclass
class LoginOutcome:
    """一次成功登录产出的热生效数据。"""

    # 需要合并写回 ConfigEntry.data 的键
    data_updates: dict[str, Any] = field(default_factory=dict)
    # 需要落 shaobor_auth_store 的载荷（手机源为 None：会话已由 client 落本地库）
    db_payload: dict[str, Any] | None = None
    # 传给 api.load_auth_state 的键（手机源为空：其实现为空操作）
    api_state: dict[str, Any] = field(default_factory=dict)


def effective_account(api: Any, entry: Any) -> str:
    """用于接收短信的号码：优先用户在「短信接收手机号」实体中指定的号码。

    留空时回退到登录账号（entry.data["login_account"] / api._login_account）。
    95598 的 loginAccount 不一定是机主手机号（账号密码/扫码登录的账号可能是用户名），
    因此提供可覆盖的号码来源。
    """
    custom = str(entry.data.get(CONF_SMS_PHONE) or "").strip()
    if custom:
        return custom
    return str(
        getattr(api, "_login_account", None)
        or entry.data.get(CONF_LOGIN_ACCOUNT)
        or ""
    )


def phone_source(entry: Any) -> str:
    """号码来源：custom=用户在实体中指定；login_account=跟随登录账号。"""
    return "custom" if str(entry.data.get(CONF_SMS_PHONE) or "").strip() else "login_account"


def _selected_index(entry: Any, total: int) -> int:
    """沿用用户原有的户号选择，越界时收敛到首个。"""
    try:
        index = int(entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0) or 0)
    except (TypeError, ValueError):
        index = 0
    if total <= 0:
        return 0
    return min(max(index, 0), total - 1)


def driver_name(api: Any) -> str:
    """当前数据源对应的驱动名（用于实体属性展示）。"""
    return "mobile" if _is_mobile_api(api) else "web"


def _is_mobile_api(api: Any) -> bool:
    from ..mobile.client import MobileIosApiClient

    return isinstance(api, MobileIosApiClient)


def build_driver(api: Any, entry: Any, db: Any) -> "SmsLoginDriver":
    """按当前数据源构造驱动。

    必须在每次动作前现场构造：Coordinator 会按数据库路由热切换数据源
    （coordinator._async_sync_upstream_source），不能缓存驱动实例。
    """
    if _is_mobile_api(api):
        return MobileSmsDriver(api, entry, db)
    return WebSmsDriver(api, entry, db)


class SmsLoginDriver:
    """短信登录驱动基类。"""

    name: str = "unknown"

    def __init__(self, api: Any, entry: Any, db: Any) -> None:
        self._api = api
        self._entry = entry
        self._db = db

    @property
    def account(self) -> str:
        """登录手机号（短信必须发到登录账号本身）。"""
        raise NotImplementedError

    async def async_request_code(self) -> None:
        """下发短信验证码。"""
        raise NotImplementedError

    async def async_verify(self, code: str) -> LoginOutcome:
        """校验验证码并拉取户号列表，返回热生效数据。"""
        raise NotImplementedError


class WebSmsDriver(SmsLoginDriver):
    """网页版 95598 短信登录链路。"""

    name = "web"

    @property
    def account(self) -> str:
        return effective_account(self._api, self._entry)

    async def async_request_code(self) -> None:
        # step1 内部会自行 initialize(force_new_uuid=True) 重置加密会话，
        # codeKey 保存在 api 实例（_sms_code_key），因此发码与校验必须用同一实例。
        # 先清掉上一轮残留的 codeKey，再用「本次是否拿到新 codeKey」判定短信是否真的发出：
        # 拿不到 codeKey 时第二步必然报 Missing codeKey，等于白等 5 分钟。
        self._api._sms_code_key = None
        await self._api.login_with_sms_step1(self.account)
        if not getattr(self._api, "_sms_code_key", None):
            raise StateGridAuthError(
                "95598 未返回 codeKey，短信未实质发出"
                "（请确认「短信接收手机号」是否为该账号绑定的手机号）"
            )

    async def async_verify(self, code: str) -> LoginOutcome:
        result = await self._api.login_with_sms_step2(self.account, code)
        if not result or not result.get("success"):
            raise StateGridAuthError("短信验证码校验未通过")

        power_user_list = await self._api.fetch_power_user_list()
        if not power_user_list:
            raise StateGridAuthError("登录成功但未获取到绑定户号")

        tokens = result.get("tokens") or {}
        login_account = str(
            getattr(self._api, "_login_account", None) or self.account or ""
        )
        index = _selected_index(self._entry, len(power_user_list))
        user_id = getattr(self._api, "user_id", None)

        return LoginOutcome(
            data_updates={
                CONF_USER_TOKEN: tokens.get("user_token"),
                CONF_USER_ID: user_id,
                CONF_ACCESS_TOKEN: tokens.get("access_token"),
                CONF_REFRESH_TOKEN: tokens.get("refresh_token"),
                CONF_POWER_USER_LIST: power_user_list,
                CONF_LOGIN_ACCOUNT: login_account,
                CONF_SELECTED_ACCOUNT_INDEX: index,
            },
            db_payload={
                "user_token": tokens.get("user_token"),
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "user_id": user_id,
                "power_user_list": power_user_list,
                "login_account": login_account,
            },
            api_state={
                "user_token": tokens.get("user_token"),
                "user_id": user_id,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "power_user_list": power_user_list,
                "selected_account_index": index,
                "login_account": login_account,
            },
        )


class MobileSmsDriver(SmsLoginDriver):
    """手机 App（iOS 链路）短信登录驱动。"""

    name = "mobile"

    def __init__(self, api: Any, entry: Any, db: Any) -> None:
        super().__init__(api, entry, db)
        # 发码返回的 codeKey 校验时必须原样带回，仅存内存
        self._code_key: str = ""

    @property
    def account(self) -> str:
        return effective_account(self._api, self._entry)

    async def async_request_code(self) -> None:
        # request_sms 内部已校验 codeKey：拿不到即抛错，不会出现「假成功」
        self._code_key = await self._api.request_sms(self.account)

    async def async_verify(self, code: str) -> LoginOutcome:
        if not self._code_key:
            raise StateGridAuthError("短信验证码会话已失效，请重新触发发送")

        # sms_login 内部会 _persist_local_session 把会话写入 HA 本地库（本地真值）
        await self._api.sms_login(self.account, code, self._code_key)
        # fetch_power_user_list 内部走 async_get_profile，自带「从本地库自愈恢复
        # 会话与户号档案」逻辑，因此无需复制 __init__.py 的启动预热代码。
        power_user_list = await self._api.fetch_power_user_list()

        login_account = str(
            getattr(self._api, "_login_account", None) or self.account or ""
        )
        index = _selected_index(self._entry, len(power_user_list))

        return LoginOutcome(
            data_updates={
                CONF_POWER_USER_LIST: power_user_list,
                CONF_LOGIN_ACCOUNT: login_account,
                CONF_USER_ID: getattr(self._api, "_user_id", "") or "",
                CONF_SELECTED_ACCOUNT_INDEX: index,
            },
            # 手机源不写 shaobor_auth_store：会话与档案在 shaobor_mobile_auth_store
            db_payload=None,
            # 手机源 load_auth_state 为空实现，状态已在 client 内部恢复
            api_state={},
        )


__all__ = [
    "LoginOutcome",
    "SmsLoginDriver",
    "WebSmsDriver",
    "MobileSmsDriver",
    "build_driver",
    "driver_name",
    "effective_account",
    "phone_source",
]

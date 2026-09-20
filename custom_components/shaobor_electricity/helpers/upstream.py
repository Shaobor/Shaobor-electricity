"""数据库驱动的上游数据源选择（system_settings 单配置项）。

后端 MySQL 表 system_settings 里的 config_key='upstream_source' 一条配置
决定集成当前应使用哪条上游链路：值为 'mobile' 时走手机 App iOS 链路，
其余情况（含未设置）一律走网页版。所有前端统一按它走，改这一行即全局切换。
集成在每次数据刷新前调用 resolve 接口询问，结果变化即热切换客户端，
无需重载集成；选项流中的「数据源切换」也只是写这一个配置项。

source 取值：
  web     → 网页版加密通道（/api/initialize + /api/encrypt/* + /api/decrypt）
  mobile  → 手机App iOS 链路（/api/mobile/ios/*，登录态/设备指纹由后端持有）

配套后端接口（均需 token + machineId）：
  POST {ENCRYPT_API_URL}/upstream-source          写入配置 {source}
  POST {ENCRYPT_API_URL}/upstream-source/resolve  查询当前生效 source
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp  # type: ignore[import-untyped]

from ..client.const import ENCRYPT_API_URL
from ..client.exceptions import StateGridAuthError, StateGridConnectionError

_LOGGER = logging.getLogger(__name__)

SOURCE_WEB = "web"
SOURCE_MOBILE = "mobile"
VALID_SOURCES = (SOURCE_WEB, SOURCE_MOBILE)


def entry_auth(hass: Any, entry: Any) -> tuple[str | None, str | None]:
    """从 entry 提取后端授权码与绑定码。"""
    from ..const import CONF_AUTH_TOKEN, CONF_MACHINE_ID

    token = entry.data.get(CONF_AUTH_TOKEN)
    machine_id = entry.data.get(CONF_MACHINE_ID) or hass.data.get("core.uuid")
    return token, machine_id


async def _post(
    session: aiohttp.ClientSession,
    path: str,
    token: str | None,
    machine_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    url = f"{ENCRYPT_API_URL}{path}"
    body = {"token": token, "machineId": machine_id, **payload}
    try:
        async with session.post(
            url, json=body, headers={"Content-Type": "application/json"}
        ) as resp:
            data: Any = await resp.json(content_type=None)
            if resp.status in (401, 403):
                raise StateGridAuthError(
                    f"数据源路由接口授权失败: {data.get('error') if isinstance(data, dict) else resp.status}"
                )
            if resp.status >= 500 or not isinstance(data, dict):
                raise StateGridConnectionError(
                    f"数据源路由接口 HTTP {resp.status}: {str(data)[:200]}"
                )
    except aiohttp.ClientError as err:
        raise StateGridConnectionError(f"中转后端通信失败: {err}") from err
    if not data.get("success"):
        raise StateGridConnectionError(
            f"数据源路由接口业务失败: {str(data.get('error') or data)[:200]}"
        )
    return data


async def resolve_upstream_source(
    hass: Any,
    entry: Any,
    session: aiohttp.ClientSession | None = None,
) -> str | None:
    """查询数据库当前生效的数据源。

    返回 'web' / 'mobile'；后端不可达或响应异常时返回 None，
    调用方应保持当前数据源不变（数据库故障不导致误切换）。
    """
    token, machine_id = entry_auth(hass, entry)
    return await resolve_upstream_source_raw(hass, token, machine_id, session)


async def resolve_upstream_source_raw(
    hass: Any,
    token: str | None,
    machine_id: str | None,
    session: aiohttp.ClientSession | None = None,
) -> str | None:
    """显式传 token/machineId 的底层 resolve（配置流程等无 ConfigEntry 的场景）。"""
    if not token:
        return None
    if session is None:
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(hass)
    try:
        data = await _post(session, "/upstream-source/resolve", token, machine_id, {})
        source = data.get("source")
        if source in VALID_SOURCES:
            return str(source)
        _LOGGER.warning("[数据源路由] resolve 返回未知 source: %s，忽略", source)
        return None
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("[数据源路由] resolve 失败，保持当前数据源: %s", err)
        return None


async def set_upstream_source(hass: Any, entry: Any, source: str) -> None:
    """写入全局数据源配置（system_settings.upstream_source，选项流调用）。失败抛异常。"""
    if source not in VALID_SOURCES:
        raise ValueError(f"source 仅支持 {'/'.join(VALID_SOURCES)}")
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    token, machine_id = entry_auth(hass, entry)
    if not token:
        raise StateGridAuthError("缺少授权密钥，无法写入数据源配置")
    session = async_get_clientsession(hass)
    await _post(session, "/upstream-source", token, machine_id, {"source": source})
    _LOGGER.info("[数据源路由] 已写入全局配置 upstream_source=%s", source)


# ----------------------------------------------------------------------
# 客户端工厂：热切换时按 entry + 本地 SQLite 重建对应链路的客户端
# ----------------------------------------------------------------------

def _billing_config(entry: Any) -> dict[str, Any]:
    from ..const import (
        CONF_BILLING_MODE,
        CONF_AVERAGE_PRICE,
        CONF_LADDER_PRICE_1,
        CONF_LADDER_PRICE_2,
        CONF_LADDER_PRICE_3,
        CONF_PRICE_TIP,
        CONF_PRICE_PEAK,
        CONF_PRICE_FLAT,
        CONF_PRICE_VALLEY,
    )

    return {
        "billing_mode": entry.data.get(CONF_BILLING_MODE, ""),
        "average_price": entry.data.get(CONF_AVERAGE_PRICE),
        "ladder_price_1": entry.data.get(CONF_LADDER_PRICE_1),
        "ladder_price_2": entry.data.get(CONF_LADDER_PRICE_2),
        "ladder_price_3": entry.data.get(CONF_LADDER_PRICE_3),
        "price_tip": entry.data.get(CONF_PRICE_TIP),
        "price_peak": entry.data.get(CONF_PRICE_PEAK),
        "price_flat": entry.data.get(CONF_PRICE_FLAT),
        "price_valley": entry.data.get(CONF_PRICE_VALLEY),
    }


def build_mobile_client(hass: Any, entry: Any, session: aiohttp.ClientSession, db: Any):
    """构建手机App（iOS 链路）客户端：登录态由后端持有，本地无状态。"""
    from ..mobile.client import MobileIosApiClient

    token, machine_id = entry_auth(hass, entry)
    api = MobileIosApiClient(
        token, session, hass, entry_id=entry.entry_id, machine_id=machine_id
    )
    api.set_db(db)
    api.set_billing_config(_billing_config(entry))
    return api


async def build_web_client(hass: Any, entry: Any, session: aiohttp.ClientSession, db: Any):
    """构建网页版客户端：认证从本地 SQLite（单点真值）恢复，entry.data 兜底。"""
    from ..client import Shaobor95598ApiClient
    from ..const import (
        CONF_USER_TOKEN,
        CONF_USER_ID,
        CONF_ACCESS_TOKEN,
        CONF_REFRESH_TOKEN,
        CONF_POWER_USER_LIST,
        CONF_SELECTED_ACCOUNT_INDEX,
        CONF_LOGIN_ACCOUNT,
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_AUTO_RELOGIN,
    )

    token, machine_id = entry_auth(hass, entry)
    api = Shaobor95598ApiClient(
        token, session, None, hass, entry_id=entry.entry_id, machine_id=machine_id
    )
    api.set_db(db)

    login_acc = entry.data.get(CONF_LOGIN_ACCOUNT)
    db_auth = await db.async_get_auth(login_acc) if login_acc else None

    api.load_auth_state(
        user_token=(db_auth or {}).get("user_token") or entry.data.get(CONF_USER_TOKEN),
        user_id=(db_auth or {}).get("user_id") or entry.data.get(CONF_USER_ID),
        access_token=(db_auth or {}).get("access_token") or entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=(db_auth or {}).get("refresh_token") or entry.data.get(CONF_REFRESH_TOKEN),
        power_user_list=(db_auth or {}).get("power_user_list") or entry.data.get(CONF_POWER_USER_LIST),
        selected_account_index=entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0),
        login_account=login_acc,
    )
    api.set_billing_config(_billing_config(entry))

    saved_acc = login_acc

    async def _update_store_callback(**kwargs: Any) -> None:
        if saved_acc:
            await db.async_save_auth(saved_acc, kwargs)

    api.set_auto_relogin_credentials(
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
        auto_relogin_enabled=entry.data.get(CONF_AUTO_RELOGIN, False),
        store_update_callback=_update_store_callback,
    )
    return api

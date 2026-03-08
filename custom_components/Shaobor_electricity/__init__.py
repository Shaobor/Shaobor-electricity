"""The Shaobor_electricity integration."""
from __future__ import annotations

import logging

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.exceptions import ConfigEntryAuthFailed  # type: ignore
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore

from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_AUTO_RELOGIN,
    CONF_LOGIN_METHOD,
    LOGIN_METHOD_PASSWORD,
    CONF_USER_TOKEN,
    CONF_USER_ID,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_POWER_USER_LIST,
    CONF_SELECTED_ACCOUNT_INDEX,
    CONF_LOGIN_ACCOUNT,
)
from .api import Shaobor95598ApiClient, StateGridAuthError, STORAGE_KEY, STORAGE_VERSION
from .storage import AuthStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shaobor_95598 from a config entry."""
    session = async_get_clientsession(hass)
    token = entry.data.get(CONF_AUTH_TOKEN)
    if not token:
        raise ConfigEntryAuthFailed("缺少授权 Token，请重新配置集成")

    # 从 Store 合并加载（全局变量方式），补充 config entry 可能缺失的字段
    store = AuthStore(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    if stored and isinstance(stored, dict) and stored.get("token") == token:
        entry_user_token = entry.data.get(CONF_USER_TOKEN) or stored.get("user_token")
        entry_access_token = entry.data.get(CONF_ACCESS_TOKEN) or stored.get("access_token")
    else:
        entry_user_token = entry.data.get(CONF_USER_TOKEN)
        entry_access_token = entry.data.get(CONF_ACCESS_TOKEN)

    if not entry_user_token or not entry_access_token:
        raise ConfigEntryAuthFailed(
            "登录信息不完整，请删除该集成后重新添加（推荐使用扫码登录）"
        )

    # 合并 entry 与 Store：entry 优先，缺失时用 Store
    def _merged(key: str, store_key: str | None = None) -> str | list | None:
        val = entry.data.get(key)
        if val is not None and val != "" and (not isinstance(val, list) or val):
            return val
        if stored and isinstance(stored, dict):
            return stored.get(store_key or key)
        return None

    api = Shaobor95598ApiClient(token, session, store, hass)
    api.load_auth_state(
        user_token=entry_user_token or _merged(CONF_USER_TOKEN, "user_token"),
        user_id=entry.data.get(CONF_USER_ID) or (stored.get("user_id") if stored else None),
        access_token=entry_access_token or _merged(CONF_ACCESS_TOKEN, "access_token"),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN) or (stored.get("refresh_token") if stored else None),
        power_user_list=entry.data.get(CONF_POWER_USER_LIST) or (stored.get("power_user_list") if stored else None),
        selected_account_index=entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0),
        login_account=entry.data.get(CONF_LOGIN_ACCOUNT) or (stored.get("login_account") if stored else None),
    )
    
    # 创建 Store 更新回调函数
    async def update_store_callback(**kwargs):
        """Callback to update Store after successful re-login."""
        await store.async_save(kwargs)
    
    # 加载自动重连配置（优先从 Store 加载，其次从 entry.data）
    # Store 中的数据是最新的，因为每次登录成功都会更新
    login_method = entry.data.get(CONF_LOGIN_METHOD)
    auto_relogin = False
    username = None
    password = None
    
    # 优先从 Store 加载
    if stored and isinstance(stored, dict):
        auto_relogin = stored.get("auto_relogin", False)
        username = stored.get("username")
        password = stored.get("password")
    
    # 如果 Store 中没有，则从 entry.data 加载
    if not auto_relogin:
        auto_relogin = entry.data.get(CONF_AUTO_RELOGIN, False)
    if not username:
        username = entry.data.get(CONF_USERNAME)
    if not password:
        password = entry.data.get(CONF_PASSWORD)
    
    # 只有密码登录方式且启用了自动重连才记录日志
    if login_method == LOGIN_METHOD_PASSWORD and auto_relogin and username and password:
        _LOGGER.info("已启用掉线自动重新登录功能（用户: %s）", username)
    
    # 设置自动重连凭据到 API 客户端
    api.set_auto_relogin_credentials(
        username=username,
        password=password,
        auto_relogin_enabled=auto_relogin,
        store_update_callback=update_store_callback,
    )

    async def async_update_data():
        """Fetch data from API. 先刷新 access_token（每10分钟），再请求户号业务."""
        try:
            await api.refresh_access_token()
            return await api.get_electricity_data()
        except StateGridAuthError as err:
            # API 层已经有 auto_relogin_on_auth_error 装饰器处理自动重连
            # 如果到这里说明自动重连也失败了，触发重新认证流程
            raise ConfigEntryAuthFailed(
                "登录已过期，请重新配置集成（使用扫码登录）"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=10),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

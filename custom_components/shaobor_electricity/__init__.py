"""The shaobor_electricity integration."""
from __future__ import annotations

import logging

from datetime import timedelta
from pathlib import Path
from homeassistant.components import frontend  # type: ignore
from homeassistant.components.http import StaticPathConfig  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.exceptions import ConfigEntryAuthFailed  # type: ignore
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore

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
    CONF_MACHINE_ID,
)
from .client import Shaobor95598ApiClient, StateGridAuthError, STORAGE_KEY, STORAGE_VERSION
from .helpers.division_mapping import async_load_division_mapping
from .storage import AuthStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]
CARD_URL = f"/{DOMAIN}/electricity-info-card.js"
CARD_PATH = Path(__file__).parent / "www" / "electricity-info-card.js"


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register and load the bundled Lovelace electricity card."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    frontend.add_extra_js_url(hass, CARD_URL)
    return True

async def _async_migrate_stores(hass: HomeAssistant) -> None:
    """迁移旧的 store 文件到新的子文件夹路径."""
    
    # 迁移 auth store: shaobor_electricity_auth -> shaobor_electricity/shaobor_electricity_auth
    old_auth_store = Store(hass, STORAGE_VERSION, "shaobor_electricity_auth")
    old_auth_data = await old_auth_store.async_load()
    if old_auth_data:
        _LOGGER.info("[迁移] 发现旧的 auth store，迁移到新路径...")
        new_auth_store = AuthStore(hass, STORAGE_VERSION, STORAGE_KEY)
        existing = await new_auth_store.async_load()
        if not existing:
            await new_auth_store.async_save(old_auth_data)
            await old_auth_store.async_remove()
            _LOGGER.info("[迁移] auth store 迁移完成")
        else:
            _LOGGER.info("[迁移] 新路径已有数据，跳过迁移")
    
    # 迁移 history store: shaobor_electricity_history -> shaobor_electricity/shaobor_electricity_history
    old_history_store = Store(hass, version=1, key="shaobor_electricity_history")
    old_history_data = await old_history_store.async_load()
    if old_history_data:
        _LOGGER.info("[迁移] 发现旧的 history store，迁移到新路径...")
        new_history_store = Store(hass, version=1, key="shaobor_electricity/shaobor_electricity_history")
        existing_history = await new_history_store.async_load()
        if not existing_history:
            await new_history_store.async_save(old_history_data)
            await old_history_store.async_remove()
            _LOGGER.info("[迁移] history store 迁移完成")
        else:
            _LOGGER.info("[迁移] 新路径已有历史数据，跳过迁移")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up shaobor_electricity from a config entry."""
    # 首先确保全局数据字典已就绪，防止 coordinator 刷新时因无法读写标志位而崩溃
    hass.data.setdefault(DOMAIN, {})
    if "division_mapping" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["division_mapping"] = await async_load_division_mapping(hass)
    if "auth_lock" not in hass.data[DOMAIN]:
        import asyncio
        hass.data[DOMAIN]["auth_lock"] = asyncio.Lock()
    
    session = async_get_clientsession(hass)
    token = entry.data.get(CONF_AUTH_TOKEN)
    if not token:
        raise ConfigEntryAuthFailed("缺少授权 Token，请重新配置集成")

    # 自动迁移旧 store 文件到新路径（shaobor_electricity/ 子文件夹）
    await _async_migrate_stores(hass)

    # 1. 优先从数据库加载授权信息 (单点真值)
    from .helpers.database import StateGridDatabase
    db_path = hass.config.path(".storage", DOMAIN, "shaobor_electricity.db")
    db = StateGridDatabase(hass, db_path)
    await db.async_init()
    
    # 获取登录账号用于数据库查询
    login_acc = entry.data.get(CONF_LOGIN_ACCOUNT)
    db_auth = await db.async_get_auth(login_acc) if login_acc else None

    # 2. 备选：从旧的 Store 加载 (用于兼容与迁移)
    store = AuthStore(hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    
    # 优先使用数据库中的最新 Token
    if db_auth:
        _LOGGER.debug("[授权] 成功从数据库加载授权状态")
        entry_user_token = db_auth.get("user_token") or entry.data.get(CONF_USER_TOKEN)
        entry_access_token = db_auth.get("access_token") or entry.data.get(CONF_ACCESS_TOKEN)
        # 合并 stored 数据以便后续 _merged 逻辑使用
        stored = {**(stored or {}), **db_auth}
    else:
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

    # 合并 entry 与 Store/DB：entry 优先，缺失时用备份
    def _merged(key: str, store_key: str | None = None) -> str | list | None:
        val = entry.data.get(key)
        if val is not None and val != "" and (not isinstance(val, list) or val):
            return val
        if stored and isinstance(stored, dict):
            return stored.get(store_key or key)
        return None

    api = Shaobor95598ApiClient(
        token, 
        session, 
        None, # 不再传入 store，内部直接对接 db
        hass, 
        entry_id=entry.entry_id,
        machine_id=entry.data.get(CONF_MACHINE_ID) or hass.data.get("core.uuid")
    )
    api.set_db(db) # 注入数据库
    api.load_auth_state(
        user_token=entry_user_token or _merged(CONF_USER_TOKEN, "user_token"),
        user_id=entry.data.get(CONF_USER_ID) or (stored.get("user_id") if stored else None),
        access_token=entry_access_token or _merged(CONF_ACCESS_TOKEN, "access_token"),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN) or (stored.get("refresh_token") if stored else None),
        power_user_list=entry.data.get(CONF_POWER_USER_LIST) or (stored.get("power_user_list") if stored else None),
        selected_account_index=entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0),
        login_account=entry.data.get(CONF_LOGIN_ACCOUNT) or (stored.get("login_account") if stored else None),
    )
    
    # 设置计费配置，用于计算日均电费
    from .const import (
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
    
    api.set_billing_config({
        "billing_mode": entry.data.get(CONF_BILLING_MODE, ""),
        "average_price": entry.data.get(CONF_AVERAGE_PRICE),
        "ladder_price_1": entry.data.get(CONF_LADDER_PRICE_1),
        "ladder_price_2": entry.data.get(CONF_LADDER_PRICE_2),
        "ladder_price_3": entry.data.get(CONF_LADDER_PRICE_3),
        "price_tip": entry.data.get(CONF_PRICE_TIP),
        "price_peak": entry.data.get(CONF_PRICE_PEAK),
        "price_flat": entry.data.get(CONF_PRICE_FLAT),
        "price_valley": entry.data.get(CONF_PRICE_VALLEY),
    })
    
    # 创建数据库同步更新回调函数
    async def update_store_callback(**kwargs):
        """Callback to update Database after successful re-login."""
        # 同步更新数据库 auth 表
        if login_acc:
            await db.async_save_auth(login_acc, kwargs)
            _LOGGER.debug("[授权] 自动重连成功，已同步 Token 至数据库")
    
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

    # 数据存储 Store，用于持久化 coordinator.data（Stale Data）
    # 增加前缀迁移逻辑：将旧的 coordinator_data_ 迁移到 shaobor_data_
    old_data_key = f"{DOMAIN}/coordinator_data_{entry.entry_id}"
    new_data_key = f"{DOMAIN}/shaobor_data_{entry.entry_id}"
    
    # 尝试检查并迁移旧数据
    old_data_store = Store(hass, 1, old_data_key)
    try:
        old_data = await old_data_store.async_load()
        if old_data:
            new_data_store = Store(hass, 1, new_data_key)
            await new_data_store.async_save(old_data)
            await old_data_store.async_remove()
            _LOGGER.info("已迁移旧版数据备份文件: %s", entry.title)
        
        # 同样迁移旧版的 history_ 文件
        old_history_key = f"{DOMAIN}/history_{entry.entry_id}"
        new_history_key = f"{DOMAIN}/shaobor_history_{entry.entry_id}"
        old_hist_store = Store(hass, 1, old_history_key)
        old_hist_data = await old_hist_store.async_load()
        if old_hist_data:
            new_hist_store = Store(hass, 1, new_history_key)
            await new_hist_store.async_save(old_hist_data)
            await old_hist_store.async_remove()
            _LOGGER.info("已迁移旧版历史记录文件: %s", entry.title)
    except Exception as err:
        _LOGGER.debug("跳过存储迁移: %s", err)

    data_store = Store(hass, 1, new_data_key)
    
    from .coordinator import Shaobor95598Coordinator
    coordinator = Shaobor95598Coordinator(
        hass=hass,
        entry=entry,
        api=api,
        store=store,
        data_store=data_store,
        db=db,
    )

    # 3. 核心：启动时立即从 SQLite 数据库加载全量数据，确保实体不会变“未知”
    await coordinator.async_load_from_db()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # 挂载数据库日志处理器
    from .helpers.database import DBLogHandler
    db_handler = DBLogHandler(hass, coordinator.db)
    # 为处理器设置格式，方便在数据库中阅读
    db_handler.setFormatter(logging.Formatter('%(message)s'))
    # 获取本集成的父级记录器并添加处理器
    root_logger = logging.getLogger("custom_components.shaobor_electricity")
    # 防止重复添加
    if not any(isinstance(h, DBLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(db_handler)
        _LOGGER.debug("数据库日志处理器已挂载")

    # 1. 先把平台加载起来（确保实体在 UI 上可见并能显示缓存数据）
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 2. 异步触发初次刷新。如果刷新抛出认证失败异常，HA 会自动把已加载的卡片标记为红色，显示“重新配置”
    hass.async_create_task(coordinator.async_config_entry_first_refresh())

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 卸载时清除该账号的 reauth 标志位，确保重新载入后能再次触发
    if DOMAIN in hass.data:
        # 尝试从 api 对象获取 token（如果存在）
        api = hass.data[DOMAIN].get(entry.entry_id, {}).get("api")
        if api:
            login_acc = api._login_account or "default"
            reauth_key = f"reauth_active_{login_acc}"
            if reauth_key in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop(reauth_key)
                _LOGGER.debug("已清除全局重新认证标志位 (Account: %s)", login_acc)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry - only clear sensitive token, keep DB file."""
    _LOGGER.info("正在卸载集成实例: %s", entry.title)
    
    # 检查是否还有其他集成实例
    other_entries = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    
    # 只有在删除最后一个实例时，才清理数据库中的全局敏感信息
    if not other_entries:
        _LOGGER.info("最后一个实例已移除，正在清理数据库中的敏感授权 Token...")
        db_path = hass.config.path(".storage", DOMAIN, "shaobor_electricity.db")
        
        def _clear_sensitive_data():
            import sqlite3
            import os
            if not os.path.exists(db_path):
                return
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # 1. 清除全局备份的授权密钥
                cursor.execute("DELETE FROM shaobor_sys_config WHERE key = 'auth_token'")
                # 2. 清除所有账号的登录凭据 (Token)
                cursor.execute("DELETE FROM shaobor_auth_store")
                conn.commit()
                conn.close()
                _LOGGER.info("已成功清除数据库中的敏感授权信息 (保留历史电量数据)")
            except Exception as e:
                _LOGGER.error("清除数据库敏感信息失败: %s", e)

        await hass.async_add_executor_job(_clear_sensitive_data)
    else:
        _LOGGER.info("仍有其他实例存在，保留授权 Token。")

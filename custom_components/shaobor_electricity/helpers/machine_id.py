"""Home Assistant instance unique machine ID helper."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def async_get_machine_id(hass: Any) -> str:
    """获取 Home Assistant 实例的唯一机器绑定码 (Machine ID)。

    兼容 HA 新版本（移除了 hass.data['core.uuid']）与旧版本，
    优先从官方 helpers.instance_id 异步获取，并同步缓存至 hass.data['core.uuid']。
    """
    # 1. 优先读取已缓存的值
    cached = hass.data.get("core.uuid")
    if cached:
        return str(cached)

    # 2. 官方标准 API 获取 (支持所有新旧版本 HA)
    try:
        from homeassistant.helpers import instance_id  # type: ignore
        uuid_val = await instance_id.async_get(hass)
        if uuid_val:
            uuid_str = str(uuid_val)
            hass.data["core.uuid"] = uuid_str
            return uuid_str
    except Exception as err:
        _LOGGER.debug("从 instance_id 获取机器码失败: %s", err)

    # 3. 兜底从 .storage/core.uuid 文件读取
    try:
        from homeassistant.helpers.storage import Store  # type: ignore
        store = Store(hass, 1, "core.uuid")
        data = await store.async_load()
        if isinstance(data, dict) and data.get("uuid"):
            uuid_str = str(data["uuid"])
            hass.data["core.uuid"] = uuid_str
            return uuid_str
    except Exception as err:
        _LOGGER.debug("从 .storage/core.uuid 获取机器码失败: %s", err)

    return ""


def get_machine_id(hass: Any) -> str:
    """同步读取已缓存的机器码（需确保之前已执行过 async_get_machine_id）。"""
    return str(hass.data.get("core.uuid") or "")

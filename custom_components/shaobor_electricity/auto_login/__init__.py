"""掉线短信自动登录（模块化装配入口）。

对外只暴露这几件事，集成其余部分只需在转发平台之前调用一次 async_setup_auto_login：
  async_setup_auto_login        装配管理器（供 __init__.py 的 web / mobile 两条入口调用）
  async_setup_switch_platform   根目录 switch.py 平台入口
  async_setup_text_platform     根目录 text.py 平台入口
  async_setup_button_platform   根目录 button.py 平台入口

实体 ID 强制为 <域>.<户号>_auto_login / <域>.<户号>_code / <域>.<户号>_button / <域>.<户号>_phone。

注意：实体类在函数内延迟导入，避免选项流（只需常量）被牵连导入
homeassistant.components.switch/text/button 平台模块。
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]

from ..const import DOMAIN
from .const import DATA_AUTO_LOGIN
from .manager import AutoLoginManager

if TYPE_CHECKING:  # pragma: no cover
    from .entities import (
        AutoLoginSwitch,
        ManualLoginButton,
        SmsCodeText,
        SmsPhoneText,
    )

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "AutoLoginManager",
    "auto_login_manager",
    "async_setup_auto_login",
    "async_setup_switch_platform",
    "async_setup_text_platform",
    "async_setup_button_platform",
]


async def async_setup_auto_login(
    hass: HomeAssistant, entry: Any, coordinator: Any
) -> AutoLoginManager:
    """装配自动登录管理器（必须在 async_forward_entry_setups 之前调用）。"""
    store = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    existing = store.get(DATA_AUTO_LOGIN)
    if isinstance(existing, AutoLoginManager):
        return existing

    manager = AutoLoginManager(hass, entry, coordinator)
    await manager.async_setup()
    store[DATA_AUTO_LOGIN] = manager
    return manager


def auto_login_manager(hass: HomeAssistant, entry: Any) -> AutoLoginManager | None:
    """读取管理器（未装配时返回 None，不抛错，便于实体与选项流安全调用）。"""
    store = hass.data.get(DOMAIN)
    if not isinstance(store, dict):
        return None
    entry_store = store.get(entry.entry_id)
    if not isinstance(entry_store, dict):
        return None
    manager = entry_store.get(DATA_AUTO_LOGIN)
    return manager if isinstance(manager, AutoLoginManager) else None


def _require_manager(hass: HomeAssistant, entry: Any) -> AutoLoginManager:
    manager = auto_login_manager(hass, entry)
    if manager is None:
        raise RuntimeError(
            "自动登录管理器未装配：请确认 async_setup_auto_login 在转发平台之前被调用"
        )
    return manager


async def async_setup_switch_platform(
    hass: HomeAssistant, entry: Any, async_add_entities: Any
) -> None:
    """switch 平台入口（根目录 switch.py 转发到此）。"""
    from .entities import AutoLoginSwitch

    manager = _require_manager(hass, entry)
    async_add_entities([AutoLoginSwitch(manager, entry)])


async def async_setup_text_platform(
    hass: HomeAssistant, entry: Any, async_add_entities: Any
) -> None:
    """text 平台入口（根目录 text.py 转发到此）：验证码 + 接收短信手机号。"""
    from .entities import SmsCodeText, SmsPhoneText

    manager = _require_manager(hass, entry)
    async_add_entities([SmsCodeText(manager, entry), SmsPhoneText(manager, entry)])


async def async_setup_button_platform(
    hass: HomeAssistant, entry: Any, async_add_entities: Any
) -> None:
    """button 平台入口（根目录 button.py 转发到此）。"""
    from .entities import ManualLoginButton

    manager = _require_manager(hass, entry)
    async_add_entities([ManualLoginButton(manager, entry)])

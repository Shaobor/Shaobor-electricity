"""掉线短信自动登录：实体定义（开关 + 验证码输入框）。

实体 ID 强制为 <域>.<户号>_auto_login / <域>.<户号>_code：
先设 self.entity_id，再在 async_added_to_hass 里用实体注册表纠偏
（HA 生成建议 ID 时会覆盖实例属性，必须以注册表为准回写）。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity  # type: ignore[import-untyped]
from homeassistant.components.switch import SwitchEntity  # type: ignore[import-untyped]
from homeassistant.components.text import TextEntity, TextMode  # type: ignore[import-untyped]
from homeassistant.core import callback  # type: ignore[import-untyped]
from homeassistant.exceptions import HomeAssistantError  # type: ignore[import-untyped]
from homeassistant.helpers import entity_registry as er  # type: ignore[import-untyped]
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore[import-untyped]

from .const import (
    CODE_MAX_LENGTH,
    CODE_MIN_LENGTH,
    ENTITY_ID_SUFFIX_BUTTON,
    ENTITY_ID_SUFFIX_CODE,
    ENTITY_ID_SUFFIX_PHONE,
    ENTITY_ID_SUFFIX_SWITCH,
    PHONE_LENGTH,
    TRANSLATION_KEY_BUTTON,
    TRANSLATION_KEY_CODE,
    TRANSLATION_KEY_PHONE,
    TRANSLATION_KEY_SWITCH,
)
from .manager import AutoLoginManager
from .naming import build_device_info, build_object_id

_LOGGER = logging.getLogger(__name__)


class AutoLoginEntityBase(CoordinatorEntity):
    """公共基类：设备信息、强制实体 ID、注册到管理器。"""

    _platform_domain: str = "switch"
    _entity_kind: str = "switch"

    def __init__(
        self, manager: AutoLoginManager, entry: Any, suffix: str, unique_suffix: str
    ) -> None:
        super().__init__(manager.coordinator)
        self._manager = manager
        self._entry = entry
        self._attr_has_entity_name = True
        self._attr_device_info = build_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._forced_entity_id = (
            f"{self._platform_domain}.{build_object_id(entry, manager.coordinator)}_{suffix}"
        )
        self.entity_id = self._forced_entity_id

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._enforce_entity_id()
        self._manager.add_entity(self, self._entity_kind)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.remove_entity(self, self._entity_kind)
        await super().async_will_remove_from_hass()

    @callback
    def _enforce_entity_id(self) -> None:
        """把实体 ID 纠偏为强制格式；目标被占用时保留原 ID 并告警。"""
        if self.hass is None or self.entity_id is None:
            return
        registry = er.async_get(self.hass)
        current = registry.async_get(self.entity_id)
        if current is None or current.entity_id == self._forced_entity_id:
            self.entity_id = self._forced_entity_id
            return
        occupied = registry.async_get(self._forced_entity_id)
        if occupied is not None and occupied.entity_id != current.entity_id:
            _LOGGER.warning(
                "[自动登录] 目标实体 ID %s 已被占用，保留 %s（请清理冲突实体后重载集成）",
                self._forced_entity_id,
                current.entity_id,
            )
            return
        try:
            registry.async_update_entity(
                current.entity_id, new_entity_id=self._forced_entity_id
            )
        except Exception as err:  # noqa: BLE001 改名失败不影响实体运行
            _LOGGER.warning("[自动登录] 实体 ID 纠偏失败: %s", err)
            return
        _LOGGER.info("[自动登录] 实体 ID 已纠偏: %s → %s", current.entity_id, self._forced_entity_id)
        self.entity_id = self._forced_entity_id

    @property
    def available(self) -> bool:
        """始终可用：离线时正是需要操作它的时刻。"""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._manager.snapshot()


class AutoLoginSwitch(AutoLoginEntityBase, SwitchEntity):
    """掉线自动登录开关。"""

    _platform_domain = "switch"
    _entity_kind = "switch"

    _attr_name = "掉线自动登录"
    _attr_translation_key = TRANSLATION_KEY_SWITCH
    _attr_icon = "mdi:login-variant"

    def __init__(self, manager: AutoLoginManager, entry: Any) -> None:
        super().__init__(manager, entry, ENTITY_ID_SUFFIX_SWITCH, "auto_login")

    @property
    def is_on(self) -> bool:
        return self._manager.enabled

    @property
    def icon(self) -> str:
        return "mdi:login-variant" if self._manager.enabled else "mdi:login"

    async def async_turn_on(self, **_kwargs: Any) -> None:
        await self._manager.async_set_enabled(True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        await self._manager.async_set_enabled(False)


class ManualLoginButton(AutoLoginEntityBase, ButtonEntity):
    """手动短信登录按钮。

    仅在离线（本地缓存模式）时触发一次短信登录；在线点击不触发（只记录原因，
    可在实体属性 last_error 中看到）。与开关相互独立：开关关闭时也能手动触发。
    """

    _platform_domain = "button"
    _entity_kind = "button"

    _attr_name = "短信登录"
    _attr_translation_key = TRANSLATION_KEY_BUTTON
    _attr_icon = "mdi:message-arrow-right-outline"

    def __init__(self, manager: AutoLoginManager, entry: Any) -> None:
        super().__init__(manager, entry, ENTITY_ID_SUFFIX_BUTTON, "sms_login")

    async def async_press(self) -> None:
        await self._manager.async_manual_login()


class SmsCodeText(AutoLoginEntityBase, TextEntity):
    """短信验证码输入框：有值即触发校验，成功后自动清空。"""

    _platform_domain = "text"
    _entity_kind = "code"

    _attr_name = "短信验证码"
    _attr_translation_key = TRANSLATION_KEY_CODE
    _attr_icon = "mdi:message-text-outline"
    _attr_mode = TextMode.TEXT
    # min 必须为 0：验证码用完后由管理器清空（空值需通过校验）
    _attr_native_min = 0
    _attr_native_max = CODE_MAX_LENGTH

    def __init__(self, manager: AutoLoginManager, entry: Any) -> None:
        super().__init__(manager, entry, ENTITY_ID_SUFFIX_CODE, "sms_code")
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """写入即提交；不阻塞服务调用（校验完成可能耗时较久）。"""
        self._attr_native_value = value if value is not None else ""
        self.async_write_ha_state()
        code = (self._attr_native_value or "").strip()
        if len(code) < CODE_MIN_LENGTH:
            return
        self.hass.async_create_task(self._manager.async_submit_code(code))


class SmsPhoneText(AutoLoginEntityBase, TextEntity):
    """短信接收手机号。

    留空 = 跟随当前登录账号（entry.data["login_account"]）。
    95598 的 loginAccount 未必是机主手机号，收不到短信时可在此显式指定；
    修改后立即生效（下一次发码即使用新号码），并作废发往旧号码的等待窗口。
    """

    _platform_domain = "text"
    _entity_kind = "phone"

    _attr_name = "短信接收手机号"
    _attr_translation_key = TRANSLATION_KEY_PHONE
    _attr_icon = "mdi:cellphone-message"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = PHONE_LENGTH

    def __init__(self, manager: AutoLoginManager, entry: Any) -> None:
        super().__init__(manager, entry, ENTITY_ID_SUFFIX_PHONE, "sms_phone")
        # 显示用户已指定的号码；留空表示跟随登录账号（实际使用的号码见属性 sms_phone）
        self._attr_native_value = manager.sms_phone

    async def async_set_value(self, value: str) -> None:
        phone = (value or "").strip()
        try:
            await self._manager.async_set_sms_phone(phone)
        except ValueError as err:
            # 直接抛出可让 UI 弹出明确提示，同时保持原值不变
            raise HomeAssistantError(str(err)) from err
        self._attr_native_value = phone
        self.async_write_ha_state()

    @callback
    def async_clear_value(self) -> None:
        """清空输入框（登录成功 / 校验失败 / 超时 / 关闭开关时由管理器调用）。"""
        if not self._attr_native_value:
            return
        self._attr_native_value = ""
        if self.hass is not None:
            self.async_write_ha_state()


__all__ = [
    "AutoLoginEntityBase",
    "AutoLoginSwitch",
    "ManualLoginButton",
    "SmsCodeText",
    "SmsPhoneText",
]

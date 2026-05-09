"""Sensor definition."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore
from ..const import DOMAIN

class Shaobor95598SensorBase(CoordinatorEntity, SensorEntity):
    """Base class for 95598 sensors. 数据均来自配置时选择的户号."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor. 设备名使用配置时选择的户号."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True
        pl = entry.data.get("power_user_list") or []
        idx = min(entry.data.get("selected_account_index", 0), len(pl) - 1) if pl else -1
        cons_no = (pl[idx].get("consNo_dst") or pl[idx].get("consNoDst") or "") if idx >= 0 else ""
        device_name = cons_no or entry.data.get("username") or entry.title.replace("Shaobor_95598 ", "").strip("()") or "95598"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"电费账户 ({device_name})",
            "manufacturer": "Shaobor",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available. 认证过期时也保持可用，显示最后一次的值."""
        return True


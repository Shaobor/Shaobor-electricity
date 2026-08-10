"""Power-grid maintenance notice sensor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorStateClass  # type: ignore

from .base import Shaobor95598SensorBase


class Shaobor95598PowerGridMaintenanceSensor(Shaobor95598SensorBase):
    """Show maintenance notices for the active account's administrative area."""

    _attr_name = "电网检修公告"
    _attr_icon = "mdi:transmission-tower"
    _attr_native_unit_of_measurement = "条"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_power_grid_maintenance"

    @property
    def native_value(self) -> int:
        notice_data = (self.coordinator.data or {}).get("power_grid_maintenance_notices") or {}
        notices = notice_data.get("notices") if isinstance(notice_data, dict) else []
        return len(notices) if isinstance(notices, list) else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the matched area and complete notice records for automations."""
        notice_data = (self.coordinator.data or {}).get("power_grid_maintenance_notices") or {}
        if not isinstance(notice_data, dict):
            return {"公告列表": []}

        attrs: dict[str, Any] = {
            "公告列表": notice_data.get("notices") if isinstance(notice_data.get("notices"), list) else [],
        }
        fields = {
            "地区": "region",
            "行政区划代码": "area_no",
            "匹配供电单位编号": "org_no",
            "最后查询": "updated_at",
            "查询错误": "error",
        }
        for attribute, key in fields.items():
            value = notice_data.get(key)
            if value:
                attrs[attribute] = value
        return attrs

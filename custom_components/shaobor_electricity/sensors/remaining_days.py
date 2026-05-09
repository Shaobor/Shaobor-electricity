"""Sensor definition."""
from __future__ import annotations

from homeassistant.components.sensor import SensorStateClass  # type: ignore
from .base import Shaobor95598SensorBase

class Shaobor95598RemainingDaysSensor(Shaobor95598SensorBase):
    """预计可用天数."""

    _attr_name = "预计可用"
    _attr_translation_key = "remaining_days"
    _attr_native_unit_of_measurement = "天"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_remaining_days"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data or {}
        # 优先读根目录字段
        val = data.get("remaining_days")
        if val is None:
            # 兜底读原始包
            api_data = data.get("_raw_api") or {}
            val = api_data.get("remaining_days")
        return val



"""Yearly usage sensor."""
from __future__ import annotations

import logging
from typing import Any
from homeassistant.const import UnitOfEnergy  # type: ignore
from homeassistant.components.sensor import SensorStateClass  # type: ignore
from .base import Shaobor95598SensorBase

_LOGGER = logging.getLogger(__name__)

class Shaobor95598YearlyUsageSensor(Shaobor95598SensorBase):
    """每年电量：显示最新一年电量，每年详细数据在属性里."""

    _attr_name = "每年电量"
    _attr_translation_key = "yearly_usage"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-bell-curve"
    _attr_suggested_display_precision = 2

    def _safe_float(self, val):
        if val is None or val == "" or val == "-":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_yearly_usage"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        yearlist = data.get("yearlist", [])
        if yearlist:
            latest = yearlist[0]
            val = latest.get("yearEleNum")
            if val is not None:
                return round(self._safe_float(val), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        yearlist = data.get("yearlist", [])

        attrs: dict[str, Any] = {}
        if yearlist:
            all_years = []
            for item in yearlist:
                y_info = {
                    "年份": item.get("year"),
                    "年用电量": item.get("yearEleNum"),
                    "年电费": f"{item.get('yearEleCost', 0)}元",
                }
                if item.get("yearTPq"): y_info["尖峰"] = item["yearTPq"]
                if item.get("yearPPq"): y_info["峰"] = item["yearPPq"]
                if item.get("yearNPq"): y_info["平"] = item["yearNPq"]
                if item.get("yearVPq"): y_info["谷"] = item["yearVPq"]
                if item.get("is_official"): y_info["来源"] = "官方结算"
                all_years.append(y_info)
            attrs["每年数据"] = all_years
        return attrs

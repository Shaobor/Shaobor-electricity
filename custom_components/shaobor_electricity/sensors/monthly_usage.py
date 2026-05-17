"""Monthly usage sensor."""
from __future__ import annotations

import logging
from typing import Any
from homeassistant.const import UnitOfEnergy  # type: ignore
from homeassistant.components.sensor import SensorStateClass  # type: ignore
from .base import Shaobor95598SensorBase

_LOGGER = logging.getLogger(__name__)

class Shaobor95598MonthlyUsageSensor(Shaobor95598SensorBase):
    """每月电量：显示最新一月电量，每月详细数据在属性里."""

    _attr_name = "每月电量"
    _attr_translation_key = "monthly_usage"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-bar"
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
        return f"{self._entry.entry_id}_monthly_usage"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        monthlist = data.get("monthlist", [])
        if monthlist:
            latest = monthlist[0]
            val = latest.get("monthEleNum")
            if val is not None:
                return round(self._safe_float(val), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        monthlist = data.get("monthlist", [])

        attrs: dict[str, Any] = {}
        if monthlist:
            all_months = []
            for item in monthlist[:24]:  # 最近 24 个月
                m_info = {
                    "月份": item.get("month"),
                    "月用电量": item.get("monthEleNum"),
                    "月电费": f"{item.get('monthEleCost', 0)}元",
                }
                if item.get("monthTPq"): m_info["尖峰"] = item["monthTPq"]
                if item.get("monthPPq"): m_info["峰"] = item["monthPPq"]
                if item.get("monthNPq"): m_info["平"] = item["monthNPq"]
                if item.get("monthVPq"): m_info["谷"] = item["monthVPq"]
                if item.get("is_official"): m_info["来源"] = "官方结算"
                all_months.append(m_info)
            attrs["每月数据"] = all_months
        return attrs

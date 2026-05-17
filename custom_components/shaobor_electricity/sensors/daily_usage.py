"""Sensor definition."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorStateClass  # type: ignore
from homeassistant.const import UnitOfEnergy  # type: ignore
from .base import Shaobor95598SensorBase
from ..helpers.fee_calculator import calculate_daily_fee
from ..helpers.regional_prices import get_region_price_config, get_region_name

_LOGGER = logging.getLogger(__name__)

class Shaobor95598DailyUsageSensor(Shaobor95598SensorBase):
    """每日电量：显示最新一天电量，每日详细数据在属性里."""

    _attr_name = "每日电量"
    _attr_translation_key = "daily_usage"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:chart-line"
    _attr_state_class = SensorStateClass.MEASUREMENT
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
        return f"{self._entry.entry_id}_daily_usage"

    @property
    def native_value(self) -> float | None:
        """显示最新一天的用电量."""
        data = self.coordinator.data or {}
        daylist = data.get("daylist", [])
        
        if daylist:
            # daylist 已经是按日期逆序排好的
            latest_day = daylist[0]
            day_ele_pq = latest_day.get("dayEleNum")
            if day_ele_pq is not None:
                return round(self._safe_float(day_ele_pq), 2)
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """显示每日用电量详细数据."""
        data = self.coordinator.data or {}
        daylist = data.get("daylist", []) # 已经在聚合器里算好并排好序了
        
        attrs: dict[str, Any] = {}
        billing_mode = self._entry.data.get("billing_mode", "year_ladder")
        
        api_data = data.get("_raw_api") or data
        if "returnCode" in api_data: attrs["返回码"] = api_data["returnCode"]
        if "returnMsg" in api_data: attrs["返回消息"] = api_data["returnMsg"]
        
        if daylist:
            all_days = []
            # 限制属性显示为最近 30 天，防止触发 HA 的 16KB 警告
            # 数据库中依然保存着全量历史，此处仅为 UI 展示精简
            display_days = daylist[:30] 
            
            for item in display_days:
                day_info = {
                    "日期": item.get("day"), 
                    "当日用电量": item.get("dayEleNum"), 
                    "当日电费": f"{item.get('dayEleCost', 0)}元"
                }
                if item.get("dayTPq"): day_info["尖峰时段"] = item["dayTPq"]
                if item.get("dayPPq"): day_info["峰时段"] = item["dayPPq"]
                if item.get("dayNPq"): day_info["平时段"] = item["dayNPq"]
                if item.get("dayVPq"): day_info["谷时段"] = item["dayVPq"]
                all_days.append(day_info)
            
            attrs["每日数据"] = all_days
            if len(daylist) > 30:
                attrs["提示"] = f"仅显示最近30天，完整{len(daylist)}天数据已存入数据库"
        
        return attrs

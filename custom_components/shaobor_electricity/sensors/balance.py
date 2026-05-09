"""Sensor definition."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass  # type: ignore
from .base import Shaobor95598SensorBase

_LOGGER = logging.getLogger(__name__)

class Shaobor95598BalanceSensor(Shaobor95598SensorBase):
    """实时电费（账户余额）."""

    _attr_name = "实时电费"
    _attr_translation_key = "balance"
    _attr_native_unit_of_measurement = "元"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
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
        return f"{self._entry.entry_id}_balance"

    @property
    def native_value(self) -> float | None:
        """返回余额或本月预估电费."""
        data = self.coordinator.data or {}
        
        # 优先读取根目录字段 (Coordinator 已帮我们同步)
        balance = data.get("balance")
        esti_amt = data.get("esti_amt")
        
        # 如果根目录没拿到，再看原始包
        if balance is None and esti_amt is None:
            api_data = data.get("_raw_api") or {}
            balance = api_data.get("balance")
            fee_data = api_data.get("electricity_fee_detail") or {}
            esti_amt = fee_data.get("estiAmt")
            
        # 预付费用户：返回余额
        if balance is not None:
            return round(self._safe_float(balance), 2)
        
        # 非预付费用户：返回本月预估电费
        if esti_amt is not None:
            return round(self._safe_float(esti_amt), 2)
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """显示 c05/f01 返回的详细电费数据."""
        data = self.coordinator.data or {}
        api_data = data.get("_raw_api") or data
        fee_data = api_data.get("electricity_fee_detail") or {}
        
        attrs: dict[str, str | float] = {}
        
        # 预付费余额（账户余额）
        if "prepayBal" in fee_data:
            attrs["预付费余额"] = round(self._safe_float(fee_data["prepayBal"]), 2)
        
        # 总电量
        if "totalPq" in fee_data:
            attrs["总电量"] = round(self._safe_float(fee_data["totalPq"]), 2)
        
        # 总金额（应缴金额）
        if "sumMoney" in fee_data:
            attrs["总金额"] = round(self._safe_float(fee_data["sumMoney"]), 2)
        
        # 预估金额（后付费用户的本月预估电费）
        if "estiAmt" in fee_data:
            attrs["预估金额"] = round(self._safe_float(fee_data["estiAmt"]), 2)
        
        # 历史欠费
        if "historyOwe" in fee_data:
            attrs["历史欠费"] = round(self._safe_float(fee_data["historyOwe"]), 2)
        
        # 违约金
        if "penalty" in fee_data:
            attrs["违约金"] = round(self._safe_float(fee_data["penalty"]), 2)
        
        # 刷新时间（优先使用 amtTime，如果没有则使用 date）
        refresh_time = fee_data.get("amtTime") or fee_data.get("date")
        if refresh_time:
            attrs["刷新时间"] = refresh_time
        
        return attrs

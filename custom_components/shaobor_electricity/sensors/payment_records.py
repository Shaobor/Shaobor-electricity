"""Sensor definition."""
from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorStateClass  # type: ignore
from .base import Shaobor95598SensorBase

class Shaobor95598PaymentRecordsSensor(Shaobor95598SensorBase):
    """缴费记录：显示缴费记录总数，完整记录在属性里."""

    _attr_name = "缴费记录"
    _attr_translation_key = "payment_records"
    _attr_native_unit_of_measurement = "条"
    _attr_icon = "mdi:receipt-text"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_payment_records"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> int | None:
        """显示缴费记录总数."""
        data = self.coordinator.data or {}
        records = data.get("payment_records", [])
        if isinstance(records, list):
            return len(records)
        return 0

    @property
    def extra_state_attributes(self) -> dict:
        """显示全量缴费记录，对齐旧版格式."""
        data = self.coordinator.data or {}
        records = data.get("payment_records", [])
        
        # 对齐旧版：键名必须是 payList
        if isinstance(records, list):
            return {
                "payList": records,
                "数据源": "数据库 (SQLite)",
                "最后同步": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        return {"payList": []}



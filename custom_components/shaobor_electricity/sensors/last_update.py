"""Sensor definition."""
from __future__ import annotations

from datetime import datetime, timezone
from homeassistant.components.sensor import SensorDeviceClass  # type: ignore
from .base import Shaobor95598SensorBase

class Shaobor95598LastUpdateSensor(Shaobor95598SensorBase):
    """最后更新时间：每10分钟刷新 token 并拉取数据的任务最近一次执行时间."""

    _attr_name = "最后更新时间"
    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_last_update"

    @property
    def native_value(self) -> datetime | None:
        data = self.coordinator.data or {}
        ts = data.get("last_update")
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None



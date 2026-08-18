"""Sensor showing whether live or cached electricity data is displayed."""
from __future__ import annotations

from .base import Shaobor95598SensorBase


class Shaobor95598DataModeSensor(Shaobor95598SensorBase):
    """Show the current live API or local cache data mode."""

    _attr_name = "电费数据模式"
    _attr_translation_key = "data_mode"
    _attr_icon = "mdi:database-sync"

    _MODE_LABELS = {
        "network": "网络模式",
        "local_cache": "本地缓存模式",
    }

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_data_mode"

    @property
    def native_value(self) -> str:
        mode = self.coordinator.data_mode
        return self._MODE_LABELS.get(mode, "本地缓存模式")

    @property
    def extra_state_attributes(self) -> dict[str, str | float | None]:
        return {
            "data_mode": self.coordinator.data_mode,
            "last_api_success": self.coordinator.last_api_success,
            "last_error_reason": self.coordinator.last_error_reason,
        }

"""Current electricity price sensor for the Home Assistant Energy dashboard."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.event import async_track_time_change

from .base import Shaobor95598SensorBase
from ..helpers.regional_prices import get_region_price_config


class Shaobor95598ElectricityPriceSensor(Shaobor95598SensorBase):
    """Expose the currently applicable electricity price in CNY/kWh."""

    _attr_name = "电费单价"
    _attr_translation_key = "electricity_price"
    _attr_icon = "mdi:cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "CNY/kWh"
    _attr_suggested_display_precision = 4

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_electricity_price"

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "", "-") else default
        except (TypeError, ValueError):
            return default

    async def async_added_to_hass(self) -> None:
        """Refresh the state exactly when Sichuan's valley period changes."""
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_change(self.hass, self._handle_tariff_boundary, hour=[7, 23], minute=0, second=0))

    def _handle_tariff_boundary(self, _now: datetime) -> None:
        self.async_write_ha_state()

    def _accumulated_usage(self, now: datetime) -> tuple[float, float]:
        """Return calendar-year and current-month consumption from daily records."""
        year, month = 0.0, 0.0
        for item in (self.coordinator.data or {}).get("daylist", []):
            date = str(item.get("day", ""))
            usage = self._float(item.get("dayEleNum"))
            if date.startswith(str(now.year)):
                year += usage
            if date.startswith(now.strftime("%Y-%m")):
                month += usage
        return year, month

    def _tier(self, mode: str, now: datetime, data: dict[str, Any]) -> int:
        year_usage, month_usage = self._accumulated_usage(now)
        cons_no = (self.coordinator.data or {}).get("selected_cons_no", "")
        regional = get_region_price_config(cons_no) if cons_no else None
        default_l1 = regional["ladder_level_1"] if regional else 2040
        default_l2 = regional["ladder_level_2"] if regional else 3240

        if mode == "month_ladder_tou_seasonal":
            normal_l1 = self._float(data.get("normal_ladder_level_1"), 180)
            normal_l2 = self._float(data.get("normal_ladder_level_2"), 280)
            summer_l1 = self._float(data.get("summer_ladder_level_1"), 260)
            summer_l2 = self._float(data.get("summer_ladder_level_2"), 460)
            if now.year >= 2027:
                l1 = sum(summer_l1 if 7 <= month <= 9 else normal_l1 for month in range(1, now.month + 1))
                l2 = sum(summer_l2 if 7 <= month <= 9 else normal_l2 for month in range(1, now.month + 1))
                usage = year_usage
            else:
                l1, l2 = (summer_l1, summer_l2) if 7 <= now.month <= 9 else (normal_l1, normal_l2)
                usage = month_usage
        elif "month_ladder" in mode:
            l1 = self._float(data.get("ladder_level_1"), 200)
            l2 = self._float(data.get("ladder_level_2"), 400)
            usage = month_usage
        else:
            l1 = self._float(data.get("ladder_level_1"), default_l1)
            l2 = self._float(data.get("ladder_level_2"), default_l2)
            usage = year_usage
        return 1 if usage <= l1 else (2 if usage <= l2 else 3)

    @property
    def native_value(self) -> float | None:
        """Return the price applicable at the current time and ladder tier."""
        now = datetime.now()
        data = self._entry.data
        mode = data.get("billing_mode", "year_ladder")
        if mode == "year_ladder_tou_seasonal":  # Compatibility with v2.2.2.
            mode = "month_ladder_tou_seasonal"
        tier = self._tier(mode, now, data)

        if mode == "average":
            return round(self._float(data.get("average_price"), 0.51), 4)

        if "tou" not in mode and mode != "charging_pile":
            cons_no = (self.coordinator.data or {}).get("selected_cons_no", "")
            regional = get_region_price_config(cons_no) if cons_no else None
            price = data.get(f"ladder_price_{tier}")
            if price is None and regional:
                price = regional[f"ladder_price_{tier}"]
            return round(self._float(price, 0.0), 4) if price is not None else None

        is_valley = now.hour >= 23 or now.hour < 7
        period = "valley" if is_valley else "peak"
        if mode == "month_ladder_tou_seasonal":
            season = "wet" if 6 <= now.month <= 10 else "dry"
            price = data.get(f"season_{season}_ladder_{tier}_{period}")
        elif mode == "month_ladder_tou_variable":
            price = data.get(f"month_{now.month:02d}_ladder_{tier}_{period}")
        else:
            base = self._float(data.get(f"price_{period}"), 0.0)
            if mode == "charging_pile":
                price = base
            else:
                cons_no = (self.coordinator.data or {}).get("selected_cons_no", "")
                regional = get_region_price_config(cons_no) if cons_no else None
                p1 = self._float(data.get("ladder_price_1"), regional["ladder_price_1"] if regional else 0.0)
                pt = self._float(data.get(f"ladder_price_{tier}"), regional[f"ladder_price_{tier}"] if regional else p1)
                price = base + pt - p1
        return round(self._float(price, 0.0), 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        now = datetime.now()
        return {
            "当前时段": "低谷" if now.hour >= 23 or now.hour < 7 else "峰/平",
            "低谷时段": "23:00-07:00",
            "说明": "当前生效电价；能源面板可将此实体作为电价实体。",
        }

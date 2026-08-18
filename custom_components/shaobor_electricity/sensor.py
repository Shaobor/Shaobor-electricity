"""Sensor platform for shaobor_electricity."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry  # type: ignore[import-untyped]
from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore[import-untyped]

from .const import DOMAIN
from .sensors import (
    Shaobor95598BalanceSensor,
    Shaobor95598RemainingDaysSensor,
    Shaobor95598LastUpdateSensor,
    Shaobor95598PaymentRecordsSensor,
    Shaobor95598ElectricityFeeSensor,
    Shaobor95598DailyUsageSensor,
    Shaobor95598StandardEntitySensor,
    Shaobor95598MonthlyUsageSensor,
    Shaobor95598YearlyUsageSensor,
    Shaobor95598ElectricityPriceSensor,
    Shaobor95598PowerGridMaintenanceSensor,
    Shaobor95598DataModeSensor,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    sensors = [
        Shaobor95598BalanceSensor(coordinator, entry),
        Shaobor95598RemainingDaysSensor(coordinator, entry),
        Shaobor95598LastUpdateSensor(coordinator, entry),
        Shaobor95598PaymentRecordsSensor(coordinator, entry),
        Shaobor95598ElectricityFeeSensor(coordinator, entry),
        Shaobor95598DailyUsageSensor(coordinator, entry),
        Shaobor95598MonthlyUsageSensor(coordinator, entry),
        Shaobor95598YearlyUsageSensor(coordinator, entry),
        Shaobor95598ElectricityPriceSensor(coordinator, entry),
        Shaobor95598StandardEntitySensor(coordinator, entry),
        Shaobor95598PowerGridMaintenanceSensor(coordinator, entry),
        Shaobor95598DataModeSensor(coordinator, entry),
    ]
    async_add_entities(sensors)

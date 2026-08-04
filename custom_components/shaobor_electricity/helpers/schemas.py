"""Schemas for config flow and options flow."""
from typing import Any
import voluptuous as vol  # type: ignore[import-untyped]

from ..const import (
    CONF_LADDER_LEVEL_1,
    CONF_LADDER_LEVEL_2,
    CONF_LADDER_PRICE_1,
    CONF_LADDER_PRICE_2,
    CONF_LADDER_PRICE_3,
    CONF_PRICE_TIP,
    CONF_PRICE_PEAK,
    CONF_PRICE_FLAT,
    CONF_PRICE_VALLEY,
    CONF_YEAR_LADDER_START,
    CONF_AVERAGE_PRICE,
)

def get_year_ladder_tou_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for year ladder TOU config."""
    return vol.Schema({
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 2040)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 3240)): int,
        vol.Required(CONF_PRICE_TIP, default=defaults.get(CONF_PRICE_TIP, 0.81)): vol.Coerce(float),
        vol.Required(CONF_PRICE_PEAK, default=defaults.get(CONF_PRICE_PEAK, 0.56)): vol.Coerce(float),
        vol.Required(CONF_PRICE_FLAT, default=defaults.get(CONF_PRICE_FLAT, 0.51)): vol.Coerce(float),
        vol.Required(CONF_PRICE_VALLEY, default=defaults.get(CONF_PRICE_VALLEY, 0.51)): vol.Coerce(float),
        vol.Optional(CONF_YEAR_LADDER_START, default=defaults.get(CONF_YEAR_LADDER_START, "0101")): str,
    })

def get_year_ladder_tou_seasonal_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for annual ladder TOU with wet/dry season prices."""
    schema_dict = {
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 2400)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 3900)): int,
        vol.Optional(CONF_YEAR_LADDER_START, default=defaults.get(CONF_YEAR_LADDER_START, "0101")): str,
    }
    for season in ("wet", "dry"):
        for tier in range(1, 4):
            for period in ("tip", "peak", "flat", "valley"):
                key = f"season_{season}_ladder_{tier}_{period}"
                schema_dict[vol.Required(key, default=defaults.get(key, 0.0))] = vol.Coerce(float)
    return vol.Schema(schema_dict)

def get_charging_pile_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for charging pile config (TOU without ladders)."""
    return vol.Schema({
        vol.Required(CONF_PRICE_TIP, default=defaults.get(CONF_PRICE_TIP, 0.81)): vol.Coerce(float),
        vol.Required(CONF_PRICE_PEAK, default=defaults.get(CONF_PRICE_PEAK, 0.56)): vol.Coerce(float),
        vol.Required(CONF_PRICE_FLAT, default=defaults.get(CONF_PRICE_FLAT, 0.51)): vol.Coerce(float),
        vol.Required(CONF_PRICE_VALLEY, default=defaults.get(CONF_PRICE_VALLEY, 0.51)): vol.Coerce(float),
    })

def get_year_ladder_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for year ladder config."""
    return vol.Schema({
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 2040)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 3240)): int,
        vol.Required(CONF_LADDER_PRICE_1, default=defaults.get(CONF_LADDER_PRICE_1, 0.51)): vol.Coerce(float),
        vol.Required(CONF_LADDER_PRICE_2, default=defaults.get(CONF_LADDER_PRICE_2, 0.56)): vol.Coerce(float),
        vol.Required(CONF_LADDER_PRICE_3, default=defaults.get(CONF_LADDER_PRICE_3, 0.81)): vol.Coerce(float),
        vol.Optional(CONF_YEAR_LADDER_START, default=defaults.get(CONF_YEAR_LADDER_START, "0101")): str,
    })

def get_month_ladder_tou_variable_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for month ladder TOU variable config."""
    schema_dict = {
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 200)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 400)): int,
    }
    for month in range(1, 13):
        # 第1档
        schema_dict[vol.Required(f"month_{month:02d}_ladder_1_tip", default=defaults.get(f"month_{month:02d}_ladder_1_tip", 0.81))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_1_peak", default=defaults.get(f"month_{month:02d}_ladder_1_peak", 0.56))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_1_flat", default=defaults.get(f"month_{month:02d}_ladder_1_flat", 0.51))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_1_valley", default=defaults.get(f"month_{month:02d}_ladder_1_valley", 0.31))] = vol.Coerce(float)
        # 第2档
        schema_dict[vol.Required(f"month_{month:02d}_ladder_2_tip", default=defaults.get(f"month_{month:02d}_ladder_2_tip", 0.91))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_2_peak", default=defaults.get(f"month_{month:02d}_ladder_2_peak", 0.66))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_2_flat", default=defaults.get(f"month_{month:02d}_ladder_2_flat", 0.61))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_2_valley", default=defaults.get(f"month_{month:02d}_ladder_2_valley", 0.41))] = vol.Coerce(float)
        # 第3档
        schema_dict[vol.Required(f"month_{month:02d}_ladder_3_tip", default=defaults.get(f"month_{month:02d}_ladder_3_tip", 1.01))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_3_peak", default=defaults.get(f"month_{month:02d}_ladder_3_peak", 0.76))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_3_flat", default=defaults.get(f"month_{month:02d}_ladder_3_flat", 0.71))] = vol.Coerce(float)
        schema_dict[vol.Required(f"month_{month:02d}_ladder_3_valley", default=defaults.get(f"month_{month:02d}_ladder_3_valley", 0.51))] = vol.Coerce(float)
    return vol.Schema(schema_dict)

def get_month_ladder_tou_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for month ladder TOU config."""
    return vol.Schema({
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 200)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 400)): int,
        vol.Required(CONF_PRICE_TIP, default=defaults.get(CONF_PRICE_TIP, 0.81)): vol.Coerce(float),
        vol.Required(CONF_PRICE_PEAK, default=defaults.get(CONF_PRICE_PEAK, 0.56)): vol.Coerce(float),
        vol.Required(CONF_PRICE_FLAT, default=defaults.get(CONF_PRICE_FLAT, 0.51)): vol.Coerce(float),
        vol.Required(CONF_PRICE_VALLEY, default=defaults.get(CONF_PRICE_VALLEY, 0.51)): vol.Coerce(float),
    })

def get_month_ladder_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for month ladder config."""
    return vol.Schema({
        vol.Required(CONF_LADDER_LEVEL_1, default=defaults.get(CONF_LADDER_LEVEL_1, 200)): int,
        vol.Required(CONF_LADDER_LEVEL_2, default=defaults.get(CONF_LADDER_LEVEL_2, 400)): int,
        vol.Required(CONF_LADDER_PRICE_1, default=defaults.get(CONF_LADDER_PRICE_1, 0.51)): vol.Coerce(float),
        vol.Required(CONF_LADDER_PRICE_2, default=defaults.get(CONF_LADDER_PRICE_2, 0.56)): vol.Coerce(float),
        vol.Required(CONF_LADDER_PRICE_3, default=defaults.get(CONF_LADDER_PRICE_3, 0.81)): vol.Coerce(float),
    })

def get_average_config_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Get schema for average config."""
    return vol.Schema({
        vol.Required(CONF_AVERAGE_PRICE, default=defaults.get(CONF_AVERAGE_PRICE, 0.51)): vol.Coerce(float),
    })

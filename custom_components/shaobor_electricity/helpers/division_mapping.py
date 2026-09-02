"""Lookup of a power account's administrative division from its service-office code."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "division_mapping.json"
_DIRECT_MUNICIPALITIES = {"110000", "120000", "310000", "500000"}


@dataclass(frozen=True, slots=True)
class DivisionMatch:
    """Resolved administrative division and matched power-company record."""

    province_code: str
    province_name: str
    city_code: str | None
    city_name: str | None
    city_org_code: str | None
    district_code: str | None
    district_name: str | None
    power_company: str
    org_code: str

    @property
    def display_name(self) -> str:
        """Return a de-duplicated human-readable hierarchy."""
        names = [self.province_name]
        for name in (self.city_name, self.district_name):
            if name and name not in names and name != "市辖区":
                names.append(name)
        return "·".join(names)


class DivisionMapping:
    """In-memory index generated from 95598 divisionGb JSON files."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._provinces: dict[str, str] = payload.get("provinces", {})
        self._by_code = {item["code"]: item for item in payload.get("records", []) if item.get("code")}
        self._org_records = [
            item for item in self._by_code.values() if str(item.get("org_code") or "")
        ]

    @staticmethod
    def _digits(value: str | None) -> str:
        return re.sub(r"\D", "", value or "")

    def lookup_org_no(self, org_no: str | None) -> DivisionMatch | None:
        """Match a service-office number using the longest known org-code prefix.

        Some account responses use a final digit for a subordinate service point,
        while the division table records the parent customer-service centre.  If a
        strict prefix match reaches only city level, accept a district record that
        differs solely in that final digit.
        """
        normalized = self._digits(org_no)
        if not normalized:
            return None
        matches = [
            item for item in self._org_records
            if normalized.startswith(self._digits(str(item.get("org_code"))))
        ]
        if matches:
            record = max(
                matches,
                key=lambda item: (
                    len(self._digits(str(item["org_code"]))), item.get("level", 0)
                ),
            )
            if record.get("level", 0) >= 2:
                return self._build_match(record)

        # E.g. account orgNo 374092303 and table org_code 374092301 both belong
        # to the Feicheng customer-service centre.  Require all digits except the
        # final one to match so neighbouring districts cannot be selected.
        final_digit_matches = [
            item for item in self._org_records
            if item.get("level", 0) >= 2
            and len(normalized) == len(self._digits(str(item["org_code"])))
            and len(normalized) > 1
            and normalized[:-1] == self._digits(str(item["org_code"]))[:-1]
        ]
        if not final_digit_matches:
            return self._build_match(record) if matches else None
        record = max(
            final_digit_matches,
            key=lambda item: (len(self._digits(str(item["org_code"]))), item.get("level", 0)),
        )
        return self._build_match(record)

    def _build_match(self, record: dict[str, Any]) -> DivisionMatch:
        """Resolve province/city/district through parent_code links."""
        nodes = [record]
        parent = record.get("parent_code")
        while parent and parent in self._by_code:
            node = self._by_code[parent]
            nodes.append(node)
            parent = node.get("parent_code")

        province_code = f"{str(record['code'])[:2]}0000"
        province_name = self._provinces.get(province_code, "未知地区")
        city = next((node for node in nodes if node.get("level") == 1), None)
        district = next((node for node in nodes if node.get("level") >= 2), None)

        city_code = city.get("code") if city else None
        city_name = city.get("name") if city else None
        if province_code in _DIRECT_MUNICIPALITIES:
            city_code, city_name = province_code, province_name

        return DivisionMatch(
            province_code=province_code,
            province_name=province_name,
            city_code=city_code,
            city_name=city_name,
            city_org_code=str(city.get("org_code") or "") if city else None,
            district_code=district.get("code") if district else None,
            district_name=district.get("name") if district else None,
            power_company=str(record.get("power_company") or ""),
            org_code=str(record.get("org_code") or ""),
        )


async def async_load_division_mapping(hass: HomeAssistant) -> DivisionMapping | None:
    """Load the bundled mapping without blocking Home Assistant's event loop."""
    if not DATA_PATH.is_file():
        return None

    def _load() -> DivisionMapping:
        with DATA_PATH.open(encoding="utf-8") as file:
            return DivisionMapping(json.load(file))

    return await hass.async_add_executor_job(_load)

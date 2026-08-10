"""Sensor definition."""
from __future__ import annotations

from .base import Shaobor95598SensorBase
from ..const import DOMAIN
from ..helpers.regional_prices import get_region_name

class Shaobor95598ElectricityFeeSensor(Shaobor95598SensorBase):
    """用户信息：显示户号，详细数据在属性里."""

    _attr_name = "用户信息"
    _attr_translation_key = "user_info"
    _attr_icon = "mdi:account-details"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_electricity_fee"

    @property
    def native_value(self) -> str | None:
        """显示户号作为传感器的值."""
        data = self.coordinator.data or {}
        return data.get("selected_cons_no") or "未知"

    @property
    def extra_state_attributes(self) -> dict:
        """显示户号相关的基本信息."""
        data = self.coordinator.data or {}
        attrs: dict[str, str] = {}
        
        # 户号
        cons_no = data.get("selected_cons_no") or ""
        if cons_no:
            attrs["户号"] = cons_no
            
            # 根据户号自动识别地区
            region_name = get_region_name(cons_no)
            attrs["识别地区"] = region_name
        
        # 用电地址
        addr = data.get("selected_elec_addr") or ""
        if addr:
            attrs["用电地址"] = addr
        
        # 户主名字
        owner = data.get("selected_owner_name") or ""
        if owner:
            attrs["户主名字"] = owner
        
        # 供电所
        org = data.get("selected_org_name") or ""
        if org:
            attrs["供电所"] = org
        
        # 供电所编号
        org_no = data.get("selected_org_no") or ""
        if org_no:
            attrs["供电所编号"] = org_no

            mapping = self.hass.data.get(DOMAIN, {}).get("division_mapping")
            match = mapping.lookup_org_no(org_no) if mapping else None
            if match:
                attrs["实际归属地区"] = match.display_name
                attrs["行政区划代码"] = match.district_code or match.city_code or match.province_code
                attrs["匹配供电单位编号"] = match.org_code
        
        return attrs


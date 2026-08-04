"""Standard entity sensor."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorStateClass, SensorDeviceClass  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore
from .base import Shaobor95598SensorBase
from ..helpers.regional_prices import get_region_price_config, get_region_name
from ..helpers.usage_aggregator import UsageAggregator

_LOGGER = logging.getLogger(__name__)

class Shaobor95598StandardEntitySensor(Shaobor95598SensorBase):
    """电网标准实体：完全兼容 electricity-info-card 格式."""

    _attr_name = "电网标准实体"
    _attr_translation_key = "standard_entity"
    _attr_native_unit_of_measurement = "元"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:flash"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._aggregator = UsageAggregator(self.hass, entry.entry_id)
        self._cached_daylist = []
        self._cached_monthlist = []
        self._cached_yearlist = []

    def _safe_float(self, val):
        if val is None or val == "" or val == "-":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._update_from_coordinator()

    def _update_from_coordinator(self):
        """从 Coordinator 获取聚合好的数据."""
        data = self.coordinator.data or {}
        self._cached_daylist = data.get("daylist", [])
        self._cached_monthlist = data.get("monthlist", [])
        self._cached_yearlist = data.get("yearlist", [])

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_standard_entity"

    @property
    def native_value(self) -> float | None:
        """显示账户余额."""
        data = self.coordinator.data or {}
        
        # 优先读根目录 (Coordinator 已同步)
        balance = data.get("balance")
        esti_amt = data.get("esti_amt")
        
        # 兜底读原始包
        if balance is None and esti_amt is None:
            api_data = data.get("_raw_api") or {}
            balance = api_data.get("balance")
            fee_detail = api_data.get("electricity_fee_detail") or {}
            esti_amt = fee_detail.get("estiAmt")

        if balance is not None: return round(self._safe_float(balance), 2)
        if esti_amt is not None: return round(self._safe_float(esti_amt), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """返回完整的属性，兼容 electricity-info-card 格式."""
        data = self.coordinator.data or {}
        electricity_fee_detail = data.get("electricity_fee_detail") or {}
        
        attrs = {}
        now = datetime.now()
        
        daily_avg = data.get("daily_avg", 0)
        remaining_days = data.get("remaining_days", 0)
        if daily_avg: attrs["日均消费"] = round(self._safe_float(daily_avg), 2)
        if remaining_days: attrs["剩余天数"] = remaining_days
        
        cons_type = electricity_fee_detail.get("consType")
        attrs["预付费"] = "是" if cons_type == "0" else "否"
        
        cons_no = data.get("selected_cons_no", "")
        billing_mode = self._entry.data.get("billing_mode", "year_ladder")
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        if regional_config:
            L1 = self._entry.data.get("ladder_level_1", regional_config["ladder_level_1"])
            L2 = self._entry.data.get("ladder_level_2", regional_config["ladder_level_2"])
            P1 = self._entry.data.get("ladder_price_1", regional_config["ladder_price_1"])
            P2 = self._entry.data.get("ladder_price_2", regional_config["ladder_price_2"])
            P3 = self._entry.data.get("ladder_price_3", regional_config["ladder_price_3"])
        else:
            L1, L2, P1, P2, P3 = 2040, 3240, 0.51, 0.56, 0.81
            
        year_ladder_start = str(self._entry.data.get("year_ladder_start", "0101"))
        start_m, start_d = int(year_ladder_start[:2]), int(year_ladder_start[2:])
        try:
            cycle_start = now.replace(month=start_m, day=start_d, hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            cycle_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if cycle_start > now: cycle_start = cycle_start.replace(year=now.year - 1)
        cycle_end = cycle_start.replace(year=cycle_start.year + 1) - timedelta(days=1)
        
        year_acc, month_acc = 0.0, 0.0
        curr_ym = now.strftime("%Y-%m")
        cycle_start_str, cycle_end_str = cycle_start.strftime("%Y%m%d"), cycle_end.strftime("%Y%m%d")
        
        for item in self._cached_daylist:
            d_s = item.get("day", "").replace("-", "")
            kwh = item.get("dayEleNum", 0)
            if cycle_start_str <= d_s <= cycle_end_str: year_acc += kwh
            if item.get("day", "").startswith(curr_ym): month_acc += kwh

        is_month_ladder = "month_ladder" in billing_mode
        acc = month_acc if is_month_ladder else year_acc
        
        if billing_mode == "average":
            current_tier, current_price = "-", self._entry.data.get("average_price", 0.51)
        else:
            current_tier = "第1档" if acc <= L1 else ("第2档" if acc <= L2 else "第3档")
            current_price = P1 if acc <= L1 else (P2 if acc <= L2 else P3)
            
        billing_names = {"year_ladder_tou": "年阶梯峰平谷", "year_ladder_tou_seasonal": "年阶梯峰平谷季节电价", "year_ladder": "年阶梯", "month_ladder_tou_variable": "月阶梯峰平谷变动价格", "month_ladder_tou": "月阶梯峰平谷", "month_ladder": "月阶梯", "average": "平均单价", "charging_pile": "充电桩计费"}
        billing_mode_name = billing_names.get(billing_mode, "年阶梯")
        
        billing_attrs = {"计费标准": billing_mode_name, "省份": region_name}
        if is_month_ladder:
            billing_attrs.update({"当前月阶梯档": current_tier, "月阶梯累计用电量": round(month_acc, 2), "月阶梯第2档起始电量": L1, "月阶梯第3档起始电量": L2})
        else:
            billing_attrs.update({"当前年阶梯档": current_tier, "年阶梯累计用电量": round(year_acc, 2), "当前年阶梯起始日期": cycle_start.strftime("%Y.%m.%d"), "当前年阶梯结束日期": cycle_end.strftime("%Y.%m.%d"), "年阶梯第2档起始电量": L1, "年阶梯第3档起始电量": L2})

        if "tou" in billing_mode or billing_mode == "charging_pile":
            current_month_str = now.strftime("%m")
            tier_num = 1 if acc <= L1 else (2 if acc <= L2 else 3)
            
            if billing_mode == "year_ladder_tou_seasonal":
                season = "wet" if 6 <= now.month <= 10 else "dry"
                season_name = "丰水期（6-10月）" if season == "wet" else "枯、平水期（11月-次年5月）"
                p_t = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{tier_num}_tip", 0))
                p_p = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{tier_num}_peak", 0))
                p_f = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{tier_num}_flat", 0))
                p_v = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{tier_num}_valley", 0))
                billing_attrs["当前电价季节"] = season_name
            elif billing_mode == "month_ladder_tou_variable":
                p_t = self._safe_float(self._entry.data.get(f"month_{current_month_str}_ladder_{tier_num}_tip", 0.81))
                p_p = self._safe_float(self._entry.data.get(f"month_{current_month_str}_ladder_{tier_num}_peak", 0.56))
                p_f = self._safe_float(self._entry.data.get(f"month_{current_month_str}_ladder_{tier_num}_flat", 0.51))
                p_v = self._safe_float(self._entry.data.get(f"month_{current_month_str}_ladder_{tier_num}_valley", 0.31))
            else:
                inc = (P2 - P1) if tier_num == 2 else ((P3 - P1) if tier_num == 3 else 0)
                p_t, p_p, p_f, p_v = [self._safe_float(self._entry.data.get(k, 0)) for k in ["price_tip", "price_peak", "price_flat", "price_valley"]]
                p_t, p_p, p_f, p_v = p_t + inc, p_p + inc, p_f + inc, p_v + inc

            if p_t: billing_attrs["尖峰电价"] = round(p_t, 4)
            if p_p: billing_attrs["高峰电价"] = round(p_p, 4)
            if p_f: billing_attrs["平段电价"] = round(p_f, 4)
            if p_v: billing_attrs["低谷电价"] = round(p_v, 4)

            prefix = "月阶梯" if is_month_ladder else "年阶梯"
            for lv in range(1, 4):
                if billing_mode == "year_ladder_tou_seasonal":
                    season = "wet" if 6 <= now.month <= 10 else "dry"
                    bt = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{lv}_tip", 0))
                    bp = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{lv}_peak", 0))
                    bf = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{lv}_flat", 0))
                    bv = self._safe_float(self._entry.data.get(f"season_{season}_ladder_{lv}_valley", 0))
                    inc_lv = 0
                else:
                    inc_lv = (P2 - P1) if lv == 2 else ((P3 - P1) if lv == 3 else 0)
                    bt, bp, bf, bv = [self._safe_float(self._entry.data.get(k, 0)) for k in ["price_tip", "price_peak", "price_flat", "price_valley"]]
                if bt: billing_attrs[f"{prefix}第{lv}档尖电价"] = round(bt + inc_lv, 4)
                if bp: billing_attrs[f"{prefix}第{lv}档峰电价"] = round(bp + inc_lv, 4)
                if bf: billing_attrs[f"{prefix}第{lv}档平电价"] = round(bf + inc_lv, 4)
                if bv: billing_attrs[f"{prefix}第{lv}档谷电价"] = round(bv + inc_lv, 4)
        else:
            billing_attrs["当前电价"] = current_price
            prefix = "月阶梯" if is_month_ladder else "年阶梯"
            billing_attrs[f"{prefix}第1档电价"] = round(self._safe_float(P1), 4)
            billing_attrs[f"{prefix}第2档电价"] = round(self._safe_float(P2), 4)
            billing_attrs[f"{prefix}第3档电价"] = round(self._safe_float(P3), 4)
        
        attrs.update({
            "date": electricity_fee_detail.get("amtTime") or now.strftime("%Y-%m-%d %H:%M:%S"),
            "daylist": self._cached_daylist,
            "monthlist": self._cached_monthlist,
            "yearlist": self._cached_yearlist,
            "计费标准": billing_attrs,
            "数据源": "95598 (数据库驱动)",
            "最后同步日期": now.strftime("%Y-%m-%d %H:%M:%S")
        })
        return attrs

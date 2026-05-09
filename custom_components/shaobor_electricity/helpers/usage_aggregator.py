"""Usage aggregator for merging daily records and official monthly/yearly totals."""
import logging
from datetime import datetime
from typing import Any
from homeassistant.core import HomeAssistant

class UsageAggregator:
    """Aggregates daily, monthly, and yearly electricity data from multiple sources."""

    def __init__(self, hass: HomeAssistant, entry_id: str, suffix: str | None = None):
        self.hass = hass
        self.entry_id = entry_id

    def aggregate(
        self, 
        all_daily_data: list[dict[str, Any]] | dict[str, Any], 
        config_data: dict[str, Any] | None = None, 
        official_yearly: dict[str, Any] | None = None,
        manual_monthly: dict[str, Any] | None = None,
        manual_yearly: dict[str, Any] | None = None,
        official_monthly: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        核心聚合逻辑：将外部传入的全量日数据转换为日、月、年列表。
        """
        # 1. 标准化日数据
        day_map = {}
        input_list = all_daily_data.values() if isinstance(all_daily_data, dict) else all_daily_data
        
        now = datetime.now()
        curr_m_key = now.strftime("%Y-%m")
        curr_y_key = now.strftime("%Y")

        def _safe_float(val):
            if val is None or val == "" or val == "-":
                return 0.0
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        for item in input_list:
            if not isinstance(item, dict): continue
            day_raw = item.get("day", "")
            if not day_raw: continue
            
            day_key = f"{day_raw[:4]}-{day_raw[4:6]}-{day_raw[6:8]}" if len(day_raw) == 8 else day_raw
            
            num = _safe_float(item.get("dayElePq") or item.get("dayEleNum") or item.get("pq") or item.get("kwh"))
            tpq = _safe_float(item.get("thisTPq") or item.get("dayTPq") or item.get("tip"))
            ppq = _safe_float(item.get("thisPPq") or item.get("dayPPq") or item.get("peak"))
            npq = _safe_float(item.get("thisFPq") or item.get("thisNPq") or item.get("dayNPq") or item.get("flat"))
            vpq = _safe_float(item.get("thisVPq") or item.get("dayVPq") or item.get("valley"))
            
            has_tou = (tpq + ppq + npq + vpq) > 0
            
            if day_key in day_map:
                existing = day_map[day_key]
                existing_has_tou = (existing["dayTPq"] + existing["dayPPq"] + existing["dayNPq"] + existing["dayVPq"]) > 0
                if existing_has_tou and not has_tou:
                    continue
            
            day_map[day_key] = {
                "day": day_key,
                "dayEleNum": num,
                "dayEleCost": _safe_float(item.get("dayEleCost") or item.get("cost")),
                "dayTPq": tpq,
                "dayPPq": ppq,
                "dayNPq": npq,
                "dayVPq": vpq,
                "_raw": item,
            }

        # 2. 构造月度汇总 (按日期顺序累加，支持阶梯电费重算)
        from .fee_calculator import calculate_daily_fee
        from ..helpers.regional_prices import get_region_price_config

        # 核心：必须合并 options，否则读不到用户手动设置的电价
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        current_data = entry.data if entry else {}
        current_options = entry.options if entry else {}
        merged_config = {**(config_data or {}), **current_data, **current_options}

        cons_no = merged_config.get("selected_cons_no", "")
        regional_config = get_region_price_config(cons_no) if cons_no else None
        
        billing_mode = merged_config.get("billing_mode", "year_ladder")
        L_L1 = merged_config.get("ladder_level_1", regional_config["ladder_level_1"] if regional_config else 2040)
        L_L2 = merged_config.get("ladder_level_2", regional_config["ladder_level_2"] if regional_config else 3240)
        P1 = merged_config.get("ladder_price_1", regional_config["ladder_price_1"] if regional_config else 0.51)
        P2 = merged_config.get("ladder_price_2", regional_config["ladder_price_2"] if regional_config else 0.56)
        P3 = merged_config.get("ladder_price_3", regional_config["ladder_price_3"] if regional_config else 0.81)

        calc_config = merged_config

        month_map = {}
        year_sum_map = {}
        running_year_acc = 0
        running_month_acc = 0
        last_y_key = ""
        last_m_key = ""

        sorted_days = sorted(day_map.keys())
        for d_key in sorted_days:
            item_raw = day_map[d_key]["_raw"]
            day_kwh = day_map[d_key]["dayEleNum"]
            m_key = d_key[:7]
            y_key = d_key[:4]

            if y_key != last_y_key:
                running_year_acc = 0
                last_y_key = y_key
            if m_key != last_m_key:
                running_month_acc = 0
                last_m_key = m_key
            
            running_year_acc = round(running_year_acc + day_kwh, 2)
            running_month_acc = round(running_month_acc + day_kwh, 2)

            day_cost = calculate_daily_fee(
                billing_mode=billing_mode,
                day_kwh=day_kwh,
                year_accumulated=running_year_acc,
                month_accumulated=running_month_acc,
                day_str=d_key,
                item=item_raw,
                entry_data=calc_config,
                ladder_level_1=L_L1,
                ladder_level_2=L_L2,
                price_1=P1,
                price_2=P2,
                price_3=P3,
            )
            
            day_map[d_key]["dayEleCost"] = round(day_cost, 2)

            if m_key not in month_map:
                month_map[m_key] = {"month": m_key, "monthEleNum": 0, "monthEleCost": 0, "monthTPq": 0, "monthPPq": 0, "monthNPq": 0, "monthVPq": 0}
            month_map[m_key]["monthEleNum"] += day_kwh
            month_map[m_key]["monthEleCost"] += day_cost
            month_map[m_key]["monthTPq"] += day_map[d_key]["dayTPq"]
            month_map[m_key]["monthPPq"] += day_map[d_key]["dayPPq"]
            month_map[m_key]["monthNPq"] += day_map[d_key]["dayNPq"]
            month_map[m_key]["monthVPq"] += day_map[d_key]["dayVPq"]

            if y_key not in year_sum_map:
                year_sum_map[y_key] = {"year": y_key, "yearEleNum": 0, "yearEleCost": 0, "yearTPq": 0, "yearPPq": 0, "yearNPq": 0, "yearVPq": 0}
            year_sum_map[y_key]["yearEleNum"] += day_kwh
            year_sum_map[y_key]["yearEleCost"] += day_cost
            year_sum_map[y_key]["yearTPq"] += day_map[d_key]["dayTPq"]
            year_sum_map[y_key]["yearPPq"] += day_map[d_key]["dayPPq"]
            year_sum_map[y_key]["yearNPq"] += day_map[d_key]["dayNPq"]
            year_sum_map[y_key]["yearVPq"] += day_map[d_key]["dayVPq"]

        # 3. 构造输出列表
        daylist = []
        for k in sorted(day_map.keys(), reverse=True):
            item = day_map[k]
            if item["dayEleNum"] <= 0: continue
            daylist.append({
                "day": item["day"],
                "dayEleNum": round(item["dayEleNum"], 2),
                "dayEleCost": round(item["dayEleCost"], 2),
                "dayTPq": round(item["dayTPq"], 2),
                "dayPPq": round(item["dayPPq"], 2),
                "dayNPq": round(item["dayNPq"], 2),
                "dayVPq": round(item["dayVPq"], 2)
            })
        
        monthlist = []
        manual_monthly = manual_monthly or {}
        official_monthly = official_monthly or {}
        all_months = set(month_map.keys()) | set(manual_monthly.keys()) | set(official_monthly.keys())
        
        for m_key in sorted(list(all_months), reverse=True):
            # 优先级：人工补录 > (若是本月则强制用日累加) > 官方结算 > 日累加
            if m_key in manual_monthly:
                m = manual_monthly[m_key]
                ele = _safe_float(m.get("monthEleNum") or m.get("monthElePq") or m.get("eleNum"))
                if ele <= 0: continue
                monthlist.append({
                    "month": m_key, "monthEleNum": round(ele, 2), "monthEleCost": round(_safe_float(m.get("monthEleAmt") or m.get("monthEleCost") or m.get("cost")), 2),
                    "is_official": True, "is_manual": True
                })
            elif m_key == curr_m_key and m_key in month_map:
                # 本月数据：强制使用日累加，因为官方结算可能还未出或不准
                m = month_map[m_key]
                monthlist.append({
                    "month": m_key, 
                    "monthEleNum": round(m["monthEleNum"], 2), 
                    "monthEleCost": round(m["monthEleCost"], 2),
                    "monthTPq": round(m["monthTPq"], 2), 
                    "monthPPq": round(m["monthPPq"], 2), 
                    "monthNPq": round(m["monthNPq"], 2), 
                    "monthVPq": round(m["monthVPq"], 2),
                    "is_official": False,
                    "note": "实时累加"
                })
            elif m_key in official_monthly:
                m = official_monthly[m_key]
                ele = _safe_float(m.get("monthEleNum") or m.get("eleNum") or m.get("ele_num") or m.get("pq"))
                if ele <= 0: continue
                m_data = {
                    "month": m_key, 
                    "monthEleNum": round(ele, 2), 
                    "monthEleCost": round(_safe_float(m.get("monthEleCost") or m.get("ele_cost") or m.get("amt")), 2),
                    "is_official": True
                }
                # 若有对应月的日数据，则从日累加中补充分时字段
                if m_key in month_map:
                    md = month_map[m_key]
                    m_data.update({
                        "monthTPq": round(md["monthTPq"], 2), "monthPPq": round(md["monthPPq"], 2),
                        "monthNPq": round(md["monthNPq"], 2), "monthVPq": round(md["monthVPq"], 2),
                    })
                monthlist.append(m_data)
            elif m_key in month_map:
                m = month_map[m_key]
                if m["monthEleNum"] <= 0: continue
                monthlist.append({
                    "month": m_key, 
                    "monthEleNum": round(m["monthEleNum"], 2), 
                    "monthEleCost": round(m["monthEleCost"], 2),
                    "monthTPq": round(m["monthTPq"], 2), 
                    "monthPPq": round(m["monthPPq"], 2), 
                    "monthNPq": round(m["monthNPq"], 2), 
                    "monthVPq": round(m["monthVPq"], 2),
                    "is_official": False
                })

        yearlist = []
        official_yearly = official_yearly or {}
        manual_yearly = manual_yearly or {}
        all_years = set(year_sum_map.keys()) | {k.replace("YEAR_", "") for k in official_yearly.keys() if k.startswith("YEAR_")} | set(manual_yearly.keys())
        
        for y_key in sorted(list(all_years), reverse=True):
            off_key = f"YEAR_{y_key}"
            # 优先级：人工补录 > (若是本年则强制用日累加) > 官方总结 > 日电量累加
            if y_key in manual_yearly:
                y_d = manual_yearly[y_key]
                ele = _safe_float(y_d.get("yearEleNum") or y_d.get("yearElePq") or y_d.get("totalEleNum"))
                if ele <= 0: continue
                yearlist.append({
                    "year": y_key, "yearEleNum": round(ele, 2), "yearEleCost": round(_safe_float(y_d.get("yearEleAmt") or y_d.get("yearEleCost") or y_d.get("totalEleCost")), 2),
                    "is_official": True, "is_manual": True
                })
            elif y_key == curr_y_key and y_key in year_sum_map:
                # 本年数据：强制使用日累加，保证实时性
                y = year_sum_map[y_key]
                yearlist.append({
                    "year": y_key, 
                    "yearEleNum": round(y["yearEleNum"], 2), 
                    "yearEleCost": round(y["yearEleCost"], 2),
                    "yearTPq": round(y["yearTPq"], 2), 
                    "yearPPq": round(y["yearPPq"], 2), 
                    "yearNPq": round(y["yearNPq"], 2), 
                    "yearVPq": round(y["yearVPq"], 2),
                    "is_official": False,
                    "note": "实时累加"
                })
            elif off_key in official_yearly:
                y_d = official_yearly[off_key]
                ele = _safe_float(y_d.get("yearEleNum") or y_d.get("totalEleNum"))
                if ele <= 0: continue
                y_data = {
                    "year": y_key, 
                    "yearEleNum": round(ele, 2), 
                    "yearEleCost": round(_safe_float(y_d.get("yearEleCost") or y_d.get("totalEleCost")), 2),
                    "is_official": True
                }
                # 若有对应年的日数据，则从日累加中补充分时字段
                if y_key in year_sum_map:
                    yd = year_sum_map[y_key]
                    y_data.update({
                        "yearTPq": round(yd["yearTPq"], 2), "yearPPq": round(yd["yearPPq"], 2),
                        "yearNPq": round(yd["yearNPq"], 2), "yearVPq": round(yd["yearVPq"], 2),
                    })
                yearlist.append(y_data)
            elif y_key in year_sum_map:
                y = year_sum_map[y_key]
                if y["yearEleNum"] <= 0: continue
                yearlist.append({
                    "year": y_key, 
                    "yearEleNum": round(y["yearEleNum"], 2), 
                    "yearEleCost": round(y["yearEleCost"], 2),
                    "yearTPq": round(y["yearTPq"], 2), 
                    "yearPPq": round(y["yearPPq"], 2), 
                    "yearNPq": round(y["yearNPq"], 2), 
                    "yearVPq": round(y["yearVPq"], 2),
                    "is_official": False
                })

        return {"daylist": daylist, "monthlist": monthlist, "yearlist": yearlist, "all_daily_data": day_map}

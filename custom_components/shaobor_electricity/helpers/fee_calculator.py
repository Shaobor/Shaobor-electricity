"""Electricity fee calculator for shaobor_electricity."""
from typing import Any

def calculate_daily_fee(
    billing_mode: str,
    day_kwh: float,
    year_accumulated: float,
    month_accumulated: float,
    day_str: str,
    item: dict[str, Any],
    entry_data: dict[str, Any],
    ladder_level_1: float,
    ladder_level_2: float,
    price_1: float,
    price_2: float,
    price_3: float,
) -> float:
    """Calculate the electricity fee for a single day based on billing mode."""
    # 兼容 2.2.2 中短暂发布的错误年阶梯模式标识。
    if billing_mode == "year_ladder_tou_seasonal":
        billing_mode = "month_ladder_tou_seasonal"
    day_cost = 0.0

    def _safe_float(val):
        if val is None or val == "" or val == "-":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    if "tou" in billing_mode or billing_mode == "charging_pile":
        # 峰谷计费模式：使用峰谷电价
        price_tip = _safe_float(entry_data.get("price_tip", 0.0))
        price_peak = _safe_float(entry_data.get("price_peak", 0.0))
        price_flat = _safe_float(entry_data.get("price_flat", 0.0))
        price_valley = _safe_float(entry_data.get("price_valley", 0.0))

        # 月阶梯峰平谷季节电价：夏季阶梯与丰水期谷价的月份范围并不相同。
        if billing_mode == "month_ladder_tou_seasonal":
            data_month = int(day_str[5:7])
            season = "wet" if 6 <= data_month <= 10 else "dry"
            normal_l1 = _safe_float(entry_data.get("normal_ladder_level_1", 180))
            normal_l2 = _safe_float(entry_data.get("normal_ladder_level_2", 280))
            summer_l1 = _safe_float(entry_data.get("summer_ladder_level_1", 260))
            summer_l2 = _safe_float(entry_data.get("summer_ladder_level_2", 460))
            month_l1 = summer_l1 if 7 <= data_month <= 9 else normal_l1
            month_l2 = summer_l2 if 7 <= data_month <= 9 else normal_l2

            # 2027年起，未用完的一、二档电量可逐月结转至年内后续月份。
            if int(day_str[:4]) >= 2027:
                first_limit = sum(summer_l1 if 7 <= month <= 9 else normal_l1 for month in range(1, data_month + 1))
                second_limit = sum(summer_l2 if 7 <= month <= 9 else normal_l2 for month in range(1, data_month + 1))
                accumulated = year_accumulated
            else:
                first_limit, second_limit, accumulated = month_l1, month_l2, month_accumulated

            if accumulated <= first_limit:
                tier = 1
            elif accumulated <= second_limit:
                tier = 2
            else:
                tier = 3
            price_tip = _safe_float(entry_data.get(f"season_{season}_ladder_{tier}_tip", 0.0))
            price_peak = _safe_float(entry_data.get(f"season_{season}_ladder_{tier}_peak", 0.0))
            price_flat = _safe_float(entry_data.get(f"season_{season}_ladder_{tier}_flat", 0.0))
            price_valley = _safe_float(entry_data.get(f"season_{season}_ladder_{tier}_valley", 0.0))

        # 根据当前档位调整峰谷电价（年阶梯峰平谷）
        elif billing_mode in ["year_ladder_tou", "charging_pile"]:
            if year_accumulated <= ladder_level_1:
                pass
            elif year_accumulated <= ladder_level_2:
                price_increase = price_2 - price_1
                price_tip += price_increase
                price_peak += price_increase
                price_flat += price_increase
                price_valley += price_increase
            else:
                price_increase = price_3 - price_1
                price_tip += price_increase
                price_peak += price_increase
                price_flat += price_increase
                price_valley += price_increase

        # 月阶梯峰平谷计费 (需要增加阶梯加价)
        elif billing_mode == "month_ladder_tou":
            if month_accumulated <= ladder_level_1:
                pass
            elif month_accumulated <= ladder_level_2:
                price_increase = price_2 - price_1
                price_tip += price_increase
                price_peak += price_increase
                price_flat += price_increase
                price_valley += price_increase
            else:
                price_increase = price_3 - price_1
                price_tip += price_increase
                price_peak += price_increase
                price_flat += price_increase
                price_valley += price_increase

        # 处理月阶梯峰平谷变动价格计费
        elif billing_mode == "month_ladder_tou_variable":
            # 获取该数据点所属月份
            data_month = day_str[5:7]
            # 获取该数据点所属档位
            if month_accumulated <= ladder_level_1:
                tier = 1
            elif month_accumulated <= ladder_level_2:
                tier = 2
            else:
                tier = 3

            price_tip = _safe_float(entry_data.get(f"month_{data_month}_ladder_{tier}_tip", 0.81))
            price_peak = _safe_float(entry_data.get(f"month_{data_month}_ladder_{tier}_peak", 0.56))
            price_flat = _safe_float(entry_data.get(f"month_{data_month}_ladder_{tier}_flat", 0.51))
            price_valley = _safe_float(entry_data.get(f"month_{data_month}_ladder_{tier}_valley", 0.31))

        # 计算峰谷电费
        # 核心修复：增加对多种字段名 (thisTPq, dayTPq, tpq 等) 的识别，确保能抓到电量
        thisTPq = _safe_float(item.get("thisTPq") or item.get("dayTPq") or item.get("tpq") or 0)
        thisPPq = _safe_float(item.get("thisPPq") or item.get("dayPPq") or item.get("ppq") or 0)
        
        # 平时段 fallback
        val_f = item.get("thisFPq") or item.get("thisNPq") or item.get("dayNPq") or item.get("npq") or item.get("flat")
        thisFPq = _safe_float(val_f)
        
        thisVPq = _safe_float(item.get("thisVPq") or item.get("dayVPq") or item.get("vpq") or 0)

        day_cost = (
            thisTPq * price_tip
            + thisPPq * price_peak
            + thisFPq * price_flat
            + thisVPq * price_valley
        )

    else:
        # 非峰谷计费
        if billing_mode == "average":
            average_price = _safe_float(entry_data.get("average_price", 0.51))
            day_cost = day_kwh * average_price
        else:
            # 阶梯计费 (年阶梯 或 月阶梯)
            is_month_l = billing_mode == "month_ladder"
            acc = month_accumulated if is_month_l else year_accumulated

            if acc <= ladder_level_1:
                day_cost = day_kwh * price_1
            elif acc <= ladder_level_2:
                if acc - day_kwh <= ladder_level_1:
                    first_part = ladder_level_1 - (acc - day_kwh)
                    second_part = day_kwh - first_part
                    day_cost = first_part * price_1 + second_part * price_2
                else:
                    day_cost = day_kwh * price_2
            else:
                if acc - day_kwh <= ladder_level_1:
                    first_part = ladder_level_1 - (acc - day_kwh)
                    remaining = day_kwh - first_part
                    second_part = min(remaining, ladder_level_2 - ladder_level_1)
                    third_part = remaining - second_part
                    day_cost = (
                        first_part * price_1
                        + second_part * price_2
                        + third_part * price_3
                    )
                elif acc - day_kwh <= ladder_level_2:
                    second_part = ladder_level_2 - (acc - day_kwh)
                    third_part = day_kwh - second_part
                    day_cost = second_part * price_2 + third_part * price_3
                else:
                    day_cost = day_kwh * price_3

    return day_cost

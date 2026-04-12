"""Sensor platform for shaobor_electricity."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from homeassistant.components.sensor import (  # type: ignore[import-untyped]
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry  # type: ignore[import-untyped]
from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]
from homeassistant.helpers.entity_platform import (  # type: ignore[import-untyped]
    AddEntitiesCallback,
)
from homeassistant.helpers.storage import Store  # type: ignore
from homeassistant.helpers.update_coordinator import (  # type: ignore[import-untyped]
    CoordinatorEntity,
)

from .const import DOMAIN
from .regional_prices import get_region_price_config, get_region_name

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
        Shaobor95598StandardEntitySensor(coordinator, entry),
    ]
    async_add_entities(sensors)

class Shaobor95598SensorBase(CoordinatorEntity, SensorEntity):
    """Base class for 95598 sensors. 数据均来自配置时选择的户号."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor. 设备名使用配置时选择的户号."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True
        pl = entry.data.get("power_user_list") or []
        idx = min(entry.data.get("selected_account_index", 0), len(pl) - 1) if pl else -1
        cons_no = (pl[idx].get("consNo_dst") or pl[idx].get("consNoDst") or "") if idx >= 0 else ""
        device_name = cons_no or entry.data.get("username") or entry.title.replace("Shaobor_95598 ", "").strip("()") or "95598"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"电费账户 ({device_name})",
            "manufacturer": "Shaobor",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available. 认证过期时也保持可用，显示最后一次的值."""
        return self.coordinator.data is not None

class Shaobor95598BalanceSensor(Shaobor95598SensorBase):
    """实时电费（账户余额）."""

    _attr_name = "实时电费"
    _attr_translation_key = "balance"
    _attr_native_unit_of_measurement = "CNY"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_balance"

    @property
    def native_value(self) -> float | None:
        """返回余额或本月预估电费."""
        data = self.coordinator.data or {}
        balance = data.get("balance")
        
        # 预付费用户：返回余额
        if balance is not None:
            return balance
        
        # 非预付费用户：返回本月预估电费
        fee_data = data.get("electricity_fee_detail") or {}
        esti_amt = fee_data.get("estiAmt")
        if esti_amt is not None:
            try:
                return float(esti_amt)
            except (TypeError, ValueError):
                pass
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """显示 c05/f01 返回的详细电费数据."""
        data = self.coordinator.data or {}
        fee_data = data.get("electricity_fee_detail") or {}
        
        attrs: dict[str, str | float] = {}
        
        # 预付费余额（账户余额）
        if "prepayBal" in fee_data:
            attrs["预付费余额"] = fee_data["prepayBal"]
        
        # 总电量
        if "totalPq" in fee_data:
            attrs["总电量"] = fee_data["totalPq"]
        
        # 总金额（应缴金额）
        if "sumMoney" in fee_data:
            attrs["总金额"] = fee_data["sumMoney"]
        
        # 预估金额（后付费用户的本月预估电费）
        if "estiAmt" in fee_data:
            attrs["预估金额"] = fee_data["estiAmt"]
        
        # 历史欠费
        if "historyOwe" in fee_data:
            attrs["历史欠费"] = fee_data["historyOwe"]
        
        # 违约金
        if "penalty" in fee_data:
            attrs["违约金"] = fee_data["penalty"]
        
        # 刷新时间（优先使用 amtTime，如果没有则使用 date）
        refresh_time = fee_data.get("amtTime）") or fee_data.get("date")
        if refresh_time:
            attrs["刷新时间"] = refresh_time
        
        return attrs


class Shaobor95598RemainingDaysSensor(Shaobor95598SensorBase):
    """预计可用天数."""

    _attr_name = "预计可用"
    _attr_translation_key = "remaining_days"
    _attr_native_unit_of_measurement = "天"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_remaining_days"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("remaining_days")


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
        ts = self.coordinator.data.get("last_update")
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None


class Shaobor95598PaymentRecordsSensor(Shaobor95598SensorBase):
    """缴费记录：显示缴费记录总数，完整记录在属性里."""

    _attr_name = "缴费记录"
    _attr_translation_key = "payment_records"
    _attr_native_unit_of_measurement = "条"
    _attr_icon = "mdi:receipt-text"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_payment_records"

    @property
    def native_value(self) -> int | None:
        """显示缴费记录总数 (count)."""
        records = self.coordinator.data.get("payment_records") or {}
        if isinstance(records, dict):
            return records.get("count")
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """完整缴费记录列表 (payList)."""
        records = self.coordinator.data.get("payment_records") or {}
        if isinstance(records, dict):
            pay_list = records.get("payList") or []
            if isinstance(pay_list, list):
                return {"payList": pay_list}
        return {}


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
        
        return attrs


class Shaobor95598DailyUsageSensor(Shaobor95598SensorBase):
    """每日电量：显示总电量，每日详细数据在属性里."""

    _attr_name = "每日电量"
    _attr_translation_key = "daily_usage"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:chart-line"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._cached_daily_data = {}
        self._last_file_load_time = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # 首次加载历史数据
        await self._async_load_historical_data()

    async def _async_load_historical_data(self) -> None:
        """异步加载历史数据从 Store."""
        try:
            # 从 Store 加载历史数据
            from homeassistant.helpers.storage import Store  # type: ignore
            history_store = Store(self.hass, version=1, key="shaobor_electricity/shaobor_electricity_history")
            
            monthly_data = await history_store.async_load()
            
            if not monthly_data:
                _LOGGER.warning("未找到历史数据")
                return
            
            _LOGGER.info(f"读取到 {len(monthly_data)} 个日期的数据")
            
            # 收集所有历史每日数据
            all_daily_data = {}
            
            # 遍历所有日期的数据
            for date_key, date_info in monthly_data.items():
                if isinstance(date_info, dict) and "data" in date_info:
                    data_obj = date_info.get("data", {})
                    if isinstance(data_obj, dict):
                        inner_data = data_obj.get("data", {})
                        if isinstance(inner_data, dict):
                            inner_inner_data = inner_data.get("data", {})
                            if isinstance(inner_inner_data, dict):
                                seven_list = inner_inner_data.get("sevenEleList", [])
                                if isinstance(seven_list, list):
                                    _LOGGER.debug(f"日期 {date_key} 有 {len(seven_list)} 条每日数据")
                                    for item in seven_list:
                                        if isinstance(item, dict):
                                            day_str = item.get("day", "")
                                            if day_str and day_str not in all_daily_data:
                                                all_daily_data[day_str] = item
            
            self._cached_daily_data = all_daily_data
            self._last_file_load_time = datetime.now()
            _LOGGER.info(f"合并后共有 {len(all_daily_data)} 天的数据")
            
        except Exception as e:
            _LOGGER.error(f"读取历史数据失败: {e}", exc_info=True)

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_daily_usage"

    @property
    def native_value(self) -> float | None:
        """显示最新一天的用电量作为传感器的值."""
        data = self.coordinator.data or {}
        daily_usage = data.get("daily_usage") or {}
        
        # 优先使用缓存的历史数据
        if self._cached_daily_data:
            # 获取最新日期的数据
            sorted_days = sorted(self._cached_daily_data.keys(), reverse=True)
            if sorted_days:
                latest_day = self._cached_daily_data[sorted_days[0]]
                day_ele_pq = latest_day.get("dayElePq", "")
                if day_ele_pq and day_ele_pq != "-":
                    try:
                        return float(day_ele_pq)
                    except (TypeError, ValueError):
                        pass
        
        # 如果缓存没有数据，使用API返回的数据
        seven_ele_list = daily_usage.get("sevenEleList") or []
        if isinstance(seven_ele_list, list) and len(seven_ele_list) > 0:
            # 获取第一条数据（通常是最新的）
            for item in seven_ele_list:
                if isinstance(item, dict):
                    day_ele_pq = item.get("dayElePq", "")
                    if day_ele_pq and day_ele_pq != "-":
                        try:
                            return float(day_ele_pq)
                        except (TypeError, ValueError):
                            continue
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """显示每日用电量详细数据."""
        data = self.coordinator.data or {}
        daily_usage = data.get("daily_usage") or {}
        
        attrs: dict[str, str | list] = {}
        
        # 从配置中读取计费模式
        billing_mode = self._entry.data.get("billing_mode", "year_ladder")
        
        # 返回码和消息
        if "returnCode" in daily_usage:
            attrs["返回码"] = daily_usage["returnCode"]
        if "returnMsg" in daily_usage:
            attrs["返回消息"] = daily_usage["returnMsg"]
        
        # 使用缓存的历史数据，如果没有则使用API返回的数据
        if self._cached_daily_data:
            # 将缓存的字典转换为列表格式
            seven_ele_list = list(self._cached_daily_data.values())
        else:
            seven_ele_list = daily_usage.get("sevenEleList") or []
        
        if isinstance(seven_ele_list, list) and len(seven_ele_list) > 0:
            # 显示所有天的数据，但过滤掉空数据
            all_days = []
            
            # 1-12月变动价格计费
            year_ladder_start_mmdd = self._entry.data.get("year_ladder_start", "0101")
            if not isinstance(year_ladder_start_mmdd, str) or len(year_ladder_start_mmdd) != 4:
                year_ladder_start_mmdd = "0101"
                
            start_month = int(year_ladder_start_mmdd[:2])
            start_day = int(year_ladder_start_mmdd[2:])
            now = datetime.now()
            
            # 计算当前年阶梯周期的起始日期
            try:
                cycle_start = now.replace(month=start_month, day=start_day, hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                cycle_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                
            if cycle_start > now:
                cycle_start = cycle_start.replace(year=now.year - 1)
            cycle_end = cycle_start.replace(year=cycle_start.year + 1) - timedelta(days=1)
            
            # 字符串格式用于比较
            cycle_start_str = cycle_start.strftime("%Y%m%d")
            cycle_end_str = cycle_end.strftime("%Y%m%d")
            
            year_accumulated = 0
            month_accumulated = 0
            current_year_month = now.strftime("%Y-%m")
            
            # 阶梯电价配置：优先从配置读取，否则根据户号自动识别地区
            data = self.coordinator.data or {}
            cons_no = data.get("selected_cons_no", "")
            
            # 尝试根据户号自动获取地区电价配置
            regional_config = get_region_price_config(cons_no) if cons_no else None
            region_name = get_region_name(cons_no) if cons_no else "未知地区"
            
            # 优先使用用户配置，其次使用地区配置，最后使用默认值（黑龙江）
            if regional_config:
                default_level_1 = regional_config["ladder_level_1"]
                default_level_2 = regional_config["ladder_level_2"]
                default_price_1 = regional_config["ladder_price_1"]
                default_price_2 = regional_config["ladder_price_2"]
                default_price_3 = regional_config["ladder_price_3"]
                _LOGGER.info(f"根据户号 {cons_no} 自动识别地区: {region_name}")
            else:
                # 默认值（黑龙江标准）
                default_level_1 = 2040
                default_level_2 = 3240
                default_price_1 = 0.51
                default_price_2 = 0.56
                default_price_3 = 0.81
                _LOGGER.warning(f"无法识别户号 {cons_no} 的地区，使用默认电价（黑龙江标准）")
            
            LADDER_LEVEL_1 = self._entry.data.get("ladder_level_1", default_level_1)
            LADDER_LEVEL_2 = self._entry.data.get("ladder_level_2", default_level_2)
            PRICE_1 = self._entry.data.get("ladder_price_1", default_price_1)
            PRICE_2 = self._entry.data.get("ladder_price_2", default_price_2)
            PRICE_3 = self._entry.data.get("ladder_price_3", default_price_3)
            
            for item in seven_ele_list:
                if isinstance(item, dict):
                    day_ele_pq = item.get("dayElePq", "")
                    day_str = item.get("day", "")
                    
                    # 跳过空数据（"-" 或空字符串）
                    if day_ele_pq == "-" or day_ele_pq == "":
                        continue
                    
                    try:
                        day_kwh = float(day_ele_pq)
                    except (TypeError, ValueError):
                        continue
                    
                    # 跳过用电量为0的数据
                    if day_kwh <= 0:
                        continue
                    
                    # 累计年阶梯周期用电量
                    if cycle_start_str <= day_str <= cycle_end_str:
                        year_accumulated += day_kwh
                    
                    # 累计本月用电量
                    if day_str.startswith(current_year_month):
                        month_accumulated += day_kwh
                    
                    # 计算当日电费
                    day_cost = 0
                    
                    # 判断是否使用峰谷电价
                    if "tou" in billing_mode:
                        # 峰谷计费模式：使用峰谷电价
                        price_tip = self._entry.data.get("price_tip", 0)
                        price_peak = self._entry.data.get("price_peak", 0)
                        price_flat = self._entry.data.get("price_flat", 0)
                        price_valley = self._entry.data.get("price_valley", 0)
                        
                        # 根据当前档位调整峰谷电价（年阶梯峰平谷）
                        if billing_mode == "year_ladder_tou":
                            if year_accumulated <= LADDER_LEVEL_1:
                                pass
                            elif year_accumulated <= LADDER_LEVEL_2:
                                price_increase = PRICE_2 - PRICE_1
                                price_peak += price_increase
                                price_tip += price_increase
                                price_flat += price_increase
                                price_valley += price_increase
                            else:
                                price_increase = PRICE_3 - PRICE_1
                                price_peak += price_increase
                                price_tip += price_increase
                                price_flat += price_increase
                                price_valley += price_increase
                        
                        # 月阶梯峰平谷计费 (需要增加阶梯加价)
                        elif billing_mode == "month_ladder_tou":
                            if month_accumulated <= LADDER_LEVEL_1:
                                pass
                            elif month_accumulated <= LADDER_LEVEL_2:
                                price_increase = PRICE_2 - PRICE_1
                                price_peak += price_increase
                                price_tip += price_increase
                                price_flat += price_increase
                                price_valley += price_increase
                            else:
                                price_increase = PRICE_3 - PRICE_1
                                price_peak += price_increase
                                price_tip += price_increase
                                price_flat += price_increase
                                price_valley += price_increase
                        
                        # 处理月阶梯峰平谷变动价格计费
                        elif billing_mode == "month_ladder_tou_variable":
                            # 获取该数据点所属月份
                            data_month = day_str[5:7]
                            # 获取该数据点所属档位
                            if month_accumulated <= LADDER_LEVEL_1:
                                tier = 1
                            elif month_accumulated <= LADDER_LEVEL_2:
                                tier = 2
                            else:
                                tier = 3
                            
                            price_tip = self._entry.data.get(f"month_{data_month}_ladder_{tier}_tip", 0.81)
                            price_peak = self._entry.data.get(f"month_{data_month}_ladder_{tier}_peak", 0.56)
                            price_flat = self._entry.data.get(f"month_{data_month}_ladder_{tier}_flat", 0.51)
                            price_valley = self._entry.data.get(f"month_{data_month}_ladder_{tier}_valley", 0.31)
                        
                        # 计算峰谷电费
                        thisTPq = float(item.get("thisTPq", 0) or 0)
                        thisPPq = float(item.get("thisPPq", 0) or 0)
                        # 平时段 fallback: thisFPq -> thisNPq
                        val_f = item.get("thisFPq")
                        if not val_f or val_f == "-" or val_f == "0":
                            val_f = item.get("thisNPq")
                        thisFPq = float(val_f or 0)
                        thisVPq = float(item.get("thisVPq", 0) or 0)
                        
                        day_cost = (thisTPq * price_tip + 
                                   thisPPq * price_peak + 
                                   thisFPq * price_flat + 
                                   thisVPq * price_valley)
                    else:
                        # 非峰谷计费
                        if billing_mode == "average":
                            average_price = self._entry.data.get("average_price", 0.51)
                            day_cost = day_kwh * average_price
                        else:
                            # 阶梯计费 (年阶梯 或 月阶梯)
                            is_month_l = billing_mode == "month_ladder"
                            acc = month_accumulated if is_month_l else year_accumulated
                            
                            if acc <= LADDER_LEVEL_1:
                                day_cost = day_kwh * PRICE_1
                            elif acc <= LADDER_LEVEL_2:
                                if acc - day_kwh <= LADDER_LEVEL_1:
                                    first_part = LADDER_LEVEL_1 - (acc - day_kwh)
                                    second_part = day_kwh - first_part
                                    day_cost = first_part * PRICE_1 + second_part * PRICE_2
                                else:
                                    day_cost = day_kwh * PRICE_2
                            else:
                                if acc - day_kwh <= LADDER_LEVEL_1:
                                    first_part = LADDER_LEVEL_1 - (acc - day_kwh)
                                    remaining = day_kwh - first_part
                                    second_part = min(remaining, LADDER_LEVEL_2 - LADDER_LEVEL_1)
                                    third_part = remaining - second_part
                                    day_cost = first_part * PRICE_1 + second_part * PRICE_2 + third_part * PRICE_3
                                elif acc - day_kwh <= LADDER_LEVEL_2:
                                    second_part = LADDER_LEVEL_2 - (acc - day_kwh)
                                    third_part = day_kwh - second_part
                                    day_cost = second_part * PRICE_2 + third_part * PRICE_3
                                else:
                                    day_cost = day_kwh * PRICE_3
                    
                    day_data = {
                        "日期": day_str,
                        "当日用电量": day_ele_pq,
                        "当日电费": f"{round(day_cost, 2)}元",
                    }
                    
                    # 分时段数据展示汇总（带 fallback）
                    def _add_segment(label, keys):
                        for k in keys:
                            val = item.get(k)
                            if val and val != "0" and val != "-":
                                day_data[label] = val
                                return

                    _add_segment("谷时段", ["thisVPq"])
                    _add_segment("峰时段", ["thisPPq"])
                    _add_segment("尖峰时段", ["thisTPq"])
                    _add_segment("平时段", ["thisFPq", "thisNPq"])
                    
                    all_days.append(day_data)
            
            if all_days:
                attrs["每日数据"] = all_days
                
                # 添加阶梯信息
                if year_accumulated <= LADDER_LEVEL_1:
                    current_tier = "第1档"
                    current_price = PRICE_1
                elif year_accumulated <= LADDER_LEVEL_2:
                    current_tier = "第2档"
                    current_price = PRICE_2
                else:
                    current_tier = "第3档"
                    current_price = PRICE_3
                
                attrs["年累计用电量"] = f"{round(year_accumulated, 2)}度"
                if billing_mode in ("month_ladder", "month_ladder_tou", "month_ladder_tou_variable"):
                    attrs["月累计用电量"] = f"{round(month_accumulated, 2)}度"
                attrs["当前阶梯"] = current_tier
                attrs["当前电价"] = f"{current_price}元/度"
        
        return attrs


class Shaobor95598StandardEntitySensor(Shaobor95598SensorBase):
    """电网标准实体：完全兼容 state_grid_info 格式."""

    _attr_name = "电网标准实体"
    _attr_translation_key = "standard_entity"
    _attr_native_unit_of_measurement = "元"
    _attr_icon = "mdi:flash"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._cached_daily_data = {}
        self._last_file_load_time = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # 首次加载历史数据
        await self._async_load_historical_data()

    async def _async_load_historical_data(self) -> None:
        """异步加载历史数据（从 Store 读取）."""
        try:
            # 从 Store 读取历史数据
            history_store = Store(self.hass, version=1, key="shaobor_electricity/shaobor_electricity_history")
            
            stored_data = await history_store.async_load()
            if not stored_data:
                _LOGGER.warning("[标准实体] Store 中没有历史数据")
                return
            
            _LOGGER.info(f"[标准实体] 从 Store 读取到 {len(stored_data)} 个日期的数据")
            
            # 收集所有历史每日数据
            all_daily_data = {}
            
            # 遍历所有日期的数据
            for date_key, date_info in stored_data.items():
                if isinstance(date_info, dict) and "data" in date_info:
                    data_obj = date_info.get("data", {})
                    if isinstance(data_obj, dict):
                        inner_data = data_obj.get("data", {})
                        if isinstance(inner_data, dict):
                            inner_inner_data = inner_data.get("data", {})
                            if isinstance(inner_inner_data, dict):
                                seven_list = inner_inner_data.get("sevenEleList", [])
                                if isinstance(seven_list, list):
                                    for item in seven_list:
                                        if isinstance(item, dict):
                                            day_str = item.get("day", "")
                                            if day_str and day_str not in all_daily_data:
                                                all_daily_data[day_str] = item
            
            self._cached_daily_data = all_daily_data
            self._last_file_load_time = datetime.now()
            _LOGGER.info(f"[标准实体] 合并后共有 {len(all_daily_data)} 天的数据")
            
        except Exception as e:
            _LOGGER.error(f"[标准实体] 读取历史数据失败: {e}", exc_info=True)

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_standard_entity"

    @property
    def native_value(self) -> float | None:
        """显示账户余额作为传感器的值，如果是非预付费用户则显示本月预估电费."""
        data = self.coordinator.data or {}
        balance = data.get("balance")
        
        # 如果有余额数据（预付费用户），直接返回
        if balance is not None:
            try:
                return float(balance)
            except (TypeError, ValueError):
                pass
        
        # 非预付费用户：计算本月预估电费
        electricity_fee_detail = data.get("electricity_fee_detail") or {}
        esti_amt = electricity_fee_detail.get("estiAmt")
        
        if esti_amt is not None:
            try:
                return float(esti_amt)
            except (TypeError, ValueError):
                pass
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """返回完整的属性，兼容 state_grid_info 格式."""
        # 每次获取属性时，检查是否需要重新加载历史数据
        # 如果距离上次加载超过5分钟，或者从未加载过，则重新加载
        import asyncio
        from datetime import timedelta
        
        should_reload = False
        if self._last_file_load_time is None:
            should_reload = True
        elif datetime.now() - self._last_file_load_time > timedelta(minutes=5):
            should_reload = True
        
        if should_reload:
            # 异步加载历史数据（不阻塞当前属性获取）
            asyncio.create_task(self._async_load_historical_data())
        
        data = self.coordinator.data or {}
        daily_usage = data.get("daily_usage") or {}
        
        attrs = {}
        
        # 1. 计算日均消费和剩余天数
        balance = data.get("balance", 0)
        daily_avg = data.get("daily_avg", 0)
        remaining_days = data.get("remaining_days", 0)
        
        if daily_avg and daily_avg > 0:
            attrs["日均消费"] = round(daily_avg, 2)
        if remaining_days:
            attrs["剩余天数"] = remaining_days
        
        # 2. 预付费状态（根据 consType 判断）
        electricity_fee_detail = data.get("electricity_fee_detail") or {}
        cons_type = electricity_fee_detail.get("consType")
        # consType = "0" 表示预付费，"1" 表示后付费
        attrs["预付费"] = "是" if cons_type == "0" else "否"
        
        # 3. 使用缓存的历史数据
        # 获取用户配置的户号
        cons_no = data.get("selected_cons_no", "")
        
        # 使用缓存的历史数据，如果没有则使用API返回的数据
        if self._cached_daily_data:
            all_daily_data = self._cached_daily_data
        else:
            # 如果没有历史数据，使用API返回的数据
            all_daily_data = {}
            seven_ele_list = daily_usage.get("sevenEleList") or []
            for item in seven_ele_list:
                if isinstance(item, dict):
                    day_str = item.get("day", "")
                    if day_str:
                        all_daily_data[day_str] = item
        
        # 处理每日数据 (daylist)
        day_list = []
        month_map = {}
        year_map = {}
        
        # 从配置中读取计费模式和电价参数
        billing_mode = self._entry.data.get("billing_mode", "year_ladder")
        
        # 阶梯电价配置：优先从配置读取，否则根据户号自动识别地区
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        # 优先使用用户配置，其次使用地区配置，最后使用默认值（黑龙江）
        if regional_config:
            default_level_1 = regional_config["ladder_level_1"]
            default_level_2 = regional_config["ladder_level_2"]
            default_price_1 = regional_config["ladder_price_1"]
            default_price_2 = regional_config["ladder_price_2"]
            default_price_3 = regional_config["ladder_price_3"]
        else:
            # 默认值（黑龙江标准）
            default_level_1 = 2040
            default_level_2 = 3240
            default_price_1 = 0.51
            default_price_2 = 0.56
            default_price_3 = 0.81
        
        LADDER_LEVEL_1 = self._entry.data.get("ladder_level_1", default_level_1)
        LADDER_LEVEL_2 = self._entry.data.get("ladder_level_2", default_level_2)
        PRICE_1 = self._entry.data.get("ladder_price_1", default_price_1)
        PRICE_2 = self._entry.data.get("ladder_price_2", default_price_2)
        PRICE_3 = self._entry.data.get("ladder_price_3", default_price_3)
        
        # 1-12月变动价格计费
        year_ladder_start_mmdd = self._entry.data.get("year_ladder_start", "0101")
        if not isinstance(year_ladder_start_mmdd, str) or len(year_ladder_start_mmdd) != 4:
            year_ladder_start_mmdd = "0101"
            
        start_month = int(year_ladder_start_mmdd[:2])
        start_day = int(year_ladder_start_mmdd[2:])
        now = datetime.now()
        
        # 计算当前年阶梯周期的起始日期
        try:
            cycle_start = now.replace(month=start_month, day=start_day, hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            cycle_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
        if cycle_start > now:
            cycle_start = cycle_start.replace(year=now.year - 1)
        cycle_end = cycle_start.replace(year=cycle_start.year + 1) - timedelta(days=1)
        
        # 字符串格式用于比较
        cycle_start_str = cycle_start.strftime("%Y%m%d")
        cycle_end_str = cycle_end.strftime("%Y%m%d")
        
        year_accumulated = 0
        month_accumulated = 0
        current_year_month = now.strftime("%Y-%m")
        
        # 按日期排序处理所有历史数据
        sorted_days = sorted(all_daily_data.keys())
        
        for day_str in sorted_days:
            item = all_daily_data[day_str]
            if not isinstance(item, dict):
                continue
                
            day_ele_pq = item.get("dayElePq", "")
            
            # 跳过空数据
            if day_ele_pq == "-" or day_ele_pq == "":
                continue
            
            try:
                day_kwh = float(day_ele_pq)
            except (TypeError, ValueError):
                continue
            
            # 跳过用电量为0的数据
            if day_kwh <= 0:
                continue
            
            # 格式化日期 YYYYMMDD -> YYYY-MM-DD
            if len(day_str) == 8:
                formatted_day = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:8]}"
            else:
                formatted_day = day_str
            
            # 累计年阶梯周期用电量
            if cycle_start_str <= day_str <= cycle_end_str:
                year_accumulated += day_kwh
            
            # 累计本月用电量（用格式化后的日期判断）
            if formatted_day.startswith(current_year_month):
                month_accumulated += day_kwh
            
            # 计算当日电费
            day_cost = 0
            
            # 获取时段用电量（所有模式共用）
            # 获取时段用电量（所有模式共用，平时段带 fallback）
            thisTPq = float(item.get("thisTPq", 0) or 0)  # 尖峰
            thisPPq = float(item.get("thisPPq", 0) or 0)  # 峰
            val_f = item.get("thisFPq")
            if not val_f or val_f == "-" or val_f == "0":
                val_f = item.get("thisNPq")
            thisFPq = float(val_f or 0)
            thisVPq = float(item.get("thisVPq", 0) or 0)  # 谷
            
            # 判断是否使用峰谷电价
            if "tou" in billing_mode:
                # 峰谷计费模式
                price_tip = self._entry.data.get("price_tip", 0)
                price_peak = self._entry.data.get("price_peak", 0)
                price_flat = self._entry.data.get("price_flat", 0)
                price_valley = self._entry.data.get("price_valley", 0)
                
                # 根据当前档位调整峰谷电价（年阶梯峰平谷）
                if billing_mode == "year_ladder_tou":
                    if year_accumulated <= LADDER_LEVEL_1:
                        pass
                    elif year_accumulated <= LADDER_LEVEL_2:
                        price_increase = PRICE_2 - PRICE_1
                        price_peak += price_increase
                        price_tip += price_increase
                        price_flat += price_increase
                        price_valley += price_increase
                    else:
                        price_increase = PRICE_3 - PRICE_1
                        price_peak += price_increase
                        price_tip += price_increase
                        price_flat += price_increase
                        price_valley += price_increase
                
                # 月阶梯峰平谷计费 (需要增加阶梯加价)
                elif billing_mode == "month_ladder_tou":
                    if month_accumulated <= LADDER_LEVEL_1:
                        pass
                    elif month_accumulated <= LADDER_LEVEL_2:
                        price_increase = PRICE_2 - PRICE_1
                        price_peak += price_increase
                        price_tip += price_increase
                        price_flat += price_increase
                        price_valley += price_increase
                    else:
                        price_increase = PRICE_3 - PRICE_1
                        price_peak += price_increase
                        price_tip += price_increase
                        price_flat += price_increase
                        price_valley += price_increase

                # 处理月阶梯峰平谷变动价格计费
                elif billing_mode == "month_ladder_tou_variable":
                    # 获取该数据点所属月份 (YYYY-MM-DD -> MM)
                    data_month = formatted_day[5:7]
                    # 获取该数据点所属档位
                    if month_accumulated <= LADDER_LEVEL_1:
                        tier = 1
                    elif month_accumulated <= LADDER_LEVEL_2:
                        tier = 2
                    else:
                        tier = 3
                    
                    price_tip = self._entry.data.get(f"month_{data_month}_ladder_{tier}_tip", 0.81)
                    price_peak = self._entry.data.get(f"month_{data_month}_ladder_{tier}_peak", 0.56)
                    price_flat = self._entry.data.get(f"month_{data_month}_ladder_{tier}_flat", 0.51)
                    price_valley = self._entry.data.get(f"month_{data_month}_ladder_{tier}_valley", 0.31)
                
                # 计算峰谷电费（平时段带 fallback）
                thisTPq = float(item.get("thisTPq", 0) or 0)
                thisPPq = float(item.get("thisPPq", 0) or 0)
                val_f = item.get("thisFPq")
                if not val_f or val_f == "-" or val_f == "0":
                    val_f = item.get("thisNPq")
                thisFPq = float(val_f or 0)
                thisVPq = float(item.get("thisVPq", 0) or 0)
                
                day_cost = (thisTPq * price_tip + 
                           thisPPq * price_peak + 
                           thisFPq * price_flat + 
                           thisVPq * price_valley)
            else:
                # 非峰谷计费
                if billing_mode == "average":
                    # 平均电价
                    average_price = self._entry.data.get("average_price", 0.51)
                    day_cost = day_kwh * average_price
                else:
                    # 阶梯电价 (年阶梯 或 月阶梯)
                    is_month_l = billing_mode == "month_ladder"
                    acc = month_accumulated if is_month_l else year_accumulated
                    
                    if acc <= LADDER_LEVEL_1:
                        day_cost = day_kwh * PRICE_1
                    elif acc <= LADDER_LEVEL_2:
                        if acc - day_kwh <= LADDER_LEVEL_1:
                            first_part = LADDER_LEVEL_1 - (acc - day_kwh)
                            second_part = day_kwh - first_part
                            day_cost = first_part * PRICE_1 + second_part * PRICE_2
                        else:
                            day_cost = day_kwh * PRICE_2
                    else:
                        if acc - day_kwh <= LADDER_LEVEL_1:
                            first_part = LADDER_LEVEL_1 - (acc - day_kwh)
                            remaining = day_kwh - first_part
                            second_part = min(remaining, LADDER_LEVEL_2 - LADDER_LEVEL_1)
                            third_part = remaining - second_part
                            day_cost = first_part * PRICE_1 + second_part * PRICE_2 + third_part * PRICE_3
                        elif acc - day_kwh <= LADDER_LEVEL_2:
                            second_part = LADDER_LEVEL_2 - (acc - day_kwh)
                            third_part = day_kwh - second_part
                            day_cost = second_part * PRICE_2 + third_part * PRICE_3
                        else:
                            day_cost = day_kwh * PRICE_3
            
            # 构建每日数据 - 只添加非零的时段数据
            day_data = {
                "day": formatted_day,
                "dayEleNum": day_kwh,
                "dayEleCost": round(day_cost, 2),
            }
            
            # 只添加非零的时段数据
            if thisTPq > 0:
                day_data["dayTPq"] = round(thisTPq, 2)
            if thisPPq > 0:
                day_data["dayPPq"] = round(thisPPq, 2)
            if thisFPq > 0:
                day_data["dayNPq"] = round(thisFPq, 2)
            if thisVPq > 0:
                day_data["dayVPq"] = round(thisVPq, 2)
            
            day_list.append(day_data)
            
            # 聚合月度数据
            month_key = formatted_day[:7]  # YYYY-MM
            if month_key not in month_map:
                month_map[month_key] = {
                    "month": month_key,
                    "monthEleNum": 0,
                    "monthEleCost": 0,
                    "monthTPq": 0,
                    "monthPPq": 0,
                    "monthNPq": 0,
                    "monthVPq": 0,
                }
            month_map[month_key]["monthEleNum"] += day_kwh
            month_map[month_key]["monthEleCost"] += day_cost
            
            # 只累加非零的时段数据
            if thisTPq > 0:
                month_map[month_key]["monthTPq"] += thisTPq
            if thisPPq > 0:
                month_map[month_key]["monthPPq"] += thisPPq
            if thisFPq > 0:
                month_map[month_key]["monthNPq"] += thisFPq
            if thisVPq > 0:
                month_map[month_key]["monthVPq"] += thisVPq
            
            # 聚合年度数据
            year_key = formatted_day[:4]  # YYYY
            if year_key not in year_map:
                year_map[year_key] = {
                    "year": year_key,
                    "yearEleNum": 0,
                    "yearEleCost": 0,
                    "yearTPq": 0,
                    "yearPPq": 0,
                    "yearNPq": 0,
                    "yearVPq": 0,
                }
            year_map[year_key]["yearEleNum"] += day_kwh
            year_map[year_key]["yearEleCost"] += day_cost
            
            # 只累加非零的时段数据
            if thisTPq > 0:
                year_map[year_key]["yearTPq"] += thisTPq
            if thisPPq > 0:
                year_map[year_key]["yearPPq"] += thisPPq
            if thisFPq > 0:
                year_map[year_key]["yearNPq"] += thisFPq
            if thisVPq > 0:
                year_map[year_key]["yearVPq"] += thisVPq
        
        # 格式化月度和年度数据（过滤掉空数据）
        month_list = []
        for m in sorted(month_map.values(), key=lambda x: x["month"], reverse=True):
            # 只添加有用电量的月份
            if m["monthEleNum"] > 0:
                month_data = {
                    "month": m["month"],
                    "monthEleNum": round(m["monthEleNum"], 2),
                    "monthEleCost": round(m["monthEleCost"], 2),
                }
                # 只添加非零的时段数据
                if m["monthTPq"] > 0:
                    month_data["monthTPq"] = round(m["monthTPq"], 2)
                if m["monthPPq"] > 0:
                    month_data["monthPPq"] = round(m["monthPPq"], 2)
                if m["monthNPq"] > 0:
                    month_data["monthNPq"] = round(m["monthNPq"], 2)
                if m["monthVPq"] > 0:
                    month_data["monthVPq"] = round(m["monthVPq"], 2)
                month_list.append(month_data)
        
        year_list = []
        for y in sorted(year_map.values(), key=lambda x: x["year"], reverse=True):
            # 只添加有用电量的年份
            if y["yearEleNum"] > 0:
                year_data = {
                    "year": y["year"],
                    "yearEleNum": round(y["yearEleNum"], 2),
                    "yearEleCost": round(y["yearEleCost"], 2),
                }
                # 只添加非零的时段数据
                if y["yearTPq"] > 0:
                    year_data["yearTPq"] = round(y["yearTPq"], 2)
                if y["yearPPq"] > 0:
                    year_data["yearPPq"] = round(y["yearPPq"], 2)
                if y["yearNPq"] > 0:
                    year_data["yearNPq"] = round(y["yearNPq"], 2)
                if y["yearVPq"] > 0:
                    year_data["yearVPq"] = round(y["yearVPq"], 2)
                year_list.append(year_data)
        
        # 4. 添加核心数据
        # 使用电费数据的更新时间，如果没有则使用当前时间
        amt_time = electricity_fee_detail.get("amtTime")
        if amt_time:
            attrs["date"] = amt_time
        else:
            attrs["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        attrs["daylist"] = sorted(day_list, key=lambda x: x["day"], reverse=True)
        attrs["monthlist"] = month_list
        attrs["yearlist"] = year_list
        
        # 5. 计费标准信息
        # 根据计费模式决定用年累计还是月累计来判断当前档位
        is_month_ladder = billing_mode in ("month_ladder", "month_ladder_tou", "month_ladder_tou_variable")
        accumulated_for_tier = month_accumulated if is_month_ladder else year_accumulated
        
        if billing_mode == "average":
            current_tier = "-"
            current_price = self._entry.data.get("average_price", 0.51)
        elif accumulated_for_tier <= LADDER_LEVEL_1:
            current_tier = "第1档"
            current_price = PRICE_1
        elif accumulated_for_tier <= LADDER_LEVEL_2:
            current_tier = "第2档"
            current_price = PRICE_2
        else:
            current_tier = "第3档"
            current_price = PRICE_3
        
        # 根据 billing_mode 显示正确的计费标准名称
        billing_mode_names = {
            "year_ladder_tou": "年阶梯峰平谷",
            "year_ladder": "年阶梯",
            "month_ladder_tou_variable": "月阶梯峰平谷变动价格",
            "month_ladder_tou": "月阶梯峰平谷",
            "month_ladder": "月阶梯",
            "average": "平均单价",
        }
        billing_mode_name = billing_mode_names.get(billing_mode, "年阶梯")
        
        # 根据计费模式构建不同的属性
        is_month_ladder = billing_mode in ("month_ladder", "month_ladder_tou", "month_ladder_tou_variable")
        is_year_ladder = billing_mode in ("year_ladder", "year_ladder_tou")
        
        if is_month_ladder:
            billing_attrs = {
                "计费标准": billing_mode_name,
                "省份": region_name,
                "当前月阶梯档": current_tier,
                "月阶梯累计用电量": round(month_accumulated, 2),
                "月阶梯第2档起始电量": LADDER_LEVEL_1,
                "月阶梯第3档起始电量": LADDER_LEVEL_2,
            }
        else:
            # 年阶梯：计算当前年阶梯档
            billing_attrs = {
                "计费标准": billing_mode_name,
                "省份": region_name,
                "当前年阶梯档": current_tier,
                "年阶梯累计用电量": round(year_accumulated, 2),
                "当前年阶梯起始日期": cycle_start.strftime("%Y.%m.%d"),
                "当前年阶梯结束日期": cycle_end.strftime("%Y.%m.%d"),
                "年阶梯第2档起始电量": LADDER_LEVEL_1,
                "年阶梯第3档起始电量": LADDER_LEVEL_2,
            }
        
        # 如果是峰谷计费模式，显示峰谷电价
        if "tou" in billing_mode:
            price_tip = self._entry.data.get("price_tip", 0)
            price_peak = self._entry.data.get("price_peak", 0)
            price_flat = self._entry.data.get("price_flat", 0)
            price_valley = self._entry.data.get("price_valley", 0)
            
            # 根据当前档位调整峰谷电价（如果是年阶梯或者月变动阶梯）
            # 根据当前档位调整峰谷电价
            if billing_mode == "year_ladder_tou" or billing_mode == "month_ladder_tou":
                # 根据档位调整电价
                if current_tier == "第2档":
                    price_increase = PRICE_2 - PRICE_1
                    price_peak += price_increase
                    price_tip += price_increase
                    price_valley += price_increase
                elif current_tier == "第3档":
                    price_increase = PRICE_3 - PRICE_1
                    price_peak += price_increase
                    price_tip += price_increase
                    price_valley += price_increase
            elif billing_mode == "month_ladder_tou_variable":
                # 处理月阶梯变动电价
                now_month = datetime.now().strftime("%m")
                tier_num = 1
                if current_tier == "第2档": tier_num = 2
                elif current_tier == "第3档": tier_num = 3
                
                price_tip = self._entry.data.get(f"month_{now_month}_ladder_{tier_num}_tip", 0.81)
                price_peak = self._entry.data.get(f"month_{now_month}_ladder_{tier_num}_peak", 0.56)
                price_flat = self._entry.data.get(f"month_{now_month}_ladder_{tier_num}_flat", 0.51)
                price_valley = self._entry.data.get(f"month_{now_month}_ladder_{tier_num}_valley", 0.31)
            
            # 动态显示当前时段电价 (针对不同地区优化)
            now_hour = datetime.now().hour
            
            # 默认高峰判定 (部分省份如黑龙江、浙江等通常是 8:00-21:00 或 8:00-22:00)
            is_peak = False
            # 浙江省: 8-22 点高峰
            if region_name == "浙江省":
                if 8 <= now_hour < 22: is_peak = True
            # 黑龙江省: 7-22 点高峰 (基于之前日志观察)
            elif region_name == "黑龙江省":
                if 7 <= now_hour < 22: is_peak = True
            # 其他地区通用判定: 8-21 点高峰
            else:
                if 8 <= now_hour < 21: is_peak = True

            if is_peak:
                # 尝试根据尖峰/高峰显示
                effective_price = price_peak or price_tip
                if effective_price:
                    billing_attrs["当前电价"] = round(effective_price, 4)
                else:
                    billing_attrs["当前电价"] = "峰谷分时"
            elif 21 <= now_hour or now_hour < 7:
                # 低谷时段 (通常 22:00 或 21:00 以后)
                billing_attrs["当前电价"] = round(price_valley, 4) if price_valley else "峰谷分时"
            else:
                # 平段时段
                if price_flat:
                    billing_attrs["当前电价"] = round(price_flat, 4)
                else:
                    # 如果没有平段电价，根据当前时间灵活选择
                    billing_attrs["当前电价"] = round(price_valley, 4) if price_valley else "峰谷分时"

            if price_tip > 0:
                billing_attrs["尖峰电价"] = round(price_tip, 4)
            if price_peak > 0:
                billing_attrs["高峰电价"] = round(price_peak, 4)
            if price_flat > 0:
                billing_attrs["平段电价"] = round(price_flat, 4)
            if price_valley > 0:
                billing_attrs["低谷电价"] = round(price_valley, 4)
        else:
            # 非峰谷计费，显示阶梯电价
            billing_attrs["当前电价"] = current_price
            if is_month_ladder:
                billing_attrs["月阶梯第1档电价"] = PRICE_1
                billing_attrs["月阶梯第2档电价"] = PRICE_2
                billing_attrs["月阶梯第3档电价"] = PRICE_3
            else:
                billing_attrs["年阶梯第1档电价"] = PRICE_1
                billing_attrs["年阶梯第2档电价"] = PRICE_2
                billing_attrs["年阶梯第3档电价"] = PRICE_3
        
        attrs["计费标准"] = billing_attrs
        
        # 6. 其他信息
        attrs["数据源"] = "95598"
        attrs["最后同步日期"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return attrs

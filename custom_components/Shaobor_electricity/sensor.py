"""Sensor platform for Shaobor_electricity."""
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
        return self.coordinator.data.get("balance")

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
        
        # 预估金额
        if "estiAmt" in fee_data:
            attrs["预估金额"] = fee_data["estiAmt"]
        
        # 历史欠费
        if "historyOwe" in fee_data:
            attrs["历史欠费"] = fee_data["historyOwe"]
        
        # 违约金
        if "penalty" in fee_data:
            attrs["违约金"] = fee_data["penalty"]
        
        # 金额时间（数据更新时间）
        if "amtTime" in fee_data:
            attrs["刷新时间"] = fee_data["amtTime"]
        
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
            history_store = Store(self.hass, version=1, key="Shaobor_electricity_history")
            
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
            
            # 计算年累计用电量（用于阶梯计费）
            year_accumulated = 0
            current_year = str(datetime.now().year)
            
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
                    
                    # 只累计当年的用电量
                    if day_str.startswith(current_year):
                        year_accumulated += day_kwh
                    
                    # 计算当日电费（基于年阶梯）
                    day_cost = 0
                    if year_accumulated <= LADDER_LEVEL_1:
                        # 第一阶梯
                        day_cost = day_kwh * PRICE_1
                    elif year_accumulated <= LADDER_LEVEL_2:
                        # 第二阶梯（可能跨阶梯）
                        if year_accumulated - day_kwh <= LADDER_LEVEL_1:
                            # 跨阶梯
                            first_part = LADDER_LEVEL_1 - (year_accumulated - day_kwh)
                            second_part = day_kwh - first_part
                            day_cost = first_part * PRICE_1 + second_part * PRICE_2
                        else:
                            # 完全在第二阶梯
                            day_cost = day_kwh * PRICE_2
                    else:
                        # 第三阶梯（可能跨阶梯）
                        if year_accumulated - day_kwh <= LADDER_LEVEL_1:
                            # 跨越三个阶梯
                            first_part = LADDER_LEVEL_1 - (year_accumulated - day_kwh)
                            remaining = day_kwh - first_part
                            second_part = min(remaining, LADDER_LEVEL_2 - LADDER_LEVEL_1)
                            third_part = remaining - second_part
                            day_cost = first_part * PRICE_1 + second_part * PRICE_2 + third_part * PRICE_3
                        elif year_accumulated - day_kwh <= LADDER_LEVEL_2:
                            # 跨越第二、第三阶梯
                            second_part = LADDER_LEVEL_2 - (year_accumulated - day_kwh)
                            third_part = day_kwh - second_part
                            day_cost = second_part * PRICE_2 + third_part * PRICE_3
                        else:
                            # 完全在第三阶梯
                            day_cost = day_kwh * PRICE_3
                    
                    day_data = {
                        "日期": day_str,
                        "当日用电量": day_ele_pq,
                        "当日电费": f"{round(day_cost, 2)}元",
                    }
                    
                    # 只添加非零的分时段数据
                    thisVPq = item.get("thisVPq", "")
                    if thisVPq and thisVPq != "0" and thisVPq != "-":
                        try:
                            if float(thisVPq) > 0:
                                day_data["谷时段"] = thisVPq
                        except (TypeError, ValueError):
                            pass
                    
                    thisPPq = item.get("thisPPq", "")
                    if thisPPq and thisPPq != "0" and thisPPq != "-":
                        try:
                            if float(thisPPq) > 0:
                                day_data["平时段"] = thisPPq
                        except (TypeError, ValueError):
                            pass
                    
                    thisNPq = item.get("thisNPq", "")
                    if thisNPq and thisNPq != "0" and thisNPq != "-":
                        try:
                            if float(thisNPq) > 0:
                                day_data["峰时段"] = thisNPq
                        except (TypeError, ValueError):
                            pass
                    
                    thisDVPq = item.get("thisDVPq", "")
                    if thisDVPq and thisDVPq != "0" and thisDVPq != "-":
                        try:
                            if float(thisDVPq) > 0:
                                day_data["尖峰时段"] = thisDVPq
                        except (TypeError, ValueError):
                            pass
                    
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
            history_store = Store(self.hass, version=1, key="Shaobor_electricity_history")
            
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
        """显示账户余额作为传感器的值."""
        data = self.coordinator.data or {}
        balance = data.get("balance")
        if balance is not None:
            try:
                return float(balance)
            except (TypeError, ValueError):
                return None
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
        
        # 2. 预付费状态
        electricity_fee_detail = data.get("electricity_fee_detail") or {}
        prepay_bal = electricity_fee_detail.get("prepayBal")
        attrs["预付费"] = "是" if prepay_bal is not None else "否"
        
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
        
        year_accumulated = 0
        current_year = str(datetime.now().year)
        
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
            
            # 只累计当年的用电量
            if day_str.startswith(current_year):
                year_accumulated += day_kwh
            
            # 计算当日电费
            day_cost = 0
            if year_accumulated <= LADDER_LEVEL_1:
                day_cost = day_kwh * PRICE_1
            elif year_accumulated <= LADDER_LEVEL_2:
                if year_accumulated - day_kwh <= LADDER_LEVEL_1:
                    first_part = LADDER_LEVEL_1 - (year_accumulated - day_kwh)
                    second_part = day_kwh - first_part
                    day_cost = first_part * PRICE_1 + second_part * PRICE_2
                else:
                    day_cost = day_kwh * PRICE_2
            else:
                if year_accumulated - day_kwh <= LADDER_LEVEL_1:
                    first_part = LADDER_LEVEL_1 - (year_accumulated - day_kwh)
                    remaining = day_kwh - first_part
                    second_part = min(remaining, LADDER_LEVEL_2 - LADDER_LEVEL_1)
                    third_part = remaining - second_part
                    day_cost = first_part * PRICE_1 + second_part * PRICE_2 + third_part * PRICE_3
                elif year_accumulated - day_kwh <= LADDER_LEVEL_2:
                    second_part = LADDER_LEVEL_2 - (year_accumulated - day_kwh)
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
            thisTPq = float(item.get("thisTPq", 0))
            if thisTPq > 0:
                day_data["dayTPq"] = thisTPq
            
            thisPPq = float(item.get("thisPPq", 0))
            if thisPPq > 0:
                day_data["dayPPq"] = thisPPq
            
            thisNPq = float(item.get("thisNPq", 0))
            if thisNPq > 0:
                day_data["dayNPq"] = thisNPq
            
            thisVPq = float(item.get("thisVPq", 0))
            if thisVPq > 0:
                day_data["dayVPq"] = thisVPq
            
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
            if thisNPq > 0:
                month_map[month_key]["monthNPq"] += thisNPq
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
            if thisNPq > 0:
                year_map[year_key]["yearNPq"] += thisNPq
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
        if year_accumulated <= LADDER_LEVEL_1:
            current_tier = "第1档"
            current_price = PRICE_1
        elif year_accumulated <= LADDER_LEVEL_2:
            current_tier = "第2档"
            current_price = PRICE_2
        else:
            current_tier = "第3档"
            current_price = PRICE_3
        
        attrs["计费标准"] = {
            "计费标准": "年阶梯计费",
            "省份": "黑龙江",
            "当前年阶梯档": current_tier,
            "年阶梯累计用电量": round(year_accumulated, 2),
            "当前电价": current_price,
            "当前年阶梯起始日期": f"{datetime.now().year}.01.01",
            "当前年阶梯结束日期": f"{datetime.now().year}.12.31",
            "年阶梯第1档电价": PRICE_1,
            "年阶梯第2档电价": PRICE_2,
            "年阶梯第3档电价": PRICE_3,
            "年阶梯第2档起始电量": LADDER_LEVEL_1,
            "年阶梯第3档起始电量": LADDER_LEVEL_2,
        }
        
        # 6. 其他信息
        attrs["数据源"] = "95598"
        attrs["最后同步日期"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return attrs

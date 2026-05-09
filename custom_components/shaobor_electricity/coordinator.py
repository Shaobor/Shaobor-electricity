import logging
import time
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .client import Shaobor95598ApiClient, StateGridAuthError, StateGridConnectionError
from .const import DOMAIN, CONF_USER_TOKEN, CONF_USER_ID, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

class Shaobor95598Coordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API with SQLite backend."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: Shaobor95598ApiClient,
        store: Store,
        data_store: Store,
        db: Any = None,
    ) -> None:
        """Initialize."""
        self.entry = entry
        self.api = api
        self.store = store
        self.data_store = data_store
        
        self.cons_no = entry.data.get("cons_no") or entry.data.get("selected_cons_no")
        if not self.cons_no:
            pl = entry.data.get("power_user_list") or []
            idx = entry.data.get("selected_account_index", 0)
            try:
                idx = int(idx)
                if pl and 0 <= idx < len(pl):
                    raw = pl[idx].get("consNo_dst") or pl[idx].get("consNoDst") or pl[idx].get("consNo") or ""
                    self.cons_no = str(raw).split("-")[0].strip() if raw else ""
            except (ValueError, TypeError):
                pass

        _LOGGER.debug(f"[数据中心] 初始化 Coordinator, 识别到户号: {self.cons_no}")
        suffix = self.cons_no if self.cons_no else entry.entry_id
        
        # 1. 核心状态存储 (仅存余额、户名、Token 等小数据)
        self.status_cache_store = Store(hass, version=1, key=f"{DOMAIN}/shaobor_status_{suffix}")
        
        # 2. SQLite 数据库初始化
        if db:
            self.db = db
        else:
            from .helpers.database import StateGridDatabase
            db_path = hass.config.path(".storage", DOMAIN, "shaobor_electricity.db")
            self.db = StateGridDatabase(hass, db_path)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=10),
        )
        
        # 启动后台初始化任务
        async def _init_task():
            await self.db.async_init()
            # 【清理任务】：彻底移除 2.0.0 之前的所有旧版 JSON 存储文件，全面转向 SQLite
            try:
                # 1. 移除旧的统合数据与历史文件
                for key_pattern in [
                    f"{DOMAIN}/shaobor_usage_{suffix}",
                    f"{DOMAIN}/shaobor_history_{suffix}",
                    f"{DOMAIN}/shaobor_data_{self.entry.entry_id}",
                    f"{DOMAIN}/shaobor_history_{self.entry.entry_id}",
                    # 2. 移除新架构过渡期产生的冗余 JSON 文件
                    f"{DOMAIN}/shaobor_imported_{suffix}",
                    f"{DOMAIN}/shaobor_monthly_{suffix}",
                    f"{DOMAIN}/shaobor_yearly_{suffix}",
                    f"{DOMAIN}/shaobor_monthly_{self.entry.entry_id}",
                    f"{DOMAIN}/shaobor_yearly_{self.entry.entry_id}",
                    "shaobor_electricity/shaobor_electricity_auth", # 彻底移除最后的 auth 缓存
                ]:
                    try:
                        legacy_store = Store(hass, version=1, key=key_pattern)
                        await legacy_store.async_remove()
                    except Exception: pass
                _LOGGER.info("[数据清理] 已完成旧版 JSON 缓存文件的清理工作")
            except Exception as e:
                _LOGGER.debug(f"[数据清理] 清理过程中出现非致命错误: {e}")
            
        # 将数据库对象注入 API，方便后续精准查询历史
        self.api.set_db(self.db)
        
        hass.async_create_task(_init_task())

    async def _async_update_data(self) -> dict[str, Any]:
        """100% Database-centric update flow. 数据库优先，API 仅作为增量补充。"""
        login_acc = self.api._login_account or self.entry.data.get("login_account")
        auth_error = None
        api_data = None
        
        _LOGGER.debug(f"[数据中心] 开始更新流程，户号: {self.cons_no}")

        # 1. 第一步：尝试从 API 获取增量数据并存入数据库
        try:
            # 认证与 Token 刷新
            db_auth = await self.db.async_get_auth(login_acc) if login_acc else None
            async with self.hass.data[DOMAIN]["auth_lock"]:
                try:
                    if db_auth and db_auth.get("access_token"):
                         self.api.load_auth_state(
                            user_token=db_auth.get("user_token"),
                            user_id=db_auth.get("user_id"),
                            access_token=db_auth.get("access_token"),
                            refresh_token=db_auth.get("refresh_token"),
                         )
                    await self.api.refresh_access_token()
                except Exception as e:
                    _LOGGER.debug(f"[认证] 预刷新 Token 失败 (非致命): {e}")

            # 抓取最新数据
            api_data = await self.api.get_electricity_data(cons_no=self.cons_no)
            
            if api_data:
                # 【自动补全户号】：如果初始化时没拿到户号（首次登录），则从 API 返回结果中提取
                if not self.cons_no:
                    self.cons_no = api_data.get("selected_cons_no")
                    if self.cons_no:
                        self.cons_no = str(self.cons_no).split("-")[0].strip()
                        _LOGGER.info(f"[数据库] 自动探测并补全当前活跃户号: {self.cons_no}")

                # 存入数据库
                daily_usage_data = api_data.get("daily_usage", {})
                all_history = daily_usage_data.get("all_daily_data")
                if all_history:
                    history_list = list(all_history.values()) if isinstance(all_history, dict) else all_history
                    await self.db.async_save_daily_usage(self.cons_no, history_list)
                else:
                    live_daylist = daily_usage_data.get("sevenEleList") or []
                    if live_daylist:
                        await self.db.async_save_daily_usage(self.cons_no, live_daylist)

                monthlist = daily_usage_data.get("monthlist")
                if monthlist:
                    await self.db.async_save_monthly_usage(self.cons_no, monthlist)
                
                yearlist = daily_usage_data.get("yearlist")
                if yearlist:
                    await self.db.async_save_yearly_usage(self.cons_no, yearlist)
                
                payment_data = api_data.get("payment_records", {})
                pay_list = payment_data.get("payList") or []
                if pay_list:
                    await self.db.async_save_payments(self.cons_no, pay_list)
                
                await self.db.async_save_account_info({**api_data, "cons_no": self.cons_no})
                
                auth_acc = login_acc or f"account_{self.entry.entry_id[:8]}"
                await self.db.async_save_auth(auth_acc, {
                    "user_token": self.api._user_token,
                    "access_token": self.api._access_token,
                    "refresh_token": self.api._refresh_token,
                    "user_id": self.api._user_id,
                    "power_user_list": self.api._power_user_list
                })

        except StateGridAuthError as err:
            auth_error = err
            _LOGGER.warning(f"[认证失效] 认证已过期，将使用本地数据库缓存展示: {err}")
            # 1. 触发持久化通知
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "国家电网认证已过期",
                        "message": f"账户 {self.cons_no or ''} 的登录认证已失效，请前往集成页面重新认证。提示: {err}",
                        "notification_id": f"{DOMAIN}_auth_error_{self.entry.entry_id}",
                    },
                )
            )
            # 2. 触发 Home Assistant 的重新认证流程 (UI 会出现“重新配置”按钮)
            self.entry.async_start_reauth(self.hass)
            
        except Exception as err:
            _LOGGER.error(f"[更新失败] API 刷新出现非认证异常: {err}")

        # 2. 第二步：无论 API 是否成功，都从数据库读回全量数据进行展示
        return await self._async_update_data_from_db(api_data)

    async def async_load_from_db(self) -> None:
        """从数据库加载历史数据到 coordinator.data，通常用于启动初始化。"""
        if not self.db or not self.cons_no:
            return
        try:
            self.data = await self._async_update_data_from_db()
            _LOGGER.info(f"[数据中心] 启动时已从数据库加载缓存数据: {self.cons_no}")
        except Exception as e:
            _LOGGER.error(f"[数据中心] 启动加载数据库失败: {e}")

    async def _async_update_data_from_db(self, api_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """内部方法：仅执行数据库读取与数据组装逻辑。"""
        if not self.cons_no:
            return {}

        db_info = await self.db.async_get_account_info(self.cons_no)
        db_days = await self.db.async_get_all_daily_usage(self.cons_no)
        db_payments = await self.db.async_get_all_payments(self.cons_no)
        db_monthly = await self.db.async_get_all_monthly_usage(self.cons_no)
        db_yearly = await self.db.async_get_all_yearly_usage(self.cons_no)
        
        # 聚合计算
        from .helpers.usage_aggregator import UsageAggregator
        aggregator = UsageAggregator(self.hass, self.entry.entry_id, suffix=self.cons_no)
        official_yearly_map = {f"YEAR_{y['year']}": y for y in db_yearly if y.get("is_official")}
        official_monthly_map = {m['month']: m for m in db_monthly if m.get("is_official")}
        aggregated = aggregator.aggregate(
            db_days, self.entry.data, official_yearly_map, {}, {}, official_monthly_map
        )
        
        # 组装展示数据
        final_data = {
            "daylist": db_days,
            "payment_records": db_payments,
            "last_update": time.time(),
            "selected_cons_no": self.cons_no,
        }
        final_data.update(aggregated)
        
        if len(db_days) >= 3:
            last_days = db_days[:7]
            avg = sum(d.get("dayEleCost", 0) for d in last_days) / len(last_days)
            final_data["daily_avg"] = round(avg, 2)
        
        if db_info:
            balance = db_info.get("balance")
            final_data.update({
                "balance": balance,
                "selected_owner_name": db_info.get("owner_name"),
                "selected_elec_addr": db_info.get("elec_addr"),
            })
            daily_avg = final_data.get("daily_avg")
            if balance is not None and daily_avg and daily_avg > 0:
                final_data["remaining_days"] = int(balance / daily_avg)
            try:
                extra = json.loads(db_info.get("extra_status", "{}"))
                for k, v in extra.items():
                    if k not in final_data: final_data[k] = v
            except Exception: pass

        if api_data:
             for k, v in api_data.items():
                 if k not in final_data and k not in ["daily_usage", "payment_records"]:
                     final_data[k] = v
        
        return final_data

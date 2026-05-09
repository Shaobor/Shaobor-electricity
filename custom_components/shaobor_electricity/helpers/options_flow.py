"""Options flow for shaobor_electricity."""
from typing import Any
import logging
import voluptuous as vol  # type: ignore[import-untyped]

_LOGGER = logging.getLogger(__name__)

from homeassistant import config_entries  # type: ignore[import-untyped]
from homeassistant.config_entries import ConfigEntry  # type: ignore[import-untyped]
from homeassistant.data_entry_flow import FlowResult  # type: ignore[import-untyped]
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode  # type: ignore[import-untyped]
from .data_importer import validate_import_json

from ..const import (
    DOMAIN,
    CONF_BILLING_MODE,
    BILLING_STANDARD_YEAR_LADDER_TOU,
    BILLING_STANDARD_YEAR_LADDER,
    BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE,
    BILLING_STANDARD_MONTH_LADDER_TOU,
    BILLING_STANDARD_MONTH_LADDER,
    BILLING_STANDARD_AVERAGE,
    BILLING_DATA_IMPORT,
    BILLING_DATA_VIEW,
    CONF_LADDER_LEVEL_1,
    CONF_LADDER_LEVEL_2,
    CONF_LADDER_PRICE_1,
    CONF_LADDER_PRICE_2,
    CONF_LADDER_PRICE_3,
    CONF_PRICE_TIP,
    CONF_PRICE_PEAK,
    CONF_PRICE_FLAT,
    CONF_PRICE_VALLEY,
    CONF_AVERAGE_PRICE,
    CONF_YEAR_LADDER_START,
)

from .schemas import (
    get_year_ladder_tou_schema,
    get_year_ladder_schema,
    get_month_ladder_tou_variable_schema,
    get_month_ladder_tou_schema,
    get_month_ladder_schema,
    get_average_config_schema,
)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Shaobor_95598."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            billing_mode = user_input[CONF_BILLING_MODE]
            # 根据计费模式跳转到对应的价格配置页面
            if billing_mode == BILLING_STANDARD_YEAR_LADDER_TOU:
                return await self.async_step_year_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_YEAR_LADDER:
                return await self.async_step_year_ladder_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE:
                return await self.async_step_month_ladder_tou_variable_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER_TOU:
                return await self.async_step_month_ladder_tou_config()
            elif billing_mode == BILLING_STANDARD_MONTH_LADDER:
                return await self.async_step_month_ladder_config()
            elif billing_mode == BILLING_STANDARD_AVERAGE:
                return await self.async_step_average_config()
            elif billing_mode == BILLING_DATA_IMPORT:
                return await self.async_step_data_import()
            elif billing_mode == BILLING_DATA_VIEW:
                return await self.async_step_data_view()

        # 获取当前配置的计费模式
        current_billing_mode = self.config_entry.data.get(CONF_BILLING_MODE, BILLING_STANDARD_YEAR_LADDER)
        
        billing_options = [
            {"value": BILLING_STANDARD_YEAR_LADDER_TOU, "label": "年阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_YEAR_LADDER, "label": "年阶梯计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE, "label": "月阶梯峰平谷变动价格计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER_TOU, "label": "月阶梯峰平谷计费"},
            {"value": BILLING_STANDARD_MONTH_LADDER, "label": "月阶梯计费"},
            {"value": BILLING_STANDARD_AVERAGE, "label": "平均单价计费"},
            {"value": BILLING_DATA_IMPORT, "label": "📥 历史数据导入 (JSON)"},
            {"value": BILLING_DATA_VIEW, "label": "🔍 查看已导入数据汇总"},
        ]
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BILLING_MODE, default=current_billing_mode): SelectSelector(
                        SelectSelectorConfig(
                            options=billing_options,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_year_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯峰平谷计费."""
        if user_input is not None:
            # 更新配置，确保包含 billing_mode
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_YEAR_LADDER_TOU}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="year_ladder_tou_config",
            data_schema=get_year_ladder_tou_schema(current_data),
        )

    async def async_step_year_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置年阶梯计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_YEAR_LADDER}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        # 根据户号自动获取地区电价配置
        from .regional_prices import get_region_price_config, get_region_name
        
        current_data = self.config_entry.data
        
        # 尝试从coordinator获取户号
        cons_no = ""
        if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
            if coordinator and coordinator.data:
                cons_no = coordinator.data.get("selected_cons_no", "")
        
        # 获取地区配置
        regional_config = get_region_price_config(cons_no) if cons_no else None
        region_name = get_region_name(cons_no) if cons_no else "未知地区"
        
        # 设置默认值
        if regional_config:
            default_level_1 = regional_config["ladder_level_1"]
            default_level_2 = regional_config["ladder_level_2"]
            default_price_1 = regional_config["ladder_price_1"]
            default_price_2 = regional_config["ladder_price_2"]
            default_price_3 = regional_config["ladder_price_3"]
            description = f"已自动识别地区：{region_name}\n当前配置的电价标准，您可以根据需要修改。"
        else:
            default_level_1 = 2040
            default_level_2 = 3240
            default_price_1 = 0.51
            default_price_2 = 0.56
            default_price_3 = 0.81
            description = "当前配置的电价标准，您可以根据实际情况修改。"
        
        # Use helper and pass the explicitly resolved defaults (fallback to regional defaults)
        defaults = {
            **current_data,
            CONF_LADDER_LEVEL_1: current_data.get(CONF_LADDER_LEVEL_1, default_level_1),
            CONF_LADDER_LEVEL_2: current_data.get(CONF_LADDER_LEVEL_2, default_level_2),
            CONF_LADDER_PRICE_1: current_data.get(CONF_LADDER_PRICE_1, default_price_1),
            CONF_LADDER_PRICE_2: current_data.get(CONF_LADDER_PRICE_2, default_price_2),
            CONF_LADDER_PRICE_3: current_data.get(CONF_LADDER_PRICE_3, default_price_3),
        }
        return self.async_show_form(
            step_id="year_ladder_config",
            description_placeholders={"description": description},
            data_schema=get_year_ladder_schema(defaults),
        )

    async def async_step_month_ladder_tou_variable_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷变动价格计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="month_ladder_tou_variable_config",
            data_schema=get_month_ladder_tou_variable_schema(current_data),
        )

    async def async_step_month_ladder_tou_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯峰平谷计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER_TOU}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="month_ladder_tou_config",
            data_schema=get_month_ladder_tou_schema(current_data),
        )

    async def async_step_month_ladder_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置月阶梯计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_MONTH_LADDER}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="month_ladder_config",
            data_schema=get_month_ladder_schema(current_data),
        )

    async def async_step_average_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """配置平均单价计费."""
        if user_input is not None:
            new_data = {**self.config_entry.data, **user_input, CONF_BILLING_MODE: BILLING_STANDARD_AVERAGE}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="average_config",
            data_schema=get_average_config_schema(current_data),
        )

    async def async_step_data_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """步骤 1：输入 JSON 数据."""
        errors = {}
        if user_input is not None:
            # 如果用户选择返回上一步
            if user_input.get("go_back"):
                return await self.async_step_init()
                
            # 如果既没选返回，也没填 JSON，则提示错误
            if not user_input.get("json_data"):
                errors["json_data"] = "empty_json"
            else:
                try:
                    _LOGGER.info(f"[数据导入] 开始校验 JSON 数据, 长度: {len(user_input['json_data'])}")
                    result = validate_import_json(user_input["json_data"])
                    
                    if not result.get("success"):
                        _LOGGER.warning(f"[数据导入] 校验失败: {result.get('error')}")
                        errors["json_data"] = result.get("error", "invalid_json")
                    else:
                        data = result.get("data", {})
                        if not data.get("daily") and not data.get("monthly") and not data.get("yearly"):
                            _LOGGER.warning("[数据导入] 校验通过但未发现有效数据块")
                            errors["json_data"] = "未找到有效的数据列表 (daylist, monthlist 或 yearlist)"
                        else:
                            self._import_temp_data = data
                            self._import_summary = result.get("summary", "未知数据")
                            _LOGGER.info(f"[数据导入] 校验成功: {self._import_summary}")
                            return await self.async_step_data_verify()
                except Exception as err:
                    _LOGGER.error(f"[数据导入] 流程异常: {err}", exc_info=True)
                    errors["json_data"] = f"处理异常: {err}"

        from homeassistant.helpers.selector import TextSelector, TextSelectorConfig # type: ignore
        
        return self.async_show_form(
            step_id="data_import",
            data_schema=vol.Schema({
                vol.Optional("json_data"): TextSelector(TextSelectorConfig(multiline=True)),
                vol.Optional("go_back", default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_data_verify(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """步骤 2：二次验证并确认导入."""
        if user_input is not None:
            # 1. 记录任务存档（元数据）
            from .data_importer import save_import_task, async_import_history_to_store
            
            try:
                # 获取户号作为后缀
                cons_no = self.config_entry.data.get("selected_cons_no", "")
                if not cons_no and DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
                    coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
                    if coordinator and hasattr(coordinator, "cons_no"):
                        cons_no = coordinator.cons_no
                
                suffix = cons_no if cons_no else self.config_entry.entry_id
                
                # 在存盘前，执行一次真实的过滤，确保任务记录文字与实际存盘条数一致
                from .data_importer import get_import_preview, save_import_task, async_import_history_to_store
                preview = await get_import_preview(self.hass, suffix, self._import_temp_data)
                
                final_data = self._import_temp_data
                final_summary = self._import_summary
                
                if preview["skip_count"] > 0:
                    # 重新构造过滤后的数据和摘要
                    min_date = preview["min_date"]
                    final_data = {
                        "daily": {d: v for d, v in self._import_temp_data.get("daily", {}).items() if d < min_date},
                        "monthly": {m: v for m, v in self._import_temp_data.get("monthly", {}).items() if m < min_date[:7]},
                        "yearly": {y: v for y, v in self._import_temp_data.get("yearly", {}).items() if y < min_date[:4]},
                    }
                    # 重新生成摘要描述
                    parts = []
                    if final_data["daily"]: parts.append(f"{len(final_data['daily'])}条日记录")
                    if final_data["monthly"]: parts.append(f"{len(final_data['monthly'])}条月记录")
                    if final_data["yearly"]: parts.append(f"{len(final_data['yearly'])}条年记录")
                    final_summary = " + ".join(parts) if parts else "0条记录 (全被拦截)"

                _LOGGER.info(f"[数据导入] 正在执行存盘操作 (ID: {suffix}): {final_summary}")
                
                # 1. 记录任务存档（使用过滤后的摘要和数据）
                task_id = await save_import_task(
                    self.hass, suffix, final_data, final_summary
                )
                
                # 2. 执行真正的电量数据保存逻辑
                await async_import_history_to_store(
                    self.hass, suffix, final_data, task_id=task_id
                )
                
                # 触发 Coordinator 刷新
                if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
                    coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
                    if coordinator:
                        await coordinator.async_request_refresh()
                        
                _LOGGER.info("[数据导入] 导入任务全部执行完毕")
                return self.async_create_entry(title="", data={})
            except Exception as err:
                _LOGGER.error(f"[数据导入] 确认存盘时发生异常: {err}", exc_info=True)
                return self.async_abort(reason="import_failed")

        # 1. 动态确定存储后缀 (用于获取预览)
        from .data_importer import get_import_preview
        cons_no = self.config_entry.data.get("selected_cons_no", "")
        if not cons_no and DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
            if coordinator and hasattr(coordinator, "cons_no"):
                cons_no = coordinator.cons_no
        suffix = cons_no if cons_no else self.config_entry.entry_id
        
        preview = await get_import_preview(self.hass, suffix, self._import_temp_data)
        skip_notice = ""
        if preview["skip_count"] > 0:
            skip_notice = (
                f"\n\n🚨 **日期冲突提醒**：\n"
                f"检测到官方最早记录为 {preview['min_date']}，"
                f"本次导入将自动跳过 {preview['skip_count']} 条重复或更新的日记录，"
                f"仅保留 {preview['keep_count']} 条早于官方的历史记录。"
            )

        summary = self._import_summary
        description = (
            f"📦 待导入数据概览：\n"
            f"{summary}\n"
            f"{skip_notice}\n\n"
            f"⚠️ 注意：导入操作会合并到现有人工库中（相同日期的记录将被覆盖）。\n"
            f"确认无误后请点击提交完成存盘。"
        )

        return self.async_show_form(
            step_id="data_verify",
            description_placeholders={"description": description},
            data_schema=vol.Schema({
                vol.Required("confirm", default=True): bool
            }),
        )
    async def async_step_data_view(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """查看人工导入的任务列表并提供管理功能."""
        from .data_importer import get_import_tasks, delete_import_task
        entry_id = self.config_entry.entry_id
        # 1. 动态确定存储后缀 (优先使用户号)
        cons_no = self.config_entry.data.get("selected_cons_no", "")
        if not cons_no and DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id].get("coordinator")
            if coordinator and hasattr(coordinator, "cons_no"):
                cons_no = coordinator.cons_no
        
        suffix = cons_no if cons_no else entry_id
        
        # 2. 获取任务列表
        tasks = await get_import_tasks(self.hass, suffix)
        
        # 迁移：如果户号下没任务，但 entry_id 下有，则尝试迁移
        if not tasks and cons_no:
            legacy_tasks = await get_import_tasks(self.hass, entry_id)
            if legacy_tasks:
                _LOGGER.info("[数据查看] 发现旧版任务记录，正在迁移至户号文件")
                tasks = legacy_tasks
                # 迁移任务文件
                from homeassistant.helpers.storage import Store
                await Store(self.hass, version=1, key=f"shaobor_electricity/shaobor_import_tasks_{suffix}").async_save(tasks)
                await Store(self.hass, version=1, key=f"shaobor_electricity/shaobor_import_tasks_{entry_id}").async_remove()
                # 迁移数据文件
                legacy_data = await Store(self.hass, version=1, key=f"shaobor_electricity/shaobor_imported_{entry_id}").async_load()
                if legacy_data:
                    await Store(self.hass, version=1, key=f"shaobor_electricity/shaobor_imported_{suffix}").async_save(legacy_data)
                    await Store(self.hass, version=1, key=f"shaobor_electricity/shaobor_imported_{entry_id}").async_remove()
        
        if user_input is not None:
            selected_tasks = user_input.get("delete_task")
            if selected_tasks:
                # 记录要删除的任务 ID 列表
                self._delete_task_ids = selected_tasks if isinstance(selected_tasks, list) else [selected_tasks]
                return await self.async_step_data_delete_confirm()
            return await self.async_step_init()

        task_options = []
        summary = "📊 人工导入任务管理助手\n"
        summary += "---------------------------------\n"
        
        if not tasks:
            summary += "💡 目前没有任何导入历史。你可以去导入页面录入 JSON 数据。"
        else:
            summary += f"✅ 发现 {len(tasks)} 个历史任务，请在下方选择需要删除的任务：\n\n"
            # 按时间倒序排列
            sorted_tasks = sorted(tasks.values(), key=lambda x: x["time"], reverse=True)
            for t in sorted_tasks:
                task_label = f"📅 {t['time']} | {t['summary']}"
                summary += f"• {task_label}\n"
                task_options.append({"value": t["id"], "label": task_label})
            
            summary += f"\n\n注：删除任务会自动从数据库中剔除对应日期的记录。"

        return self.async_show_form(
            step_id="data_view",
            data_schema=vol.Schema({
                vol.Optional("delete_task"): SelectSelector(
                    SelectSelectorConfig(
                        options=task_options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }),
            description_placeholders={
                "data_summary": summary,
            }
        )

    async def async_step_data_delete_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """二次确认删除操作."""
        from .data_importer import get_import_tasks, delete_import_task
        from homeassistant.helpers.storage import Store
        
        # 1. 动态确定存储后缀
        entry_id = self.config_entry.entry_id
        cons_no = self.config_entry.data.get("selected_cons_no", "")
        if not cons_no and DOMAIN in self.hass.data and entry_id in self.hass.data[DOMAIN]:
            coordinator = self.hass.data[DOMAIN][entry_id].get("coordinator")
            if coordinator and hasattr(coordinator, "cons_no"):
                cons_no = coordinator.cons_no
        suffix = cons_no if cons_no else entry_id

        tasks = await get_import_tasks(self.hass, suffix)
        task_info_list = []
        for tid in self._delete_task_ids:
            task = tasks.get(tid, {})
            if task:
                task_info_list.append(f"• 📅 {task.get('time')} | {task.get('summary')}")
        
        task_info = "\n".join(task_info_list) if task_info_list else "未知任务"

        if user_input is not None:
            if user_input.get("confirm"):
                for tid in self._delete_task_ids:
                    await delete_import_task(self.hass, suffix, tid)
                
                # 核心：触发刷新
                if DOMAIN in self.hass.data and entry_id in self.hass.data[DOMAIN]:
                    coordinator = self.hass.data[DOMAIN][entry_id].get("coordinator")
                    if coordinator:
                        await coordinator.async_request_refresh()
                
                return await self.async_step_data_view()
            
            # 如果没勾选确认直接提交，返回列表
            return await self.async_step_data_view()

        return self.async_show_form(
            step_id="data_delete_confirm",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
            }),
            description_placeholders={"task_info": task_info},
        )

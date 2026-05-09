import json
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

def validate_import_json(json_text: str):
    """验证导入的 JSON 数据格式 (支持日、月、年)."""
    try:
        if not json_text or not isinstance(json_text, str):
            return {"success": False, "error": "输入内容不能为空"}
            
        obj = json.loads(json_text)
        if not isinstance(obj, dict):
            return {"success": False, "error": "JSON 根节点必须是对象 {}"}
        
        data_to_import = {"daily": {}, "monthly": {}, "yearly": {}}
        summary_parts = []
        
        # 1. 处理日流水
        day_list = obj.get("daylist") or obj.get("sevenEleList") or []
        if isinstance(day_list, list):
            for item in day_list:
                if isinstance(item, dict): # 必须是字典
                    day = item.get("day")
                    if day and len(str(day)) == 8:
                        d_str = str(day)
                        fmt_day = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                        data_to_import["daily"][fmt_day] = item
            if data_to_import["daily"]:
                summary_parts.append(f"{len(data_to_import['daily'])}条日记录")

        # 2. 处理月流水
        month_list = obj.get("monthlist") or []
        if isinstance(month_list, list):
            for item in month_list:
                if isinstance(item, dict):
                    month = item.get("month")
                    if not month: continue
                    m_str = str(month).replace("-", "")  # 兑容 YYYY-MM 和 YYYYMM 两种格式
                    if len(m_str) == 6:
                        fmt_month = f"{m_str[:4]}-{m_str[4:6]}"
                        # 导入的数据默认标记为官方数据
                        item["month"] = fmt_month
                        if "is_official" not in item:
                            item["is_official"] = True
                        data_to_import["monthly"][fmt_month] = item
            if data_to_import["monthly"]:
                summary_parts.append(f"{len(data_to_import['monthly'])}条月记录")

        # 3. 处理年流水
        year_list = obj.get("yearlist") or []
        if isinstance(year_list, list):
            for item in year_list:
                if isinstance(item, dict):
                    year = item.get("year")
                    if not year: continue
                    y_str = str(year).strip()
                    if len(y_str) == 4 and y_str.isdigit():
                        # 导入的数据默认标记为官方数据
                        if "is_official" not in item:
                            item["is_official"] = True
                        data_to_import["yearly"][y_str] = item
            if data_to_import["yearly"]:
                summary_parts.append(f"{len(data_to_import['yearly'])}条年记录")

        if not any(data_to_import.values()):
            return {"success": False, "error": "未找到有效的数据列表 (daylist, monthlist 或 yearlist)"}
            
        return {
            "success": True, 
            "data": data_to_import,
            "summary": " + ".join(summary_parts)
        }
    except Exception as e:
        _LOGGER.error(f"[数据导入] 校验异常: {e}", exc_info=True)
        return {"success": False, "error": f"解析异常: {str(e)}"}

async def get_import_preview(hass, suffix, data_to_import):
    """在真正导入前，预览哪些数据会被跳过 (对接数据库)."""
    from ..const import DOMAIN
    min_official_date = None
    
    # 1. 动态从数据库获取官方数据的“护城河”
    if DOMAIN in hass.data:
        coordinator = None
        for entry_id in hass.data[DOMAIN]:
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
                if coordinator: break
        
        if coordinator and hasattr(coordinator, "db"):
            db_history = await coordinator.db.async_get_all_daily_usage(suffix)
            if db_history:
                valid_dates = [d.get("day") for d in db_history if d.get("day")]
                if valid_dates:
                    min_official_date = min(valid_dates)
            
    if not min_official_date:
        return {"min_date": None, "skip_count": 0, "keep_count": len(data_to_import.get("daily", {}))}
        
    # 2. 计算跳过数量
    daily = data_to_import.get("daily", {})
    keep_daily = {d: v for d, v in daily.items() if d < min_official_date}
    skip_count = len(daily) - len(keep_daily)
    
    return {
        "min_date": min_official_date,
        "skip_count": skip_count,
        "keep_count": len(keep_daily)
    }

async def async_import_history_to_store(hass, suffix, data_to_import, task_id: str = ""):
    """将验证后的数据存入 SQLite 数据库。"""
    
    # 1. 保存到数据库 (实时对接新数据库架构)——带上 task_id
    from ..const import DOMAIN
    if DOMAIN in hass.data:
        # 获取第一个可用的 coordinator 及其数据库实例
        coordinator = None
        for entry_id in hass.data[DOMAIN]:
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
                if coordinator: break
        
        if coordinator and hasattr(coordinator, "db"):
            db = coordinator.db
            cons_no = suffix  # suffix 通常就是户号
            
            filtered_daily = data_to_import.get("daily", {})
            filtered_monthly = data_to_import.get("monthly", {})
            filtered_yearly = data_to_import.get("yearly", {})

            if filtered_daily:
                await db.async_save_imported_daily_usage(cons_no, list(filtered_daily.values()), task_id)
            if filtered_monthly:
                await db.async_save_imported_monthly_usage(cons_no, list(filtered_monthly.values()), task_id)
            if filtered_yearly:
                await db.async_save_imported_yearly_usage(cons_no, list(filtered_yearly.values()), task_id)
            
            _LOGGER.info("[数据导入] 数据已成功同步至数据库导入表 (task_id=%s)", task_id)
            return True

    return False

async def save_import_task(hass, suffix: str, data: dict, summary: str):
    """保存导入任务元数据 (对接数据库)。dates 字段只存范围摘要，不再存全量日期列表."""
    import uuid
    from datetime import datetime
    from ..const import DOMAIN
    
    task_id = str(uuid.uuid4())[:8]
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 只存范围摘要（如 2023-01-01~2023-12-31, 202301~202312, 2022~2023），不再存全量日期列表
    range_parts = []
    if isinstance(data, dict):
        daily = data.get("daily", {})
        monthly = data.get("monthly", {})
        yearly = data.get("yearly", {})
        if daily:
            days = sorted(daily.keys())
            range_parts.append(f"日: {days[0]}~{days[-1]}" if len(days) > 1 else f"日: {days[0]}")
        if monthly:
            months = sorted(monthly.keys())
            range_parts.append(f"月: {months[0]}~{months[-1]}" if len(months) > 1 else f"月: {months[0]}")
        if yearly:
            years = sorted(yearly.keys())
            range_parts.append(f"年: {years[0]}~{years[-1]}" if len(years) > 1 else f"年: {years[0]}")
    
    date_range_str = " | ".join(range_parts) if range_parts else ""
    
    # 存入数据库， dates 字段存范围摘要字符串
    if DOMAIN in hass.data:
        coordinator = None
        for entry_id in hass.data[DOMAIN]:
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
                if coordinator: break
        
        if coordinator and hasattr(coordinator, "db"):
            await coordinator.db.async_save_import_task(task_id, suffix, time_str, summary, [date_range_str])
            _LOGGER.info(f"[数据导入] 任务元数据已存入数据库: {task_id} ({date_range_str})")
            
    return task_id

async def get_import_tasks(hass, suffix: str):
    """获取所有导入任务 (从数据库读取)."""
    from ..const import DOMAIN
    if DOMAIN in hass.data:
        coordinator = None
        for entry_id in hass.data[DOMAIN]:
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
                if coordinator: break
        
        if coordinator and hasattr(coordinator, "db"):
            return await coordinator.db.async_get_import_tasks(suffix)
    return {}

async def delete_import_task(hass, suffix: str, task_id: str):
    """删除特定导入任务及其关联数据 (按 task_id 精准删除)."""
    from ..const import DOMAIN
    
    if DOMAIN in hass.data:
        coordinator = None
        for entry_id in hass.data[DOMAIN]:
            if isinstance(hass.data[DOMAIN][entry_id], dict):
                coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
                if coordinator: break
        
        if coordinator and hasattr(coordinator, "db"):
            # A. 按 task_id 精准删除导入的电量数据
            await coordinator.db.async_delete_imported_data(suffix, [], task_id=task_id)
            # B. 删除任务元数据
            await coordinator.db.async_delete_import_task(task_id, cons_no=suffix)
            _LOGGER.info(f"[数据管理] 已从数据库删除任务 {task_id} 及其关联数据")
            
    return True

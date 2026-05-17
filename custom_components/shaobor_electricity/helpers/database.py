import logging
import sqlite3
import os
import asyncio
from datetime import datetime
from typing import Any, List, Dict

_LOGGER = logging.getLogger(__name__)

class StateGridDatabase:
    """SQLite database helper for shaobor_electricity."""

    def __init__(self, hass, db_path: str):
        self.hass = hass
        self.db_path = db_path
        self._lock = asyncio.Lock()

    def _get_connection(self):
        """Get a database connection (thread-local)."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    async def async_init(self):
        """Initialize the database and create tables."""
        def _init_db():
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # 1. 每日电量表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_daily_usage (
                        cons_no TEXT, day TEXT, ele_num REAL, ele_cost REAL,
                        tpq REAL DEFAULT 0, ppq REAL DEFAULT 0, npq REAL DEFAULT 0, vpq REAL DEFAULT 0,
                        PRIMARY KEY (cons_no, day)
                    )
                """)
                # 2. 月度汇总表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_monthly_usage (
                        cons_no TEXT, month TEXT, ele_num REAL, ele_cost REAL,
                        is_official INTEGER DEFAULT 0,
                        PRIMARY KEY (cons_no, month)
                    )
                """)
                # 3. 年度汇总表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_yearly_usage (
                        cons_no TEXT, year TEXT, ele_num REAL, ele_cost REAL,
                        is_official INTEGER DEFAULT 0,
                        PRIMARY KEY (cons_no, year)
                    )
                """)
                # 4. 导入专用表 (日、月、年) —— 带 task_id 列，方便按任务精准删除
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_daily_usage_imported (
                        cons_no TEXT, day TEXT, ele_num REAL, ele_cost REAL,
                        tpq REAL, ppq REAL, npq REAL, vpq REAL,
                        task_id TEXT,
                        PRIMARY KEY (cons_no, day)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_monthly_usage_imported (
                        cons_no TEXT, month TEXT, ele_num REAL, ele_cost REAL,
                        is_official INTEGER DEFAULT 0,
                        task_id TEXT,
                        PRIMARY KEY (cons_no, month)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_yearly_usage_imported (
                        cons_no TEXT, year TEXT, ele_num REAL, ele_cost REAL,
                        is_official INTEGER DEFAULT 0,
                        task_id TEXT,
                        PRIMARY KEY (cons_no, year)
                    )
                """)
                # 5. 缴费记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_payment_records (
                        cons_no TEXT, query_date TEXT, pay_date TEXT, amt REAL,
                        status TEXT, type_name TEXT, chan_name TEXT,
                        chan_cls TEXT, pay_mode_name TEXT, remark TEXT,
                        PRIMARY KEY (cons_no, pay_date, amt)
                    )
                """)
                # 6. 账户状态表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_account_info (
                        cons_no TEXT PRIMARY KEY, owner_name TEXT, elec_addr TEXT,
                        balance REAL, daily_avg REAL, last_update TEXT, extra_status TEXT
                    )
                """)
                # 7. 授权密钥表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_auth_store (
                        login_account TEXT PRIMARY KEY, user_token TEXT, access_token TEXT,
                        refresh_token TEXT, user_id TEXT, power_user_list TEXT, last_update TEXT
                    )
                """)
                # 8. 导入任务记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_import_tasks (
                        task_id TEXT PRIMARY KEY, cons_no TEXT, time TEXT,
                        summary TEXT, dates TEXT
                    )
                """)
                # 9. 系统配置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_sys_config (
                        key TEXT PRIMARY KEY, value TEXT
                    )
                """)
                # 10. 运行日志表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shaobor_app_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
                        level TEXT, module TEXT, message TEXT
                    )
                """)
                # 11. 索引优化
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_cons ON shaobor_daily_usage(cons_no)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_day ON shaobor_daily_usage(day)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_month ON shaobor_monthly_usage(month)")
                
                # 自动清理全 0 的脏数据 (日电量)
                cursor.execute("DELETE FROM shaobor_daily_usage WHERE (ele_num <= 0 OR ele_num IS NULL) AND (ele_cost <= 0 OR ele_cost IS NULL)")
                # 自动清理空的缴费记录
                cursor.execute("DELETE FROM shaobor_payment_records WHERE amt IS NULL OR amt = 0")
                
                # 兼容性升级：为旧表补全缺失的列
                cursor.execute("PRAGMA table_info(shaobor_payment_records)")
                columns = [column[1] for column in cursor.fetchall()]
                new_columns = [
                    ("type_name", "TEXT"),
                    ("chan_name", "TEXT"),
                    ("chan_cls", "TEXT"),
                    ("pay_mode_name", "TEXT"),
                    ("remark", "TEXT")
                ]
                for col_name, col_type in new_columns:
                    if col_name not in columns:
                        cursor.execute(f"ALTER TABLE shaobor_payment_records ADD COLUMN {col_name} {col_type}")
                        _LOGGER.info(f"[数据库] 缴费记录表已补全缺失列: {col_name}")
                
                # 兼容性升级：为旧版导入表补全 task_id 列
                for tbl in ["shaobor_daily_usage_imported", "shaobor_monthly_usage_imported", "shaobor_yearly_usage_imported"]:
                    cursor.execute(f"PRAGMA table_info({tbl})")
                    tbl_cols = [c[1] for c in cursor.fetchall()]
                    if "task_id" not in tbl_cols:
                        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN task_id TEXT")
                        _LOGGER.info(f"[数据库] {tbl} 已补全 task_id 列")
                    
                    # 自动清理孤儿数据：如果 task_id 为空，或者 task_id 在任务记录表中找不到，说明是残留脏数据，直接删除
                    cursor.execute(f"""
                        DELETE FROM {tbl} 
                        WHERE task_id IS NULL 
                        OR task_id = '' 
                        OR task_id NOT IN (SELECT task_id FROM shaobor_import_tasks)
                    """)
                
                _LOGGER.info("[数据库] 已清理导入表中的孤儿残留数据")
                
                conn.commit()
                _LOGGER.info("[数据库] 初始化成功: %s", self.db_path)
            finally:
                conn.close()

        await self.hass.async_add_executor_job(_init_db)
    
    @staticmethod
    def _safe_float(val):
        """安全转换浮点数."""
        if val is None or val == "" or val == "-":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    async def async_save_daily_usage(self, cons_no: str, daylist: List[Dict]):
        """批量保存日电量数据 (使用 REPLACE 确保覆盖)."""
        if not daylist: return

        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in daylist:
                    # 统一日期格式 YYYY-MM-DD
                    day = item.get("day", "")
                    if not day: continue
                    fmt_day = f"{day[:4]}-{day[4:6]}-{day[6:8]}" if len(str(day)) == 8 else day
                    
                    # 提取数值并进行“零值过滤”
                    ele_num = item.get("dayEleNum") or item.get("dayElePq") or item.get("pq") or 0
                    ele_cost = item.get("dayEleCost") or item.get("cost") or 0
                    
                    # 防御性转换，确保是数字
                    try:
                        f_num = float(ele_num) if ele_num != "-" else 0
                        f_cost = float(ele_cost) if ele_cost != "-" else 0
                    except (ValueError, TypeError):
                        f_num, f_cost = 0, 0

                    # 如果电量和电费都是 0，则不存入数据库
                    if f_num <= 0 and f_cost <= 0:
                        continue

                    data.append((
                        cons_no,
                        fmt_day,
                        f_num,
                        f_cost,
                        self._safe_float(item.get("thisTPq") or item.get("dayTPq") or item.get("tip")),
                        self._safe_float(item.get("thisPPq") or item.get("dayPPq") or item.get("peak")),
                        self._safe_float(item.get("thisFPq") or item.get("thisNPq") or item.get("dayNPq") or item.get("flat")),
                        self._safe_float(item.get("thisVPq") or item.get("dayVPq") or item.get("valley"))
                    ))
                
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_daily_usage 
                    (cons_no, day, ele_num, ele_cost, tpq, ppq, npq, vpq)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()

        await self.hass.async_add_executor_job(_save)

    async def async_get_all_daily_usage(self, cons_no: str) -> List[Dict]:
        """获取所有日电量历史 (自动合并实时表和导入表)."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                # 使用 UNION 自动合并并去重
                cursor.execute("""
                    SELECT * FROM (
                        SELECT cons_no, day, ele_num, ele_cost, tpq, ppq, npq, vpq FROM shaobor_daily_usage WHERE cons_no = ?
                        UNION
                        SELECT cons_no, day, ele_num, ele_cost, tpq, ppq, npq, vpq FROM shaobor_daily_usage_imported WHERE cons_no = ?
                    ) GROUP BY day ORDER BY day DESC
                """, (cons_no, cons_no))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "day": row["day"].replace("-", ""),
                        "dayEleNum": row["ele_num"],
                        "dayEleCost": row["ele_cost"],
                        "dayTPq": row["tpq"],
                        "dayPPq": row["ppq"],
                        "dayNPq": row["npq"],
                        "dayVPq": row["vpq"],
                    })
                return results
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_save_imported_daily_usage(self, cons_no: str, daylist: List[Dict], task_id: str = ""):
        """将数据保存到导入专用表 (不触碰实时表)."""
        if not daylist: return
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in daylist:
                    day_raw = item.get("day")
                    if not day_raw: continue
                    fmt_day = f"{day_raw[:4]}-{day_raw[4:6]}-{day_raw[6:8]}" if len(str(day_raw)) == 8 else day_raw
                    data.append((
                        cons_no, fmt_day,
                        self._safe_float(item.get("dayEleNum") or item.get("pq") or 0),
                        self._safe_float(item.get("dayEleCost") or item.get("cost") or 0),
                        self._safe_float(item.get("dayTPq") or item.get("thisTPq") or item.get("tip") or 0),
                        self._safe_float(item.get("dayPPq") or item.get("thisPPq") or item.get("peak") or 0),
                        self._safe_float(item.get("dayNPq") or item.get("thisNPq") or item.get("thisFPq") or item.get("flat") or 0),
                        self._safe_float(item.get("dayVPq") or item.get("thisVPq") or item.get("valley") or 0),
                        task_id
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_daily_usage_imported 
                    (cons_no, day, ele_num, ele_cost, tpq, ppq, npq, vpq, task_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)
    async def async_add_log(self, level: str, module: str, message: str):
        """记录程序日志并自动清理旧日志."""
        def _add():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO shaobor_app_logs (timestamp, level, module, message)
                    VALUES (?, ?, ?, ?)
                """, (now, level, module, message))
                
                # 自动清理：保留最近 1000 条
                cursor.execute("""
                    DELETE FROM shaobor_app_logs 
                    WHERE id NOT IN (SELECT id FROM shaobor_app_logs ORDER BY id DESC LIMIT 1000)
                """)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_add)

    async def async_save_config(self, key: str, value: str):
        """保存系统配置 (如授权码)."""
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shaobor_sys_config (key, value)
                    VALUES (?, ?)
                """, (key, value))
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_get_config(self, key: str) -> str | None:
        """读取系统配置."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM shaobor_sys_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else None
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_save_account_info(self, info: Dict):
        """仅保存账户属性和实时状态 (不存密钥)."""
        import json
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shaobor_account_info 
                    (cons_no, owner_name, elec_addr, balance, daily_avg, last_update, extra_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    info.get("cons_no") or info.get("selected_cons_no"),
                    info.get("owner_name") or info.get("selected_owner_name"),
                    info.get("elec_addr") or info.get("selected_elec_addr"),
                    round(self._safe_float(info.get("balance")), 2) if info.get("balance") is not None else None,
                    round(self._safe_float(info.get("daily_avg")), 2) if info.get("daily_avg") is not None else None,
                    datetime.now().isoformat(),
                    json.dumps({k: v for k, v in info.items() if k not in [
                        "cons_no", "selected_cons_no", "owner_name", "selected_owner_name",
                        "elec_addr", "selected_elec_addr", "balance", "daily_avg",
                        "daylist", "payment_records", "user_token", "access_token", "refresh_token"
                    ]})
                ))
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_save_auth(self, account: str, auth_data: Dict):
        """保存登录密钥 (独立表)."""
        import json
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shaobor_auth_store 
                    (login_account, user_token, access_token, refresh_token, user_id, power_user_list, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    account,
                    auth_data.get("user_token"),
                    auth_data.get("access_token"),
                    auth_data.get("refresh_token"),
                    auth_data.get("user_id"),
                    json.dumps(auth_data.get("power_user_list", [])),
                    datetime.now().isoformat()
                ))
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_get_auth(self, account: str) -> Dict | None:
        """获取登录密钥."""
        import json
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM shaobor_auth_store WHERE login_account = ?", (account,))
                row = cursor.fetchone()
                if row:
                    res = dict(row)
                    try:
                        res["power_user_list"] = json.loads(res["power_user_list"])
                    except: pass
                    return res
                return None
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_get_account_info(self, cons_no: str) -> Dict | None:
        """获取账户信息."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM shaobor_account_info WHERE cons_no = ?", (cons_no,))
                row = cursor.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_save_payments(self, cons_no: str, payments: Any):
        """批量保存缴费记录."""
        if not payments: return
        
        # 兼容处理：如果传入的是字典，提取其中的 payList
        records = []
        if isinstance(payments, dict):
            records = payments.get("payList") or []
        elif isinstance(payments, list):
            records = payments
            
        if not records: return

        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in records:
                    amt = round(self._safe_float(item.get("rcvAmt") or item.get("amt")), 2)
                    # 如果金额为 0，说明是无效数据，跳过
                    if amt <= 0:
                        continue

                    data.append((
                        cons_no,
                        item.get("queryDate") or item.get("payDate"), # 优先使用查询日期
                        item.get("payDate"),
                        amt,
                        item.get("status") or item.get("typeName") or "成功",
                        item.get("typeName"),
                        item.get("chanName"),
                        item.get("chanCls"),
                        item.get("payModeName"),
                        item.get("remark")
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_payment_records 
                    (cons_no, query_date, pay_date, amt, status, type_name, chan_name, chan_cls, pay_mode_name, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_save_monthly_usage(self, cons_no: str, monthlist: List[Dict]):
        """批量保存月度电量数据."""
        if not monthlist: return
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in monthlist:
                    data.append((
                        cons_no,
                        item.get("month"),
                        item.get("ele_num") or item.get("monthEleNum") or item.get("eleNum") or item.get("pq") or 0,
                        item.get("ele_cost") or item.get("monthEleCost") or item.get("eleCost") or item.get("cost") or 0,
                        1 if item.get("is_official") else 0
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_monthly_usage 
                    (cons_no, month, ele_num, ele_cost, is_official)
                    VALUES (?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)


    async def async_save_yearly_usage(self, cons_no: str, yearlist: List[Dict]):
        """批量保存年度电量汇总."""
        if not yearlist: return
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in yearlist:
                    data.append((
                        cons_no,
                        str(item.get("year")),
                        item.get("ele_num") or item.get("yearEleNum") or item.get("eleNum") or item.get("totalEleNum") or 0,
                        item.get("ele_cost") or item.get("yearEleCost") or item.get("eleCost") or item.get("totalEleCost") or 0,
                        1 if item.get("is_official") else 0
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_yearly_usage 
                    (cons_no, year, ele_num, ele_cost, is_official)
                    VALUES (?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_get_all_yearly_usage(self, cons_no: str) -> List[Dict]:
        """获取所有年度汇总 (自动合并实时表和导入表)."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM (
                        SELECT cons_no, year, ele_num, ele_cost, is_official FROM shaobor_yearly_usage WHERE cons_no = ?
                        UNION
                        SELECT cons_no, year, ele_num, ele_cost, is_official FROM shaobor_yearly_usage_imported WHERE cons_no = ?
                    ) GROUP BY year ORDER BY year DESC
                """, (cons_no, cons_no))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "year": row["year"],
                        "yearEleNum": row["ele_num"],
                        "yearEleCost": row["ele_cost"],
                        "eleNum": row["ele_num"],
                        "eleCost": row["ele_cost"],
                        "is_official": bool(row["is_official"]),
                    })
                return results
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_save_imported_yearly_usage(self, cons_no: str, yearlist: List[Dict], task_id: str = ""):
        """将年度数据保存到导入表."""
        if not yearlist: return
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in yearlist:
                    data.append((
                        cons_no, str(item.get("year")),
                        # 兼容多种字段名：yearEleNum > eleNum > totalEleNum
                        self._safe_float(item.get("yearEleNum") or item.get("eleNum") or item.get("totalEleNum") or 0),
                        self._safe_float(item.get("yearEleCost") or item.get("eleCost") or item.get("totalEleCost") or 0),
                        1 if item.get("is_official") else 0,
                        task_id
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_yearly_usage_imported 
                    (cons_no, year, ele_num, ele_cost, is_official, task_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_get_all_monthly_usage(self, cons_no: str) -> List[Dict]:
        """获取所有月度汇总 (自动合并实时表和导入表)."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM (
                        SELECT cons_no, month, ele_num, ele_cost, is_official FROM shaobor_monthly_usage WHERE cons_no = ?
                        UNION
                        SELECT cons_no, month, ele_num, ele_cost, is_official FROM shaobor_monthly_usage_imported WHERE cons_no = ?
                    ) GROUP BY month ORDER BY month DESC
                """, (cons_no, cons_no))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "month": row["month"],
                        "monthEleNum": row["ele_num"],
                        "monthEleCost": row["ele_cost"],
                        "eleNum": row["ele_num"],
                        "eleCost": row["ele_cost"],
                        "is_official": bool(row["is_official"]),
                    })
                return results
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_save_imported_monthly_usage(self, cons_no: str, monthlist: List[Dict], task_id: str = ""):
        """将月度数据保存到导入表."""
        if not monthlist: return
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                data = []
                for item in monthlist:
                    data.append((
                        cons_no, item.get("month"),
                        # 兼容多种字段名：monthEleNum > eleNum > pq
                        self._safe_float(item.get("monthEleNum") or item.get("eleNum") or item.get("pq") or 0),
                        self._safe_float(item.get("monthEleCost") or item.get("eleCost") or item.get("cost") or 0),
                        1 if item.get("is_official") else 0,
                        task_id
                    ))
                cursor.executemany("""
                    INSERT OR REPLACE INTO shaobor_monthly_usage_imported 
                    (cons_no, month, ele_num, ele_cost, is_official, task_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_delete_imported_data(self, cons_no: str, dates: List[str], task_id: str = ""):
        """删除导入表中的数据。优先按 task_id 精准删除；兜底支持 'ALL' 关键词或日期列表."""
        def _delete():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                # 优先：按 task_id 精准删除（task_id 是唯一的，不需要带 cons_no 也能删干净）
                if task_id and task_id != "ALL":
                    cursor.execute("DELETE FROM shaobor_daily_usage_imported WHERE task_id = ?", (task_id,))
                    cursor.execute("DELETE FROM shaobor_monthly_usage_imported WHERE task_id = ?", (task_id,))
                    cursor.execute("DELETE FROM shaobor_yearly_usage_imported WHERE task_id = ?", (task_id,))

                elif dates:
                    # 兜底：按日期列表逐条删除（兼容旧逻辑）
                    cursor.executemany(
                        "DELETE FROM shaobor_daily_usage_imported WHERE cons_no = ? AND day = ?",
                        [(cons_no, d) for d in dates if len(d) == 10]
                    )
                    cursor.executemany(
                        "DELETE FROM shaobor_monthly_usage_imported WHERE cons_no = ? AND month = ?",
                        [(cons_no, d) for d in dates if len(d) == 7]
                    )
                    cursor.executemany(
                        "DELETE FROM shaobor_yearly_usage_imported WHERE cons_no = ? AND year = ?",
                        [(cons_no, d) for d in dates if len(d) == 4]
                    )
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_delete)

    async def async_save_import_task(self, task_id: str, cons_no: str, time_str: str, summary: str, dates: List[str]):
        """保存导入任务元数据."""
        import json
        def _save():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shaobor_import_tasks (task_id, cons_no, time, summary, dates)
                    VALUES (?, ?, ?, ?, ?)
                """, (task_id, cons_no, time_str, summary, json.dumps(dates)))
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_save)

    async def async_get_import_tasks(self, cons_no: str) -> Dict[str, Dict]:
        """获取指定户号的所有导入任务."""
        import json
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM shaobor_import_tasks WHERE cons_no = ?", (cons_no,))
                rows = cursor.fetchall()
                tasks = {}
                for row in rows:
                    tasks[row["task_id"]] = {
                        "id": row["task_id"],
                        "time": row["time"],
                        "summary": row["summary"],
                        "dates": json.loads(row["dates"]) if row["dates"] else []
                    }
                return tasks
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

    async def async_delete_import_task(self, task_id: str, cons_no: str = ""):
        """从数据库中删除特定任务记录 (支持 'ALL' 关键词)."""
        def _delete():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM shaobor_import_tasks WHERE task_id = ?", (task_id,))
                conn.commit()
            finally:
                conn.close()
        await self.hass.async_add_executor_job(_delete)

    async def async_get_all_payments(self, cons_no: str) -> List[Dict]:
        """获取指定户号的所有缴费记录."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM shaobor_payment_records 
                    WHERE cons_no = ? 
                    ORDER BY pay_date DESC
                """, (cons_no,))
                rows = cursor.fetchall()
                _LOGGER.info(f"[数据库查询] 户号: '{cons_no}', 查到缴费记录: {len(rows)} 条")
                results = []
                for row in rows:
                    results.append({
                        "queryDate": row["query_date"],
                        "payDate": row["pay_date"],
                        "rcvAmt": row["amt"],
                        "status": row["status"],
                        "typeName": row["type_name"],
                        "chanName": row["chan_name"],
                        "chanCls": row["chan_cls"],
                        "payModeName": row["pay_mode_name"],
                        "remark": row["remark"],
                    })
                return results
            finally:
                conn.close()
        return await self.hass.async_add_executor_job(_get)

import logging
import threading
class DBLogHandler(logging.Handler):
    """自定义日志处理器，将日志写入数据库."""

    def __init__(self, hass, db):
        super().__init__()
        self.hass = hass
        self.db = db
        self.setLevel(logging.INFO)
        self._writing = threading.Lock()

    def emit(self, record):
        # 防止递归：写数据库的日志不要再触发写数据库
        if record.module == "shaobor_electricity.helpers.database":
            return
        if not self._writing.acquire(blocking=False):
            return
        try:
            msg = self.format(record)
            if self.hass and self.hass.loop:
                self.hass.loop.call_soon_threadsafe(
                    self._schedule_log,
                    record.levelname,
                    record.module,
                    msg,
                )
        except Exception:
            self.handleError(record)
        finally:
            self._writing.release()

    def _schedule_log(self, levelname, module, msg):
        self.hass.async_create_task(
            self.db.async_add_log(levelname, module, msg)
        )

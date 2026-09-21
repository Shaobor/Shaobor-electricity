"""手机 App（iOS REST 链路）数据源客户端。

架构：HA 集成 → Node 中转后端 (/api/mobile/ios/*) → csc-service-sh.sgcc.com.cn。
信封组装（serviceCode/source/target/data）、SM4/SM2 加解密、设备指纹、登录态
续期全部由后端负责；本客户端只做薄封装，与网页版 UsageMixin.get_electricity_data
返回同构数据，供 Coordinator 无感切换数据源。

后端接口（均需 token + machineId）：
  POST {ENCRYPT_API_URL}/mobile/ios/call        operation 分发（登录/业务）
  POST {ENCRYPT_API_URL}/mobile/ios/capabilities 授权校验
  POST {ENCRYPT_API_URL}/mobile/ios/profile      登录档案（户号列表）
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp  # type: ignore[import-untyped]

from ..client.const import ENCRYPT_API_URL
from ..client.base import REQUEST_TIMEOUT
from ..client.exceptions import StateGridAuthError, StateGridConnectionError
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 日用电量查询窗口：c11/f01 queryType '2' 实证为七日区间。
DAILY_USAGE_WINDOW_DAYS = 15


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class MobileIosApiClient:
    """手机 App（iOS 链路）数据源客户端，接口与网页版客户端鸭子类型兼容。"""

    def __init__(
        self,
        token: str,
        session: aiohttp.ClientSession,
        hass: Any | None = None,
        entry_id: str | None = None,
        machine_id: str | None = None,
    ) -> None:
        self._encrypt_token = token
        self._session = session
        self._hass = hass
        self._entry_id = entry_id
        self._machine_id = machine_id

        self._db: Any = None
        self._billing_config: dict[str, Any] = {}

        # 以下属性供 Coordinator / 选项流读取（保持与网页版客户端同名）
        self._user_token: str | None = ""
        self._user_id: str | None = ""
        self._access_token: str | None = ""
        self._refresh_token: str | None = ""
        self._power_user_list: list[dict[str, Any]] = []
        self._raw_power_users: list[dict[str, Any]] = []
        self._selected_account_index: int = 0
        self._login_account: str | None = None
        self._active_account: dict[str, Any] = {}
        self._key_code: str = ""
        # 停电公告缓存（key: machineId:areaNo）：上游对该接口有频控（S1009
        # "系统繁忙"），公告变化频率低，缓存 1 小时并在失败时回退旧值。
        self._notices_cache: dict[str, dict[str, Any]] = {}
        # 最近一次实际发起查询的时间（1 小时节流窗口）
        self._notices_last_attempt: dict[str, datetime] = {}

        # 登录会话（本地真值：登录后/启动预热时写入，请求时随带上送中转后端）
        self._ios_session: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 兼容层：网页版客户端的公共接口（Coordinator / __init__ / 选项流调用）
    # ------------------------------------------------------------------

    def set_db(self, db: Any) -> None:
        """兼容接口：移动源历史直接入数据库。"""
        self._db = db

    def set_billing_config(self, config: dict[str, Any]) -> None:
        self._billing_config = config

    def set_auto_relogin_credentials(self, **_kwargs: Any) -> None:
        """兼容接口：移动源掉线重登由后端/选项流处理，无需凭据。"""

    def set_selected_account(self, index: int) -> None:
        self._selected_account_index = index

    def load_auth_state(self, **_kwargs: Any) -> None:
        """兼容接口：登录态保存在后端，无需本地恢复。"""

    async def initialize(self, force_new_uuid: bool = False) -> None:
        """兼容接口：校验后端授权（同 validate_token）。"""
        if not await self.validate_token():
            raise StateGridAuthError("中转后端授权校验失败 (mobile/ios)")

    async def validate_token(self) -> bool:
        """校验服务授权码与 machineId 绑定。"""
        try:
            await self._post("/mobile/ios/capabilities", {})
            _LOGGER.info("[API][mobile_ios] 授权密钥验证通过")
            return True
        except Exception as err:  # noqa: BLE001 授权校验不允许抛非授权类异常穿透
            _LOGGER.error("[API][mobile_ios] 授权密钥验证失败: %s", err)
            return False

    async def refresh_access_token(self) -> None:
        """兼容接口：移动源登录态由后端自动复用/续期，无需刷新。"""

    # ------------------------------------------------------------------
    # 后端调用
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{ENCRYPT_API_URL}{path}"
        body = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            **payload,
        }
        try:
            async with self._session.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                try:
                    data: Any = await resp.json(content_type=None)
                except Exception as err:  # noqa: BLE001 网关 404/HTML 等非 JSON 响应
                    raise StateGridConnectionError(
                        f"中转后端响应非 JSON (HTTP {resp.status}): {err}"
                    ) from err
                if resp.status in (401, 403):
                    msg = (
                        data.get("error")
                        if isinstance(data, dict)
                        else f"HTTP {resp.status}"
                    )
                    raise StateGridAuthError(f"后端授权失败: {msg}")
                if resp.status >= 400 or not isinstance(data, dict):
                    raise StateGridConnectionError(
                        f"中转后端 HTTP {resp.status}: {str(data)[:200]}"
                    )
        except aiohttp.ClientError as err:
            raise StateGridConnectionError(f"中转后端通信失败: {err}") from err

        if not data.get("success"):
            code = str(data.get("code") or "")
            msg = str(data.get("error") or "未知错误")
            if code == "authentication_expired":
                raise StateGridAuthError(f"手机App登录态已过期: {msg}")
            if code == "risk_control":
                raise StateGridAuthError(f"上游风控拦截: {msg}")
            raise StateGridConnectionError(f"后端业务错误 ({code or 'unknown'}): {msg}")
        return data

    async def ios_call(
        self,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """调用 /mobile/ios/call，返回 data 字段。

        本地持有会话：session 与当前户号档案随请求一并带给中转后端，
        后端不再依赖其落库状态（落库仅作旧版兼容兜底）。
        """
        body: dict[str, Any] = {"operation": operation, "payload": payload or {}}
        if self._ios_session.get("token"):
            body["session"] = {
                "token": self._ios_session.get("token"),
                "userId": self._ios_session.get("userId") or "",
                "province": self._ios_session.get("province") or "",
            }
        active = getattr(self, "_active_account", None)
        if (
            isinstance(active, dict)
            and active.get("consNo")
            and "account" not in body["payload"]
        ):
            # 户号档案随请求上送（后端 normalizePowerUser 兼容网页版字段名，
            # consName 为其缺失字段，此处补齐）
            body["payload"] = {
                **(payload or {}),
                "account": {
                    # iOS 字段名（后端 builders 取 proCode/consType/consNoSrc）
                    "consNo": active.get("consNo", ""),
                    "proCode": active.get("proNo") or active.get("proCode", ""),
                    "consType": (
                        active.get("consSortCode")
                        or active.get("consType")
                        or active.get("elecTypeCode", "")
                    ),
                    "consNoSrc": active.get("consNo_dst") or active.get("consNoSrc") or active.get("consNo", ""),
                    # 网页版字段名（HA 内部/显示用）
                    "consNo_dst": active.get("consNo_dst") or active.get("consNo", ""),
                    "proNo": active.get("proNo", ""),
                    "orgNo": active.get("orgNo", ""),
                    "consSortCode": active.get("consSortCode", ""),
                    "userNameLong": active.get("userNameLong", ""),
                    "consName": active.get("consName_dst", ""),
                    "consName_dst": active.get("consName_dst", ""),
                    "elecAddr": active.get("elecAddr_dst") or active.get("elecAddr", ""),
                    "elecAddr_dst": active.get("elecAddr_dst", ""),
                    "isDefault": active.get("isDefault", "0"),
                },
            }
        result = await self._post("/mobile/ios/call", body)
        data = result.get("data")
        return data if isinstance(data, dict) else {}

    async def async_get_profile(self) -> dict[str, Any]:
        """获取登录档案：优先本地库（session 真值），本地无会话才查后端。"""
        # 自愈：配置流每步新建实例，会话/档案从本地库恢复
        if not self._ios_session.get("token") and self._db and self._machine_id:
            await self._load_local_session()
        if not self._power_user_list and self._ios_session.get("token") and (
            self._db and self._machine_id
        ):
            try:
                mirror = await self._db.async_get_mobile_auth(self._machine_id)
            except Exception:  # noqa: BLE001 镜像损坏按无档案处理
                mirror = None
            if mirror and mirror.get("session_token"):
                users = [
                    u
                    for u in (mirror.get("power_users") or [])
                    if isinstance(u, dict)
                ]
                if users:
                    self._raw_power_users = users
                    self._power_user_list = [
                        self._map_power_user(u) for u in users
                    ]
                    self._login_account = mirror.get("mobile") or self._login_account
        if self._ios_session.get("token") and self._power_user_list:
            # 本地已持有会话与档案（登录后/启动预热后），直接返回
            return {
                "success": True,
                "logged_in": True,
                "account": {
                    "mobile": self._login_account or "",
                    "userId": self._ios_session.get("userId") or "",
                    "province": self._ios_session.get("province") or "",
                    "powerUsers": self._raw_power_users or [],
                },
            }
        result = await self._post("/mobile/ios/profile", {})
        profile = result if isinstance(result, dict) else {}
        # 本地镜像：对齐 web 版 shaobor_auth_store，档案真值由本地持有
        if self._db and self._machine_id:
            try:
                await self._db.async_save_mobile_auth(self._machine_id, profile)
            except Exception as err:  # noqa: BLE001 镜像失败不影响主流程
                _LOGGER.debug("[API][mobile_ios] 登录档案本地镜像写入失败: %s", err)
        return profile

    async def request_sms(self, account: str) -> str:
        """请求短信验证码，返回 codeKey。"""
        data = await self.ios_call("requestSms", {"account": account})
        bizrt = data.get("bizrt") if isinstance(data.get("bizrt"), dict) else {}
        code_key = data.get("codeKey") or bizrt.get("codeKey") or ""
        if not code_key:
            raise StateGridAuthError("发送验证码成功但未返回 codeKey")
        return str(code_key)

    async def sms_login(self, account: str, code: str, code_key: str) -> dict[str, Any]:
        """短信验证码登录，返回后端响应（含 session/powerUserList）。"""
        result = await self._post(
            "/mobile/ios/call",
            {
                "operation": "smsLogin",
                "payload": {"account": account, "code": code, "codeKey": code_key},
            },
        )
        await self._persist_local_session(account, result, "smsLogin")
        return result

    async def password_login(self, account: str, password: str) -> dict[str, Any]:
        """密码登录（c2/f01）。

        仅当后端设备指纹已进信任名单（此前至少完成过一次短信登录）时可直接成功；
        新设备会触发设备验证/风控，此时应改走短信登录。
        """
        result = await self._post(
            "/mobile/ios/call",
            {
                "operation": "passwordLogin",
                "payload": {"account": account, "password": password},
            },
        )
        await self._persist_local_session(account, result, "passwordLogin")
        return result

    async def _persist_local_session(
        self, account: str, result: dict[str, Any], via: str
    ) -> None:
        """登录成功：把 session 令牌与户号档案存入 HA 本地库（本地真值）。"""
        sess = result.get("session") or {}
        token = str(sess.get("token") or "")
        if not token:
            return
        self._ios_session = {
            "token": token,
            "userId": sess.get("userId") or "",
            "province": sess.get("province") or "",
        }
        if self._db and self._machine_id:
            try:
                await self._db.async_save_mobile_auth(
                    self._machine_id,
                    {
                        "logged_in": True,
                        "account": {
                            "mobile": account,
                            "userId": sess.get("userId") or "",
                            "province": sess.get("province") or "",
                            "via": via,
                            "loginAt": datetime.now().isoformat(timespec="seconds"),
                            "powerUsers": sess.get("powerUserList") or [],
                        },
                    },
                    session=self._ios_session,
                )
                _LOGGER.info(
                    "[API][mobile_ios] 登录会话已保存到本地数据库 (machineId=%s)",
                    self._machine_id,
                )
            except Exception as err:  # noqa: BLE001 本地保存失败不阻断登录结果返回
                _LOGGER.warning("[API][mobile_ios] 登录会话本地保存失败: %s", err)

    async def _load_local_session(self) -> dict[str, Any]:
        """从本地库恢复 session（启动时调用；返回恢复的会话，无则空 dict）。"""
        if not (self._db and self._machine_id):
            return {}
        try:
            mirror = await self._db.async_get_mobile_auth(self._machine_id)
        except Exception:  # noqa: BLE001
            mirror = None
        if not mirror or not mirror.get("session_token"):
            return {}
        self._ios_session = {
            "token": mirror.get("session_token") or "",
            "userId": mirror.get("session_user_id") or "",
            "province": mirror.get("session_province") or "",
        }
        return self._ios_session

    # ------------------------------------------------------------------
    # 数据获取（与网页版 get_electricity_data 同构）
    # ------------------------------------------------------------------

    @staticmethod
    def _map_power_user(user: dict[str, Any]) -> dict[str, Any]:
        """iOS 登录响应 powerUserList → 网页版 powerUserList 字段名。

        原始字段实证（session_token.json raw_bizrt.userInfo.powerUserList）：
        consNo=长格式 98:...:001（业务请求用）、consNo_dst=短户号 2350000280080
        （显示用）、consName_dst=户名、elecAddr_dst=地址、proNo=表计版本。
        兼容旧后端归一化字段（consNoSrc/proCode/consType/name/address）。
        """
        return {
            "consNo": user.get("consNo", ""),
            # 显示用短户号：优先原生 consNo_dst，绝不能回退到长格式 consNo
            "consNo_dst": (
                user.get("consNo_dst")
                or user.get("consNoSrc")
                or ""
            ),
            "proNo": user.get("proNo") or user.get("proCode", ""),
            "orgNo": user.get("orgNo", ""),
            "orgName": user.get("orgName", ""),
            "consSortCode": (
                user.get("consSortCode")
                or user.get("consType")
                or user.get("elecTypeCode", "")
            ),
            "userNameLong": user.get("userNameLong") or user.get("consName", ""),
            "consName_dst": user.get("consName_dst") or user.get("name", ""),
            "elecAddr_dst": user.get("elecAddr_dst") or user.get("address", ""),
            "elecAddr": user.get("elecAddr_dst") or user.get("address", ""),
            "isDefault": "1" if user.get("isDefault") else "0",
        }

    async def fetch_power_user_list(self) -> list[dict[str, Any]]:
        """从后端档案取户号列表（网页版同构字段）。"""
        profile = await self.async_get_profile()
        if not profile.get("logged_in"):
            raise StateGridAuthError("手机App源尚未登录，请在集成选项中完成短信登录")
        account = profile.get("account") or {}
        users = account.get("powerUsers") or []
        if not users:
            raise StateGridAuthError("该账号名下未绑定任何户号 (powerUserList 为空)")
        self._raw_power_users = [u for u in users if isinstance(u, dict)]
        self._power_user_list = [self._map_power_user(u) for u in self._raw_power_users]
        self._login_account = account.get("mobile") or self._login_account
        self._user_id = account.get("userId") or self._user_id
        return self._power_user_list

    async def _fetch_maintenance_notices(
        self, active_account: dict[str, Any]
    ) -> dict[str, Any]:
        """停电信息·按区域（后端 c8/f05），结果与网页版 c4/f08 同构。

        areaNo/orgNo 推导复用网页版 division_mapping（orgNo→行政区划）；
        查询顺序同网页版：区县供电单位 → 市级回退。c8/f05 响应字段
        （powerRange/powerCause/powerCircuit/powerArea/powerType/startTime/
        stopTime/takeType）与网页公告天然同名，直接透传给传感器/前端卡片。
        """
        raw_org_no = str(active_account.get("orgNo") or active_account.get("org_no") or "")
        mapping = None
        if self._hass:
            mapping = self._hass.data.get(DOMAIN, {}).get("division_mapping")
        match = mapping.lookup_org_no(raw_org_no) if mapping and raw_org_no else None

        if not match or not match.district_code:
            return {
                "notices": [],
                "error": "当前账户缺少可匹配的供电地区信息",
                "org_no": raw_org_no,
            }

        async def _query_notices(query_org_no: str) -> list[dict[str, Any]]:
            data = await self.ios_call(
                "powerOutageByArea",
                {
                    "areaNo": match.district_code,
                    "orgNo": query_org_no,
                    "pageNo": 1,
                    "pageSize": 100,
                },
            )
            return [n for n in data.get("powerCutList") or [] if isinstance(n, dict)]

        query_org_no = match.org_code
        cache_key = f"{self._machine_id}:{match.district_code}"
        cached = self._notices_cache.get(cache_key)
        now = datetime.now()

        # 节流：该接口上游有频控（S1009"系统繁忙"），实际查询间隔限 1 小时；
        # 窗口内直接复用缓存（允许过期值），无缓存时返回空结构且不打上游。
        last_attempt = self._notices_last_attempt.get(cache_key)
        if last_attempt and (now - last_attempt).total_seconds() < 3600:
            if cached:
                return cached["data"]
            return {
                "notices": [],
                "error": "停电信息处于 1 小时节流窗口内，跳过本次查询",
                "org_no": match.org_code,
            }

        self._notices_last_attempt[cache_key] = now
        try:
            notices = await _query_notices(query_org_no)
            if not notices and match.city_org_code and match.city_org_code != query_org_no:
                query_org_no = match.city_org_code
                notices = await _query_notices(query_org_no)
            result = {
                "notices": notices,
                "region": match.display_name,
                "area_no": match.district_code,
                "org_no": match.org_code,
                "query_org_no": query_org_no,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            # 成功结果写入缓存（1 小时内直接复用，避开上游频控）
            self._notices_cache[cache_key] = {"ts": datetime.now(), "data": result}
            return result
        except StateGridAuthError:
            raise  # 登录态过期需要上抛触发重登流程
        except Exception as err:  # noqa: BLE001 上游频控（S1009 等）：回退最近一次成功结果
            if cached:
                _LOGGER.info(
                    "[API][mobile_ios] 停电信息查询失败，回退 %d 分钟前缓存: %s",
                    int((datetime.now() - cached["ts"]).total_seconds() / 60),
                    err,
                )
                return cached["data"]
            raise

    async def get_electricity_data(self, cons_no: str | None = None, **_kwargs: Any) -> dict[str, Any]:
        """获取余额 + 日用电量 + 月账单 + 缴费记录，映射为网页版同构结构。"""
        if not self._power_user_list:
            await self.fetch_power_user_list()

        # 确定活跃户号：优先匹配传入户号（consNoSrc 为明文户号）
        active: dict[str, Any] = {}
        if cons_no:
            for acc in self._power_user_list:
                if str(acc.get("consNo_dst") or "") == str(cons_no):
                    active = acc
                    break
        if not active:
            for acc in self._power_user_list:
                if str(acc.get("isDefault")) == "1":
                    active = acc
                    break
        if not active:
            active = self._power_user_list[0]
        # 记录活跃户号：ios_call 自动上送档案（notices 等未显式传 account 的调用）
        self._active_account = active

        now = datetime.now()
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=DAILY_USAGE_WINDOW_DAYS)).strftime("%Y-%m-%d")

        # 户号档案：显式传给后端（payload.account 覆盖默认户），
        # 否则后端用登录时落库的默认户号查询，会查错户。
        account_payload = {
            "consNo": active.get("consNo") or "",
            "consNoSrc": active.get("consNo_dst") or "",
            "proCode": active.get("proNo") or "",
            "orgNo": active.get("orgNo") or "",
            "consType": active.get("consSortCode") or "",
            "userNameLong": active.get("userNameLong") or "",
        }

        # 并发四个业务查询（后端各自组装信封、自动复用登录态）；
        # 单项失败降级为空结构，不影响其余传感器。
        async def _safe_call(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                return await self.ios_call(operation, payload)
            except StateGridAuthError:
                raise  # 登录态过期需要上抛触发重登流程
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("[API][mobile_ios] %s 查询失败: %s", operation, err)
                return {}

        daily_task = _safe_call(
            "dailyUsage",
            {
                "startDate": start_date,
                "endDate": end_date,
                "account": account_payload,
            },
        )
        balance_task = _safe_call("accountBalance", {"account": account_payload})
        bills_task = _safe_call(
            "monthlyBills", {"year": now.year, "account": account_payload}
        )
        # 缴费记录：窗口对齐网页版 _fetch_payment_records —— 3 年前 1 月 1 日 → 今天，全量拉取
        payment_task = _safe_call(
            "paymentRecords",
            {
                "startDate": f"{now.year - 3}-01-01",
                "endDate": end_date,
                "page": 1,
                "number": 10000,
                "account": account_payload,
            },
        )

        # 停电信息（c8/f05 按区域）：与网页版同策略——公告查询失败不影响核心实体，
        # 降级为带 error 的空结构。
        async def _notices_task() -> dict[str, Any]:
            try:
                return await self._fetch_maintenance_notices(active)
            except StateGridAuthError:
                raise  # 登录态过期需要上抛触发重登流程
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("[API][mobile_ios] 停电信息查询失败 (c8/f05): %s", err)
                return {"notices": [], "error": str(err)}

        notice_task = _notices_task()
        daily, balance_data, bills, payments, notices = await _gather_quiet(
            daily_task, balance_task, bills_task, payment_task, notice_task
        )

        # ---- 余额（c16/f01 → list[0]），判定逻辑与网页版 c05/f01 一致 ----
        found: dict[str, Any] = {}
        bal_list = balance_data.get("list") or []
        if bal_list and isinstance(bal_list[0], dict):
            found = bal_list[0]
        prepay_bal = _to_float(found.get("prepayBal"))
        sum_money = _to_float(found.get("sumMoney"))
        cons_type = found.get("consType")
        esti_amt_value = found.get("estiAmt")
        balance: float | None = None
        if cons_type == "0" and not esti_amt_value:
            balance = prepay_bal
        elif sum_money is not None:
            balance = sum_money
        elif prepay_bal is not None:
            balance = prepay_bal
        esti_amt = _to_float(esti_amt_value)

        fee_detail: dict[str, Any] = {}
        for key in (
            "prepayBal", "totalPq", "sumMoney", "estiAmt", "historyOwe",
            "penalty", "amtTime", "date", "consType",
        ):
            if found.get(key) is not None:
                fee_detail[key] = found.get(key)

        # ---- 月账单（c51/f04）→ monthlist / yearlist ----
        month_list: list[dict[str, Any]] = []
        for item in bills.get("list") or []:
            if not isinstance(item, dict):
                continue
            ym = str(item.get("ym") or "")
            if len(ym) == 6:
                month_list.append({
                    "month": f"{ym[:4]}-{ym[4:]}",
                    "eleNum": _to_float(item.get("monthPq")) or 0,
                    "eleCost": _to_float(item.get("monthAmt")) or 0,
                    "is_official": True,
                })
        month_list.sort(key=lambda x: x["month"], reverse=True)

        year_list: list[dict[str, Any]] = []
        year_pq = _to_float(bills.get("yearPq"))
        year_amt = _to_float(bills.get("yearAmt"))
        if year_pq and year_pq > 0:
            year_list.append({
                "year": str(now.year),
                "yearEleNum": year_pq,
                "yearEleCost": year_amt or 0,
                "is_official": True,
            })

        # ---- 缴费记录（c12/f01 → payList，字段过滤与网页版完全一致） ----
        pay_count = 0
        try:
            pay_count = int(payments.get("count") or 0)
        except (TypeError, ValueError):
            pay_count = 0
        pay_list: list[dict[str, Any]] = []
        for item in payments.get("payList") or []:
            if isinstance(item, dict):
                pay_list.append({
                    "payDate": item.get("payDate", ""),
                    "rcvAmt": item.get("rcvAmt", ""),
                    "typeName": item.get("typeName", ""),
                    "chanName": item.get("chanName", ""),
                    "chanCls": item.get("chanCls", ""),
                    "payModeName": item.get("payModeName", ""),
                    "consName": item.get("consName", ""),
                    "consNo": item.get("consNo", ""),
                    "elecAddr": item.get("elecAddr", ""),
                    "remark": item.get("remark", ""),
                })

        daily_usage: dict[str, Any] = {
            "sevenEleList": daily.get("sevenEleList") or [],
            "totalPq": daily.get("totalPq"),
            "monthlist": month_list,
            "yearlist": year_list,
        }

        return {
            "selected_cons_no": active.get("consNo_dst") or "",
            "balance": balance,
            "esti_amt": esti_amt,
            "electricity_fee_detail": fee_detail,
            "selected_owner_name": active.get("consName_dst") or "",
            "selected_elec_addr": active.get("elecAddr_dst") or "",
            "selected_org_name": active.get("orgName") or "",
            "selected_org_no": active.get("orgNo") or "",
            "power_grid_maintenance_notices": notices,
            "daily_usage": daily_usage,
            "payment_records": {"count": pay_count, "payList": pay_list},
        }


async def _gather_quiet(*coros: Any) -> list[Any]:
    """并发等待并聚合结果；单个查询失败时抛首个异常。"""
    import asyncio

    results = await asyncio.gather(*coros)
    return list(results)

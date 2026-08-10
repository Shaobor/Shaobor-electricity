"""Usage and balance handlers for State Grid API."""
import logging
import asyncio
import time
import json
import hashlib
from typing import Any
from datetime import datetime
from urllib.parse import urlencode

from .base import BaseStateGridApi
from .const import ENCRYPT_API_URL, SGCC_HOST, APP_KEY, VERSION
from .exceptions import StateGridAuthError
from .decorators import auto_relogin_on_auth_error, retry_on_network_error
from ..const import DOMAIN

# 移除旧的 Store 导入，全面转向数据库
Store = None 

_LOGGER = logging.getLogger(__name__)

class UsageMixin(BaseStateGridApi):
    def _bearer_header(self) -> str | None:
        if not self._access_token:
            return None
        access = str(self._access_token)
        access_no_prefix = access.replace("WEB.", "")
        trimmed = access_no_prefix[:250]
        if not trimmed:
            return None
        return f"Bearer WEB.{trimmed}"

    def _t_header(self) -> str | None:
        if not self._user_token:
            return None
        token = str(self._user_token)
        half = max(1, len(token) // 2)
        return token[:half]

    @retry_on_network_error(max_retries=3, delay=2.0)
    async def _fetch_power_user_list(self) -> list[dict[str, Any]]:
        """Fetch powerUserList via c8f11."""
        _LOGGER.warning("[c8f11] ===== 开始执行 _fetch_power_user_list =====")
        _LOGGER.warning("[c8f11] 当前状态: key_code=%s, public_key=%s, user_token=%s, access_token=%s",
                       "有值" if self._key_code else "空",
                       "有值" if self._public_key else "空",
                       "有值" if self._user_token else "空",
                       "有值" if self._access_token else "空")
        
        # 每次请求前都重新初始化（获取 keyCode 和 publicKey）
        _LOGGER.warning("[c8f11] 执行初始化操作")
        await self.initialize()
        _LOGGER.warning("[c8f11] 初始化完成: key_code=%s, public_key=%s",
                       "有值" if self._key_code else "空",
                       "有值" if self._public_key else "空")
        
        # c8f11 需要 userId、userToken、accessToken，这些参数不能为空
        if not self._user_token:
            raise StateGridAuthError("Missing user_token for c8f11")
        if not self._access_token:
            raise StateGridAuthError("Missing access_token for c8f11")
        
        # 确保所有参数都是字符串类型，不能是 None（会被序列化为 null）
        # 扫码登录使用 c8/f11 接口，不需要 userId 参数
        for attempt in range(2):
            encrypt_payload = {
                "token": str(self._encrypt_token) if self._encrypt_token else "",
                "machineId": self._machine_id,
                "uuid": str(self._uuid) if self._uuid else "",
                "publicKey": str(self._public_key) if self._public_key else "",
                "userToken": str(self._user_token) if self._user_token else "",
                "accessToken": str(self._access_token) if self._access_token else "",
            }
            
            encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/c8f11", encrypt_payload)
            
            headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
            bearer = self._bearer_header()
            if bearer:
                headers["Authorization"] = bearer
            t = self._t_header()
            if t:
                headers["t"] = t

            payload_sgcc = {
                "data": encrypted.get("data"),
                "skey": encrypted.get("skey"),
                "timestamp": encrypted.get("timestamp"),
            }
            
            async with self._session.post(
                "https://www.95598.cn/api/osg-open-uc0001/member/c8/f11",
                json=payload_sgcc,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
            
            raw = self._parse_sgcc_response(text)
            _LOGGER.debug("[c8f11] 第%d次响应: %s", attempt + 1, raw)
            
            if isinstance(raw, dict):
                code = raw.get("code")
                if code == "GB010" and attempt == 0:
                    _LOGGER.warning("[c8f11] 获取个人中心数据时检测到 GB010，重新初始化会话...")
                    self._key_code = ""
                    await self.initialize(force_new_uuid=True)
                    continue
                
                self._check_and_raise_business_error(raw, "c8/f11")

            encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
            if encrypted_data:
                break
            
            if attempt == 1:
                raise StateGridAuthError(f"获取户号列表失败 (c8f11)。响应: {str(raw)[:200]}")

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
        if not encrypted_data:
            _LOGGER.error("[c8f11] 无法从响应中提取加密数据")
            raise StateGridAuthError("c8/f11 did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        _LOGGER.warning("[c8f11] 解密后的数据类型: %s", type(decrypted).__name__)
        
        if not isinstance(decrypted, dict):
            raise StateGridAuthError(f"c8/f11 decrypt returned unexpected type: {type(decrypted)}")
        
        # 输出解密后的数据结构
        _LOGGER.warning("[c8f11] 解密后的数据keys: %s", list(decrypted.keys()) if isinstance(decrypted, dict) else "非字典")
        
        # 输出完整的解密数据用于调试
        try:
            import json
            _LOGGER.warning("[c8f11] 完整解密数据: %s", json.dumps(decrypted, ensure_ascii=False, indent=2)[:2000])
        except Exception as e:
            _LOGGER.warning("[c8f11] 无法序列化解密数据: %s", e)
        
        # c8/f11 返回的是 data 字段,不是 bizrt
        data_field = decrypted.get("data", {}) if isinstance(decrypted.get("data"), dict) else {}
        _LOGGER.warning("[c8f11] data keys: %s", list(data_field.keys()) if isinstance(data_field, dict) else "非字典")
        
        # 从 data 字段提取 userId
        user_id = data_field.get("userId")
        if user_id:
            self._user_id = str(user_id)
            _LOGGER.warning("[c8f11] 成功从 data 提取到 userId: %s", self._user_id)
        else:
            _LOGGER.warning("[c8f11] 未能从 data 提取到 userId，该账号可能未绑定任何户号")
            return []
        
        # 从 data 字段提取 realName 作为 loginAccount（用于后续 API 调用的 userName 参数）
        # 扫码登录时，c8/f11 返回的 data 中包含 realName，可以作为 loginAccount 使用
        real_name = data_field.get("realName") or data_field.get("realName_dst")
        if real_name:
            self._login_account = str(real_name)
            _LOGGER.warning("[c8f11] 成功从 data 提取到 realName 作为 loginAccount: %s", self._login_account)
        
        # 步骤2: 使用 userId 调用 c9/f02 获取 powerUserList
        _LOGGER.warning("[c9f02] ===== 开始调用 c9/f02 获取户号列表 =====")
        _LOGGER.warning("[c9f02] 使用 userId: %s", self._user_id)
        
        # 构建 c9/f02 的请求 payload
        encrypt_payload_c9f02 = {
            "token": str(self._encrypt_token) if self._encrypt_token else "",
            "machineId": self._machine_id,
            "uuid": str(self._uuid) if self._uuid else "",
            "publicKey": str(self._public_key) if self._public_key else "",
            "userId": str(self._user_id),
            "userToken": str(self._user_token) if self._user_token else "",
            "accessToken": str(self._access_token) if self._access_token else "",
        }
        
        _LOGGER.warning("[c9f02] 请求 URL: %s", f"{ENCRYPT_API_URL}/encrypt/c9f02")
        encrypted_c9f02 = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/c9f02", encrypt_payload_c9f02)
        
        headers_c9f02 = self._get_sgcc_headers(str(encrypted_c9f02.get("timestamp")))
        if bearer:
            headers_c9f02["Authorization"] = bearer
        if t:
            headers_c9f02["t"] = t
        
        payload_sgcc_c9f02 = {
            "data": encrypted_c9f02.get("data"),
            "skey": encrypted_c9f02.get("skey"),
            "timestamp": encrypted_c9f02.get("timestamp"),
        }
        
        _LOGGER.warning("[c9f02] 准备调用 95598 API: https://www.95598.cn/api/osg-open-uc0001/member/c9/f02")
        
        async with self._session.post(
            "https://www.95598.cn/api/osg-open-uc0001/member/c9/f02",
            json=payload_sgcc_c9f02,
            headers=headers_c9f02,
        ) as resp:
            resp.raise_for_status()
            text_c9f02 = await resp.text()
            _LOGGER.warning("[c9f02] 95598 API 响应状态: %s", resp.status)
            _LOGGER.warning("[c9f02] 95598 API 响应内容(前200字符): %s", text_c9f02[:200] if text_c9f02 else "空")
        
        raw_c9f02 = self._parse_sgcc_response(text_c9f02)
        encrypted_data_c9f02 = self._get_encrypted_data(raw_c9f02) or (text_c9f02.strip() if self._is_likely_encrypted(text_c9f02) else "")
        if not encrypted_data_c9f02:
            _LOGGER.error("[c9f02] 无法从响应中提取加密数据")
            raise StateGridAuthError("c9/f02 did not return decryptable payload")
        
        decrypted_c9f02 = await self._decrypt_to_data(encrypted_data_c9f02)
        _LOGGER.warning("[c9f02] 解密后的数据类型: %s", type(decrypted_c9f02).__name__)
        
        if not isinstance(decrypted_c9f02, dict):
            raise StateGridAuthError(f"c9/f02 decrypt returned unexpected type: {type(decrypted_c9f02)}")
        
        # 输出完整的解密数据
        try:
            import json
            _LOGGER.warning("[c9f02] 完整解密数据: %s", json.dumps(decrypted_c9f02, ensure_ascii=False, indent=2)[:2000])
        except Exception as e:
            _LOGGER.warning("[c9f02] 无法序列化解密数据: %s", e)
        
        # c9/f02 应该返回 bizrt 字段
        bizrt = decrypted_c9f02.get("bizrt", {}) if isinstance(decrypted_c9f02.get("bizrt"), dict) else {}
        _LOGGER.warning("[c9f02] bizrt keys: %s", list(bizrt.keys()) if isinstance(bizrt, dict) else "非字典")
        
        power_list = bizrt.get("powerUserList")
        _LOGGER.warning("[c9f02] powerUserList 类型: %s, 长度: %s", type(power_list).__name__, len(power_list) if isinstance(power_list, list) else "N/A")
        if isinstance(power_list, list) and power_list:
            _LOGGER.warning("[c9f02] powerUserList[0] keys: %s", list(power_list[0].keys()) if isinstance(power_list[0], dict) else "非字典")
        
        if not isinstance(power_list, list) or not power_list:
            raise StateGridAuthError("Empty powerUserList from c9/f02")
        _sanitized_pl = self._sanitize_for_log(power_list)
        try:
            _LOGGER.debug("[调试] 户号返回值: %s", json.dumps(_sanitized_pl, ensure_ascii=False, default=str)[:1500])
        except (TypeError, ValueError):
            _LOGGER.debug("[调试] 户号返回值: len=%s", len(power_list))
        return power_list

    async def fetch_power_user_list(self) -> list[dict[str, Any]]:
        """Public wrapper to fetch and cache power user list."""
        self._power_user_list = await self._fetch_power_user_list()
        return self._power_user_list

    @staticmethod
    def _extract_maintenance_notices(payload: Any) -> list[dict[str, Any]]:
        """Extract a notice list while accepting the known 95598 response variants."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []

        for key in (
            "powerCutList", "powercutList", "powerCutInfoList", "noticeList",
            "records", "list", "resultList",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        for key in ("data", "bizrt", "result"):
            notices = UsageMixin._extract_maintenance_notices(payload.get(key))
            if notices:
                return notices
        return []

    async def _fetch_power_grid_maintenance_notices(
        self, active_account: dict[str, Any]
    ) -> dict[str, Any]:
        """Fetch maintenance notices for the active account's mapped district."""
        raw_org_no = str(active_account.get("orgNo") or active_account.get("org_no") or "")
        target = str(active_account.get("proNo") or active_account.get("proCode") or "")
        mapping = None
        if self._hass:
            mapping = self._hass.data.get(DOMAIN, {}).get("division_mapping")
        match = mapping.lookup_org_no(raw_org_no) if mapping and raw_org_no else None

        if not target or not match or not match.district_code:
            return {
                "notices": [],
                "error": "当前账户缺少可匹配的供电地区信息",
                "org_no": raw_org_no,
            }

        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "target": target,
            # 95598 停电公告接口使用地区映射中最长匹配到的供电单位编号。
            "orgNo": match.org_code,
            "powerCutNo": "02",
            "areaNo": match.district_code,
            "pageSize": "20",
            "pageNo": 1,
            "keyWord": "",
        }
        encrypted = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/c4f08", encrypt_payload
        )
        headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        payload_sgcc = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }

        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/member/c4/f08",
            json=payload_sgcc,
            headers=headers,
        ) as response:
            response.raise_for_status()
            text = await response.text()

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (
            text.strip() if self._is_likely_encrypted(text) else ""
        )
        if not encrypted_data:
            raise StateGridAuthError("c4/f08 did not return decryptable payload")
        decrypted = await self._decrypt_to_data(encrypted_data)
        notices = self._extract_maintenance_notices(decrypted)

        return {
            "notices": notices,
            "region": match.display_name,
            "area_no": match.district_code,
            "org_no": match.org_code,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def _fetch_balance_info(self) -> dict[str, float | None]:
        """Fetch account balance and estimated amount via c05/f01."""
        if not self._power_user_list or len(self._power_user_list) == 0:
            raise StateGridAuthError("Missing power user list")
        idx = min(self._selected_account_index, len(self._power_user_list) - 1)
        active = self._power_user_list[idx]
        # Support both snake_case and camelCase from API
        cons_no_src = active.get("consNo_dst") or active.get("consNoDst") or ""
        cons_no = active.get("consNo") or ""
        pro_code = active.get("proNo") or active.get("proCode") or ""
        org_no = active.get("orgNo") or ""
        scene_type = active.get("consSortCode") or active.get("sceneType") or ""

        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "proCode": pro_code,
            "consNoSrc": cons_no_src,
            "consNo": cons_no,
            "orgNo": org_no,
            "sceneType": scene_type,
        }
        if self._user_id: encrypt_payload["userId"] = self._user_id
        if self._user_token: encrypt_payload["userToken"] = self._user_token
        if self._access_token: encrypt_payload["accessToken"] = self._access_token
        if self._login_account: encrypt_payload["userName"] = self._login_account
        encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/c05f01", encrypt_payload)

        headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        bearer = self._bearer_header()
        if bearer:
            headers["Authorization"] = bearer
        t = self._t_header()
        if t:
            headers["t"] = t

        payload_sgcc = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }
        async with self._session.post(
            "https://www.95598.cn/api/osg-open-bc0001/member/c05/f01",
            json=payload_sgcc,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
        if not encrypted_data:
            raise StateGridAuthError("c05/f01 did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        
        # [调试] 输出 c05/f01 解密后的完整返回值
        _LOGGER.warning("[c05/f01 实时电费] ===== 开始输出解密数据 =====")
        _LOGGER.warning("[c05/f01 实时电费] 解密数据类型: %s", type(decrypted).__name__)
        if isinstance(decrypted, str):
            _LOGGER.warning("[c05/f01 实时电费] 解密数据长度: %d", len(decrypted))
            _LOGGER.warning("[c05/f01 实时电费] 解密数据内容: %s", decrypted[:500] if len(decrypted) > 500 else decrypted)
        else:
            _sanitized_c05 = self._sanitize_for_log(decrypted)
            try:
                json_str = json.dumps(_sanitized_c05, ensure_ascii=False, indent=2, default=str)
                _LOGGER.warning("[c05/f01 实时电费] 解密数据内容:\n%s", json_str)
            except (TypeError, ValueError) as e:
                _LOGGER.warning("[c05/f01 实时电费] 解密后的数据无法序列化: %s", e)
        _LOGGER.warning("[c05/f01 实时电费] ===== 结束输出解密数据 =====")
        
        # 优先从 list 数组中获取数据（新版API返回格式）
        found = None
        if isinstance(decrypted, dict):
            data_list = decrypted.get("list", [])
            if isinstance(data_list, list) and len(data_list) > 0:
                found = data_list[0]
                _LOGGER.info("[c05/f01] 从 list 数组中获取到数据")
            else:
                # 兼容旧版API：直接在根对象中查找
                found = self._find_first_dict_with_keys(decrypted, {"sumMoney"})
                if found:
                    _LOGGER.info("[c05/f01] 从根对象中获取到数据（旧版API）")
        
        balance = None
        esti_amt = None
        fee_detail = {}
        
        if found:
            # 根据账户类型判断使用哪个余额字段
            prepay_bal = self._to_float(found.get("prepayBal"))
            sum_money = self._to_float(found.get("sumMoney"))
            cons_type = found.get("consType")
            esti_amt_value = found.get("estiAmt")
            
            # 判断逻辑：
            # 1. 如果 consType == "0" 且没有 estiAmt，使用 prepayBal（纯预付费）
            # 2. 如果 consType == "1" 或有 estiAmt，使用 sumMoney（后付费或混合）
            # 3. 其他情况：优先 sumMoney，没有则用 prepayBal
            if cons_type == "0" and not esti_amt_value:
                # 纯预付费账户
                balance = prepay_bal
                _LOGGER.info("[c05/f01] 纯预付费账户，使用预付费余额: %s", balance)
            elif sum_money is not None:
                # 后付费或混合账户，使用应缴金额
                balance = sum_money
                _LOGGER.info("[c05/f01] 后付费/混合账户，使用应缴金额: %s", balance)
            elif prepay_bal is not None:
                # 兜底：使用预付费余额
                balance = prepay_bal
                _LOGGER.info("[c05/f01] 使用预付费余额: %s", balance)
            
            esti_amt = self._to_float(esti_amt_value)
            
            # 提取完整的电费详情数据（只添加有值的字段）
            fee_detail = {}
            
            if found.get("prepayBal") is not None:
                fee_detail["prepayBal"] = found.get("prepayBal")
            if found.get("totalPq") is not None:
                fee_detail["totalPq"] = found.get("totalPq")
            if found.get("sumMoney") is not None:
                fee_detail["sumMoney"] = found.get("sumMoney")
            if found.get("estiAmt") is not None:
                fee_detail["estiAmt"] = found.get("estiAmt")
            if found.get("historyOwe") is not None:
                fee_detail["historyOwe"] = found.get("historyOwe")
            if found.get("penalty") is not None:
                fee_detail["penalty"] = found.get("penalty")
            if found.get("amtTime"):
                fee_detail["amtTime"] = found.get("amtTime")
            if found.get("date"):
                fee_detail["date"] = found.get("date")
            if found.get("consType") is not None:
                fee_detail["consType"] = found.get("consType")
            
            _LOGGER.info("[c05/f01] 解析结果 - balance: %s, esti_amt: %s", balance, esti_amt)
        else:
            _LOGGER.warning("[c05/f01] 未找到有效的电费数据")
        
        return {
            "balance": balance, 
            "esti_amt": esti_amt,
            "electricity_fee_detail": fee_detail
        }

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def _fetch_payment_records(self) -> dict[str, Any]:
        """Fetch payment records via c24/f01 (缴费记录) from current year to today."""
        if not self._power_user_list or len(self._power_user_list) == 0:
            raise StateGridAuthError("Missing power user list")
        idx = min(self._selected_account_index, len(self._power_user_list) - 1)
        active = self._power_user_list[idx]
        
        # 使用 consNo_dst（解密后的实际户号）而不是 consNo（加密值）
        cons_no = active.get("consNo_dst") or active.get("consNoDst") or active.get("consNo") or ""
        pro_code = active.get("proNo") or active.get("proCode") or ""
        org_no = active.get("orgNo") or ""
        
        # 日期范围：3年前的1月1日 到今天
        now = datetime.now()
        three_years_ago = now.year - 3
        bgn_pay_date = f"{three_years_ago}-01-01"
        end_pay_date = now.strftime("%Y-%m-%d")
        
        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "consNo": cons_no,
            "proCode": pro_code,
            "orgNo": org_no,
            "bgnPayDate": bgn_pay_date,  # 注意：参数名是 bgnPayDate，不是 startDate
            "endPayDate": end_pay_date,  # 注意：参数名是 endPayDate，不是 endDate
            "page": 1,
            "number": 10000,
        }
        if self._user_id: encrypt_payload["userId"] = self._user_id
        if self._user_token: encrypt_payload["userToken"] = self._user_token
        if self._access_token: encrypt_payload["accessToken"] = self._access_token
        if self._login_account: encrypt_payload["userName"] = self._login_account
        
        # 注意：使用 c24f01-payment 端点，不是 c24f01
        encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/c24f01-payment", encrypt_payload)

        headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        bearer = self._bearer_header()
        if bearer:
            headers["Authorization"] = bearer
        t = self._t_header()
        if t:
            headers["t"] = t

        payload_sgcc = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }
        # 注意：使用 osg-web0004，不是 osg-open-bc0001
        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/member/c24/f01",
            json=payload_sgcc,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
        if not encrypted_data:
            raise StateGridAuthError("c24f01-payment did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        
        count = 0
        pay_list = []
        if isinstance(decrypted, dict):
            count = int(decrypted.get("count") or 0)
            pay_list_raw = decrypted.get("payList") or []
            if isinstance(pay_list_raw, list):
                for item in pay_list_raw:
                    if isinstance(item, dict):
                        filtered = {
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
                        }
                        pay_list.append(filtered)
        
        return {"count": count, "payList": pay_list}

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def _fetch_yearly_usage(self, year: int | None = None) -> dict[str, Any]:
        """获取年度用电量 (020070054)，包含官方年度/月度结算数据。返回的 consList 包含该登录账号下所有户号的数据，调用方需自行匹配。"""
        if year is None:
            year = datetime.now().year

        _LOGGER.info("[020070054-yearly] 正在获取 %d 年官方结算数据", year)

        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "year": str(year),
        }
        if self._user_id: encrypt_payload["userId"] = self._user_id
        if self._user_token: encrypt_payload["userToken"] = self._user_token
        if self._access_token: encrypt_payload["accessToken"] = self._access_token
        if self._login_account: encrypt_payload["userName"] = self._login_account
        
        encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/020070054", encrypt_payload)
        headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        bearer = self._bearer_header()
        if bearer: headers["Authorization"] = bearer
        t = self._t_header()
        if t: headers["t"] = t

        payload_sgcc = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }
        
        async with self._session.post(
            "https://www.95598.cn/api/osg-open-bc0001/member/arg/020070054",
            json=payload_sgcc,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
        if not encrypted_data:
            raise StateGridAuthError("020070054-yearly did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        # 逻辑已迁移：现在由 Coordinator 统一从返回结果中提取并存入 SQLite 数据库
        return decrypted

    async def _save_yearly_usage_to_file(self, data: dict[str, Any], year: int) -> None:
        """年度总计数据现在直接存入数据库，不再写入 Store 文件"""
        if not self._db or not data: return
        try:
            data_info = data.get("dataInfo") or data.get("data", {}).get("dataInfo") or {}
            total_ele = data_info.get("totalEleNum")
            if not total_ele or float(total_ele) <= 0: return

            # 如果持有数据库对象，直接保存
            idx = min(self._selected_account_index, len(self._power_user_list) - 1) if self._power_user_list else 0
            active = self._power_user_list[idx] if self._power_user_list and idx >= 0 else {}
            cons_no = active.get("consNo_dst") or active.get("consNoDst") or active.get("consNo") or ""
            
            if cons_no and self._db:
                await self._db.async_save_yearly_usage(cons_no, [{
                    "year": str(year),
                    "yearEleNum": total_ele,
                    "yearEleCost": data_info.get("totalEleCost"),
                    "is_official": True
                }])
                _LOGGER.info(f"[数据库] 已通过 API 成功同步并保存 {year} 年官方年度总计")
        except Exception as e:
            _LOGGER.error(f"[数据库] 保存 {year} 年年度总计到数据库失败: {e}")

    async def _async_sync_historical_years(self, cons_no: str) -> None:
        """动态溯源：根据数据库最小记录年份开始探测官方账单"""
        now = datetime.now()
        current_year = now.year
        current_month_str = now.strftime("%Y-%m")
        
        try:
            # 1. 确定探测范围：从数据库日流水的最小年份开始
            min_year = current_year # 默认今年
            
            if self._db and cons_no:
                try:
                    # 从数据库查询该户号的所有日电量记录
                    db_history = await self._db.async_get_all_daily_usage(cons_no)
                    if db_history:
                        years = []
                        for row in db_history:
                            day_str = row.get("day")
                            if day_str and len(day_str) >= 4:
                                try:
                                    years.append(int(day_str[:4]))
                                except: continue
                        if years:
                            min_year = min(years)
                            _LOGGER.info(f"[历史溯源] 数据库查询到该户号最早记录年份: {min_year}")
                except Exception as e:
                    _LOGGER.warning(f"[历史溯源] 查询数据库最小年份失败: {e}")
            
            # 如果没查到，默认往前推2年
            if min_year == current_year:
                min_year = current_year - 2
            
            _LOGGER.info(f"[历史溯源] 最终确定探测区间: {min_year} -> {current_year}")
            
            # 2. 逐年探测
            for check_year in range(min_year, current_year + 1):
                _LOGGER.info(f"[历史溯源] 正在探测 {check_year} 年官方账单...")
                try:
                    decrypted = await self._fetch_yearly_usage(check_year)
                    total_num = 0.0
                    total_cost = 0.0
                    official_months = []
                    
                    cons_list = decrypted.get("consList") or []
                    if cons_list and len(cons_list) > 0:
                        matched = None
                        for c in cons_list:
                            # consNoDst 是真实户号，consNo 是 UUID 标识
                            c_no = c.get("consNoDst") or c.get("consNo_dst") or c.get("consNo") or ""
                            c_no_plain = str(c_no).split("-")[0].strip()
                            if c_no_plain == cons_no:
                                matched = c
                                break
                        if not matched:
                            _LOGGER.warning(
                                "[历史溯源] consList 中未找到户号 %s，跳过 %s 年官方账单同步",
                                cons_no, check_year,
                            )
                            continue
                        bill_list = matched.get("billList") or []
                        for bill in bill_list:
                            ym_str = bill.get("ym") # "202512"
                            m_list = bill.get("monthList") or []
                            
                            # 定义一个宽泛的“探测”函数，尝试从字典中抓取可能的数值
                            def _probe(d, keys):
                                for k in keys:
                                    v = d.get(k)
                                    if v is not None and v != "" and v != "-":
                                        try:
                                            return float(v)
                                        except (ValueError, TypeError): continue
                                return 0.0

                            # 探测键位列表
                            pq_keys = ["pq", "monthEleNum", "eleNum", "totalEleNum", "thisEleNum", "thisPq", "thisElePq", "pq_1"]
                            amt_keys = ["amt", "monthEleCost", "eleCost", "totalEleAmt", "totalEleCost", "thisEleAmt", "amt_1"]

                            for m_item in m_list:
                                try:
                                    # 优先从月度明细中探测
                                    m_pq = _probe(m_item, pq_keys)
                                    m_amt = _probe(m_item, amt_keys)
                                    
                                    # 如果明细里没拿到，尝试从账单层级抓取（兜底逻辑）
                                    if m_pq == 0: m_pq = _probe(bill, pq_keys)
                                    if m_amt == 0: m_amt = _probe(bill, amt_keys)

                                    total_num += m_pq
                                    total_cost += m_amt
                                    
                                    if ym_str and len(ym_str) == 6:
                                        formatted_month = f"{ym_str[:4]}-{ym_str[4:]}"
                                        # 【月表规则】：只存当前月份以前的（或当前月，取决于业务需求，通常存历史）
                                        if formatted_month <= current_month_str:
                                            official_months.append({
                                                "month": formatted_month,
                                                "ele_num": m_pq,
                                                "ele_cost": m_amt,
                                                "is_official": True
                                            })
                                except Exception: continue
                    
                    # 【核心变更】：所有历史溯源结果直接存入 SQLite 数据库
                    if check_year < current_year and total_num > 0:
                        _LOGGER.info(f"[历史溯源] {check_year} 年(正式)账单同步成功: {total_num} kWh")
                        if self._db:
                            await self._db.async_save_yearly_usage(cons_no, [{
                                "year": str(check_year),
                                "yearEleNum": total_num,
                                "yearEleCost": total_cost,
                                "is_official": True
                            }])
                    
                    if official_months and self._db:
                        await self._db.async_save_monthly_usage(cons_no, official_months)
                        _LOGGER.info(f"[历史溯源] {check_year} 年已同步 {len(official_months)} 个历史月度正式账单到数据库")
                        
                    await asyncio.sleep(1) 
                except Exception as e:
                    _LOGGER.error(f"[历史溯源] 探测 {check_year} 年出错: {e}")
        except Exception as e:
            _LOGGER.error(f"[历史溯源] 任务异常终止: {e}")

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def _fetch_daily_usage(self) -> dict[str, Any]:
        """获取每日用电量 (c24/f01-daily)，使用增量更新策略"""
        if not self._power_user_list or len(self._power_user_list) == 0:
            raise StateGridAuthError("Missing power user list")
        idx = min(self._selected_account_index, len(self._power_user_list) - 1)
        active = self._power_user_list[idx]
        
        cons_no = active.get("consNo_dst") or active.get("consNoDst") or ""
        pro_code = active.get("proNo") or active.get("proCode") or ""
        org_no = active.get("orgNo") or ""
        
        # 增量更新策略：
        # - 首次运行：从3年前的1月1日开始获取（获取近3年历史数据，但只保存有数据的记录）
        # - 后续运行：只从上个月1日开始获取
        now = datetime.now()
        
        # 从存储中读取上次获取的标记
        store_key = f"daily_usage_fetched_{cons_no}"
        stored_data = await self._store.async_load() if self._store else None
        is_first_fetch = True
        
        if stored_data and isinstance(stored_data, dict):
            is_first_fetch = not stored_data.get(store_key, False)
        
        if is_first_fetch:
            # 首次获取：从3年前的1月1日开始
            three_years_ago = now.year - 3
            start_time = f"{three_years_ago}-01-01"
            _LOGGER.info("[c24/f01-daily] 首次获取数据，从%s开始（只保存有数据的记录）", start_time)
        else:
            # 后续获取：从上个月1日开始
            if now.month == 1:
                # 如果是1月，上个月是去年12月
                last_month_year = now.year - 1
                last_month = 12
            else:
                last_month_year = now.year
                last_month = now.month - 1
            start_time = f"{last_month_year}-{last_month:02d}-01"
            _LOGGER.info("[c24/f01-daily] 增量获取数据，从%s开始", start_time)
        
        end_time = now.strftime("%Y-%m-%d")
        
        _LOGGER.info("[c24/f01-daily] 请求参数 - startTime: %s, endTime: %s, consNo: %s", start_time, end_time, cons_no)
        
        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "consNo": cons_no,
            "proCode": pro_code,
            "orgNo": org_no,
            "startTime": start_time,
            "endTime": end_time,
        }
        if self._user_id: encrypt_payload["userId"] = self._user_id
        if self._user_token: encrypt_payload["userToken"] = self._user_token
        if self._access_token: encrypt_payload["accessToken"] = self._access_token
        if self._login_account: encrypt_payload["userName"] = self._login_account
        
        encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/c24f01-daily", encrypt_payload)

        headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        bearer = self._bearer_header()
        if bearer:
            headers["Authorization"] = bearer
        t = self._t_header()
        if t:
            headers["t"] = t

        payload_sgcc = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }
        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/member/c24/f01",
            json=payload_sgcc,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()

        raw = self._parse_sgcc_response(text)
        encrypted_data = self._get_encrypted_data(raw) or (text.strip() if self._is_likely_encrypted(text) else "")
        if not encrypted_data:
            raise StateGridAuthError("c24/f01-daily did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        
        # 只输出数据类型和记录数量，不输出完整内容（数据量太大）
        _LOGGER.info("[c24/f01-daily 每日电量] 解密数据类型: %s", type(decrypted).__name__)
        if isinstance(decrypted, dict):
            seven_ele_list = decrypted.get("sevenEleList", [])
            total_pq = decrypted.get("totalPq", "未知")
            _LOGGER.info("[c24/f01-daily 每日电量] 获取到 %d 条记录，总电量: %s kWh", len(seven_ele_list), total_pq)
        elif isinstance(decrypted, str):
            _LOGGER.info("[c24/f01-daily 每日电量] 解密数据长度: %d", len(decrypted))
        
        # 保存数据到文件（只保存有数据的记录）
        await self._save_daily_usage_to_file(decrypted)
        
        # 标记已完成首次获取 (注释掉，交由 Coordinator 统一管理)
        # if is_first_fetch and self._store:
        #     if stored_data is None:
        #         stored_data = {}
        #     stored_data[store_key] = True
        #     await self._store.async_save(stored_data)
        #     _LOGGER.info("[c24/f01-daily] 已标记首次获取完成")
        
        return decrypted

    async def _save_daily_usage_to_file(self, data: dict[str, Any]) -> None:
        """不再向旧的 shaobor_data 文件写入，逻辑已迁移至 coordinator 分流存储"""
        pass


    @retry_on_network_error(max_retries=3, delay=2.0)
    async def get_electricity_data(self, **kwargs) -> dict[str, Any]:
        """获取所有电力数据：余额、详情、日流水以及异步同步往年历史"""
        if not self._key_code:
            await self.initialize()
        if not self._user_token or not self._access_token:
            raise StateGridAuthError("Missing login state. Reconfigure integration.")

        if not self._power_user_list or not self._login_account:
            self._power_user_list = await self._fetch_power_user_list()

        # 0. 精准确定当前活跃账户：如果外部传了 target_cons_no，则优先匹配
        target_cons_no = kwargs.get("cons_no")
        active = {}
        if target_cons_no:
            for acc in self._power_user_list:
                c_dst = acc.get("consNo_dst") or acc.get("consNoDst") or acc.get("consNo") or ""
                if c_dst == target_cons_no:
                    active = acc
                    break
        
        # 如果没找到匹配或没传，则回退到当前选择的索引
        if not active:
            idx = min(self._selected_account_index, len(self._power_user_list) - 1) if self._power_user_list else 0
            active = self._power_user_list[idx] if self._power_user_list and idx >= 0 else {}
            
        cons_no = active.get("consNo_dst") or active.get("consNoDst") or ""

        # 1. 获取基础数据 (余额等)
        balance_info = await self._fetch_balance_info()
        daily_usage = {}
        try:
            daily_usage = await self._fetch_daily_usage()
        except Exception as e:
            _LOGGER.debug("无法获取每日用电量: %s", e)

        maintenance_notices: dict[str, Any] = {"notices": []}
        try:
            maintenance_notices = await self._fetch_power_grid_maintenance_notices(active)
        except Exception as e:
            # 公告查询失败不应影响电费、余额等核心实体刷新。
            _LOGGER.debug("无法获取电网检修公告: %s", e)
            maintenance_notices = {"notices": [], "error": str(e)}

        # 2. 异步同步往年历史
        if self._hass and cons_no:
            self._hass.async_create_task(self._async_sync_historical_years(cons_no))

        # 3. 统计日流水历史 (供后续计算使用)
        all_daily_data = {}
        try:
            # 【核心变更】：直接从数据库中加载历史记录，不再读取冗余的 JSON 文件
            if self._db and cons_no:
                db_history = await self._db.async_get_all_daily_usage(cons_no)
                for item in db_history:
                    day_key = item.get("day")
                    if day_key:
                        all_daily_data[day_key] = item
            
            # 如果数据库是空的（首次运行），尝试做一次冷启动备份读取（可选，这里为了纯粹直接放弃读取旧文件）
            if not all_daily_data:
                _LOGGER.info("[数据中心] 数据库历史为空，尝试初始化...")
            
            # 合并本次最新抓取
            if isinstance(daily_usage, dict) and daily_usage.get("sevenEleList"):
                for item in daily_usage["sevenEleList"]:
                    if isinstance(item, dict) and item.get("day"):
                        all_daily_data[item["day"]] = item
        except Exception as e:
            _LOGGER.error(f"整合全量日数据失败: {e}")

        # 4. 获取缴费记录
        payment_records = {"count": 0, "payList": []}
        try:
            payment_records = await self._fetch_payment_records()
        except Exception: pass

        # 5. 计算日均和预计天数
        balance = balance_info.get("balance")
        esti_amt = balance_info.get("esti_amt")
        daily_avg = None
        remaining_days = None
        
        recent_samples = []
        if all_daily_data:
            sorted_dates = sorted(all_daily_data.keys(), reverse=True)
            for d_key in sorted_dates:
                item = all_daily_data[d_key]
                val = item.get("dayElePq") or item.get("pq") or item.get("dayEleNum")
                try:
                    if val and val != "-" and float(val) > 0:
                        recent_samples.append(float(val))
                        if len(recent_samples) >= 7: break
                except (ValueError, TypeError): continue
        
        if recent_samples:
            avg_kwh = sum(recent_samples) / len(recent_samples)
            price = self._billing_config.get("ladder_price_1", 0.51) or 0.51
            daily_avg = avg_kwh * price
            if balance is not None and daily_avg > 0:
                try:
                    remaining_days = int(float(balance) // daily_avg)
                except Exception: pass

        # 6. 【核心变更】：从数据库加载官方汇总，不再读取 Store 文件
        official_yearly = {}
        official_monthly = {}
        if self._db and cons_no:
            db_yearly = await self._db.async_get_all_yearly_usage(cons_no)
            db_monthly = await self._db.async_get_all_monthly_usage(cons_no)
            
            for y in db_yearly:
                if y.get("is_official"):
                    official_yearly[f"YEAR_{y['year']}"] = {
                        "dataInfo": {"totalEleNum": y["yearEleNum"], "totalEleAmt": y["yearEleCost"]}
                    }
            for m in db_monthly:
                if m.get("is_official"):
                    official_monthly[m["month"]] = {
                        "month": m["month"], "ele_num": m["monthEleNum"], "ele_cost": m["monthEleCost"]
                    }
            _LOGGER.info(f"[数据中心] 从数据库成功加载 {len(official_yearly)} 年和 {len(official_monthly)} 个月的官方结算")

        # 7. 账号元数据
        idx = min(self._selected_account_index, len(self._power_user_list) - 1) if self._power_user_list else 0
        active = self._power_user_list[idx] if self._power_user_list and idx >= 0 else {}
        
        if isinstance(daily_usage, dict):
            daily_usage["all_daily_data"] = all_daily_data
            
            # 将官方年度数据转换为 coordinator 识别的 yearlist 格式
            year_list = []
            for y_key, y_data in official_yearly.items():
                d_info = y_data.get("dataInfo") or y_data.get("data", {}).get("dataInfo") or {}
                if d_info:
                    num = d_info.get("totalEleNum")
                    if num is not None and float(num) > 0:
                        year_list.append({
                            "year": str(y_key).replace("YEAR_", ""),
                            "yearEleNum": float(num),
                            "yearEleCost": float(d_info.get("totalEleAmt") or 0),
                            "is_official": True
                        })
            # 按年份倒序排列
            year_list.sort(key=lambda x: x["year"], reverse=True)
            daily_usage["yearlist"] = year_list
            
            # 将官方月度数据转换为 coordinator 识别的 monthlist 格式
            month_list = []
            for m_data in official_monthly.values():
                if isinstance(m_data, dict):
                    month_list.append({
                        "month": m_data.get("month"),
                        "eleNum": m_data.get("ele_num"),
                        "eleCost": m_data.get("ele_cost"),
                        "is_official": True
                    })
            # 按月份倒序排列
            month_list.sort(key=lambda x: x["month"], reverse=True)
            daily_usage["monthlist"] = month_list
            
            daily_usage["official_yearly"] = official_yearly

        return {
            "selected_cons_no": active.get("consNo_dst") or active.get("consNoDst") or "",
            "balance": balance,
            "daily_avg": daily_avg,
            "remaining_days": remaining_days,
            "esti_amt": esti_amt,
            "electricity_fee_detail": balance_info.get("electricity_fee_detail", {}),
            "selected_owner_name": active.get("consName_dst") or active.get("consNameDst") or active.get("consName") or "",
            "selected_elec_addr": active.get("elecAddr") or active.get("elec_addr") or "",
            "selected_org_name": active.get("orgName") or active.get("org_name") or "",
            "selected_org_no": active.get("orgNo") or active.get("org_no") or "",
            "power_grid_maintenance_notices": maintenance_notices,
            "daily_usage": daily_usage,
            "payment_records": payment_records,
        }

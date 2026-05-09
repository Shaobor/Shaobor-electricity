"""Base API client handling encryption and communication."""
import asyncio
import logging
import uuid
from typing import Any
import aiohttp  # type: ignore[import-untyped]
import hashlib
import json
import re

from .const import ENCRYPT_API_URL, DEFAULT_USER_AGENT, APP_KEY, VERSION
from .exceptions import StateGridAuthError, StateGridTokenExpiredError, StateGridConnectionError

_LOGGER = logging.getLogger(__name__)

class BaseStateGridApi:
    """Base class for State Grid API communication."""

    def __init__(
        self,
        token: str,
        session: aiohttp.ClientSession,
        machine_id: str | None = None,
    ) -> None:
        self._encrypt_token = token
        self._session = session
        self._machine_id = machine_id
        self._uuid = str(uuid.uuid4()).replace("-", "")
        self._key_code: str = ""
        self._public_key: str = ""
        self._db = None  # 持有数据库对象引用
        self._headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Content-Type": "application/json",
        }

    def set_db(self, db) -> None:
        """设置数据库对象，用于精准查询历史记录"""
        self._db = db

    async def initialize(self, force_new_uuid: bool = False) -> None:
        """Initialize the encryption session and fetch public keys."""
        if force_new_uuid:
            self._uuid = str(uuid.uuid4()).replace("-", "")
            
        url = f"{ENCRYPT_API_URL}/initialize"
        payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
        }
        try:
            async with self._session.post(url, json=payload, headers=self._headers) as response:
                response.raise_for_status()
                data = await response.json()
                
            success_flag = data.get("success")
            inner_data = data.get("data", {})
                
            if not success_flag or inner_data.get("code") not in (1, "1", 0, "0", "00"):
                msg = inner_data.get("message", "Unknown error")
                raise StateGridAuthError(f"Init failed: {msg}")
                
            result = inner_data.get("data") or {}
            self._key_code = result.get("keyCode") or ""
            self._public_key = result.get("publicKey") or ""
            
            # 重要：同步 _uuid 和 _key_code，确保加密密钥一致
            if self._key_code:
                self._uuid = self._key_code
                
            _LOGGER.info("[API] 初始化成功: keyCode=%s", self._key_code[:8] + "...")
        except aiohttp.ClientError as err:
            raise StateGridConnectionError(f"Communication error during init: {err}")

    async def _secure_post_encrypt(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send encrypted POST request to bridge server."""
        headers = {"Authorization": f"Bearer {self._encrypt_token}"}
        try:
            async with self._session.post(url, json=payload, headers=headers) as response:
                if response.status == 401:
                    raise StateGridAuthError("Encryption server: Unauthorized (check token)")
                response.raise_for_status()
                res = await response.json()
                
                if not res.get("success"):
                    raise StateGridAuthError(f"Helper API error: {res.get('message')}")
                
                inner = res.get("data", {})
                if not isinstance(inner, dict):
                    return {"data": inner}
                
                for key in ["skey", "client_id", "timestamp"]:
                    if key in res and key not in inner:
                        inner[key] = res[key]
                return inner
        except aiohttp.ClientError as err:
            raise StateGridConnectionError(f"Encryption server error: {err}")

    async def _decrypt_to_data(self, encrypt_data: str, *, uuid_override: str | None = None) -> Any:
        """Decrypt helper response."""
        url = f"{ENCRYPT_API_URL}/decrypt"
        payload = {
            "token": self._encrypt_token,
            "uuid": uuid_override or self._uuid,
            "machineId": self._machine_id,
            "encryptData": encrypt_data,
        }
        # _secure_post_encrypt already unwraps the top-level {"success": true, "data": {...}}
        # So `inner` here is the actual decrypted payload wrapper (which usually has code, message, data, or srvrt/bizrt)
        inner = await self._secure_post_encrypt(url, payload)
        
        if not isinstance(inner, dict):
            raise StateGridAuthError(f"Decrypt returned unexpected type: {type(inner).__name__}")
            
        decrypt_code = inner.get("code")
        if decrypt_code is not None and decrypt_code not in [1, "1", "00", 0, "0"]:
            err_msg = inner.get("message") or inner.get("msg") or f"code={decrypt_code}"
            raise StateGridAuthError(f"业务异常: {err_msg}")

        result = inner.get("data")
        
        # If there is no 'data' key, but 'bizrt' or 'srvrt' exist at this level, then 'inner' itself is the result
        if result is None and (inner.get("bizrt") or inner.get("srvrt")):
            result = inner
            
        if result is None:
            # Fallback for payloads like `{"redirect_url": "..."}` where it's inside `data` but wait...
            # If inner was `{"redirect_url": "..."}` directly (no 'data' key), we should return inner
            # But normally `authorize` returns `{"code": 1, "data": {"redirect_url": "..."}}` so result is `{"redirect_url": "..."}`
            return inner
            
        return result

    async def validate_token(self) -> bool:
        """Validate if the provided auth token is valid by attempting initialization."""
        _LOGGER.info("[API] 正在验证授权密钥...")
        try:
            await self.initialize()
            _LOGGER.info("[API] 授权密钥验证通过")
            return True
        except Exception as e:
            _LOGGER.error("[API] 授权密钥验证失败: %s", str(e))
            return False

    def _find_first_dict_with_keys(self, data: Any, keys: set[str]) -> dict[str, Any] | None:
        """Deep search for a dictionary containing all the specified keys."""
        if isinstance(data, dict):
            if all(k in data for k in keys):
                return data
            for v in data.values():
                res = self._find_first_dict_with_keys(v, keys)
                if res:
                    return res
        elif isinstance(data, list):
            for i in data:
                res = self._find_first_dict_with_keys(i, keys)
                if res:
                    return res
        return None

    def _generate_temp_token(self) -> str:
        """生成前端随机 Token (98或99开头 + 10位随机数字)."""
        import random
        prefix = random.choice(["98", "99"])
        return prefix + "".join([str(random.randint(0, 9)) for _ in range(10)])

    def _get_sgcc_headers(self, timestamp: str, token: str | None = None, include_device_token: bool = False) -> dict[str, str]:
        """Generate common headers for SGCC requests."""
        headers = {
            "Host": "www.95598.cn",
            "keyCode": self._key_code,
            "timestamp": timestamp,
            "wsgwType": "web",
            "source": "0901",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json;charset=UTF-8",
            "appKey": APP_KEY,
            "version": VERSION,
            "Content-Type": "application/json; charset=UTF-8",
        }
        if token:
            headers["token"] = token
            
        if include_device_token:
            # Simple device token mock based on timestamp
            headers["deviceToken"] = hashlib.md5(f"device_{timestamp}".encode()).hexdigest()
        return headers

    def _parse_sgcc_response(self, text: str) -> Any:
        """Parse raw response from SGCC (often contains a prefix or is direct JSON)."""
        if not text:
            return {}
        text = text.strip()
        
        # More lenient JSON detection
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Handle SGCC legacy prefix "json="
        if text.startswith("json="):
            try:
                return json.loads(text[5:])
            except json.JSONDecodeError:
                pass
                
        return text

    def _get_encrypted_data(self, data: Any) -> str | None:
        """Extract encrypted string from various SGCC response structures."""
        if isinstance(data, str):
            return data if self._is_likely_encrypted(data) else None
        if isinstance(data, dict):
            # Try common keys
            for key in ["encryptData", "data", "result", "value"]:
                val = data.get(key)
                if isinstance(val, str):
                    return val
            
            # Nested 'encryptData' inside 'data'
            inner_data = data.get("data")
            if isinstance(inner_data, dict):
                val = inner_data.get("encryptData")
                if isinstance(val, str):
                    return val
        return None

    def _is_likely_encrypted(self, text: str) -> bool:
        """Simple check if a string looks like base64 encrypted data."""
        if not text or len(text) < 20:
            return False
        return bool(re.match(r'^[A-Za-z0-9+/=]+$', text))

    def _sanitize_for_log(self, data: Any) -> Any:
        """Hide sensitive info for logging."""
        if not isinstance(data, dict):
            return data
        output = data.copy()
        sensitive_keys = ["password", "token", "access_token", "refresh_token", "skey", "rsi"]
        for k in output:
            if k in sensitive_keys and isinstance(output[k], str):
                output[k] = output[k][:6] + "***" + output[k][-4:] if len(output[k]) > 10 else "***"
        return output

    def _check_and_raise_business_error(self, response: dict, context: str = "") -> None:
        """检查响应中是否存在业务错误并抛出异常."""
        if not isinstance(response, dict):
            return
            
        code = response.get("code")
        # 如果 code 存在且不是成功码（1, 0, 00, "1", "0", "00"），则报错
        # 注意：None（由 .get 返回）不应触发报错
        if code is not None and str(code) not in ("1", "0", "00", "None"):
            msg = response.get("message") or response.get("msg") or f"code={code}"
            prefix = f"{context} " if context else ""
            raise StateGridAuthError(f"{prefix}业务异常: {msg}")

    def _to_float(self, val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

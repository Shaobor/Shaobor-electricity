"""API Client for shaobor_electricity."""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp  # type: ignore[import-untyped]

_LOGGER = logging.getLogger(__name__)

# Constants based on flows.json
ENCRYPT_API_URL = "https://encrypt.hrbzlyy.com/api"
SLIDER_API_URL = "https://cv2.hrbzlyy.com"
SGCC_HOST = "https://www.95598.cn"
APP_KEY = "7e5b5e84ddad4994b0ebc68dedca4962"
VERSION = "1.0"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

class StateGridAuthError(Exception):
    """Exception raised for State Grid Auth errors."""
    pass


class StateGridTokenExpiredError(StateGridAuthError):
    """Exception raised when token has expired and needs refresh."""
    pass

STORAGE_KEY = "shaobor_electricity/shaobor_electricity_auth"
STORAGE_VERSION = 2  # v2: full session (bizrt.token + userInfo + access_token etc.)


def retry_on_network_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry async functions on network errors."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        _LOGGER.warning(
                            "[重试] %s 网络错误 (第%d/%d次): %s (类型: %s). %s秒后重试...",
                            func.__name__, attempt + 1, max_retries, str(e), type(e).__name__, delay
                        )
                        await asyncio.sleep(delay)
                    else:
                        _LOGGER.error(
                            "[重试失败] %s 在%d次尝试后仍失败: %s (类型: %s)",
                            func.__name__, max_retries, str(e), type(e).__name__
                        )
                except (StateGridAuthError, StateGridTokenExpiredError):
                    # 认证错误，直接抛出让外层装饰器处理
                    raise
                except Exception as e:
                    # 其他非网络错误，记录后直接抛出，不重试
                    _LOGGER.error(
                        "[非网络错误] %s 遇到异常: %s (类型: %s)，不重试",
                        func.__name__, str(e), type(e).__name__
                    )
                    raise
            raise StateGridAuthError(f"Network error after {max_retries} retries: {last_exception}")
        return wrapper
    return decorator


def auto_relogin_on_auth_error(func):
    """Decorator to automatically refresh token or re-login when auth fails."""
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except (StateGridAuthError, StateGridTokenExpiredError) as e:
            error_msg = str(e).lower()
            # 检测常见的 token 失效错误信息
            token_expired_keywords = [
                "token", "unauthorized", "401", "403", "expired", 
                "invalid", "认证失败", "登录失效", "未登录"
            ]
            
            is_token_error = any(keyword in error_msg for keyword in token_expired_keywords)
            
            # 检查是否已经在重试中，避免无限循环
            if hasattr(self, '_auto_relogin_in_progress') and self._auto_relogin_in_progress:
                _LOGGER.debug("[自动重连] 已在重连中，跳过重复尝试")
                raise
            
            # 检查重试次数限制
            if not hasattr(self, '_auto_relogin_retry_count'):
                self._auto_relogin_retry_count = 0
            
            if self._auto_relogin_retry_count >= 3:
                _LOGGER.error("[自动重连] 已达到最大重试次数(3次)，停止重试")
                self._auto_relogin_retry_count = 0  # 重置计数器
                raise StateGridTokenExpiredError(
                    "Token expired and max retry attempts (3) reached. Please reconfigure the integration."
                ) from e
            
            if is_token_error and self._user_token:
                # 设置重连标志，防止递归
                self._auto_relogin_in_progress = True
                self._auto_relogin_retry_count += 1
                try:
                    _LOGGER.warning(
                        "[自动重连] 检测到认证失败(第%d/3次)，尝试刷新 token: %s", 
                        self._auto_relogin_retry_count, str(e)
                    )
                    try:
                        # 尝试刷新 access_token
                        await self.refresh_access_token()
                        _LOGGER.info("[自动重连] Token 刷新成功，重试原操作")
                        # 重置计数器
                        self._auto_relogin_retry_count = 0
                        # 重试原操作
                        return await func(self, *args, **kwargs)
                    except Exception as refresh_error:
                        _LOGGER.error("[自动重连] Token 刷新失败: %s", str(refresh_error))
                        
                        # 如果刷新失败，检查是否启用了自动重新登录
                        if (hasattr(self, '_auto_relogin_enabled') and self._auto_relogin_enabled and
                            hasattr(self, '_username') and self._username and
                            hasattr(self, '_password') and self._password):
                            _LOGGER.warning("[自动重连] Token 刷新失败，尝试使用账号密码重新登录")
                            try:
                                # 使用保存的账号密码重新登录
                                result = await self.login_with_password(self._username, self._password)
                                if result.get("success"):
                                    data = result.get("data", {})
                                    # 更新内部状态
                                    if data.get("token"):
                                        self._token = data.get("token")  # 更新 bizrt.token
                                    self._user_token = data.get("user_token")
                                    self._user_id = data.get("user_id")
                                    self._access_token = data.get("access_token")
                                    self._refresh_token = data.get("refresh_token")
                                    if data.get("power_user_list"):
                                        self._power_user_list = data.get("power_user_list")
                                    if data.get("login_account"):
                                        self._login_account = data.get("login_account")
                                    
                                    _LOGGER.info("[自动重连] 账号密码重新登录成功，重试原操作")
                                    
                                    # 调用回调函数更新 Store
                                    if hasattr(self, '_store_update_callback') and self._store_update_callback:
                                        try:
                                            await self._store_update_callback(
                                                token=self._encrypt_token,
                                                user_token=self._user_token,
                                                user_id=self._user_id,
                                                access_token=self._access_token,
                                                refresh_token=self._refresh_token,
                                                power_user_list=self._power_user_list,
                                                login_account=self._login_account,
                                                username=self._username,
                                                password=self._password,
                                                auto_relogin=self._auto_relogin_enabled,
                                            )
                                            _LOGGER.info("[自动重连] Store 更新成功")
                                        except Exception as store_err:
                                            _LOGGER.warning("[自动重连] Store 更新失败: %s", str(store_err))
                                    
                                    # 重置计数器
                                    self._auto_relogin_retry_count = 0
                                    # 重试原操作
                                    return await func(self, *args, **kwargs)
                                else:
                                    _LOGGER.error("[自动重连] 账号密码重新登录失败")
                                    raise StateGridTokenExpiredError(
                                        f"Token expired, refresh failed, and re-login failed: {result.get('message')}"
                                    ) from refresh_error
                            except Exception as relogin_error:
                                _LOGGER.error("[自动重连] 账号密码重新登录异常: %s", str(relogin_error))
                                raise StateGridTokenExpiredError(
                                    f"Token expired, refresh failed, and re-login error: {relogin_error}"
                                ) from refresh_error
                        else:
                            # 未启用自动重新登录或缺少账号密码
                            raise StateGridTokenExpiredError(
                                f"Token expired and refresh failed: {refresh_error}"
                            ) from refresh_error
                finally:
                    # 重置重连标志
                    self._auto_relogin_in_progress = False
            else:
                # 非 token 错误或没有保存的 user_token，直接抛出
                raise
    return wrapper


class Shaobor95598ApiClient:
    """95598 API Client handling encryption and SGCC commands."""

    def __init__(
        self,
        token: str,
        session: aiohttp.ClientSession,
        store: Any | None = None,
        hass: Any | None = None,
        entry_id: str | None = None,
        machine_id: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._encrypt_token = token  # 用于加密服务的固定 token，不应被修改
        self._token = token  # bizrt.token，登录后会被更新
        self._session = session
        self._store = store  # 用于持久化存储
        self._hass = hass  # Home Assistant 实例，用于创建 Store
        self._entry_id = entry_id
        self._machine_id = machine_id
        
        # Internal state mimicking Node-RED globals
        self._uuid = str(uuid.uuid4()).replace("-", "")
        self._key_code: str = ""
        self._public_key: str = ""

        # Login/session state
        self._user_token: str | None = None  # 95598_token (rsi)
        self._user_id: str | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._power_user_list: list[dict[str, Any]] | None = None
        self._selected_account_index: int = 0  # 户号选择索引，用于 c05f01 等
        self._login_account: str | None = None  # loginAccount from userInfo for c05f01
        self._user_info: Any | None = None  # bizrt.userInfo (95598_userInfo)
        
        # SMS login state
        self._sms_code_key: str | None = None  # codeKey from step1, needed for step2
        
        # Auto re-login credentials (only stored if auto_relogin is enabled)
        self._username: str | None = None
        self._password: str | None = None
        self._auto_relogin_enabled: bool = False
        
        # Callback for updating store after successful re-login
        self._store_update_callback: Any = None
        
        # Billing configuration for calculating daily average cost
        self._billing_config: dict[str, Any] = {}

    def set_billing_config(self, config: dict[str, Any]) -> None:
        """Set billing configuration for calculating daily average cost."""
        self._billing_config = config

    def load_auth_state(
        self,
        *,
        user_token: str | None = None,
        user_id: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        power_user_list: Any | None = None,
        selected_account_index: int | None = None,
        login_account: str | None = None,
    ) -> None:
        """Load previously stored auth state from config entry."""
        if user_token:
            self._user_token = user_token
        if user_id:
            self._user_id = user_id
        if access_token:
            self._access_token = access_token
        if refresh_token:
            self._refresh_token = refresh_token
        if isinstance(power_user_list, list):
            self._power_user_list = power_user_list
        if selected_account_index is not None and selected_account_index >= 0:
            self._selected_account_index = selected_account_index
        if login_account:
            self._login_account = login_account

    def set_auto_relogin_credentials(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        auto_relogin_enabled: bool = False,
        store_update_callback: Any = None,
    ) -> None:
        """Set credentials for auto re-login when token expires."""
        self._username = username
        self._password = password
        self._auto_relogin_enabled = auto_relogin_enabled
        self._store_update_callback = store_update_callback

    @property
    def user_id(self) -> str | None:
        return self._user_id

    @property
    def user_token(self) -> str | None:
        return self._user_token

    async def initialize(self, force_new_uuid: bool = False) -> None:
        """Step 1: Initialize the encryption session."""
        if force_new_uuid:
            import uuid
            self._uuid = str(uuid.uuid4()).replace("-", "")
            _LOGGER.info("[接口初始化] 强制重置 UUID: %s", self._uuid)
            
        url = f"{ENCRYPT_API_URL}/initialize"
        payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
        }  # 使用加密服务的固定 token
        try:
            async with self._session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                
            success_flag = data.get("success")
            inner_data = data.get("data", {})
                
            # The actual payload says code: 1 is success（支持整数 1 或字符串 "1"）
            if not success_flag or inner_data.get("code") not in (1, "1", 0, "0", "00"):
                msg = inner_data.get("message", "Unknown error")
                raise StateGridAuthError(f"Init failed: {msg}")
                
            result = inner_data.get("data") or {}
            if not isinstance(result, dict):
                result = {}
            self._key_code = result.get("keyCode") or ""
            self._public_key = result.get("publicKey") or ""
            _LOGGER.info("[接口初始化] 初始化成功: keyCode=%s", self._key_code[:8] + "...")
        except aiohttp.ClientError as err:
            raise StateGridAuthError(f"Communication error during init: {err}")

    async def _decrypt_to_data(self, encrypt_data: str, *, uuid_override: str | None = None) -> Any:
        """Decrypt helper response and return the decrypted 'data' payload (dict or string)."""
        url = f"{ENCRYPT_API_URL}/decrypt"
        use_uuid = uuid_override or self._uuid
        payload = {
            "token": self._encrypt_token,  # 使用加密服务的固定 token
            "uuid": use_uuid,
            "machineId": self._machine_id,
            "encryptData": encrypt_data,
        }
        try:
            async with self._session.post(url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    response.raise_for_status()
                    
                data = await response.json()
                if not isinstance(data, dict):
                    raise StateGridAuthError(f"Decrypt returned unexpected type: {type(data).__name__}")
                # 解密服务返回 code=1（整数）或 code="1"/"00"（字符串）表示成功
                # 支持两种结构: 顶层 code 或 data.code（如 {"success":true,"data":{"code":1,"data":{...}}）
                decrypt_code = data.get("code")
                if decrypt_code is None and isinstance(data.get("data"), dict):
                    decrypt_code = data["data"].get("code")
                
                # 优先检查业务错误码（如 11401 等错误）
                if decrypt_code is not None and decrypt_code not in [1, "1", "00", 0, "0"]:
                    # 提取错误信息
                    err_msg = None
                    if isinstance(data.get("data"), dict):
                        err_msg = data["data"].get("message") or data["data"].get("msg")
                    if not err_msg:
                        err_msg = data.get("message") or data.get("msg")
                    if not err_msg:
                        err_msg = f"code={decrypt_code}"
                    
                    # 如果 code 是 11401 或类似业务错误码，或者消息包含 "验证错误"，则标记为业务异常而不是解密失败
                    if "验证错误" in str(err_msg) or "验证码" in str(err_msg):
                        raise StateGridAuthError(f"业务异常: {err_msg} (可能是验证码识别错误或会话已过期)")
                    raise StateGridAuthError(f"业务异常: {err_msg}")
                
                # 检查是否成功
                is_ok = (
                    decrypt_code in [1, "1", "00", 0, "0"]
                    or data.get("success") is True
                )
                _LOGGER.debug("[解密] 解密服务返回原始 JSON: %s", data)
                
                # 解密服务返回结构: {"success":true,"data":{"code":1,"message":"成功","data":{实际内容}}}
                # 需要提取 data.data 才是真正的解密后业务数据（含 srvrt/bizrt 等）
                inner = data.get("data") if data.get("data") is not None else {}
                if inner is None:
                    inner = {}
                
                _LOGGER.debug("[解密] 解密服务返回的 data: %s", data)
                _LOGGER.debug("[解密] 提取的 inner: %s", inner)
                
                if isinstance(inner, dict):
                    result = inner.get("data")
                    # 部分解密服务直接返回 data 为业务内容，无嵌套 data.data
                    has_biz = inner.get("bizrt") is not None
                    has_srv = inner.get("srvrt") is not None
                    if result is None and (has_biz or has_srv):
                        result = inner
                    # 当 inner 为空但 data 顶层有 bizrt/srvrt 时，直接返回 data
                    if result is None and not (has_biz or has_srv):
                        if data.get("bizrt") is not None or data.get("srvrt") is not None:
                            result = data
                else:
                    result = inner if inner is not None else None
                
                _LOGGER.debug("[解密] 最终 result: %s (类型: %s)", result, type(result))
                
                # 当 data 在顶层直接包含 bizrt/srvrt 时（无嵌套 data 键）
                if result is None and isinstance(data, dict) and (data.get("bizrt") or data.get("srvrt")):
                    return data
                
                # 如果 result 仍然是 None 或空字符串，记录错误
                if result is None or result == "":
                    _LOGGER.error("[解密] 无法从解密数据中提取有效结果。原始数据: %s", data)
                    raise StateGridAuthError(f"Failed to extract valid data from decrypt response")
                
                return result
        except aiohttp.ClientError as err:
            raise StateGridAuthError(f"Communication error during decrypt: {err}")

    async def validate_token(self) -> bool:
        """Validate if the provided auth token is valid."""
        try:
            await self.initialize()
            return True
        except StateGridAuthError:
            return False

    async def login_with_password(self, username: str, password: str) -> dict[str, Any]:
        """Password login with slider captcha (flows.json: lf05 -> c44/f05 -> decrypt -> cv2/match -> lf06 -> c44/f06)."""
        # 强制重置会话，防止 reauth 流程中因之前失败的请求污染导致 【GB010】 业务异常
        self._key_code = ""
        await self.initialize(force_new_uuid=True)

        # 密码需 MD5 加密（与 Node-RED 流程一致，见 flows.json 提示）
        password_md5 = hashlib.md5(password.encode("utf-8")).hexdigest().upper()

        # 注释掉滑块相关接口请求
        # # Step 1: encrypt lf05 (account+password)
        # encrypt_lf05 = await self._secure_post_encrypt(
        #     f"{ENCRYPT_API_URL}/encrypt/lf05",
        #     {
        #         "token": self._encrypt_token,
        #         "keyCode": self._key_code,
        #         "uuid": self._uuid,
        #         "publicKey": self._public_key,
        #         "account": username,
        #         "password": password_md5,
        #     },
        # )

        # # Step 2: call 95598 c44/f05 to get captcha
        # for attempt in range(2):
        #     headers_f05 = self._get_sgcc_headers(str(encrypt_lf05.get("timestamp", "")))
        #     payload_f05 = {
        #         "data": encrypt_lf05.get("data"),
        #         "skey": encrypt_lf05.get("skey"),
        #         "client_id": encrypt_lf05.get("client_id"),
        #         "timestamp": encrypt_lf05.get("timestamp"),
        #     }
        #     async with self._session.post(
        #         "https://www.95598.cn/api/osg-web0004/open/c44/f05",
        #         json=payload_f05,
        #         headers=headers_f05,
        #     ) as resp:
        #         resp.raise_for_status()
        #         text_f05 = await resp.text()

        #     raw_f05 = self._parse_sgcc_response(text_f05)
        #     _LOGGER.debug("[登录] c44/f05 第%d次响应: %s", attempt + 1, raw_f05)
            
        #     # 检查是否有业务错误码且需要重试
        #     if isinstance(raw_f05, dict):
        #         code_f05 = raw_f05.get("code")
        #         if code_f05 == "GB010" and attempt == 0:
        #             _LOGGER.warning("[登录] 检测到 GB010 错误，可能是加密会话失效，尝试强制重置 UUID 并初始化...")
        #             self._key_code = "" # 清除旧的 keyCode 触发重新初始化
        #             await self.initialize(force_new_uuid=True)
                    
        #             # 重新加密 lf05
        #             encrypt_lf05 = await self._secure_post_encrypt(
        #                 f"{ENCRYPT_API_URL}/encrypt/lf05",
        #                 {
        #                     "token": self._encrypt_token,
        #                     "keyCode": self._key_code,
        #                     "uuid": self._uuid,
        #                     "publicKey": self._public_key,
        #                     "account": username,
        #                     "password": password_md5,
        #                 },
        #             )
        #             continue # 进行第二次尝试
                
        #         # 如果不是 GB010 或者已经是第二次尝试，则按常规处理业务错误
        #         self._check_and_raise_business_error(raw_f05, "c44/f05")

        #     encrypted_f05 = self._get_encrypted_data(raw_f05) or (
        #         text_f05.strip() if self._is_likely_encrypted(text_f05) else ""
        #     )
        #     if encrypted_f05:
        #         # 提取到加密数据，不再重试
        #         break
            
        #     if attempt == 1:
        #         # 如果第二次尝试仍然没有加密数据，则抛出异常
        #         raise StateGridAuthError(f"c44/f05 响应无法解析，结构: {type(raw_f05).__name__}")

        # decrypted_captcha = await self._decrypt_to_data(encrypted_f05)
        # ... (此处省略大量的验证码识别逻辑) ...
        
        # Step 4: encrypt lf06
        encrypt_lf06 = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/lf06",
            {
                "token": self._encrypt_token,
                "uuid": self._uuid,
                "machineId": self._machine_id,
                "publicKey": self._public_key,
                "account": username,
                "password": password_md5,
            },
        )

        # Step 5: call 95598 c44/f06 to login
        headers_f06 = self._get_sgcc_headers(
            str(encrypt_lf06.get("timestamp", "")), 
            include_device_token=True
        )
        payload_f06 = {
            "data": encrypt_lf06.get("data"),
            "skey": encrypt_lf06.get("skey"),
            "timestamp": encrypt_lf06.get("timestamp"),
        }
        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/open/c44/f06",
            json=payload_f06,
            headers=headers_f06,
        ) as resp:
            resp.raise_for_status()
            text_f06 = await resp.text()

        raw_f06 = self._parse_sgcc_response(text_f06)
        _LOGGER.debug("[登录] c44/f06 原始响应: %s", raw_f06)
        
        # 检查是否是业务错误（此时还未解密，但报错通常是明文 JSON）
        # 只有当 code 存在且不是成功码时才报错
        if isinstance(raw_f06, dict):
            code = raw_f06.get("code")
            # 如果 code 存在且不是成功码（1, 0, 00, "1", "0", "00"），则报错
            if code is not None and str(code) not in ("1", "0", "00", "None"):
                msg = raw_f06.get("message") or raw_f06.get("msg") or f"code={code}"
                raise StateGridAuthError(f"c44/f06 业务异常: {msg}")

        encrypted_f06 = self._get_encrypted_data(raw_f06) or (
            text_f06.strip() if self._is_likely_encrypted(text_f06) else ""
        )
        if not encrypted_f06:
            raise StateGridAuthError(f"c44/f06 响应无法识别加密内容，响应体长: {len(text_f06)}")

        # c44/f06 解密后得到 bizrt.token，此时才是真正的登录成功
        decrypted_login = await self._decrypt_to_data(encrypted_f06)
        
        # 深度检查业务错误码（解密后的 bizrt/srvrt 可能包含错误）
        if isinstance(decrypted_login, dict):
            srvrt = decrypted_login.get("srvrt") or decrypted_login.get("data", {}).get("srvrt")
            if isinstance(srvrt, dict) and srvrt.get("resultCode") not in (None, "0000", "1", "0"):
                msg = srvrt.get("resultMessage") or "登录失败"
                raise StateGridAuthError(f"服务异常: {msg} (code={srvrt.get('resultCode')})")
        _sanitized = self._sanitize_for_log(decrypted_login)
        try:
            _LOGGER.debug("[调试] 登录返回值(脱敏): %s", json.dumps(_sanitized, ensure_ascii=False, default=str)[:1500])
        except (TypeError, ValueError):
            _LOGGER.debug("[调试] 登录返回值(脱敏): %s", repr(_sanitized)[:800])
        
        # 确保 decrypted_login 是字典类型
        if not isinstance(decrypted_login, dict):
            _LOGGER.error("[登录] 解密后的数据不是字典类型: %s (类型: %s)", decrypted_login, type(decrypted_login))
            raise StateGridAuthError(f"Login decryption returned unexpected type: {type(decrypted_login).__name__}")
        
        bizrt = self._find_first_dict_with_keys(decrypted_login, {"token", "userInfo"})
        if not bizrt:
            bizrt = (
                decrypted_login.get("data", {})
                if isinstance(decrypted_login.get("data"), dict)
                else {}
            )
            bizrt = bizrt.get("bizrt", bizrt) if isinstance(bizrt, dict) else {}
        user_token = bizrt.get("token") or bizrt.get("rsi")
        user_info = bizrt.get("userInfo")
        if not user_token:
            raise StateGridAuthError("Login result missing token")
        # 从 bizrt 提取 user_id、login_account（真正的登录成功时刻）
        if isinstance(user_info, list) and user_info and isinstance(user_info[0], dict):
            first_ui = user_info[0]
            self._user_id = str(first_ui.get("userId", ""))
            if first_ui.get("loginAccount"):
                self._login_account = str(first_ui["loginAccount"])
        elif isinstance(user_info, dict) and user_info.get("loginAccount"):
            self._login_account = str(user_info["loginAccount"])
        self._user_token = str(user_token)
        self._token = str(user_token)  # 更新 token（bizrt.token）

        # Step 6: exchange for access_token
        tokens = await self.exchange_user_token_for_access_token(str(user_token))
        power_user_list = None
        try:
            power_user_list = await self.fetch_power_user_list()
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "token": str(user_token),  # bizrt.token
                "user_token": str(user_token),  # 保持兼容性
                "user_id": self._user_id,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "power_user_list": power_user_list,
                "login_account": self._login_account,
                "user_info": user_info,  # bizrt.userInfo，真正的登录成功时刻的数据
            },
        }

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def exchange_user_token_for_access_token(self, user_token: str) -> dict[str, str]:
        """Exchange 95598 'rsi' user_token for oauth2 access_token/refresh_token."""
        # 确保在刷新 token 之前先执行初始化操作（获取 key_code 和 public_key）
        if not self._key_code or not self._public_key:
            await self.initialize()

        self._user_token = user_token

        # Step A: authorize -> decrypt -> extract code
        timestamp = int(time.time() * 1000)
        headers = {
            "keyCode": self._key_code,
            "timestamp": str(timestamp),
            "wsgwType": "web",
            "source": "0901",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json;charset=UTF-8",
            "appKey": APP_KEY,
            "version": VERSION,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        form_payload = urlencode(
            {
                "client_id": APP_KEY,
                "response_type": "code",
                "redirect_url": "/test",
                "timestamp": str(timestamp),
                "rsi": user_token,
            }
        )

        async with self._session.post(
            "https://www.95598.cn/api/oauth2/oauth/authorize",
            data=form_payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            authorize_text = await resp.text()

        authorize_raw = self._parse_sgcc_response(authorize_text)
        authorize_encrypted = self._get_encrypted_data(authorize_raw) or (
            authorize_text.strip() if self._is_likely_encrypted(authorize_text) else ""
        )
        if not authorize_encrypted:
            raise StateGridAuthError("Authorize did not return decryptable payload")

        authorize_data = await self._decrypt_to_data(authorize_encrypted, uuid_override=user_token)
        if not isinstance(authorize_data, dict):
            raise StateGridAuthError(f"Authorize decrypt returned unexpected type: {type(authorize_data)}")

        redirect_url = authorize_data.get("redirect_url") or ""
        if "code=" not in redirect_url:
            raise StateGridAuthError("Authorize response missing code in redirect_url")
        code = redirect_url.split("code=", 1)[1]

        # Step B: helper encrypt getWebToken
        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "code": code,
            "key_code": self._key_code,
            "uuid": self._uuid,
            "publicKey": self._public_key,
        }
        encrypted = await self._secure_post_encrypt(f"{ENCRYPT_API_URL}/encrypt/getWebToken", encrypt_payload)

        # Step C: call getWebToken and decrypt
        web_token_headers = self._get_sgcc_headers(str(encrypted.get("timestamp")))
        web_token_payload = {
            "data": encrypted.get("data"),
            "skey": encrypted.get("skey"),
            "timestamp": encrypted.get("timestamp"),
        }
        async with self._session.post(
            "https://www.95598.cn/api/oauth2/outer/getWebToken",
            json=web_token_payload,
            headers=web_token_headers,
        ) as resp:
            resp.raise_for_status()
            web_token_text = await resp.text()

        web_token_raw = self._parse_sgcc_response(web_token_text)
        web_token_encrypted = self._get_encrypted_data(web_token_raw) or (
            web_token_text.strip() if self._is_likely_encrypted(web_token_text) else ""
        )
        if not web_token_encrypted:
            raise StateGridAuthError("getWebToken did not return decryptable payload")

        web_token_data = await self._decrypt_to_data(web_token_encrypted)
        if not isinstance(web_token_data, dict):
            raise StateGridAuthError(f"getWebToken decrypt returned unexpected type: {type(web_token_data)}")

        access_token = web_token_data.get("access_token")
        refresh_token = web_token_data.get("refresh_token")
        
        _LOGGER.debug("[getWebToken] 解密后的数据: %s", 
                     {k: (v[:20] + "..." if isinstance(v, str) and len(v) > 20 else v) 
                      for k, v in web_token_data.items()})
        
        if not access_token:
            raise StateGridAuthError("Missing access_token in getWebToken decrypted payload")

        self._access_token = str(access_token)
        self._refresh_token = str(refresh_token) if refresh_token else None
        
        _LOGGER.debug("[getWebToken] 已设置 access_token: %s..., refresh_token: %s...",
                     self._access_token[:20] if self._access_token else None,
                     self._refresh_token[:20] if self._refresh_token else None)
        
        out = {"access_token": self._access_token, "refresh_token": self._refresh_token or ""}
        return out

    async def refresh_access_token(self) -> dict[str, str]:
        """Refresh access_token via authorize+getWebToken (与 Node-RED 获取Token 流程一致，每10分钟执行)."""
        _LOGGER.warning("[Token刷新] 开始刷新 access_token")
        if not self._user_token:
            raise StateGridAuthError("Missing user_token. Reconfigure integration.")
        try:
            result = await self.exchange_user_token_for_access_token(str(self._user_token))
            _LOGGER.warning("[Token刷新] access_token 刷新成功")
            return result
        except Exception as e:
            _LOGGER.error("[Token刷新] 刷新失败: %s", str(e))
            
            # 如果刷新失败且启用了自动重新登录,尝试用账号密码重新登录
            if (hasattr(self, '_auto_relogin_enabled') and self._auto_relogin_enabled and
                hasattr(self, '_username') and self._username and
                hasattr(self, '_password') and self._password):
                _LOGGER.warning("[Token刷新] 尝试使用账号密码重新登录")
                try:
                    # 重新初始化加密密钥(可能已过期)
                    _LOGGER.info("[Token刷新] 重新初始化加密密钥")
                    await self.initialize()
                    
                    result = await self.login_with_password(self._username, self._password)
                    if result.get("success"):
                        data = result.get("data", {})
                        # 更新内部状态
                        if data.get("token"):
                            self._token = data.get("token")
                        self._user_token = data.get("user_token")
                        self._user_id = data.get("user_id")
                        self._access_token = data.get("access_token")
                        self._refresh_token = data.get("refresh_token")
                        if data.get("power_user_list"):
                            self._power_user_list = data.get("power_user_list")
                        if data.get("login_account"):
                            self._login_account = data.get("login_account")
                        
                        _LOGGER.info("[Token刷新] 账号密码重新登录成功")
                        
                        # 调用回调函数更新 Store
                        if hasattr(self, '_store_update_callback') and self._store_update_callback:
                            try:
                                await self._store_update_callback(
                                    token=self._encrypt_token,
                                    user_token=self._user_token,
                                    user_id=self._user_id,
                                    access_token=self._access_token,
                                    refresh_token=self._refresh_token,
                                    power_user_list=self._power_user_list,
                                    login_account=self._login_account,
                                    username=self._username,
                                    password=self._password,
                                    auto_relogin=self._auto_relogin_enabled,
                                )
                                _LOGGER.info("[Token刷新] Store 更新成功")
                            except Exception as store_err:
                                _LOGGER.warning("[Token刷新] Store 更新失败: %s", str(store_err))
                        
                        return {"access_token": self._access_token, "refresh_token": self._refresh_token or ""}
                    else:
                        _LOGGER.error("[Token刷新] 账号密码重新登录失败")
                        raise StateGridAuthError("Auto re-login failed") from e
                except Exception as login_err:
                    _LOGGER.error("[Token刷新] 自动重新登录异常: %s", str(login_err))
                    raise StateGridAuthError("Auto re-login exception") from login_err
            else:
                _LOGGER.warning("[Token刷新] 未启用自动重新登录或缺少账号密码")
                raise

    @auto_relogin_on_auth_error
    @retry_on_network_error(max_retries=3, delay=2.0)
    async def get_electricity_data(self) -> dict[str, Any]:
        """Fetch all electricity data from SGCC."""
        if not self._key_code:
            await self.initialize()
        if not self._user_token or not self._access_token:
            raise StateGridAuthError("Missing login state (user_token/access_token). Reconfigure integration.")

        # 拿到 access_token 后才能获取户号（c8f11 需要 Authorization: Bearer access_token）
        # c05f01 需要 userName，来自 c8f11 返回的 userInfo.loginAccount
        if not self._power_user_list or not self._login_account:
            self._power_user_list = await self._fetch_power_user_list()

        # 当前所选户号：所有后续数据（余额、预估等）均仅针对该户号
        idx = min(self._selected_account_index, len(self._power_user_list) - 1) if self._power_user_list else 0
        active_account = self._power_user_list[idx] if self._power_user_list and idx >= 0 else {}
        selected_cons_no = active_account.get("consNo_dst") or active_account.get("consNoDst") or ""
        selected_elec_addr = active_account.get("elecAddr_dst") or active_account.get("elecAddrDst") or ""
        selected_org_name = active_account.get("orgName") or ""
        selected_owner_name = active_account.get("consName_dst") or active_account.get("consNameDst") or ""
        selected_org_no = active_account.get("orgNo") or ""
        selected_province_id = active_account.get("provinceId") or ""
        selected_pro_no = active_account.get("proNo") or ""
        selected_elec_type = active_account.get("elecTypeCode") or ""
        selected_cons_sort = active_account.get("consSortCode") or active_account.get("sceneType") or ""
        selected_status = active_account.get("status") or ""
        selected_is_default = active_account.get("isDefault") or ""

        balance_info = await self._fetch_balance_info()
        balance = balance_info.get("balance")
        esti_amt = balance_info.get("esti_amt")
        electricity_fee_detail = balance_info.get("electricity_fee_detail", {})

        # 获取每日用电量（用于计算日均电费）
        daily_usage = {}
        try:
            daily_usage = await self._fetch_daily_usage()
        except Exception as e:
            _LOGGER.debug("无法获取每日用电量（不影响主要功能）: %s", e)

        daily_avg = None
        remaining_days = None
        
        # 尝试从所有返回的历史记录中，逆序寻找最近 7 个有数据的记录（方法A：历史稳健均值）
        history_daily_avg = None
        if isinstance(daily_usage, dict) and daily_usage.get("sevenEleList"):
            all_history = daily_usage.get("sevenEleList", [])
            # 按日期降序排列（确保从最亮的项开始往回找）
            try:
                sorted_history = sorted(all_history, key=lambda x: str(x.get("day", "")), reverse=True)
            except Exception:
                sorted_history = all_history[::-1] # 回退：直接逆序

            recent_samples = []
            recent_peaks = []
            recent_valleys = []
            
            for day_data in sorted_history:
                if len(recent_samples) >= 7: # 我们只采集最近 7 个有效样本
                    break
                    
                day_ele_pq = day_data.get("dayElePq")
                # 排除无效字符 "-" 或 0 以及 Null
                if day_ele_pq and day_ele_pq != "-":
                    try:
                        val = float(day_ele_pq)
                        if val > 0: # 必须有实际消耗量才作为样本点
                            recent_samples.append(val)
                            # 采集对应的峰谷，如果缺失则补0以便对齐计算
                            p = day_data.get("thisPPq") or day_data.get("thisTPq") or "0"
                            v = day_data.get("thisVPq") or "0"
                            recent_peaks.append(float(p))
                            recent_valleys.append(float(v))
                    except (ValueError, TypeError):
                        pass
            
            # 只要有至少 1 个有效样本，就开始计算
            if recent_samples:
                avg_daily_kwh = sum(recent_samples) / len(recent_samples)
                billing_mode = self._billing_config.get("billing_mode", "")
                
                # 如果是峰谷模式且峰谷数据齐全
                if "tou" in billing_mode.lower() and len(recent_peaks) == len(recent_samples):
                    avg_peak_kwh = sum(recent_peaks) / len(recent_peaks)
                    avg_valley_kwh = sum(recent_valleys) / len(recent_valleys)
                    p_tip = self._billing_config.get("price_tip", 0)
                    p_peak = self._billing_config.get("price_peak", 0)
                    p_valley = self._billing_config.get("price_valley", 0)
                    eff_p = max(p_tip, p_peak) if p_tip or p_peak else 0.6
                    eff_v = p_valley if p_valley else 0.3
                    history_daily_avg = (avg_peak_kwh * eff_p) + (avg_valley_kwh * eff_v)
                elif "average" in billing_mode.lower():
                    price = self._billing_config.get("average_price", 0.6)
                    history_daily_avg = avg_daily_kwh * price
                else: # 阶梯模式
                    price = self._billing_config.get("ladder_price_1", 0.6)
                    history_daily_avg = avg_daily_kwh * price
                
                _LOGGER.info("[预计可用] 从最近%d个历史工作日样本中提取日均值: %.2f元/天", len(recent_samples), history_daily_avg)

        # 辅助方法：从 estiAmt 计算（方法B：当月快照预估）
        current_month_daily_avg = None
        if isinstance(esti_amt, (int, float)) and esti_amt > 0:
            now = datetime.now()
            day_of_month = now.day
            if day_of_month == 1:
                current_month_daily_avg = float(esti_amt) / max(0.5, now.hour / 24.0)
            else:
                current_month_daily_avg = float(esti_amt) / float(day_of_month)

        # 最终决策
        now_day = datetime.now().day
        if history_daily_avg and history_daily_avg > 0:
            # 强化处理：每月前 7 天，本月预估数据严重偏低，强制完全信任历史均值
            if now_day <= 7:
                daily_avg = history_daily_avg
            else:
                # 稳定期：综合两者（历史稳健，当月实时）
                if current_month_daily_avg:
                    daily_avg = (history_daily_avg * 0.6) + (current_month_daily_avg * 0.4)
                else:
                    daily_avg = history_daily_avg
        else:
            daily_avg = current_month_daily_avg

        # 计算预计可用天数 (剩余天数)
        if isinstance(balance, (int, float)) and balance is not None and daily_avg and daily_avg > 0:
            remaining_days = int(float(balance) // float(daily_avg))
            _LOGGER.info("[预计可用] 最终计算 -> 余额 %.2f元 ÷ 日均 %.2f元 = %d天", balance, daily_avg, remaining_days)

        # 获取缴费记录（可选功能，失败不影响主要功能）
        payment_records = {"count": 0, "payList": []}
        try:
            payment_records = await self._fetch_payment_records()
        except Exception as e:
            # 缴费记录接口可能对某些登录方式有限制，失败不影响主要功能
            _LOGGER.debug("无法获取缴费记录（不影响主要功能）: %s", e)

        return {
            "balance": balance,
            "daily_avg": daily_avg,
            "remaining_days": remaining_days,
            "last_update": time.time(),
            "payment_records": payment_records,
            "electricity_fee_detail": electricity_fee_detail,
            "daily_usage": daily_usage,
            "selected_cons_no": selected_cons_no,
            "selected_elec_addr": selected_elec_addr,
            "selected_org_name": selected_org_name,
            "selected_owner_name": selected_owner_name,
            "selected_org_no": selected_org_no,
            "selected_province_id": selected_province_id,
            "selected_pro_no": selected_pro_no,
            "selected_elec_type": selected_elec_type,
            "selected_cons_sort": selected_cons_sort,
            "selected_status": selected_status,
            "selected_is_default": selected_is_default,
        }

    async def get_login_qrcode(self) -> dict[str, Any]:
        """Fetch login QR code and serial number."""
        # 强制重置会话，防止验证失败的状态带入新验证周期
        self._key_code = ""
        await self.initialize(force_new_uuid=True)
            
        url = "https://www.95598.cn/api/osg-open-uc0001/member/c8/f24"
        serial_no = "".join([str(random.randint(0, 9)) for _ in range(28)])
        
        for attempt in range(2):
            timestamp = int(time.time() * 1000)
            headers = self._get_sgcc_headers(str(timestamp))
            payload = {
                "_access_token": "",
                "_t": "",
                "_data": {
                    "uscInfo": {
                        "devciceIp": "",
                        "tenant": "state_grid",
                        "member": "0902",
                        "devciceId": ""
                    },
                    "quInfo": {
                        "optType": "01",
                        "serialNo": serial_no
                    }
                },
                "timestamp": timestamp
            }
            async with self._session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                text = await resp.text()
                
            data = self._parse_sgcc_response(text)
            _LOGGER.debug("[扫码登录] c8/f24 第%d次响应: %s", attempt + 1, data)
            
            if isinstance(data, dict):
                code = data.get("code")
                if code == "GB010" and attempt == 0:
                    _LOGGER.warning("[扫码登录] 获取二维码时检测到 GB010，重新初始化会话...")
                    self._key_code = ""
                    await self.initialize(force_new_uuid=True)
                    continue
                
                # Check business code
                srvrt = (data.get("data") or {}).get("srvrt") if isinstance(data.get("data"), dict) else {}
                if code is not None and str(code) not in ("1", "0", "00", "None"):
                    msg = srvrt.get("resultMessage") or data.get("message") or f"code={code}"
                    raise StateGridAuthError(f"Failed to get QR code: {msg}")
            
            bizrt = data.get("data", {}).get("bizrt", {}) if isinstance(data.get("data"), dict) else {}
            qr_code = bizrt.get("qrCode")
            qr_serial = bizrt.get("qrCodeSerial")
            
            if qr_code:
                return {
                    "qr_code": qr_code,
                    "serial_no": qr_serial
                }
            
            if attempt == 1:
                raise StateGridAuthError("Server returned empty QR code")
        
        return {} # Should not reach here

    async def check_qrcode_status(self, serial_no: str) -> dict[str, Any]:
        """Check if QR code has been scanned via c50f02."""
        if not self._key_code:
            await self.initialize()

        for attempt in range(2):
            encrypt_url = f"{ENCRYPT_API_URL}/encrypt/c50f02"
            payload = {
                "token": self._encrypt_token,
                "uuid": self._uuid,
                "publicKey": self._public_key,
                "qrCodeSerial": serial_no
            }
            
            try:
                encrypt_res = await self._secure_post_encrypt(encrypt_url, payload)
                
                # Now call 95598.cn status check
                url = "https://www.95598.cn/api/osg-web0004/open/c50/f02"
                headers = self._get_sgcc_headers(
                    str(encrypt_res["timestamp"]), 
                    token=self._generate_temp_token(),
                    include_device_token=True
                )
                
                payload_sgcc = {
                    "data": encrypt_res["data"],
                    "skey": encrypt_res["skey"],
                    "timestamp": encrypt_res["timestamp"]
                }
                
                _LOGGER.debug("[扫码登录] c50/f02 请求 URL: %s", url)
                _LOGGER.debug("[扫码登录] c50/f02 请求 Headers: %s", headers)
                _LOGGER.debug("[扫码登录] c50/f02 请求 Payload: %s", payload_sgcc)
                
                async with self._session.post(url, json=payload_sgcc, headers=headers) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                    
                res_data_raw = self._parse_sgcc_response(text)
                _LOGGER.debug("[扫码登录] c50/f02 第%d次响应: %s", attempt + 1, res_data_raw)
                
                if isinstance(res_data_raw, dict):
                    code = res_data_raw.get("code")
                    if code == "GB010" and attempt == 0:
                        _LOGGER.warning("[扫码登录] 检查扫码状态时检测到 GB010，重新初始化会话...")
                        self._key_code = ""
                        await self.initialize(force_new_uuid=True)
                        continue
                
                res_data_to_decrypt = self._get_encrypted_data(res_data_raw)
                if not res_data_to_decrypt:
                    if isinstance(res_data_raw, dict) and str(res_data_raw.get("code")) not in ["None", "1", "0000", "0"]:
                        return {"status": "WAITING", "message": res_data_raw.get("message")}
                    return {"status": "WAITING"}
                
                decrypted = await self._decrypt_to_data(res_data_to_decrypt or text)

                # 只要解密出来的是有效字符串且不是 "null"，就认为扫码成功拿到 Token 了
                if isinstance(decrypted, str) and decrypted.strip() and decrypted.lower() != "null":
                    return {"status": "SUCCESS", "user_token": decrypted}

                if isinstance(decrypted, dict):
                    srvrt = decrypted.get("srvrt", {}) if isinstance(decrypted.get("srvrt"), dict) else {}
                    bizrt = decrypted.get("bizrt", {}) if isinstance(decrypted.get("bizrt"), dict) else {}
                    if srvrt.get("resultCode") == "0000" and (bizrt or decrypted):
                        token = None
                        if isinstance(bizrt, dict):
                            token = bizrt.get("token") or bizrt.get("rsi")
                        token = token or decrypted.get("token") or decrypted.get("rsi")
                        if token:
                            return {"status": "SUCCESS", "user_token": str(token), "bizrt": bizrt}
                
                return {
                    "status": "WAITING",
                    "message": "Waiting for scan"
                }
            except Exception as err:
                if "验证失败" in str(err) or "GB010" in str(err):
                    if attempt == 0:
                         _LOGGER.warning("[扫码登录] 检查扫码状态时异常 (%s)，尝试重新初始化...", err)
                         self._key_code = ""
                         await self.initialize(force_new_uuid=True)
                         continue
                return {"status": "ERROR", "message": str(err)}
        
        return {"status": "WAITING"}

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

    def _generate_temp_token(self) -> str:
        """生成前端随机 Token (98或99开头 + 10位随机数字)."""
        prefix = random.choice(["98", "99"])
        return prefix + "".join([str(random.randint(0, 9)) for _ in range(10)])

    def _get_sgcc_headers(self, timestamp: str, token: str | None = None, include_device_token: bool = False) -> dict[str, str]:
        """Generate headers required for www.95598.cn calls."""
        headers = {
            'Host': 'www.95598.cn',
            'keyCode': self._key_code,
            'timestamp': str(timestamp),
            'wsgwType': 'web',
            'source': '0901',
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept': 'application/json;charset=UTF-8',
            'appKey': APP_KEY,
            'version': VERSION,
            'Content-Type': 'application/json;charset=UTF-8',
        }
        if include_device_token:
            headers['devicetokentx'] = 'v2:P5eYtUHti1SyWs/DyDs4pdqFkVx8L/ByeHNwEq64jEokhFKkOHeOtUjtxfGvCWLvF0DZjDSWTHtvjv9DYA3GvzPcgSNdWjz4gwfmjWo+Ka76MvH+WKqYnLkWzITiCxIDtxQyU7OOEDGqn7Gdm5bxbKMEznMWh/RiPCwRa2LtcZDw1eRiWOQM084Glcui6BHjnif6sqBPQ7BMjUGtfl58zryX2TcF+dzj7vZo9DkQFKATJXNEDNjynSn6bkPhuMHlY17NejA2GGdEJq9Af04nMyXivg=='
        if token:
            headers['token'] = token
        return headers

    def _parse_sgcc_response(self, text: str) -> dict:
        """Parse SGCC response text robustly, handling concatenated JSON or mixed content."""
        if not text:
            return {}
        
        stripped = text.strip()
        
        # 情况1：以 { 或 [ 开头，直接尝试 JSON 解析
        if stripped.startswith('{') or stripped.startswith('['):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError as e:
                # 处理 {JSON}{JSON} 格式（Extra data）
                if "Extra data" in str(e):
                    try:
                        return json.loads(stripped[:e.pos])
                    except Exception:
                        pass
        
        # 情况2：文本以非 JSON 字符（如 Base64）开头，后面跟着 JSON
        # 例如：BASE64DATA{...}，尝试从第一个 { 开始解析
        elif '{' in stripped:
            json_start = stripped.index('{')
            try:
                candidate = stripped[json_start:]
                result = json.loads(candidate)
                return result
            except json.JSONDecodeError as e:
                if "Extra data" in str(e):
                    try:
                        return json.loads(candidate[:e.pos])
                    except Exception:
                        pass
        
        # 情况3：无法解析，将原始文本包装为 data 字段（可能是纯 Base64 加密数据）
        return {"data": stripped}


    def _get_encrypted_data(self, data: Any) -> Optional[str]:
        """Extract encrypted Base64 data from various SGCC response structures."""
        if not isinstance(data, dict):
            return None
        
        # 1. Direct 'encryptData' or 'data' string
        for key in ["encryptData", "data"]:
            val = data.get(key)
            if isinstance(val, str):
                return val
        
        # 2. Nested 'encryptData' inside 'data'
        inner_data = data.get("data")
        if isinstance(inner_data, dict):
            val = inner_data.get("encryptData")
            if isinstance(val, str):
                return val
        
        return None

    def _is_likely_encrypted(self, text: str) -> bool:
        """粗略判断字符串是否像 Base64 加密数据（而非普通 JSON/文本）。"""
        if not text or len(text) < 20:
            return False
        # 如果文本以 '{' 或 '[' 开头，它很可能是 JSON 明文，不是加密数据
        stripped = text.strip()
        if stripped.startswith(('{', '[')):
            return False
        # Base64 只包含 A-Z a-z 0-9 + / = 字符
        import re
        return bool(re.match(r'^[A-Za-z0-9+/=]+$', stripped))

    async def _secure_post_encrypt(self, url: str, payload: dict) -> dict:
        """Helper to post to encrypt helper server using session."""
        try:
            async with self._session.post(url, json=payload) as response:
                body = await response.text()
                if response.status >= 400:
                    try:
                        err_json = json.loads(body) if body else {}
                        err_msg = err_json.get("error") or err_json.get("message") or err_json.get("msg") or body[:500]
                    except (json.JSONDecodeError, TypeError):
                        err_msg = body[:500] if body else str(response.status)
                    raise StateGridAuthError(
                        f"Helper API {response.status}: {err_msg}"
                    )
                res = json.loads(body) if isinstance(body, str) else body
                if not res.get("success"):
                    raise StateGridAuthError(f"Helper API error: {res.get('message')}")
                
                # Extract inner data but also keep important metadata if present
                inner = res.get("data", {})
                if not isinstance(inner, dict):
                    return {"data": inner}
                
                # If skey/client_id are at top level (unlikely but defensive), merge them
                for key in ["skey", "client_id", "timestamp"]:
                    if key in res and key not in inner:
                        inner[key] = res[key]
                return inner
        except StateGridAuthError:
            raise
        except aiohttp.ClientError as err:
            raise StateGridAuthError(f"Helper API communication error: {err}")
        except Exception as err:
            raise StateGridAuthError(f"Unexpected error in _secure_post_encrypt: {err}")

    async def login_with_sms_step1(self, phone: str) -> dict[str, Any]:
        """发送短信验证码.
        
        Args:
            phone: 手机号码
            
        Returns:
            {"success": True}
        """
        # 强制重置会话，防止验证失败的状态带入新验证周期
        self._key_code = ""
        await self.initialize(force_new_uuid=True)
        
        _LOGGER.info("[短信登录] 步骤1: 发送验证码到 %s", phone)
        
        # Step 1: 加密手机号 (使用 c8f04 加密接口)
        encrypt_data = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/c8f04",
            {
                "token": self._encrypt_token,
                "keyCode": self._key_code,
                "uuid": self._uuid,
                "publicKey": self._public_key,
                "account": phone,
                "sendType": "0",
                "businessType": "login",
            },
        )
        
        # Step 2: 调用 95598 API 发送短信 (osg-open-uc0001/member/c8/f04 端点)
        for attempt in range(2):
            headers = self._get_sgcc_headers(str(encrypt_data.get("timestamp", "")))
            payload = {
                "data": encrypt_data.get("data"),
                "skey": encrypt_data.get("skey"),
                "timestamp": encrypt_data.get("timestamp"),
            }
            
            async with self._session.post(
                "https://www.95598.cn/api/osg-open-uc0001/member/c8/f04",
                json=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
            
            raw_response = self._parse_sgcc_response(text)
            _LOGGER.debug("[短信登录] c8/f04 第%d次响应: %s", attempt + 1, raw_response)
            
            if isinstance(raw_response, dict):
                code = raw_response.get("code")
                if code == "GB010" and attempt == 0:
                    _LOGGER.warning("[短信登录] 检测到 GB010 错误，自动尝试强制重置 UUID 并初始化...")
                    self._key_code = ""
                    await self.initialize(force_new_uuid=True)
                    
                    # 重新加密 c8f04
                    encrypt_data = await self._secure_post_encrypt(
                        f"{ENCRYPT_API_URL}/encrypt/c8f04",
                        {
                            "token": self._encrypt_token,
                            "keyCode": self._key_code,
                            "uuid": self._uuid,
                            "publicKey": self._public_key,
                            "account": phone,
                            "sendType": "0",
                            "businessType": "login",
                        },
                    )
                    continue
                
                self._check_and_raise_business_error(raw_response, "c8/f04")

            encrypted_response = self._get_encrypted_data(raw_response) or (
                text.strip() if self._is_likely_encrypted(text) else ""
            )
            if encrypted_response:
                break
            
            if attempt == 1:
                raise StateGridAuthError(f"发送短信验证码请求异常，未返回加密数据 (c8/f04)。响应: {str(raw_response)[:200]}")
        
        if not encrypted_response:
            raise StateGridAuthError("发送短信验证码失败：未返回加密数据")
        
        # 解密响应
        decrypted = await self._decrypt_to_data(encrypted_response)
        
        # 保存 codeKey 用于步骤2
        if isinstance(decrypted, dict):
            # 尝试从多个可能的位置提取 codeKey
            code_key = (
                decrypted.get("codeKey") or 
                decrypted.get("code_key") or
                (decrypted.get("data", {}).get("codeKey") if isinstance(decrypted.get("data"), dict) else None) or
                (decrypted.get("bizrt", {}).get("codeKey") if isinstance(decrypted.get("bizrt"), dict) else None)
            )
            if code_key:
                self._sms_code_key = str(code_key)
                _LOGGER.info("[短信登录] 步骤1: 保存 codeKey: %s", self._sms_code_key[:10] + "..." if len(self._sms_code_key) > 10 else self._sms_code_key)
            else:
                _LOGGER.warning("[短信登录] 步骤1: 未找到 codeKey，响应结构: %s", list(decrypted.keys()))
        
        _LOGGER.info("[短信登录] 步骤1: 验证码发送成功")
        
        return {"success": True, "data": decrypted}

    async def login_with_sms_step2(self, phone: str, code: str) -> dict[str, Any]:
        """验证短信验证码并登录.
        
        Args:
            phone: 手机号码
            code: 短信验证码
            
        Returns:
            {
                "success": True,
                "tokens": {...},
                "user_id": "...",
                ...
            }
        """
        if not self._key_code:
            await self.initialize()
        
        if not self._sms_code_key:
            raise StateGridAuthError("Missing codeKey. Please call login_with_sms_step1 first.")
        
        _LOGGER.info("[短信登录] 步骤2: 验证验证码")
        
        # Step 1: 加密手机号和验证码 (使用 c4f02 加密接口)
        encrypt_payload = {
            "token": self._encrypt_token,
            "machineId": self._machine_id,
            "keyCode": self._key_code,
            "uuid": self._uuid,
            "publicKey": self._public_key,
            "account": phone,
            "code": code,
            "codeKey": self._sms_code_key,
        }
        
        _LOGGER.info("[短信登录] 步骤2: 加密参数 - account=%s, code=%s, codeKey=%s", 
                     phone, code, self._sms_code_key[:10] + "..." if len(self._sms_code_key) > 10 else self._sms_code_key)
        
        encrypt_data = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/c4f02",
            encrypt_payload,
        )
        
        # Step 2: 调用 95598 API 验证短信 (osg-uc0013/member/c4/f02 端点)
        for attempt in range(2):
            headers = self._get_sgcc_headers(str(encrypt_data.get("timestamp", "")))
            payload = {
                "data": encrypt_data.get("data"),
                "skey": encrypt_data.get("skey"),
                "timestamp": encrypt_data.get("timestamp"),
            }
            
            async with self._session.post(
                "https://www.95598.cn/api/osg-uc0013/member/c4/f02",
                json=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
            
            raw_response = self._parse_sgcc_response(text)
            _LOGGER.debug("[短信登录] c4/f02 第%d次响应: %s", attempt + 1, raw_response)
            
            if isinstance(raw_response, dict):
                code = raw_response.get("code")
                if code == "GB010" and attempt == 0:
                    _LOGGER.warning("[短信登录] 验证验证码时检测到 GB010，重新初始化会话...")
                    self._key_code = ""
                    await self.initialize(force_new_uuid=True)
                    
                    # 重新加密 c4f02
                    encrypt_data = await self._secure_post_encrypt(
                        f"{ENCRYPT_API_URL}/encrypt/c4f02",
                        {
                            "token": self._encrypt_token,
                            "keyCode": self._key_code,
                            "uuid": self._uuid,
                            "publicKey": self._public_key,
                            "account": phone,
                            "code": code,
                            "codeKey": self._sms_code_key,
                        },
                    )
                    continue
                
                self._check_and_raise_business_error(raw_response, "c4/f02")

            encrypted_response = self._get_encrypted_data(raw_response) or (
                text.strip() if self._is_likely_encrypted(text) else ""
            )
            if encrypted_response:
                break
            
            if attempt == 1:
                raise StateGridAuthError(f"验证验证码请求异常 (c4/f02)。响应: {str(raw_response)[:200]}")
        
        if not encrypted_response:
            raise StateGridAuthError("验证短信验证码失败：未返回加密数据")
        
        # 解密响应，获取登录信息
        decrypted_login = await self._decrypt_to_data(encrypted_response)
        
        # 提取 token 信息（与密码登录类似）
        bizrt = decrypted_login.get("bizrt") or decrypted_login.get("data") or decrypted_login
        user_token = None
        if isinstance(bizrt, dict):
            user_token = bizrt.get("token") or bizrt.get("rsi")
            user_info = bizrt.get("userInfo")
            if user_token:
                self._user_token = str(user_token)
                self._token = str(user_token)  # 更新 token（bizrt.token）
                _LOGGER.info("[短信登录] 步骤2: 获取到 user_token")
                
                # 从 bizrt 提取 user_id、login_account
                if isinstance(user_info, list) and user_info and isinstance(user_info[0], dict):
                    first_ui = user_info[0]
                    self._user_id = str(first_ui.get("userId", ""))
                    if first_ui.get("loginAccount"):
                        self._login_account = str(first_ui["loginAccount"])
                elif isinstance(user_info, dict) and user_info.get("loginAccount"):
                    self._login_account = str(user_info["loginAccount"])
        
        if not user_token:
            raise StateGridAuthError("短信登录失败：未获取到 token")
        
        # Step 3: 用 user_token 换取 access_token（与密码登录一致）
        _LOGGER.info("[短信登录] 步骤3: 换取 access_token")
        tokens = await self.exchange_user_token_for_access_token(str(user_token))
        
        _LOGGER.info("[短信登录] 步骤2: 登录成功")
        
        return {
            "success": True,
            "tokens": {
                "user_token": self._user_token,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
            },
            "data": decrypted_login,
        }

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

    # @auto_relogin_on_auth_error  # 暂时禁用自动重连，调试用
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
            raise StateGridAuthError("c8/f11 did not return userId")
        
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
            raise StateGridAuthError("c24/f01 did not return decryptable payload")

        decrypted = await self._decrypt_to_data(encrypted_data)
        
        # 提取 count 和 payList
        # 注意：c24f01-payment 返回的数据结构是直接的 {count, payList}，不是嵌套在 data.data 中
        count = 0
        pay_list = []
        if isinstance(decrypted, dict):
            # 直接从 decrypted 中提取
            count = int(decrypted.get("count") or 0)
            pay_list_raw = decrypted.get("payList") or []
            if isinstance(pay_list_raw, list):
                # 提取需要的字段
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

    @staticmethod
    def _sanitize_for_log(obj: Any, _mask_keys: frozenset | None = None) -> Any:
        """Deep copy with token/rsi/accessToken etc masked for debug logging."""
        mask = _mask_keys or frozenset({"token", "rsi", "accessToken", "refreshToken", "access_token", "refresh_token"})
        if isinstance(obj, dict):
            return {k: ("<masked>" if k in mask and v else Shaobor95598ApiClient._sanitize_for_log(v, mask))
                    for k, v in obj.items()}
        if isinstance(obj, list):
            return [Shaobor95598ApiClient._sanitize_for_log(x, mask) for x in obj]
        return obj

    def _find_first_dict_with_keys(self, obj: Any, keys: set[str]) -> dict[str, Any] | None:
        if isinstance(obj, dict):
            if keys.issubset(obj.keys()):
                return obj
            for v in obj.values():
                hit = self._find_first_dict_with_keys(v, keys)
                if hit:
                    return hit
        elif isinstance(obj, list):
            for item in obj:
                hit = self._find_first_dict_with_keys(item, keys)
                if hit:
                    return hit
        return None

    def _collect_base64_strings(self, obj: Any, out: list[tuple[int, str]]) -> None:
        """递归收集 base64 样字符串（长度, 值），用于后备提取验证码图片。"""
        if isinstance(obj, str):
            s = obj.split("base64,", 1)[-1].strip() if "base64," in obj else obj
            if len(s) > 200 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in s[:min(100, len(s))]):
                out.append((len(s), obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                self._collect_base64_strings(v, out)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_base64_strings(item, out)

    def _to_float(self, val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

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
        
        # 标记已完成首次获取
        if is_first_fetch and self._store:
            if stored_data is None:
                stored_data = {}
            stored_data[store_key] = True
            await self._store.async_save(stored_data)
            _LOGGER.info("[c24/f01-daily] 已标记首次获取完成")
        
        return decrypted
    
    async def _save_daily_usage_to_file(self, data: dict[str, Any]) -> None:
        """将每日用电量数据保存到 Store"""
        from datetime import timezone
        
        if not self._hass:
            _LOGGER.warning("[c24/f01-daily] 无法保存数据: hass 实例不可用")
            return
        
        try:
            # 创建历史数据 Store，使用 entry_id 进行隔离
            from homeassistant.helpers.storage import Store  # type: ignore
            storage_key = f"shaobor_electricity/shaobor_history_{self._entry_id}" if self._entry_id else "shaobor_electricity/shaobor_electricity_history"
            history_store = Store(self._hass, version=1, key=storage_key)
            
            # 读取现有数据
            existing_data = await history_store.async_load() or {}
            
            # 解析 sevenEleList 中的每日数据
            seven_ele_list = data.get("sevenEleList", [])
            current_timestamp = datetime.now(timezone.utc).isoformat()
            
            saved_count = 0
            skipped_count = 0
            for day_data in seven_ele_list:
                day_str = day_data.get("day")
                if not day_str or len(day_str) != 8:
                    continue
                
                # 检查是否有有效数据（dayElePq 不为 "-" 或空）
                day_ele_pq = day_data.get("dayElePq")
                if not day_ele_pq or day_ele_pq == "-":
                    skipped_count += 1
                    continue
                
                # 将 YYYYMMDD 格式转换为 YYYY-MM-DD
                try:
                    date_key = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:8]}"
                    
                    # 只保存有数据的记录
                    existing_data[date_key] = {
                        "date": date_key,
                        "timestamp": current_timestamp,
                        "data": {
                            "success": True,
                            "data": {
                                "code": 1,
                                "message": "成功",
                                "data": {
                                    "sevenEleList": [day_data],
                                    "returnCode": "1",
                                    "returnMsg": "成功",
                                    "totalPq": day_data.get("dayElePq", "-")
                                }
                            }
                        }
                    }
                    saved_count += 1
                except Exception as e:
                    _LOGGER.warning(f"[c24/f01-daily] 解析日期失败 {day_str}: {e}")
                    continue
            
            # 保存到 Store
            await history_store.async_save(existing_data)
            _LOGGER.info(f"[c24/f01-daily] 已保存 {saved_count} 天的有效数据，跳过 {skipped_count} 天的空数据")
        except Exception as e:
            _LOGGER.error(f"[c24/f01-daily] 保存数据失败: {e}", exc_info=True)

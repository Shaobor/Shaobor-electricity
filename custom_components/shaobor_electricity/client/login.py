"""Login handlers for State Grid API."""
import logging
import asyncio
import time
import json
import hashlib
import random
from typing import Any, Optional
from urllib.parse import urlencode

from .base import BaseStateGridApi
from .const import ENCRYPT_API_URL, SGCC_HOST, APP_KEY, VERSION
from .exceptions import StateGridAuthError
from .decorators import auto_relogin_on_auth_error, retry_on_network_error

_LOGGER = logging.getLogger(__name__)

class LoginMixin(BaseStateGridApi):
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
        
        # === 两步走登录流程 ===
        
        # 1. 第一步：预校验 (Pre-validation)
        _LOGGER.warning("[登录] 步骤 1/2: 发送预校验请求 (isInit=True)")
        encrypt_lf06_init = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/lf06",
            {
                "token": self._encrypt_token,
                "uuid": self._uuid,
                "machineId": self._machine_id,
                "publicKey": self._public_key,
                "account": username,
                "password": password_md5,
                "isInit": True,
            },
        )

        headers_f06_init = self._get_sgcc_headers(
            str(encrypt_lf06_init.get("timestamp", "")), 
            include_device_token=True
        )
        payload_f06_init = {
            "data": encrypt_lf06_init.get("data"),
            "skey": encrypt_lf06_init.get("skey"),
            "timestamp": encrypt_lf06_init.get("timestamp"),
        }

        current_cookies = ""
        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/open/c44/f06",
            json=payload_f06_init,
            headers=headers_f06_init,
        ) as resp:
            resp.raise_for_status()
            text_f06_init = await resp.text()
            # 捕获 Set-Cookie
            if "Set-Cookie" in resp.headers:
                current_cookies = resp.headers["Set-Cookie"]
                _LOGGER.debug("[登录] 捕获到 Cookie: %s", current_cookies)

        _LOGGER.debug("[登录] 预校验响应: %s", text_f06_init)

        # 2. 中间等待 3 秒 (风控延迟)
        _LOGGER.warning("[登录] 正在等待 3 秒 (模拟滑块风控延迟)...")
        await asyncio.sleep(3.0)

        # 3. 第二步：正式登录 (Final Login)
        _LOGGER.warning("[登录] 步骤 2/2: 发送正式登录请求 (isInit=False)")
        encrypt_lf06_final = await self._secure_post_encrypt(
            f"{ENCRYPT_API_URL}/encrypt/lf06",
            {
                "token": self._encrypt_token,
                "uuid": self._uuid,
                "machineId": self._machine_id,
                "publicKey": self._public_key,
                "account": username,
                "password": password_md5,
                "isInit": False,
            },
        )

        headers_f06_final = self._get_sgcc_headers(
            str(encrypt_lf06_final.get("timestamp", "")), 
            include_device_token=True
        )
        # 必须带上第一步拿到的 Cookie，且只需携带 NAME=VALUE 部分
        if current_cookies:
            cookie_main = current_cookies.split(';', 1)[0]
            headers_f06_final["Cookie"] = cookie_main
            _LOGGER.debug("[登录] 发送 Cookie: %s", cookie_main)

        # 增加 deviceTokenTX 字段 (参考 demo 脚本)
        headers_f06_final["deviceTokenTX"] = "v2:P5eYxFNxHFaOie1b8MaqwOeoTAoUA+Dj5D5sJP4DcqhS1PZGW5AP4Mm76j1QBCXvBu6JzB5QWkT564fZUDHO+6lOvYiHkF1MwU4DD6WPyPfcBKxwLUNLJkoF+93PNbpDnyl16hZ54bWcSLIHwIvo/99Y/ch0kbH310Zm/u3yre5bbozKW8PABmoHiUqSkhTxIuXc65rcQ4Mxn9VsSkaRhSjD3XibgN4psb4NBmmvo9mF+tLvzRnOBSAZ3SmhJcoZ95erwIdv6v25P2SoTxJXpEEk8w=="
        
        payload_f06_final = {
            "data": encrypt_lf06_final.get("data"),
            "skey": encrypt_lf06_final.get("skey"),
            "timestamp": encrypt_lf06_final.get("timestamp"),
        }

        async with self._session.post(
            "https://www.95598.cn/api/osg-web0004/open/c44/f06",
            json=payload_f06_final,
            headers=headers_f06_final,
        ) as resp:
            resp.raise_for_status()
            text_f06 = await resp.text()

        raw_f06 = self._parse_sgcc_response(text_f06)
        _LOGGER.debug("[登录] c44/f06 正式登录响应: %s", raw_f06)
        
        # 检查是否是业务错误
        if isinstance(raw_f06, dict):
            code = raw_f06.get("code")
            if code is not None and str(code) not in ("1", "0", "00", "None"):
                msg = raw_f06.get("message") or raw_f06.get("msg") or f"code={code}"
                raise StateGridAuthError(f"c44/f06 业务异常: {msg}")

        encrypted_f06 = self._get_encrypted_data(raw_f06) or (
            text_f06.strip() if self._is_likely_encrypted(text_f06) else ""
        )
        if not encrypted_f06:
            raise StateGridAuthError(f"c44/f06 响应无法识别加密内容，响应体长: {len(text_f06)}")

        # c44/f06 解密后得到 bizrt.token
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
        
        # 检查是否是业务错误 (如 GB010 认证过期)
        self._check_and_raise_business_error(authorize_raw, "Authorize")
        
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
        
        # 检查是否是业务错误
        self._check_and_raise_business_error(web_token_raw, "getWebToken")
        
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
                _LOGGER.exception("[扫码登录] check_qrcode_status 出现异常: %s", err)
                if "验证失败" in str(err) or "GB010" in str(err):
                    if attempt == 0:
                         _LOGGER.warning("[扫码登录] 检查扫码状态时异常 (%s)，尝试重新初始化...", err)
                         self._key_code = ""
                         await self.initialize(force_new_uuid=True)
                         continue
                return {"status": "ERROR", "message": str(err)}
        
        return {"status": "WAITING"}

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


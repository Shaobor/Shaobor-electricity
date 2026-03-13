"""SMS login handler for Shaobor_95598."""
import logging
from typing import Any

from ..api import Shaobor95598ApiClient, StateGridAuthError

_LOGGER = logging.getLogger(__name__)


class SMSLoginHandler:
    """处理短信登录流程."""

    def __init__(self, api: Shaobor95598ApiClient):
        """初始化短信登录处理器."""
        self._api = api
        self._phone_number: str | None = None

    async def send_code(self, phone_number: str) -> dict[str, Any]:
        """发送短信验证码.
        
        Args:
            phone_number: 手机号码
            
        Returns:
            {"success": True}
        """
        _LOGGER.warning("[短信登录] 步骤1: 发送验证码到 %s", phone_number)
        self._phone_number = phone_number
        
        # 调用 API 发送短信
        await self._api.login_with_sms_step1(phone_number)
        
        _LOGGER.warning("[短信登录] 步骤1: 验证码发送成功")
        return {"success": True}

    async def verify_and_login(self, code: str) -> dict[str, Any]:
        """验证短信验证码并登录.
        
        Args:
            code: 短信验证码
            
        Returns:
            {
                "success": True,
                "tokens": {
                    "user_token": "用户token",
                    "access_token": "访问token",
                    "refresh_token": "刷新token"
                },
                "user_id": "用户ID",
                "power_user_list": "户号列表",
                "login_account": "登录账号"
            }
        """
        if not self._phone_number:
            raise StateGridAuthError("Phone number not set. Call send_code first.")
        
        _LOGGER.warning("[短信登录] 步骤2: 验证验证码, phone=%s, code=%s", self._phone_number, code)
        
        # 调用 API 验证短信
        result = await self._api.login_with_sms_step2(self._phone_number, code)
        
        if not result or not result.get("success"):
            _LOGGER.error("[短信登录] 验证失败: %s", result.get("message") if result else "Unknown error")
            raise StateGridAuthError(f"SMS verification failed: {result.get('message') if result else 'Unknown error'}")
        
        _LOGGER.warning("[短信登录] 步骤2: 验证成功")
        
        # 获取户号列表
        _LOGGER.warning("[短信登录] 步骤3: 获取户号列表")
        power_user_list = await self._api.fetch_power_user_list()
        _LOGGER.warning("[短信登录] 步骤3: 户号列表获取成功, 数量=%s", len(power_user_list or []))
        
        # 验证登录（获取电费数据）
        _LOGGER.warning("[短信登录] 步骤4: 验证登录")
        await self._api.get_electricity_data()
        _LOGGER.warning("[短信登录] 步骤4: 登录验证成功")
        
        tokens = result.get("tokens", {})
        return {
            "success": True,
            "tokens": tokens,
            "user_id": self._api._user_id,
            "power_user_list": power_user_list,
            "login_account": self._api._login_account,
        }

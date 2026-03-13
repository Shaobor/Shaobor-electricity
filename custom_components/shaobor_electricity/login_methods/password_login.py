"""Password login handler for Shaobor_95598."""
import logging
from typing import Any

from ..api import Shaobor95598ApiClient, StateGridAuthError

_LOGGER = logging.getLogger(__name__)


class PasswordLoginHandler:
    """处理密码登录流程."""

    def __init__(self, api: Shaobor95598ApiClient):
        """初始化密码登录处理器."""
        self._api = api

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """使用账号密码登录.
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            {
                "success": True,
                "data": {
                    "token": "bizrt.token",
                    "user_token": "用户token",
                    "user_id": "用户ID",
                    "access_token": "访问token",
                    "refresh_token": "刷新token",
                    "power_user_list": "户号列表",
                    "login_account": "登录账号",
                    "user_info": "用户信息"
                }
            }
        """
        _LOGGER.warning("[密码登录] 步骤1: 开始密码登录, username=%s", username)
        
        # 调用 API 的密码登录方法（包含滑块验证）
        result = await self._api.login_with_password(username, password)
        
        if not isinstance(result, dict):
            _LOGGER.error("[密码登录] 返回了非字典类型: %s (类型: %s)", result, type(result))
            raise StateGridAuthError(f"Unexpected result type: {type(result).__name__}")
        
        if not result.get("success"):
            _LOGGER.error("[密码登录] 登录失败: %s", result.get("message"))
            raise StateGridAuthError(f"Login failed: {result.get('message')}")
        
        _LOGGER.warning("[密码登录] 步骤2: 登录成功")
        
        # 验证登录（获取电费数据）
        _LOGGER.warning("[密码登录] 步骤3: 验证登录")
        await self._api.get_electricity_data()
        _LOGGER.warning("[密码登录] 步骤3: 登录验证成功")
        
        return result

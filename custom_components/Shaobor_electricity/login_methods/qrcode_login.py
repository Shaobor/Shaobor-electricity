"""QR Code login handler for Shaobor_95598."""
import logging
from typing import Any

from ..api import Shaobor95598ApiClient, StateGridAuthError

_LOGGER = logging.getLogger(__name__)


class QRCodeLoginHandler:
    """处理扫码登录流程."""

    def __init__(self, api: Shaobor95598ApiClient):
        """初始化扫码登录处理器."""
        self._api = api
        self._qr_serial: str | None = None
        self._qr_code: str | None = None

    async def get_qrcode(self) -> dict[str, Any]:
        """获取二维码.
        
        Returns:
            {
                "qr_code": "base64 图片数据",
                "serial_no": "二维码序列号"
            }
        """
        _LOGGER.warning("[扫码登录] 步骤1: 获取二维码")
        result = await self._api.get_login_qrcode()
        self._qr_code = result.get("qr_code")
        self._qr_serial = result.get("serial_no")
        _LOGGER.warning("[扫码登录] 步骤1: 二维码获取成功, serial_no=%s", self._qr_serial)
        return result

    async def check_scan_status(self) -> dict[str, Any]:
        """检查二维码扫描状态.
        
        Returns:
            {
                "status": "SUCCESS" | "WAITING" | "ERROR",
                "user_token": "用户token (仅 SUCCESS 时)",
                "bizrt": "业务数据 (仅 SUCCESS 时)",
                "message": "错误信息 (仅 ERROR 时)"
            }
        """
        if not self._qr_serial:
            raise StateGridAuthError("QR serial not initialized")
        
        _LOGGER.warning("[扫码登录] 步骤2: 检查扫码状态, serial_no=%s", self._qr_serial)
        result = await self._api.check_qrcode_status(self._qr_serial)
        _LOGGER.warning("[扫码登录] 步骤2: 状态=%s", result.get("status"))
        return result

    async def complete_login(self, user_token: str, bizrt: dict[str, Any]) -> dict[str, Any]:
        """完成登录流程（扫码成功后）.
        
        Args:
            user_token: c50/f02 返回的 token (bizrt.token)
            bizrt: c50/f02 返回的 bizrt 数据
            
        Returns:
            {
                "user_token": "用户token",
                "user_id": "用户ID",
                "access_token": "访问token",
                "refresh_token": "刷新token",
                "power_user_list": "户号列表",
                "login_account": "登录账号"
            }
        """
        _LOGGER.warning("[扫码登录] 步骤3: 开始完成登录流程")
        _LOGGER.warning("[扫码登录] 步骤3.1: user_token=%s..., bizrt keys=%s",
                       user_token[:20] if user_token else None,
                       list(bizrt.keys()) if isinstance(bizrt, dict) else type(bizrt))
        
        # 步骤3.1: 从 bizrt 中提取 userInfo，设置 user_id 和 login_account
        if isinstance(bizrt, dict):
            user_info = bizrt.get("userInfo")
            _LOGGER.warning("[扫码登录] 步骤3.1: userInfo type=%s", type(user_info))
            
            if isinstance(user_info, list) and user_info and isinstance(user_info[0], dict):
                first_ui = user_info[0]
                self._api._user_id = str(first_ui.get("userId", ""))
                if first_ui.get("loginAccount"):
                    self._api._login_account = str(first_ui["loginAccount"])
                _LOGGER.warning("[扫码登录] 步骤3.1: 从 list 提取: user_id=%s, login_account=%s",
                               self._api._user_id, self._api._login_account)
            elif isinstance(user_info, dict):
                if user_info.get("loginAccount"):
                    self._api._login_account = str(user_info["loginAccount"])
                if user_info.get("userId"):
                    self._api._user_id = str(user_info["userId"])
                _LOGGER.warning("[扫码登录] 步骤3.1: 从 dict 提取: user_id=%s, login_account=%s",
                               self._api._user_id, self._api._login_account)
        
        # 步骤3.2: 设置 user_token（c50/f02 返回的 bizrt.token）
        self._api._user_token = str(user_token)
        self._api._token = str(user_token)
        _LOGGER.warning("[扫码登录] 步骤3.2: 已设置 user_token=%s...", user_token[:20] if user_token else None)
        
        # 步骤3.3: 用 user_token 换取 access_token（调用 authorize + getWebToken）
        _LOGGER.warning("[扫码登录] 步骤3.3: 开始换取 access_token")
        tokens = await self._api.exchange_user_token_for_access_token(str(user_token))
        _LOGGER.warning("[扫码登录] 步骤3.3: 成功获取 access_token=%s...",
                       tokens.get("access_token")[:20] if tokens.get("access_token") else None)
        
        # 验证必要的参数是否已设置
        if not self._api._access_token:
            _LOGGER.error("[扫码登录] 步骤3.3: access_token 未设置")
            raise StateGridAuthError("access_token not set after exchange")
        
        _LOGGER.warning("[扫码登录] 步骤3.3: API 状态检查: user_token=%s..., access_token=%s..., user_id=%s",
                       self._api._user_token[:20] if self._api._user_token else None,
                       self._api._access_token[:20] if self._api._access_token else None,
                       self._api._user_id)
        
        # 步骤3.4: 获取户号列表（需要 access_token）
        _LOGGER.warning("[扫码登录] 步骤3.4: 开始获取户号列表")
        power_user_list = await self._api.fetch_power_user_list()
        _LOGGER.warning("[扫码登录] 步骤3.4: 户号列表获取成功, 数量=%s", len(power_user_list or []))
        
        # 步骤3.5: 验证登录（获取电费数据）
        _LOGGER.warning("[扫码登录] 步骤3.5: 验证登录")
        await self._api.get_electricity_data()
        _LOGGER.warning("[扫码登录] 步骤3.5: 登录验证成功")
        
        return {
            "user_token": str(user_token),
            "user_id": self._api._user_id,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "power_user_list": power_user_list,
            "login_account": self._api._login_account,
        }

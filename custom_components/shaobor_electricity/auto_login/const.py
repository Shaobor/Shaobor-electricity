"""掉线短信自动登录：常量定义。

本模块只服务 auto_login 包，刻意不写进集成公共 const.py，
以降低与其他开发者的改动冲突面。
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Final

# 开关状态存放位置：ConfigEntry.data
# 之所以不放 entry.options：现有选项流每一步收尾都是
# `async_create_entry(title="", data={})`（helpers/options_flow.py），
# HA 会用它整体覆盖 entry.options，导致开关状态被静默清空。
CONF_AUTO_LOGIN: Final = "auto_login"

# 短信接收手机号（留空 = 跟随当前登录账号 entry.data["login_account"]）
CONF_SMS_PHONE: Final = "sms_phone"

# hass.data[DOMAIN][entry_id] 中的管理器键
DATA_AUTO_LOGIN: Final = "auto_login"

# 强制实体 ID 后缀：
#   switch.<户号>_auto_login / text.<户号>_code / button.<户号>_button / text.<户号>_phone
ENTITY_ID_SUFFIX_SWITCH: Final = "auto_login"
ENTITY_ID_SUFFIX_CODE: Final = "code"
ENTITY_ID_SUFFIX_BUTTON: Final = "button"
ENTITY_ID_SUFFIX_PHONE: Final = "phone"

# 实体翻译 key（HA 约定：<domain>__<translation_key>）
TRANSLATION_KEY_SWITCH: Final = "auto_login"
TRANSLATION_KEY_CODE: Final = "sms_code"
TRANSLATION_KEY_BUTTON: Final = "sms_login"
TRANSLATION_KEY_PHONE: Final = "sms_phone"

# 手机号校验：11 位、以 1 开头
PHONE_LENGTH: Final = 11
PHONE_PATTERN: Final = re.compile(r"1\d{10}")

# 节奏与上限
CODE_RESEND_COOLDOWN_SECONDS: Final = 60   # 发码后多久内不重发
CODE_WAIT_TIMEOUT_SECONDS: Final = 300     # 等待用户填码窗口（超时清空输入框）
MAX_CONSECUTIVE_FAILURES: Final = 3        # 连续失败上限，达到后锁定（关→开开关解锁）

# 验证码长度约束（仅用于 HA 文本框校验，真实长度由服务端判定）
CODE_MIN_LENGTH: Final = 4
CODE_MAX_LENGTH: Final = 8

# 数据模式取值（与 coordinator._data_mode 一致）
DATA_MODE_LOCAL_CACHE: Final = "local_cache"

# 离线原因取值（与 coordinator.last_error_reason 一致）
# network_error = 网络/中转后端不可达：此时短信登录同样不可能成功，自动触发直接跳过
ERROR_REASON_NETWORK: Final = "network_error"


class AutoLoginState(str, Enum):
    """自动登录状态机。"""

    DISABLED = "disabled"          # 开关关闭
    IDLE = "idle"                  # 待命（离线时按冷却节奏发码）
    REQUESTING = "requesting"       # 正在下发验证码
    WAITING_CODE = "waiting_code"   # 验证码已下发，等待用户填写
    VERIFYING = "verifying"         # 正在校验验证码
    LOCKED = "locked"              # 连续失败达上限，停止下发（关→开开关解锁）

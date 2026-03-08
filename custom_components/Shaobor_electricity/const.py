"""Constants for the Shaobor_electricity integration."""
from typing import Final

DOMAIN: Final = "Shaobor_electricity"

CONF_AUTH_TOKEN: Final = "auth_token"
CONF_LOGIN_METHOD: Final = "login_method"

# Stored auth/session fields
CONF_USER_TOKEN: Final = "user_token"
CONF_USER_ID: Final = "user_id"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_POWER_USER_LIST: Final = "power_user_list"
CONF_SELECTED_ACCOUNT_INDEX: Final = "selected_account_index"  # 户号选择索引
CONF_LOGIN_ACCOUNT: Final = "login_account"  # loginAccount for c05f01 userName
CONF_USER_INFO: Final = "user_info"  # userInfo from bizrt (Node-RED: 95598_userInfo)

# Login methods
LOGIN_METHOD_PASSWORD: Final = "password"
LOGIN_METHOD_QRCODE: Final = "qrcode"
LOGIN_METHOD_SMS: Final = "sms"

# Config keys for password method
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_AUTO_RELOGIN: Final = "auto_relogin"  # 掉线自动重新登录

# Config keys for sms method
CONF_PHONE_NUMBER: Final = "phone_number"
CONF_SMS_CODE: Final = "sms_code"

# 计费标准选项
BILLING_STANDARD_YEAR_LADDER_TOU: Final = "year_ladder_tou"  # 年阶梯峰平谷计费
BILLING_STANDARD_YEAR_LADDER: Final = "year_ladder"  # 年阶梯计费
BILLING_STANDARD_MONTH_LADDER_TOU_VARIABLE: Final = "month_ladder_tou_variable"  # 月阶梯峰平谷变动价格计费
BILLING_STANDARD_MONTH_LADDER_TOU: Final = "month_ladder_tou"  # 月阶梯峰平谷计费
BILLING_STANDARD_MONTH_LADDER: Final = "month_ladder"  # 月阶梯计费
BILLING_STANDARD_AVERAGE: Final = "average"  # 平均单价计费

# 阶梯价格配置
CONF_LADDER_LEVEL_1: Final = "ladder_level_1"  # 第1档上限
CONF_LADDER_LEVEL_2: Final = "ladder_level_2"  # 第2档上限
CONF_LADDER_PRICE_1: Final = "ladder_price_1"  # 第1档电价
CONF_LADDER_PRICE_2: Final = "ladder_price_2"  # 第2档电价
CONF_LADDER_PRICE_3: Final = "ladder_price_3"  # 第3档电价
CONF_YEAR_LADDER_START: Final = "year_ladder_start"  # 年阶梯起始日期（MMDD格式）

# 峰平谷价格配置
CONF_PRICE_TIP: Final = "price_tip"  # 尖峰电价
CONF_PRICE_PEAK: Final = "price_peak"  # 峰时电价
CONF_PRICE_FLAT: Final = "price_flat"  # 平时电价
CONF_PRICE_VALLEY: Final = "price_valley"  # 谷时电价

# 平均单价
CONF_AVERAGE_PRICE: Final = "average_price"  # 平均电价

# 计费模式配置
CONF_BILLING_MODE: Final = "billing_mode"  # 计费模式

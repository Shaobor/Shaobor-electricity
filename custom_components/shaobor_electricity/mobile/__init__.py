"""手机App（iOS 链路）模块。

与网页版（client/ + login_methods/）平级的独立文件夹：
  client.py     手机源 API 客户端（信封/登录态全部由中转后端持有）
  login_flow.py 手机源登录流程（配置流/选项流共用混入）

宿主（ConfigFlow / OptionsFlowHandler）通过 MobileIosLoginMixin 复用登录步骤，
只需实现 _mobile_auth_token / _mobile_machine_id /
_async_mobile_invalid_token / _async_mobile_login_complete 四个钩子。
"""
from .client import MobileIosApiClient
from .login_flow import MobileIosLoginMixin

__all__ = ["MobileIosApiClient", "MobileIosLoginMixin"]

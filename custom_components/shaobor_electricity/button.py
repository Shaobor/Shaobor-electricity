"""Button platform for shaobor_electricity.

本集成唯一按钮实体：短信登录（button.<户号>_button）。
离线时点击触发一次短信登录，在线点击不触发；实体实现位于 auto_login/entities.py，
此处仅作 HA 平台入口转发。
"""
from __future__ import annotations

from .auto_login import async_setup_button_platform as async_setup_entry

__all__ = ["async_setup_entry"]

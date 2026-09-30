"""Switch platform for shaobor_electricity.

本集成唯一开关实体：掉线自动登录（switch.<户号>_auto_login）。
实体实现位于 auto_login/entities.py，此处仅作 HA 平台入口转发。
"""
from __future__ import annotations

from .auto_login import async_setup_switch_platform as async_setup_entry

__all__ = ["async_setup_entry"]

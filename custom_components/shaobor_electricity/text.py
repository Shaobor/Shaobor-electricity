"""Text platform for shaobor_electricity.

本集成唯一文本实体：短信验证码输入（text.<户号>_code）。
实体实现位于 auto_login/entities.py，此处仅作 HA 平台入口转发。
"""
from __future__ import annotations

from .auto_login import async_setup_text_platform as async_setup_entry

__all__ = ["async_setup_entry"]

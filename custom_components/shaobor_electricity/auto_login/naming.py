"""掉线短信自动登录：实体命名与设备信息。

实体 ID 强制为用户指定格式：<域>.<户号>_<后缀>
  switch.<户号>_auto_login   自动登录开关
  text.<户号>_code           短信验证码输入
户号缺失（首次登录尚未取到）时用 entry_id 兜底，保证实体 ID 稳定、可写自动化。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..const import CONF_POWER_USER_LIST, CONF_SELECTED_ACCOUNT_INDEX, DOMAIN

_LOGGER = logging.getLogger(__name__)

# HA entity_id 只允许 [a-z0-9_]，且须为小写
_UNSAFE_OBJECT_ID = re.compile(r"[^0-9a-z_]")


def resolve_cons_no(entry: Any, coordinator: Any) -> str:
    """取当前所选户号（仅数字部分，与 sensors/base.py 口径一致）。"""
    cons_no = str(getattr(coordinator, "cons_no", "") or "").strip()
    if cons_no:
        return cons_no

    cons_no = str(
        entry.data.get("selected_cons_no") or entry.data.get("cons_no") or ""
    ).strip()
    if cons_no:
        return cons_no

    power_users = entry.data.get(CONF_POWER_USER_LIST) or []
    try:
        index = int(entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0) or 0)
    except (TypeError, ValueError):
        index = 0
    if not power_users:
        return ""
    index = min(max(index, 0), len(power_users) - 1)
    raw = (
        power_users[index].get("consNo_dst")
        or power_users[index].get("consNoDst")
        or power_users[index].get("consNo")
        or ""
    )
    return str(raw).split("-")[0].strip() if raw else ""


def build_object_id(entry: Any, coordinator: Any) -> str:
    """构造 entity_id 的 object_id 部分（<户号>）。"""
    cons_no = resolve_cons_no(entry, coordinator)
    if cons_no:
        cleaned = _UNSAFE_OBJECT_ID.sub("", cons_no.lower())
        if cleaned:
            return cleaned
    # 兜底：户号尚未取到（例如首次登录失败）时用 entry_id 片段，避免实体 ID 漂移
    fallback = f"shaobor_{str(entry.entry_id)[:8]}"
    _LOGGER.warning(
        "[自动登录] 未能确定户号，实体 ID 暂用兜底前缀 %s（取到户号后不会自动改名）",
        fallback,
    )
    return fallback


def build_device_info(entry: Any) -> dict[str, Any]:
    """设备信息：与 sensors/base.py 保持同一设备（identifiers 相同即归组）。"""
    power_users = entry.data.get(CONF_POWER_USER_LIST) or []
    try:
        index = int(entry.data.get(CONF_SELECTED_ACCOUNT_INDEX, 0) or 0)
    except (TypeError, ValueError):
        index = 0
    index = min(index, len(power_users) - 1) if power_users else -1
    cons_no = ""
    if index >= 0:
        user = power_users[index]
        cons_no = str(
            user.get("consNo_dst") or user.get("consNoDst") or user.get("consNo") or ""
        ).split("-")[0].strip()
    device_name = (
        cons_no
        or entry.data.get("username")
        or str(entry.title).replace("Shaobor_95598 ", "").strip("()")
        or "95598"
    )
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": f"电费账户 ({device_name})",
        "manufacturer": "Shaobor",
    }


__all__ = ["resolve_cons_no", "build_object_id", "build_device_info"]

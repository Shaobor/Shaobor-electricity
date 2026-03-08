"""Auth storage with migration support for Shaobor_electricity."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]
from homeassistant.helpers.storage import Store  # type: ignore[import-untyped]

from .api import STORAGE_KEY, STORAGE_VERSION


class AuthStore(Store[dict[str, Any]]):
    """Store with migration from v1 (token only) to v2 (full session)."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Migrate from v1 to v2 format."""
        if old_major_version == 1:
            return {
                "token": old_data.get("token", ""),
                "user_token": old_data.get("user_token", ""),
                "user_id": old_data.get("user_id"),
                "access_token": old_data.get("access_token", ""),
                "refresh_token": old_data.get("refresh_token", ""),
                "power_user_list": old_data.get("power_user_list", []),
                "login_account": old_data.get("login_account", ""),
                "user_info": old_data.get("user_info"),
            }
        raise ValueError(f"Cannot migrate from version {old_major_version}.{old_minor_version}")

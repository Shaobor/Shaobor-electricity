"""API Client for shaobor_electricity."""
import logging
import asyncio
import aiohttp  # type: ignore[import-untyped]
from typing import Any

from .const import STORAGE_KEY, STORAGE_VERSION
from .exceptions import StateGridAuthError, StateGridTokenExpiredError, StateGridConnectionError
from .base import BaseStateGridApi
from .login import LoginMixin
from .usage import UsageMixin

_LOGGER = logging.getLogger(__name__)

# Re-exporting for backward compatibility
__all__ = [
    "Shaobor95598ApiClient",
    "StateGridAuthError",
    "StateGridTokenExpiredError",
    "StateGridConnectionError",
    "STORAGE_KEY",
    "STORAGE_VERSION",
]


class Shaobor95598ApiClient(LoginMixin, UsageMixin):
    """The unified API client combining all functional mixins."""

    def __init__(
        self,
        token: str,
        session: aiohttp.ClientSession,
        store: Any | None = None,
        hass: Any | None = None,
        entry_id: str | None = None,
        machine_id: str | None = None,
    ) -> None:
        """Initialize the unified API client."""
        # Initialize BaseStateGridApi
        super().__init__(token=token, session=session, machine_id=machine_id)
        _LOGGER.info("[API] 创建客户端实例, machine_id=%s", machine_id)
        
        self._store = store
        self._hass = hass
        self._entry_id = entry_id
        
        # State inherited from original api.py
        self._user_token: str | None = None
        self._user_id: str | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._power_user_list: list[dict[str, Any]] | None = None
        self._selected_account_index: int = 0
        self._login_account: str | None = None
        self._sms_code_key: str | None = None
        self._user_info: Any | None = None
        
        # Auth storage callbacks
        self._store_update_callback: Any = None
        self._auto_relogin_enabled: bool = False
        self._username: str | None = None
        self._password: str | None = None
        self._billing_config: dict[str, Any] = {}

    @property
    def user_id(self) -> str | None:
        """Return the user ID."""
        return self._user_id

    @property
    def user_token(self) -> str | None:
        """Return the user token (rsi)."""
        return self._user_token

    def load_auth_state(
        self,
        *,
        user_token: str | None = None,
        user_id: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        power_user_list: Any | None = None,
        selected_account_index: int | None = None,
        login_account: str | None = None,
    ) -> None:
        """Load previously stored auth state."""
        if user_token: self._user_token = user_token
        if user_id: self._user_id = user_id
        if access_token: self._access_token = access_token
        if refresh_token: self._refresh_token = refresh_token
        if isinstance(power_user_list, list): self._power_user_list = power_user_list
        if selected_account_index is not None: self._selected_account_index = selected_account_index
        if login_account: self._login_account = login_account

    def set_auto_relogin_credentials(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        auto_relogin_enabled: bool = False,
        store_update_callback: Any = None,
    ) -> None:
        """Set credentials for auto re-login."""
        self._username = username
        self._password = password
        self._auto_relogin_enabled = auto_relogin_enabled
        self._store_update_callback = store_update_callback

    def set_selected_account(self, index: int) -> None:
        """Set which power user account to fetch data for."""
        self._selected_account_index = index

    def set_billing_config(self, config: dict[str, Any]) -> None:
        """Set billing configuration."""
        self._billing_config = config

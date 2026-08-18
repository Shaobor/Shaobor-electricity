import logging
import asyncio
import aiohttp  # type: ignore[import-untyped]
from typing import Any

from .exceptions import (
    StateGridAuthError,
    StateGridConnectionError,
    StateGridTokenExpiredError,
)

_LOGGER = logging.getLogger(__name__)

def auto_relogin_on_auth_error(func):
    """Decorator to automatically refresh token or re-login when auth fails."""
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except (StateGridAuthError, StateGridTokenExpiredError) as e:
            error_msg = str(e).lower()
            # 明确标记为失效的关键字
            token_expired_keywords = ["token", "unauthorized", "401", "403", "expired", "invalid", "认证失败", "登录失效", "未登录", "请重新登录"]
            is_token_error = any(keyword in error_msg for keyword in token_expired_keywords)
            
            # 如果正在自动登录中又报授权错，说明自动登录失败了，直接抛出
            if hasattr(self, '_auto_relogin_in_progress') and self._auto_relogin_in_progress:
                raise StateGridTokenExpiredError(f"自动登录尝试失败: {e}") from e
            
            if not hasattr(self, '_auto_relogin_retry_count'):
                self._auto_relogin_retry_count = 0
            
            # 如果已经尝试过重连但失败，或者重试次数过多，直接宣告失效
            if self._auto_relogin_retry_count >= 2:
                self._auto_relogin_retry_count = 0
                raise StateGridTokenExpiredError("登录已过期，自动尝试恢复失败，请手动重新登录") from e
            
            # 只有有基础 Token 的情况下才尝试自动恢复
            if is_token_error and self._user_token:
                self._auto_relogin_in_progress = True
                self._auto_relogin_retry_count += 1
                try:
                    _LOGGER.warning("[自动重连] 检测到认证失败，尝试刷新或重新登录 (第%d次): %s", self._auto_relogin_retry_count, str(e))
                    await self.refresh_access_token()
                    # 成功刷新后，重置计数器并重试原函数
                    self._auto_relogin_retry_count = 0
                    return await func(self, *args, **kwargs)
                except Exception as refresh_err:
                    _LOGGER.error("[自动重连] 尝试自动恢复登录状态失败: %s", refresh_err)
                    raise StateGridTokenExpiredError(f"登录失效且自动恢复失败: {refresh_err}") from refresh_err
                finally:
                    self._auto_relogin_in_progress = False
            raise
    return wrapper

def retry_on_network_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry async functions on network errors."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    StateGridConnectionError,
                ) as err:
                    last_err = err
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        _LOGGER.warning(
                            "Network error calling %s: %s. Retrying in %.1fs...",
                            func.__name__, err, wait_time
                        )
                        await asyncio.sleep(wait_time)
            raise StateGridConnectionError(
                f"Network error after {max_retries} attempts: {last_err}"
            ) from last_err
        return wrapper
    return decorator

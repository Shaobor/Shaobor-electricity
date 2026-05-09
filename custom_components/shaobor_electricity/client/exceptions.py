"""Exceptions for the Shaobor 95598 API."""

class StateGridAuthError(Exception):
    """Exception raised for State Grid Auth errors."""
    pass

class StateGridTokenExpiredError(StateGridAuthError):
    """Exception raised when token has expired and needs refresh."""
    pass

class StateGridConnectionError(Exception):
    """Exception raised for network connectivity issues."""
    pass

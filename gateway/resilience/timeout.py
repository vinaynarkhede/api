"""Timeout utilities for async operations."""
import asyncio
from typing import Callable, Any, TypeVar
from functools import wraps

from gateway.config.settings import settings
from shared.exceptions import TimeoutError as GatewayTimeoutError


T = TypeVar('T')


async def with_timeout(
    coro: Callable[..., T],
    timeout_seconds: float = None,
    *args,
    **kwargs
) -> T:
    """
    Execute an async function with a timeout.

    Args:
        coro: Coroutine or async function
        timeout_seconds: Timeout in seconds (uses default if None)
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        GatewayTimeoutError: If operation times out
    """
    timeout = timeout_seconds or settings.proxy_timeout_seconds

    try:
        if asyncio.iscoroutine(coro):
            result = await asyncio.wait_for(coro, timeout=timeout)
        else:
            result = await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout)

        return result

    except asyncio.TimeoutError:
        raise GatewayTimeoutError(
            f"Operation timed out after {timeout} seconds"
        )


def timeout(seconds: float = None):
    """
    Decorator to add timeout to async functions.

    Args:
        seconds: Timeout in seconds (uses default if None)

    Returns:
        Decorated function with timeout

    Example:
        @timeout(30)
        async def slow_operation():
            # Your code here
            pass
    """
    timeout_value = seconds or settings.proxy_timeout_seconds

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_value
                )
            except asyncio.TimeoutError:
                raise GatewayTimeoutError(
                    f"Function '{func.__name__}' timed out after {timeout_value} seconds"
                )

        return wrapper

    return decorator


class TimeoutManager:
    """Manages timeouts for multiple operations."""

    def __init__(self, default_timeout: float = None):
        """
        Initialize timeout manager.

        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout or settings.proxy_timeout_seconds
        self.timeouts: dict[str, float] = {}

    def set_timeout(self, name: str, timeout: float) -> None:
        """
        Set timeout for a named operation.

        Args:
            name: Operation name
            timeout: Timeout in seconds
        """
        self.timeouts[name] = timeout

    def get_timeout(self, name: str) -> float:
        """
        Get timeout for a named operation.

        Args:
            name: Operation name

        Returns:
            Timeout in seconds
        """
        return self.timeouts.get(name, self.default_timeout)

    async def execute_with_timeout(
        self,
        name: str,
        coro: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with configured timeout.

        Args:
            name: Operation name
            coro: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            GatewayTimeoutError: If operation times out
        """
        timeout = self.get_timeout(name)
        return await with_timeout(coro, timeout, *args, **kwargs)


# Global timeout manager
timeout_manager = TimeoutManager()

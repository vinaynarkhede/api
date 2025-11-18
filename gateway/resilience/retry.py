"""Retry logic with exponential backoff."""
import asyncio
from typing import Callable, Any, Type, Tuple
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from gateway.config.settings import settings
from shared.exceptions import UpstreamError, TimeoutError


class RetryPolicy:
    """Retry policy configuration."""

    def __init__(
        self,
        max_attempts: int = None,
        min_wait_seconds: float = 1.0,
        max_wait_seconds: float = 10.0,
        exponential_base: int = 2,
        retry_on_exceptions: Tuple[Type[Exception], ...] = None,
    ):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            min_wait_seconds: Minimum wait time between retries
            max_wait_seconds: Maximum wait time between retries
            exponential_base: Base for exponential backoff
            retry_on_exceptions: Tuple of exception types to retry on
        """
        self.max_attempts = max_attempts or settings.proxy_max_retries
        self.min_wait_seconds = min_wait_seconds
        self.max_wait_seconds = max_wait_seconds
        self.exponential_base = exponential_base
        self.retry_on_exceptions = retry_on_exceptions or (
            UpstreamError,
            TimeoutError,
            ConnectionError,
        )


def with_retry(policy: RetryPolicy = None):
    """
    Decorator to add retry logic to async functions.

    Args:
        policy: RetryPolicy instance (uses default if None)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(RetryPolicy(max_attempts=3))
        async def make_request():
            # Your code here
            pass
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(policy.max_attempts),
            wait=wait_exponential(
                multiplier=policy.min_wait_seconds,
                min=policy.min_wait_seconds,
                max=policy.max_wait_seconds,
                exp_base=policy.exponential_base,
            ),
            retry=retry_if_exception_type(policy.retry_on_exceptions),
            reraise=True,
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Function arguments
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt < max_attempts - 1:
                # Calculate backoff time
                wait_time = min(min_wait * (2 ** attempt), max_wait)
                await asyncio.sleep(wait_time)
            else:
                # Last attempt failed
                raise last_exception

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


# Default retry policy
default_retry_policy = RetryPolicy(
    max_attempts=settings.proxy_max_retries,
    min_wait_seconds=settings.proxy_retry_delay_seconds,
)

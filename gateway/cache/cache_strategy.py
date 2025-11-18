"""Cache strategies and policies."""
from enum import Enum
from typing import Optional
from datetime import datetime


class CacheStrategy(str, Enum):
    """Cache strategy types."""
    NO_CACHE = "no-cache"
    CACHE_FIRST = "cache-first"
    NETWORK_FIRST = "network-first"
    CACHE_ONLY = "cache-only"
    NETWORK_ONLY = "network-only"
    STALE_WHILE_REVALIDATE = "stale-while-revalidate"


class CachePolicy:
    """Cache policy configuration."""

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.CACHE_FIRST,
        ttl: int = 300,
        stale_ttl: Optional[int] = None,
        cache_methods: list = None,
        cache_status_codes: list = None,
    ):
        """
        Initialize cache policy.

        Args:
            strategy: Caching strategy to use
            ttl: Time to live in seconds
            stale_ttl: Stale TTL for stale-while-revalidate strategy
            cache_methods: HTTP methods to cache (default: ["GET", "HEAD"])
            cache_status_codes: Status codes to cache (default: [200, 203, 300, 301])
        """
        self.strategy = strategy
        self.ttl = ttl
        self.stale_ttl = stale_ttl or ttl * 2
        self.cache_methods = cache_methods or ["GET", "HEAD"]
        self.cache_status_codes = cache_status_codes or [200, 203, 300, 301, 304]

    def should_cache_request(self, method: str) -> bool:
        """
        Check if request method should be cached.

        Args:
            method: HTTP method

        Returns:
            True if should cache, False otherwise
        """
        return method.upper() in self.cache_methods

    def should_cache_response(self, status_code: int) -> bool:
        """
        Check if response status code should be cached.

        Args:
            status_code: HTTP status code

        Returns:
            True if should cache, False otherwise
        """
        return status_code in self.cache_status_codes

    def get_cache_control_header(self) -> str:
        """
        Get Cache-Control header value.

        Returns:
            Cache-Control header string
        """
        if self.strategy == CacheStrategy.NO_CACHE:
            return "no-cache, no-store, must-revalidate"
        elif self.strategy == CacheStrategy.CACHE_ONLY:
            return f"max-age={self.ttl}, only-if-cached"
        elif self.strategy == CacheStrategy.NETWORK_ONLY:
            return "no-cache"
        elif self.strategy == CacheStrategy.STALE_WHILE_REVALIDATE:
            return f"max-age={self.ttl}, stale-while-revalidate={self.stale_ttl}"
        else:
            return f"max-age={self.ttl}, public"


# Default cache policy
default_cache_policy = CachePolicy(
    strategy=CacheStrategy.CACHE_FIRST,
    ttl=300,
)

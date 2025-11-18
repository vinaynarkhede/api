"""Rate limiting implementation using Redis."""
from typing import Optional, Tuple
from datetime import datetime
import time
import redis.asyncio as redis

from gateway.config.settings import settings
from shared.exceptions import RateLimitExceeded


class RateLimiter:
    """
    Distributed rate limiter using Redis.

    Implements both Token Bucket and Sliding Window algorithms.
    """

    def __init__(self, algorithm: str = "sliding_window"):
        """
        Initialize rate limiter.

        Args:
            algorithm: "token_bucket" or "sliding_window"
        """
        self.algorithm = algorithm
        self.redis_client: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                settings.redis_connection_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not settings.rate_limit_enabled:
            return True, max_requests, 0

        if self.algorithm == "sliding_window":
            return await self._sliding_window(key, max_requests, window_seconds)
        else:
            return await self._token_bucket(key, max_requests, window_seconds)

    async def _sliding_window(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Sliding window rate limiting algorithm.

        Uses Redis sorted sets to track requests in a time window.
        """
        redis_client = await self.get_redis()
        now = time.time()
        window_start = now - window_seconds

        rate_limit_key = f"rate_limit:sliding:{key}"

        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(rate_limit_key, 0, window_start)

        # Count requests in current window
        pipe.zcard(rate_limit_key)

        # Add current request
        pipe.zadd(rate_limit_key, {str(now): now})

        # Set expiration on the key
        pipe.expire(rate_limit_key, window_seconds)

        results = await pipe.execute()
        request_count = results[1]  # Count after removing old entries

        remaining = max(0, max_requests - request_count - 1)
        is_allowed = request_count < max_requests

        if not is_allowed:
            # Calculate retry after time
            oldest = await redis_client.zrange(rate_limit_key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                retry_after = int(oldest_timestamp + window_seconds - now)
            else:
                retry_after = window_seconds

            raise RateLimitExceeded(
                f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s. "
                f"Retry after {retry_after} seconds."
            )

        return is_allowed, remaining, 0

    async def _token_bucket(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Token bucket rate limiting algorithm.

        Uses Redis to maintain token count and refill rate.
        """
        redis_client = await self.get_redis()
        now = time.time()

        rate_limit_key = f"rate_limit:bucket:{key}"
        last_refill_key = f"rate_limit:bucket:{key}:last_refill"

        # Get current token count and last refill time
        tokens = await redis_client.get(rate_limit_key)
        last_refill = await redis_client.get(last_refill_key)

        tokens = float(tokens) if tokens else max_requests
        last_refill = float(last_refill) if last_refill else now

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        refill_rate = max_requests / window_seconds
        tokens_to_add = time_elapsed * refill_rate

        # Refill tokens (cap at max_requests)
        tokens = min(max_requests, tokens + tokens_to_add)

        if tokens >= 1:
            # Consume one token
            tokens -= 1

            # Update Redis
            pipe = redis_client.pipeline()
            pipe.set(rate_limit_key, tokens, ex=window_seconds * 2)
            pipe.set(last_refill_key, now, ex=window_seconds * 2)
            await pipe.execute()

            remaining = int(tokens)
            return True, remaining, 0
        else:
            # No tokens available
            retry_after = int((1 - tokens) / refill_rate)
            raise RateLimitExceeded(
                f"Rate limit exceeded. Retry after {retry_after} seconds."
            )

    async def reset_rate_limit(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Rate limit key to reset
        """
        redis_client = await self.get_redis()

        if self.algorithm == "sliding_window":
            await redis_client.delete(f"rate_limit:sliding:{key}")
        else:
            await redis_client.delete(f"rate_limit:bucket:{key}")
            await redis_client.delete(f"rate_limit:bucket:{key}:last_refill")

    async def get_rate_limit_info(self, key: str, max_requests: int) -> dict:
        """
        Get current rate limit information.

        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed

        Returns:
            Dict with rate limit information
        """
        redis_client = await self.get_redis()

        if self.algorithm == "sliding_window":
            rate_limit_key = f"rate_limit:sliding:{key}"
            count = await redis_client.zcard(rate_limit_key)
            remaining = max(0, max_requests - count)
        else:
            rate_limit_key = f"rate_limit:bucket:{key}"
            tokens = await redis_client.get(rate_limit_key)
            remaining = int(float(tokens)) if tokens else max_requests

        return {
            "limit": max_requests,
            "remaining": remaining,
            "used": max_requests - remaining,
        }


# Global rate limiter instance
rate_limiter = RateLimiter(algorithm="sliding_window")

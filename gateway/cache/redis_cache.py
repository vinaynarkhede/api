"""Redis-based caching implementation."""
import json
from typing import Optional, Any
import redis.asyncio as redis
from datetime import timedelta

from gateway.config.settings import settings
from shared.utils import calculate_cache_key


class RedisCache:
    """Distributed cache using Redis."""

    def __init__(self):
        """Initialize Redis cache."""
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = settings.cache_ttl_seconds

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

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not settings.cache_enabled:
            return None

        redis_client = await self.get_redis()
        value = await redis_client.get(f"cache:{key}")

        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for default)
        """
        if not settings.cache_enabled:
            return

        redis_client = await self.get_redis()
        ttl = ttl or self.default_ttl

        # Serialize value
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)

        await redis_client.set(f"cache:{key}", serialized, ex=ttl)

    async def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        redis_client = await self.get_redis()
        await redis_client.delete(f"cache:{key}")

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        redis_client = await self.get_redis()
        return bool(await redis_client.exists(f"cache:{key}"))

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        redis_client = await self.get_redis()
        keys = []

        async for key in redis_client.scan_iter(match=f"cache:{pattern}"):
            keys.append(key)

        if keys:
            return await redis_client.delete(*keys)

        return 0

    async def get_response_cache(
        self,
        method: str,
        path: str,
        query_params: dict
    ) -> Optional[dict]:
        """
        Get cached response for a request.

        Args:
            method: HTTP method
            path: Request path
            query_params: Query parameters

        Returns:
            Cached response dict or None
        """
        cache_key = calculate_cache_key(method, path, query_params)
        return await self.get(cache_key)

    async def set_response_cache(
        self,
        method: str,
        path: str,
        query_params: dict,
        response_data: dict,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache a response.

        Args:
            method: HTTP method
            path: Request path
            query_params: Query parameters
            response_data: Response data to cache
            ttl: Time to live in seconds
        """
        cache_key = calculate_cache_key(method, path, query_params)
        await self.set(cache_key, response_data, ttl)

    async def invalidate_route_cache(self, path: str) -> int:
        """
        Invalidate all cached responses for a route.

        Args:
            path: Route path

        Returns:
            Number of cache entries cleared
        """
        # Create pattern from path
        pattern = f"*{path}*"
        return await self.clear_pattern(pattern)

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        redis_client = await self.get_redis()
        info = await redis_client.info("stats")

        return {
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "keys": await redis_client.dbsize(),
        }


# Global cache instance
redis_cache = RedisCache()

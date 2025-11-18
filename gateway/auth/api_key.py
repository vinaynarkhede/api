"""API Key authentication handler."""
from typing import Optional, Dict
from datetime import datetime
import redis.asyncio as redis

from gateway.config.settings import settings
from shared.models import APIKey
from shared.utils import generate_api_key, hash_api_key
from shared.exceptions import AuthenticationError


class APIKeyHandler:
    """Handles API key validation and management."""

    def __init__(self):
        """Initialize API key handler."""
        self.redis_client: Optional[redis.Redis] = None
        self.api_keys_cache: Dict[str, APIKey] = {}

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

    def create_api_key(
        self,
        name: str,
        user_id: int,
        scopes: list = None,
        expires_at: Optional[datetime] = None
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Args:
            name: Name/description for the API key
            user_id: User ID this key belongs to
            scopes: List of permission scopes
            expires_at: Optional expiration date

        Returns:
            Tuple of (raw_key, APIKey object)
        """
        raw_key = generate_api_key()
        hashed_key = hash_api_key(raw_key)

        api_key = APIKey(
            key=hashed_key,
            name=name,
            user_id=user_id,
            scopes=scopes or [],
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True
        )

        return raw_key, api_key

    async def validate_api_key(self, api_key: str) -> APIKey:
        """
        Validate an API key.

        Args:
            api_key: Raw API key string

        Returns:
            APIKey object if valid

        Raises:
            AuthenticationError: If key is invalid or expired
        """
        hashed_key = hash_api_key(api_key)

        # Check cache first
        if hashed_key in self.api_keys_cache:
            cached_key = self.api_keys_cache[hashed_key]
            return self._check_key_validity(cached_key)

        # Check Redis
        redis_client = await self.get_redis()
        key_data = await redis_client.get(f"api_key:{hashed_key}")

        if not key_data:
            raise AuthenticationError("Invalid API key")

        # In a real implementation, you would deserialize from Redis
        # For now, we'll create a mock API key
        # This would typically involve JSON deserialization
        api_key_obj = APIKey(
            key=hashed_key,
            name="Demo Key",
            user_id=1,
            scopes=["read", "write"],
            created_at=datetime.utcnow(),
            is_active=True
        )

        # Cache the key
        self.api_keys_cache[hashed_key] = api_key_obj

        return self._check_key_validity(api_key_obj)

    async def store_api_key(self, api_key: APIKey) -> None:
        """
        Store an API key in Redis.

        Args:
            api_key: APIKey object to store
        """
        redis_client = await self.get_redis()

        # In a real implementation, you would serialize the APIKey object
        # For now, we'll store a simple marker
        await redis_client.set(
            f"api_key:{api_key.key}",
            "valid",  # In production, store serialized APIKey
            ex=86400 * 30  # 30 days expiration
        )

        # Update cache
        self.api_keys_cache[api_key.key] = api_key

    async def revoke_api_key(self, api_key: str) -> None:
        """
        Revoke an API key.

        Args:
            api_key: Raw API key to revoke
        """
        hashed_key = hash_api_key(api_key)
        redis_client = await self.get_redis()

        await redis_client.delete(f"api_key:{hashed_key}")

        if hashed_key in self.api_keys_cache:
            del self.api_keys_cache[hashed_key]

    def _check_key_validity(self, api_key: APIKey) -> APIKey:
        """
        Check if an API key is still valid.

        Args:
            api_key: APIKey object to check

        Returns:
            APIKey if valid

        Raises:
            AuthenticationError: If key is inactive or expired
        """
        if not api_key.is_active:
            raise AuthenticationError("API key is inactive")

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise AuthenticationError("API key has expired")

        return api_key


# Global API key handler instance
api_key_handler = APIKeyHandler()

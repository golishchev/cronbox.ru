import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings


class RedisClient:
    """Redis client wrapper for async operations."""

    def __init__(self):
        self._client: Redis | None = None

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client is not initialized")
        return self._client

    async def get(self, key: str) -> str | None:
        """Get a value from Redis."""
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        """Set a value in Redis with optional expiration."""
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete a key from Redis.

        Returns:
            Number of keys deleted (0 or 1).
        """
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return bool(await self.client.exists(key))

    async def incr(self, key: str) -> int:
        """Increment a counter in Redis."""
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        """Set expiration on a key."""
        await self.client.expire(key, seconds)


redis_client = RedisClient()


async def get_redis() -> Redis:
    """Get Redis client instance."""
    return redis_client.client

"""Tests for Redis cache invalidation."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.billing import PLANS_CACHE_KEY, BillingService


class TestRedisCacheInvalidation:
    """Test Redis cache invalidation for plans."""

    @pytest.mark.asyncio
    async def test_invalidate_plans_cache_success(self):
        """Test successful cache invalidation."""
        billing = BillingService()

        with patch("app.services.billing.redis_client") as mock_redis:
            # Mock successful deletion (1 key deleted)
            mock_redis.delete = AsyncMock(return_value=1)

            result = await billing.invalidate_plans_cache()

            assert result is True
            mock_redis.delete.assert_called_once_with(PLANS_CACHE_KEY)

    @pytest.mark.asyncio
    async def test_invalidate_plans_cache_key_not_exists(self):
        """Test cache invalidation when key doesn't exist."""
        billing = BillingService()

        with patch("app.services.billing.redis_client") as mock_redis:
            # Mock deletion when key doesn't exist (0 keys deleted)
            mock_redis.delete = AsyncMock(return_value=0)

            result = await billing.invalidate_plans_cache()

            assert result is True
            mock_redis.delete.assert_called_once_with(PLANS_CACHE_KEY)

    @pytest.mark.asyncio
    async def test_invalidate_plans_cache_redis_error(self):
        """Test cache invalidation handles Redis errors gracefully."""
        billing = BillingService()

        with patch("app.services.billing.redis_client") as mock_redis:
            # Mock Redis error
            mock_redis.delete = AsyncMock(side_effect=Exception("Redis connection failed"))

            result = await billing.invalidate_plans_cache()

            # Should return False but not raise exception (best-effort)
            assert result is False
            mock_redis.delete.assert_called_once_with(PLANS_CACHE_KEY)

    @pytest.mark.asyncio
    async def test_redis_delete_returns_count(self):
        """Test that redis_client.delete() returns count of deleted keys."""
        from unittest.mock import AsyncMock

        from app.core.redis import redis_client

        # Mock the underlying Redis client
        with patch.object(redis_client, "_client") as mock_client:
            mock_client.delete = AsyncMock(return_value=1)

            result = await redis_client.delete("test_key")

            assert result == 1
            assert isinstance(result, int)

"""Tests for rate limiter module."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, status

from app.core.rate_limiter import (
    RateLimitExceeded,
    RateLimiter,
    free_limiter,
    pro_limiter,
    enterprise_limiter,
    get_limiter_for_plan,
    RateLimitMiddleware,
)


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_exception_attributes(self):
        """Test exception has correct attributes."""
        exc = RateLimitExceeded(retry_after=60)

        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.retry_after == 60
        assert "detail" in dir(exc)
        assert exc.detail["error"] == "rate_limit_exceeded"
        assert exc.detail["retry_after"] == 60


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init_default_values(self):
        """Test default initialization."""
        limiter = RateLimiter()

        assert limiter.requests_per_minute == 100
        assert limiter.key_prefix == "ratelimit"
        assert limiter.window_seconds == 60

    def test_init_custom_values(self):
        """Test custom initialization."""
        limiter = RateLimiter(
            requests_per_minute=50,
            key_prefix="custom",
        )

        assert limiter.requests_per_minute == 50
        assert limiter.key_prefix == "custom"

    def test_get_key_format(self):
        """Test key generation format."""
        limiter = RateLimiter(key_prefix="test")

        with patch("app.core.rate_limiter.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 15, 10, 30)
            key = limiter._get_key("user123")

            assert key == "test:user123:202401151030"

    @pytest.mark.asyncio
    async def test_is_allowed_first_request(self):
        """Test first request is always allowed."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch("app.core.rate_limiter.redis_client") as mock_redis:
            mock_redis.incr = AsyncMock(return_value=1)
            mock_redis.expire = AsyncMock()

            is_allowed, count, remaining = await limiter.is_allowed("user1")

            assert is_allowed is True
            assert count == 1
            assert remaining == 9
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self):
        """Test request under limit is allowed."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch("app.core.rate_limiter.redis_client") as mock_redis:
            mock_redis.incr = AsyncMock(return_value=5)

            is_allowed, count, remaining = await limiter.is_allowed("user1")

            assert is_allowed is True
            assert count == 5
            assert remaining == 5

    @pytest.mark.asyncio
    async def test_is_allowed_at_limit(self):
        """Test request at limit is still allowed."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch("app.core.rate_limiter.redis_client") as mock_redis:
            mock_redis.incr = AsyncMock(return_value=10)

            is_allowed, count, remaining = await limiter.is_allowed("user1")

            assert is_allowed is True
            assert count == 10
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(self):
        """Test request over limit is blocked."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch("app.core.rate_limiter.redis_client") as mock_redis:
            mock_redis.incr = AsyncMock(return_value=11)

            is_allowed, count, remaining = await limiter.is_allowed("user1")

            assert is_allowed is False
            assert count == 11
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_is_allowed_redis_failure(self):
        """Test fail-open when Redis fails."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch("app.core.rate_limiter.redis_client") as mock_redis:
            mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

            is_allowed, count, remaining = await limiter.is_allowed("user1")

            # Should fail open
            assert is_allowed is True
            assert count == 0
            assert remaining == 10

    @pytest.mark.asyncio
    async def test_check_raises_on_limit_exceeded(self):
        """Test check method raises exception when limit exceeded."""
        limiter = RateLimiter(requests_per_minute=10)

        with patch.object(limiter, "is_allowed", return_value=(False, 11, 0)):
            with pytest.raises(RateLimitExceeded) as exc:
                await limiter.check("user1")

            assert exc.value.retry_after == 60


class TestDefaultLimiters:
    """Tests for default limiter instances."""

    def test_free_limiter(self):
        """Test free tier limiter configuration."""
        assert free_limiter.requests_per_minute == 100
        assert "free" in free_limiter.key_prefix

    def test_pro_limiter(self):
        """Test pro tier limiter configuration."""
        assert pro_limiter.requests_per_minute == 500
        assert "pro" in pro_limiter.key_prefix

    def test_enterprise_limiter(self):
        """Test enterprise tier limiter configuration."""
        assert enterprise_limiter.requests_per_minute == 2000
        assert "enterprise" in enterprise_limiter.key_prefix


class TestGetLimiterForPlan:
    """Tests for get_limiter_for_plan function."""

    def test_get_free_limiter(self):
        """Test getting free tier limiter."""
        limiter = get_limiter_for_plan("free")
        assert limiter is free_limiter

    def test_get_pro_limiter(self):
        """Test getting pro tier limiter."""
        limiter = get_limiter_for_plan("pro")
        assert limiter is pro_limiter

    def test_get_enterprise_limiter(self):
        """Test getting enterprise tier limiter."""
        limiter = get_limiter_for_plan("enterprise")
        assert limiter is enterprise_limiter

    def test_unknown_plan_gets_free_limiter(self):
        """Test unknown plan defaults to free limiter."""
        limiter = get_limiter_for_plan("unknown")
        assert limiter is free_limiter


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware class."""

    def test_excluded_paths(self):
        """Test excluded paths are defined."""
        assert "/" in RateLimitMiddleware.EXCLUDED_PATHS
        assert "/health" in RateLimitMiddleware.EXCLUDED_PATHS

    def test_init(self):
        """Test middleware initialization."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, default_requests_per_minute=50)

        assert middleware.default_limiter.requests_per_minute == 50

    def test_get_ip_identifier_direct(self):
        """Test IP identifier from direct connection."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client.host = "192.0.2.1"

        identifier = middleware._get_ip_identifier(mock_request)

        assert identifier == "ip:192.0.2.1"

    def test_get_ip_identifier_forwarded(self):
        """Test IP identifier from X-Forwarded-For header."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        mock_request.client.host = "10.0.0.1"

        identifier = middleware._get_ip_identifier(mock_request)

        # Should use first IP from X-Forwarded-For
        assert identifier == "ip:203.0.113.1"

    def test_get_identifier_with_bearer_token(self):
        """Test identifier with Bearer token."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer some-jwt-token"}
        mock_request.client.host = "192.0.2.1"

        identifier = middleware._get_identifier(mock_request)

        # Should be token-based
        assert identifier.startswith("token:")

    def test_get_identifier_without_auth(self):
        """Test identifier without auth falls back to IP."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client.host = "192.0.2.1"

        identifier = middleware._get_identifier(mock_request)

        assert identifier == "ip:192.0.2.1"

    def test_get_auth_limiter_for_login(self):
        """Test auth limiter is returned for login path."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        limiter = middleware._get_auth_limiter("/v1/auth/login")

        assert limiter is not None

    def test_get_auth_limiter_for_register(self):
        """Test auth limiter is returned for register path."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        limiter = middleware._get_auth_limiter("/v1/auth/register")

        assert limiter is not None

    def test_get_auth_limiter_for_non_auth_path(self):
        """Test None returned for non-auth paths."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        limiter = middleware._get_auth_limiter("/v1/tasks")

        assert limiter is None

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self):
        """Test excluded paths bypass rate limiting."""
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health"

        mock_call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)

"""Rate limiting middleware using Redis."""

from datetime import datetime
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.redis import redis_client


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after,
            },
        )
        self.retry_after = retry_after


class RateLimiter:
    """Rate limiter using Redis sliding window counter."""

    def __init__(
        self,
        requests_per_minute: int = 100,
        key_prefix: str = "ratelimit",
    ):
        self.requests_per_minute = requests_per_minute
        self.key_prefix = key_prefix
        self.window_seconds = 60

    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for rate limiting."""
        minute = datetime.utcnow().strftime("%Y%m%d%H%M")
        return f"{self.key_prefix}:{identifier}:{minute}"

    async def is_allowed(self, identifier: str) -> tuple[bool, int, int]:
        """
        Check if request is allowed.

        Returns:
            tuple of (is_allowed, current_count, remaining)
        """
        key = self._get_key(identifier)

        try:
            # Increment counter
            count = await redis_client.incr(key)

            # Set expiration on first request
            if count == 1:
                await redis_client.expire(key, self.window_seconds)

            remaining = max(0, self.requests_per_minute - count)
            is_allowed = count <= self.requests_per_minute

            return is_allowed, count, remaining

        except Exception:
            # If Redis fails, allow the request (fail open)
            return True, 0, self.requests_per_minute

    async def check(self, identifier: str) -> None:
        """Check rate limit and raise exception if exceeded."""
        allowed, _, _ = await self.is_allowed(identifier)
        if not allowed:
            raise RateLimitExceeded(retry_after=self.window_seconds)


# Default rate limiters for different tiers
free_limiter = RateLimiter(requests_per_minute=100, key_prefix="ratelimit:free")
pro_limiter = RateLimiter(requests_per_minute=500, key_prefix="ratelimit:pro")
enterprise_limiter = RateLimiter(requests_per_minute=2000, key_prefix="ratelimit:enterprise")


def get_limiter_for_plan(plan_name: str) -> RateLimiter:
    """Get rate limiter based on subscription plan."""
    if plan_name == "enterprise":
        return enterprise_limiter
    elif plan_name == "pro":
        return pro_limiter
    else:
        return free_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""

    # Paths that should not be rate limited
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        # Note: webhook paths now have their own IP-based protection
    }

    # Auth endpoints with stricter rate limits (path prefix -> requests per minute)
    AUTH_RATE_LIMITS: dict[str, int] = {}

    # Public endpoints with stricter rate limits (to prevent DDoS on landing page APIs)
    PUBLIC_ENDPOINTS: set[str] = {
        "/v1/billing/plans",
    }

    def __init__(self, app, default_requests_per_minute: int = 100):
        super().__init__(app)
        self.default_limiter = RateLimiter(
            requests_per_minute=default_requests_per_minute
        )
        # Cache allowed origins for CORS
        self.allowed_origins = set(settings.cors_origins)

        # Initialize auth-specific rate limiters from settings
        self.AUTH_RATE_LIMITS = {
            "/v1/auth/login": settings.auth_rate_limit_login,
            "/v1/auth/register": settings.auth_rate_limit_register,
            "/v1/auth/forgot-password": settings.auth_rate_limit_password_reset,
            "/v1/auth/reset-password": settings.auth_rate_limit_password_reset,
            "/v1/auth/send-verification": settings.auth_rate_limit_send_verification,
        }

        # Create rate limiters for auth endpoints
        self.auth_limiters: dict[str, RateLimiter] = {}
        for path, limit in self.AUTH_RATE_LIMITS.items():
            self.auth_limiters[path] = RateLimiter(
                requests_per_minute=limit,
                key_prefix=f"ratelimit:auth:{path.replace('/', '_')}"
            )

        # Rate limiter for public endpoints (stricter than default)
        self.public_limiter = RateLimiter(
            requests_per_minute=settings.public_rate_limit,
            key_prefix="ratelimit:public"
        )

    def _get_auth_limiter(self, path: str) -> RateLimiter | None:
        """Get rate limiter for auth endpoint if applicable."""
        for auth_path, limiter in self.auth_limiters.items():
            if path.startswith(auth_path):
                return limiter
        return None

    def _create_rate_limit_response(
        self,
        request: Request,
        limiter: RateLimiter,
        message: str = "Too many requests. Please try again later.",
    ) -> JSONResponse:
        """Create 429 response with CORS headers."""
        headers = {
            "Retry-After": "60",
            "X-RateLimit-Limit": str(limiter.requests_per_minute),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(60),
        }

        # Add CORS headers if origin is allowed
        origin = request.headers.get("Origin")
        if origin and origin in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Expose-Headers"] = (
                "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            )

        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": message,
                "retry_after": 60,
            },
            headers=headers,
        )

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Get client identifier (IP address for auth, token hash for authenticated)
        identifier = self._get_identifier(request)
        path = request.url.path

        # Check for auth-specific rate limiting (stricter limits)
        auth_limiter = self._get_auth_limiter(path)
        if auth_limiter:
            # For auth endpoints, always use IP-based limiting
            ip_identifier = self._get_ip_identifier(request)
            try:
                is_allowed, count, remaining = await auth_limiter.is_allowed(
                    ip_identifier
                )
                if not is_allowed:
                    return self._create_rate_limit_response(
                        request,
                        auth_limiter,
                        "Too many attempts. Please try again later.",
                    )
            except Exception:
                pass  # Continue with default rate limiting

        # Check for public endpoint rate limiting (stricter than default, IP-based)
        if path in self.PUBLIC_ENDPOINTS:
            ip_identifier = self._get_ip_identifier(request)
            try:
                is_allowed, count, remaining = await self.public_limiter.is_allowed(
                    ip_identifier
                )
                if not is_allowed:
                    return self._create_rate_limit_response(
                        request, self.public_limiter
                    )
            except Exception:
                pass  # Continue with default rate limiting

        # Check default rate limit
        try:
            is_allowed, count, remaining = await self.default_limiter.is_allowed(
                identifier
            )
        except Exception:
            # If rate limiting fails, allow the request
            return await call_next(request)

        if not is_allowed:
            return self._create_rate_limit_response(request, self.default_limiter)

        # Process request and add rate limit headers
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(
            self.default_limiter.requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(60)

        return response

    def _get_ip_identifier(self, request: Request) -> str:
        """Get IP-based identifier for rate limiting."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use token hash as identifier (more granular than IP)
            import hashlib

            token = auth_header[7:]
            return f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        return self._get_ip_identifier(request)


# Dependency for per-endpoint rate limiting
async def rate_limit_check(
    request: Request,
    identifier: str | None = None,
    plan: str = "free",
) -> None:
    """
    Rate limit check dependency.

    Usage:
        @router.get("/endpoint")
        async def endpoint(
            _: None = Depends(lambda r: rate_limit_check(r, plan="pro"))
        ):
            ...
    """
    if identifier is None:
        # Get from request
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            identifier = forwarded.split(",")[0].strip()
        else:
            identifier = request.client.host if request.client else "unknown"

    limiter = get_limiter_for_plan(plan)
    is_allowed, _, _ = await limiter.is_allowed(identifier)

    if not is_allowed:
        raise RateLimitExceeded(retry_after=60)

"""Security headers middleware.

This module provides HTTP security headers to protect against common web vulnerabilities.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy (for API responses)
    """

    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year
        include_subdomains: bool = True,
        frame_options: str = "DENY",
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.include_subdomains = include_subdomains
        self.frame_options = frame_options

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HTTP Strict Transport Security
        # Forces browsers to use HTTPS for future requests
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.include_subdomains:
            hsts_value += "; includeSubDomains"
        response.headers["Strict-Transport-Security"] = hsts_value

        # Prevent MIME type sniffing
        # Stops browsers from trying to guess content types
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking protection
        # Prevents the page from being embedded in iframes
        response.headers["X-Frame-Options"] = self.frame_options

        # XSS filter (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        # Controls how much referrer information is sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        # Restricts access to browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Content-Security-Policy for API responses
        # This is a restrictive policy suitable for JSON APIs
        # Frontend should have its own CSP configured in nginx/CDN
        if self._is_api_response(response):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'none'"
            )

        # Prevent caching of sensitive responses
        if self._is_sensitive_endpoint(request):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    def _is_api_response(self, response: Response) -> bool:
        """Check if the response is a JSON API response."""
        content_type = response.headers.get("content-type", "")
        return "application/json" in content_type

    def _is_sensitive_endpoint(self, request: Request) -> bool:
        """Check if the request is to a sensitive endpoint that shouldn't be cached."""
        sensitive_paths = {
            "/v1/auth/",
            "/v1/users/me",
            "/v1/billing/",
            "/v1/workers/",
        }
        path = request.url.path
        return any(path.startswith(p) for p in sensitive_paths)

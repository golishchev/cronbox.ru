"""URL validation for SSRF protection.

This module provides utilities to validate URLs before making HTTP requests,
preventing Server-Side Request Forgery (SSRF) attacks.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()

# Blocked hostnames that could be used for SSRF
BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    # Common internal service names
    "redis",
    "postgres",
    "postgresql",
    "mysql",
    "mongodb",
    "mongo",
    "db",
    "database",
    "memcached",
    "elasticsearch",
    "rabbitmq",
    "kafka",
    "zookeeper",
    # Kubernetes internal
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
    # Docker internal
    "host.docker.internal",
    "gateway.docker.internal",
})

# Private and reserved IP ranges (RFC 1918, RFC 5737, etc.)
BLOCKED_IP_NETWORKS = [
    # Private networks
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # Loopback
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    # Link-local
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
    # Cloud metadata endpoints
    ipaddress.ip_network("169.254.169.254/32"),  # AWS, GCP, Azure metadata
    # Documentation/test networks
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    # Broadcast
    ipaddress.ip_network("255.255.255.255/32"),
    # Multicast
    ipaddress.ip_network("224.0.0.0/4"),
    # Reserved
    ipaddress.ip_network("0.0.0.0/8"),
]


class SSRFError(Exception):
    """Exception raised when URL fails SSRF validation."""

    def __init__(self, message: str, url: str):
        self.message = message
        self.url = url
        super().__init__(f"SSRF validation failed for URL: {message}")


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is in a blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve hostname to IP addresses."""
    try:
        # Get all IP addresses for the hostname
        result = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return list(set(addr[4][0] for addr in result))
    except socket.gaierror:
        return []


def validate_url_for_ssrf(url: str, allow_private: bool = False) -> None:
    """
    Validate a URL to prevent SSRF attacks.

    Args:
        url: The URL to validate
        allow_private: If True, allow private IP ranges (for testing only)

    Raises:
        SSRFError: If the URL fails validation
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFError(f"Invalid URL format: {e}", url)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Invalid scheme: {parsed.scheme}. Only http and https are allowed.", url)

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("Missing hostname", url)

    # Normalize hostname
    hostname_lower = hostname.lower()

    # Check against blocked hostnames
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise SSRFError(f"Blocked hostname: {hostname}", url)

    # Check for blocked hostname patterns
    if hostname_lower.endswith(".internal") or hostname_lower.endswith(".local"):
        raise SSRFError(f"Blocked hostname pattern: {hostname}", url)

    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if not allow_private and _is_ip_blocked(str(ip)):
            raise SSRFError(f"Blocked IP address: {ip}", url)
        return  # IP address is valid
    except ValueError:
        pass  # Not an IP address, continue with DNS resolution

    # Resolve hostname and check all IPs
    if not allow_private:
        resolved_ips = _resolve_hostname(hostname)

        if not resolved_ips:
            # DNS resolution failed - this could be intentional to avoid check
            # We allow it but log a warning
            logger.warning(
                "DNS resolution failed for URL",
                hostname=hostname,
                url_scheme=parsed.scheme,
            )
            return

        for ip_str in resolved_ips:
            if _is_ip_blocked(ip_str):
                raise SSRFError(
                    f"Hostname {hostname} resolves to blocked IP: {ip_str}",
                    url
                )


def is_url_safe(url: str, allow_private: bool = False) -> tuple[bool, str | None]:
    """
    Check if a URL is safe for making requests.

    Args:
        url: The URL to check
        allow_private: If True, allow private IP ranges

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        validate_url_for_ssrf(url, allow_private=allow_private)
        return True, None
    except SSRFError as e:
        return False, e.message
    except Exception as e:
        return False, str(e)


def sanitize_url_for_logging(url: str) -> str:
    """
    Remove credentials from URL for safe logging.

    Args:
        url: The URL to sanitize

    Returns:
        URL with credentials removed
    """
    try:
        parsed = urlparse(url)

        # If there are credentials, remove them
        if parsed.username or parsed.password:
            # Reconstruct netloc without credentials
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"

            # Reconstruct URL
            return parsed._replace(netloc=netloc).geturl()

        return url
    except Exception:
        # If parsing fails, return a placeholder
        return "<invalid-url>"


def sanitize_headers_for_logging(headers: dict[str, str] | None) -> dict[str, str]:
    """
    Remove sensitive values from headers for safe logging.

    Args:
        headers: The headers dict to sanitize

    Returns:
        Headers with sensitive values redacted
    """
    if not headers:
        return {}

    sensitive_keys = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "api-key",
        "apikey",
        "secret",
        "token",
        "password",
        "x-worker-key",
        "cookie",
        "set-cookie",
        "x-csrf-token",
        "x-xsrf-token",
    }

    return {
        k: "***REDACTED***" if k.lower() in sensitive_keys else v
        for k, v in headers.items()
    }

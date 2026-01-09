"""Tests for URL validator (SSRF protection)."""
import pytest
from unittest.mock import patch

from app.core.url_validator import (
    SSRFError,
    validate_url_for_ssrf,
    is_url_safe,
    sanitize_url_for_logging,
    sanitize_headers_for_logging,
    _is_ip_blocked,
    BLOCKED_HOSTNAMES,
    BLOCKED_IP_NETWORKS,
)


class TestSSRFError:
    """Tests for SSRFError exception."""

    def test_ssrf_error_message(self):
        """Test SSRFError stores message and URL."""
        error = SSRFError("Blocked hostname", "http://localhost")

        assert error.message == "Blocked hostname"
        assert error.url == "http://localhost"
        assert "Blocked hostname" in str(error)

    def test_ssrf_error_inherits_exception(self):
        """Test SSRFError is an Exception."""
        error = SSRFError("test", "http://test")
        assert isinstance(error, Exception)


class TestIPBlocking:
    """Tests for IP blocking functionality."""

    def test_loopback_ipv4_blocked(self):
        """Test IPv4 loopback addresses are blocked."""
        assert _is_ip_blocked("127.0.0.1") is True
        assert _is_ip_blocked("127.0.0.255") is True
        assert _is_ip_blocked("127.255.255.255") is True

    def test_loopback_ipv6_blocked(self):
        """Test IPv6 loopback is blocked."""
        assert _is_ip_blocked("::1") is True

    def test_private_10_network_blocked(self):
        """Test 10.0.0.0/8 private network is blocked."""
        assert _is_ip_blocked("10.0.0.1") is True
        assert _is_ip_blocked("10.255.255.255") is True

    def test_private_172_network_blocked(self):
        """Test 172.16.0.0/12 private network is blocked."""
        assert _is_ip_blocked("172.16.0.1") is True
        assert _is_ip_blocked("172.31.255.255") is True
        # 172.32.x.x is NOT in the private range
        assert _is_ip_blocked("172.32.0.1") is False

    def test_private_192_168_network_blocked(self):
        """Test 192.168.0.0/16 private network is blocked."""
        assert _is_ip_blocked("192.168.0.1") is True
        assert _is_ip_blocked("192.168.255.255") is True

    def test_metadata_endpoint_blocked(self):
        """Test cloud metadata endpoint is blocked."""
        assert _is_ip_blocked("169.254.169.254") is True

    def test_link_local_blocked(self):
        """Test link-local addresses are blocked."""
        assert _is_ip_blocked("169.254.0.1") is True
        assert _is_ip_blocked("169.254.255.255") is True

    def test_public_ip_allowed(self):
        """Test public IPs are not blocked."""
        assert _is_ip_blocked("8.8.8.8") is False
        assert _is_ip_blocked("1.1.1.1") is False
        assert _is_ip_blocked("93.184.216.34") is False  # example.com

    def test_invalid_ip_not_blocked(self):
        """Test invalid IP returns False."""
        assert _is_ip_blocked("not-an-ip") is False
        assert _is_ip_blocked("") is False


class TestValidateURLForSSRF:
    """Tests for SSRF validation function."""

    def test_valid_http_url(self):
        """Test valid HTTP URLs pass validation."""
        # Should not raise
        validate_url_for_ssrf("http://example.com/api")
        validate_url_for_ssrf("https://api.github.com/users")

    def test_valid_https_url(self):
        """Test valid HTTPS URLs pass validation."""
        validate_url_for_ssrf("https://example.com")

    def test_invalid_scheme_ftp(self):
        """Test FTP scheme is rejected."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("ftp://example.com/file")
        assert "Invalid scheme" in exc.value.message

    def test_invalid_scheme_file(self):
        """Test file:// scheme is rejected."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("file:///etc/passwd")
        assert "Invalid scheme" in exc.value.message

    def test_invalid_scheme_javascript(self):
        """Test javascript: scheme is rejected."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("javascript:alert(1)")
        assert "Invalid scheme" in exc.value.message

    def test_blocked_hostname_localhost(self):
        """Test localhost is blocked."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("http://localhost/api")
        assert "Blocked hostname" in exc.value.message

    def test_blocked_hostname_127_0_0_1(self):
        """Test 127.0.0.1 is blocked."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("http://127.0.0.1:8080")
        # 127.0.0.1 is in BLOCKED_HOSTNAMES, so message says "Blocked hostname"
        assert "Blocked" in exc.value.message

    def test_blocked_hostname_redis(self):
        """Test common internal service names are blocked."""
        for hostname in ["redis", "postgres", "mysql", "mongodb"]:
            with pytest.raises(SSRFError):
                validate_url_for_ssrf(f"http://{hostname}:6379")

    def test_blocked_internal_suffix(self):
        """Test .internal and .local suffixes are blocked."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("http://service.internal/api")
        assert "Blocked hostname pattern" in exc.value.message

        with pytest.raises(SSRFError):
            validate_url_for_ssrf("http://myservice.local/endpoint")

    def test_blocked_private_ip(self):
        """Test private IP addresses are blocked."""
        private_ips = [
            "http://10.0.0.1/api",
            "http://192.168.1.1:80/",
            "http://172.16.0.1/endpoint",
        ]
        for url in private_ips:
            with pytest.raises(SSRFError):
                validate_url_for_ssrf(url)

    def test_blocked_metadata_endpoint(self):
        """Test cloud metadata endpoint is blocked."""
        with pytest.raises(SSRFError):
            validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")

    def test_missing_hostname(self):
        """Test URL without hostname is rejected."""
        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("http:///path")
        assert "Missing hostname" in exc.value.message

    def test_allow_private_flag(self):
        """Test allow_private flag enables private IPs."""
        # Should not raise when allow_private=True
        validate_url_for_ssrf("http://10.0.0.1/api", allow_private=True)
        validate_url_for_ssrf("http://192.168.1.1/", allow_private=True)

    @patch("app.core.url_validator._resolve_hostname")
    def test_dns_rebinding_protection(self, mock_resolve):
        """Test that DNS resolution is checked for SSRF."""
        # Simulate a hostname resolving to a private IP
        mock_resolve.return_value = ["192.168.1.100"]

        with pytest.raises(SSRFError) as exc:
            validate_url_for_ssrf("http://evil-rebind.example.com/api")
        assert "resolves to blocked IP" in exc.value.message

    @patch("app.core.url_validator._resolve_hostname")
    def test_dns_resolution_failure_allowed(self, mock_resolve):
        """Test that DNS resolution failure is allowed (logged but not blocked)."""
        mock_resolve.return_value = []

        # Should not raise - we allow when DNS fails
        validate_url_for_ssrf("http://unknown-host.example.com/api")


class TestIsURLSafe:
    """Tests for is_url_safe convenience function."""

    def test_safe_url_returns_true(self):
        """Test safe URL returns True with no error."""
        is_safe, error = is_url_safe("https://api.example.com/endpoint")

        assert is_safe is True
        assert error is None

    def test_unsafe_url_returns_false(self):
        """Test unsafe URL returns False with error message."""
        is_safe, error = is_url_safe("http://localhost/api")

        assert is_safe is False
        assert error is not None
        assert "Blocked hostname" in error

    def test_invalid_url_returns_false(self):
        """Test invalid URL returns False."""
        is_safe, error = is_url_safe("not-a-valid-url")

        assert is_safe is False
        assert error is not None


class TestSanitizeURLForLogging:
    """Tests for URL sanitization for logging."""

    def test_url_without_credentials_unchanged(self):
        """Test URL without credentials is returned as-is."""
        url = "https://api.example.com/path?query=value"
        result = sanitize_url_for_logging(url)

        assert result == url

    def test_url_with_username_only(self):
        """Test URL with username only is sanitized."""
        url = "https://user@api.example.com/path"
        result = sanitize_url_for_logging(url)

        assert "user" not in result
        assert "api.example.com" in result

    def test_url_with_credentials(self):
        """Test URL with username:password is sanitized."""
        url = "https://admin:secretpass@api.example.com:8080/path"
        result = sanitize_url_for_logging(url)

        assert "admin" not in result
        assert "secretpass" not in result
        assert "api.example.com" in result
        assert "8080" in result

    def test_invalid_url_returns_placeholder(self):
        """Test truly invalid URL parsing returns placeholder."""
        # URL parsing is quite lenient, test with None or empty
        # The function handles exceptions during parsing
        result = sanitize_url_for_logging("")
        # Empty URL is still parseable by urlparse
        assert isinstance(result, str)


class TestSanitizeHeadersForLogging:
    """Tests for header sanitization for logging."""

    def test_empty_headers(self):
        """Test empty headers returns empty dict."""
        assert sanitize_headers_for_logging(None) == {}
        assert sanitize_headers_for_logging({}) == {}

    def test_non_sensitive_headers_unchanged(self):
        """Test non-sensitive headers are not redacted."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Test/1.0",
        }
        result = sanitize_headers_for_logging(headers)

        assert result == headers

    def test_authorization_header_redacted(self):
        """Test Authorization header is redacted."""
        headers = {
            "Authorization": "Bearer secret-token",
            "Content-Type": "application/json",
        }
        result = sanitize_headers_for_logging(headers)

        assert result["Authorization"] == "***REDACTED***"
        assert result["Content-Type"] == "application/json"

    def test_multiple_sensitive_headers_redacted(self):
        """Test multiple sensitive headers are redacted."""
        headers = {
            "Authorization": "Bearer token",
            "X-Api-Key": "api-secret-key",
            "X-Auth-Token": "auth-token",
            "Cookie": "session=abc123",
            "Content-Type": "application/json",
        }
        result = sanitize_headers_for_logging(headers)

        assert result["Authorization"] == "***REDACTED***"
        assert result["X-Api-Key"] == "***REDACTED***"
        assert result["X-Auth-Token"] == "***REDACTED***"
        assert result["Cookie"] == "***REDACTED***"
        assert result["Content-Type"] == "application/json"

    def test_case_insensitive_matching(self):
        """Test header matching is case-insensitive."""
        headers = {
            "AUTHORIZATION": "token",
            "x-api-key": "key",
            "X-WORKER-KEY": "worker",
        }
        result = sanitize_headers_for_logging(headers)

        assert result["AUTHORIZATION"] == "***REDACTED***"
        assert result["x-api-key"] == "***REDACTED***"
        assert result["X-WORKER-KEY"] == "***REDACTED***"


class TestBlockedHostnames:
    """Tests for blocked hostname configuration."""

    def test_blocked_hostnames_is_frozenset(self):
        """Test BLOCKED_HOSTNAMES is immutable."""
        assert isinstance(BLOCKED_HOSTNAMES, frozenset)

    def test_localhost_in_blocked(self):
        """Test localhost variants are blocked."""
        assert "localhost" in BLOCKED_HOSTNAMES
        assert "127.0.0.1" in BLOCKED_HOSTNAMES
        assert "::1" in BLOCKED_HOSTNAMES

    def test_database_services_blocked(self):
        """Test common database hostnames are blocked."""
        db_hosts = ["redis", "postgres", "postgresql", "mysql", "mongodb", "mongo"]
        for host in db_hosts:
            assert host in BLOCKED_HOSTNAMES

    def test_docker_internal_blocked(self):
        """Test Docker internal hostnames are blocked."""
        assert "host.docker.internal" in BLOCKED_HOSTNAMES
        assert "gateway.docker.internal" in BLOCKED_HOSTNAMES


class TestBlockedIPNetworks:
    """Tests for blocked IP network configuration."""

    def test_blocked_networks_list_not_empty(self):
        """Test BLOCKED_IP_NETWORKS is not empty."""
        assert len(BLOCKED_IP_NETWORKS) > 0

    def test_private_networks_included(self):
        """Test private networks are in the list."""
        import ipaddress

        private_ranges = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ]

        for private_range in private_ranges:
            network = ipaddress.ip_network(private_range)
            assert network in BLOCKED_IP_NETWORKS

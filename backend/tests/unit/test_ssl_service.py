"""Tests for SSL Monitor Service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models.ssl_monitor import SSLMonitorStatus
from app.schemas.ssl_monitor import SSLCertificateInfo, SSLCheckResult
from app.services.ssl_monitor import SSLMonitorService


class TestSSLMonitorServiceCheckCertificate:
    """Tests for SSLMonitorService.check_certificate method."""

    @pytest.fixture
    def service(self):
        """Create SSL monitor service instance."""
        return SSLMonitorService()

    @pytest.mark.asyncio
    async def test_check_certificate_connection_refused(self, service):
        """Test handling of connection refused error."""
        with patch("app.services.ssl_monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()

            result = await service.check_certificate("example.com", 443)

            assert result.success is False
            assert result.status == SSLMonitorStatus.ERROR
            assert "refused" in result.error.lower()

    @pytest.mark.asyncio
    async def test_check_certificate_timeout(self, service):
        """Test handling of timeout error."""
        import socket

        with patch("app.services.ssl_monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = socket.timeout()

            result = await service.check_certificate("example.com", 443)

            assert result.success is False
            assert result.status == SSLMonitorStatus.ERROR
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_check_certificate_dns_error(self, service):
        """Test handling of DNS resolution error."""
        import socket

        with patch("app.services.ssl_monitor.socket.create_connection") as mock_conn:
            mock_conn.side_effect = socket.gaierror(8, "Name resolution failed")

            result = await service.check_certificate("nonexistent.example.com", 443)

            assert result.success is False
            assert result.status == SSLMonitorStatus.ERROR
            assert "dns" in result.error.lower() or "resolution" in result.error.lower()

    @pytest.mark.asyncio
    async def test_check_certificate_ssl_error(self, service):
        """Test handling of SSL verification error."""
        import ssl

        with patch("app.services.ssl_monitor.socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_sock

            with patch("app.services.ssl_monitor.ssl.create_default_context") as mock_ctx:
                mock_ctx_instance = MagicMock()
                mock_ctx.return_value = mock_ctx_instance
                mock_ctx_instance.wrap_socket.side_effect = ssl.SSLCertVerificationError("certificate verify failed")

                result = await service.check_certificate("example.com", 443)

                assert result.success is False
                assert result.status == SSLMonitorStatus.INVALID


class TestSSLCheckResultStatus:
    """Tests for SSL check result status values."""

    def test_status_valid(self):
        """Test valid status in check result."""
        result = SSLCheckResult(
            success=True,
            status=SSLMonitorStatus.VALID,
            certificate=SSLCertificateInfo(
                issuer="Test CA",
                subject="example.com",
                serial_number="ABC123",
                valid_from=datetime.utcnow() - timedelta(days=30),
                valid_until=datetime.utcnow() + timedelta(days=60),
                days_until_expiry=60,
                tls_version="TLSv1.3",
                cipher_suite="TLS_AES_256_GCM_SHA384",
                chain_valid=True,
                hostname_match=True,
            ),
        )
        assert result.status == SSLMonitorStatus.VALID
        assert result.success is True

    def test_status_expiring(self):
        """Test expiring status in check result."""
        result = SSLCheckResult(
            success=True,
            status=SSLMonitorStatus.EXPIRING,
            certificate=SSLCertificateInfo(
                issuer="Test CA",
                subject="example.com",
                serial_number="ABC123",
                valid_from=datetime.utcnow() - timedelta(days=350),
                valid_until=datetime.utcnow() + timedelta(days=7),
                days_until_expiry=7,
                tls_version="TLSv1.3",
                cipher_suite="TLS_AES_256_GCM_SHA384",
                chain_valid=True,
                hostname_match=True,
            ),
        )
        assert result.status == SSLMonitorStatus.EXPIRING

    def test_status_expired(self):
        """Test expired status in check result."""
        result = SSLCheckResult(
            success=False,
            status=SSLMonitorStatus.EXPIRED,
            error="Certificate expired",
        )
        assert result.status == SSLMonitorStatus.EXPIRED
        assert result.success is False

    def test_status_error(self):
        """Test error status in check result."""
        result = SSLCheckResult(
            success=False,
            status=SSLMonitorStatus.ERROR,
            error="Connection refused",
        )
        assert result.status == SSLMonitorStatus.ERROR

    def test_status_invalid(self):
        """Test invalid status in check result."""
        result = SSLCheckResult(
            success=False,
            status=SSLMonitorStatus.INVALID,
            error="Hostname mismatch",
        )
        assert result.status == SSLMonitorStatus.INVALID


class TestSSLCertificateInfo:
    """Tests for SSL certificate info schema."""

    def test_days_until_expiry_calculation(self):
        """Test that days_until_expiry is set correctly."""
        valid_until = datetime.utcnow() + timedelta(days=30)
        info = SSLCertificateInfo(
            issuer="Test CA",
            subject="example.com",
            serial_number="ABC123",
            valid_from=datetime.utcnow() - timedelta(days=30),
            valid_until=valid_until,
            days_until_expiry=30,
            tls_version="TLSv1.3",
            cipher_suite="TLS_AES_256_GCM_SHA384",
            chain_valid=True,
            hostname_match=True,
        )
        assert info.days_until_expiry == 30

    def test_all_fields_present(self):
        """Test that all certificate info fields are present."""
        info = SSLCertificateInfo(
            issuer="Let's Encrypt",
            subject="example.com",
            serial_number="ABC123DEF456",
            valid_from=datetime(2024, 1, 1),
            valid_until=datetime(2024, 12, 31),
            days_until_expiry=180,
            tls_version="TLSv1.3",
            cipher_suite="TLS_AES_256_GCM_SHA384",
            chain_valid=True,
            hostname_match=True,
        )
        assert info.issuer == "Let's Encrypt"
        assert info.subject == "example.com"
        assert info.serial_number == "ABC123DEF456"
        assert info.tls_version == "TLSv1.3"
        assert info.chain_valid is True
        assert info.hostname_match is True


class TestSSLMonitorStatus:
    """Tests for SSL monitor status enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert SSLMonitorStatus.PENDING == "pending"
        assert SSLMonitorStatus.VALID == "valid"
        assert SSLMonitorStatus.EXPIRING == "expiring"
        assert SSLMonitorStatus.EXPIRED == "expired"
        assert SSLMonitorStatus.INVALID == "invalid"
        assert SSLMonitorStatus.ERROR == "error"
        assert SSLMonitorStatus.PAUSED == "paused"


class TestHostnameMatches:
    """Tests for SSLMonitorService._hostname_matches method."""

    @pytest.fixture
    def service(self):
        """Create SSL monitor service instance."""
        return SSLMonitorService()

    def test_exact_match(self, service):
        """Test exact hostname match."""
        assert service._hostname_matches("example.com", "example.com") is True
        assert service._hostname_matches("example.com", "other.com") is False

    def test_exact_match_case_insensitive(self, service):
        """Test that matching is case insensitive."""
        assert service._hostname_matches("Example.Com", "example.com") is True
        assert service._hostname_matches("EXAMPLE.COM", "example.com") is True

    def test_wildcard_single_subdomain(self, service):
        """Test wildcard certificate matches single subdomain."""
        assert service._hostname_matches("*.example.com", "sub.example.com") is True
        assert service._hostname_matches("*.example.com", "www.example.com") is True
        assert service._hostname_matches("*.example.com", "api.example.com") is True

    def test_wildcard_no_subdomain(self, service):
        """Test wildcard certificate does not match bare domain."""
        assert service._hostname_matches("*.example.com", "example.com") is False

    def test_wildcard_multiple_subdomains(self, service):
        """Test wildcard certificate does not match multiple subdomain levels."""
        assert service._hostname_matches("*.example.com", "sub.sub.example.com") is False
        assert service._hostname_matches("*.example.com", "a.b.example.com") is False

    def test_wildcard_different_domain(self, service):
        """Test wildcard certificate does not match different domains."""
        assert service._hostname_matches("*.example.com", "sub.other.com") is False
        assert service._hostname_matches("*.example.com", "example.org") is False

    def test_wildcard_case_insensitive(self, service):
        """Test wildcard matching is case insensitive."""
        assert service._hostname_matches("*.Example.Com", "sub.example.com") is True
        assert service._hostname_matches("*.EXAMPLE.COM", "SUB.EXAMPLE.COM") is True

    def test_wildcard_partial_match_not_allowed(self, service):
        """Test that partial wildcard matches are not allowed."""
        # notexample.com should not match *.example.com
        assert service._hostname_matches("*.example.com", "notexample.com") is False
        # fooexample.com should not match *.example.com
        assert service._hostname_matches("*.example.com", "fooexample.com") is False

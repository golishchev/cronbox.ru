"""Tests for webhook API endpoints."""

import ipaddress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestYookassaIPRanges:
    """Tests for YooKassa IP range constants."""

    def test_ip_ranges_defined(self):
        """Test YooKassa IP ranges are defined."""
        from app.api.v1.webhooks import YOOKASSA_IP_RANGES

        assert len(YOOKASSA_IP_RANGES) > 0
        for network in YOOKASSA_IP_RANGES:
            assert isinstance(network, (ipaddress.IPv4Network, ipaddress.IPv6Network))


class TestGetClientIP:
    """Tests for _get_client_ip function."""

    def test_get_client_ip_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header."""
        from app.api.v1.webhooks import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda h: {
            "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
            "X-Real-IP": None,
        }.get(h)

        result = _get_client_ip(mock_request)

        assert result == "1.2.3.4"

    def test_get_client_ip_x_real_ip(self):
        """Test extracting IP from X-Real-IP header."""
        from app.api.v1.webhooks import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda h: {
            "X-Forwarded-For": None,
            "X-Real-IP": "10.0.0.1",
        }.get(h)

        result = _get_client_ip(mock_request)

        assert result == "10.0.0.1"

    def test_get_client_ip_direct(self):
        """Test extracting IP from direct connection."""
        from app.api.v1.webhooks import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        result = _get_client_ip(mock_request)

        assert result == "192.168.1.1"

    def test_get_client_ip_no_client(self):
        """Test extracting IP when no client."""
        from app.api.v1.webhooks import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = None

        result = _get_client_ip(mock_request)

        assert result == "unknown"


class TestIsYookassaIP:
    """Tests for _is_yookassa_ip function."""

    def test_valid_yookassa_ip(self):
        """Test recognizes valid YooKassa IP."""
        from app.api.v1.webhooks import _is_yookassa_ip

        # 185.71.76.0/27 range
        assert _is_yookassa_ip("185.71.76.1") is True
        assert _is_yookassa_ip("185.71.76.15") is True

    def test_invalid_yookassa_ip(self):
        """Test rejects non-YooKassa IP."""
        from app.api.v1.webhooks import _is_yookassa_ip

        assert _is_yookassa_ip("1.2.3.4") is False
        assert _is_yookassa_ip("192.168.1.1") is False

    def test_invalid_ip_format(self):
        """Test handles invalid IP format."""
        from app.api.v1.webhooks import _is_yookassa_ip

        assert _is_yookassa_ip("not-an-ip") is False
        assert _is_yookassa_ip("") is False


class TestVerifyPaymentWithYookassa:
    """Tests for _verify_payment_with_yookassa function."""

    @pytest.mark.asyncio
    async def test_verify_not_configured(self):
        """Test verify returns None when not configured."""
        from app.api.v1.webhooks import _verify_payment_with_yookassa

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.yookassa_shop_id = None
            mock_settings.yookassa_secret_key = None

            result = await _verify_payment_with_yookassa("payment-123")

            assert result is None

    @pytest.mark.asyncio
    @patch("app.api.v1.webhooks.httpx.AsyncClient")
    async def test_verify_success(self, mock_client_class):
        """Test successful payment verification."""
        from app.api.v1.webhooks import _verify_payment_with_yookassa

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "payment-123",
            "status": "succeeded",
            "amount": {"value": "299.00", "currency": "RUB"},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            result = await _verify_payment_with_yookassa("payment-123")

            assert result is not None
            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    @patch("app.api.v1.webhooks.httpx.AsyncClient")
    async def test_verify_not_found(self, mock_client_class):
        """Test verification when payment not found."""
        from app.api.v1.webhooks import _verify_payment_with_yookassa

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            result = await _verify_payment_with_yookassa("payment-123")

            assert result is None

    @pytest.mark.asyncio
    @patch("app.api.v1.webhooks.httpx.AsyncClient")
    async def test_verify_exception(self, mock_client_class):
        """Test verification handles exception."""
        from app.api.v1.webhooks import _verify_payment_with_yookassa

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            result = await _verify_payment_with_yookassa("payment-123")

            assert result is None


class TestYookassaWebhook:
    """Tests for yookassa_webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self):
        """Test webhook with invalid JSON."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "185.71.76.1"
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "development"

            with pytest.raises(HTTPException) as exc_info:
                await yookassa_webhook(mock_request, mock_db)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_missing_event_type(self):
        """Test webhook with missing event type."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "185.71.76.1"
        mock_request.json = AsyncMock(return_value={"object": {}})

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "development"

            with pytest.raises(HTTPException) as exc_info:
                await yookassa_webhook(mock_request, mock_db)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_missing_payment_id(self):
        """Test webhook with missing payment ID."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "185.71.76.1"
        mock_request.json = AsyncMock(return_value={"event": "payment.succeeded", "object": {}})

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "development"

            with pytest.raises(HTTPException) as exc_info:
                await yookassa_webhook(mock_request, mock_db)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_unauthorized_ip_in_production(self):
        """Test webhook from unauthorized IP in production."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"  # Non-YooKassa IP

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "production"

            with pytest.raises(HTTPException) as exc_info:
                await yookassa_webhook(mock_request, mock_db)

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_success(self):
        """Test successful webhook processing."""
        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "185.71.76.1"
        mock_request.json = AsyncMock(
            return_value={"event": "payment.succeeded", "object": {"id": "payment-123", "status": "succeeded"}}
        )

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "development"

            with patch("app.api.v1.webhooks.billing_service") as mock_billing:
                mock_billing.handle_webhook = AsyncMock(return_value=True)

                result = await yookassa_webhook(mock_request, mock_db)

                assert result == {"status": "ok"}
                mock_billing.handle_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_processing_failed(self):
        """Test webhook when billing service fails."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import yookassa_webhook

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "185.71.76.1"
        mock_request.json = AsyncMock(
            return_value={"event": "payment.succeeded", "object": {"id": "payment-123", "status": "succeeded"}}
        )

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.environment = "development"

            with patch("app.api.v1.webhooks.billing_service") as mock_billing:
                mock_billing.handle_webhook = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await yookassa_webhook(mock_request, mock_db)

                assert exc_info.value.status_code == 500


class TestPostalWebhook:
    """Tests for postal_webhook endpoint."""

    @pytest.mark.asyncio
    async def test_postal_webhook_missing_signature(self):
        """Test postal webhook with missing signature."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "MessageSent"}')

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = "secret"

            with pytest.raises(HTTPException) as exc_info:
                await postal_webhook(mock_request, mock_db, x_postal_signature=None)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_postal_webhook_invalid_signature(self):
        """Test postal webhook with invalid signature."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "MessageSent"}')

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = "secret"

            with patch("app.api.v1.webhooks.postal_service") as mock_postal:
                mock_postal.verify_webhook_signature.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    await postal_webhook(mock_request, mock_db, x_postal_signature="invalid")

                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_postal_webhook_invalid_json(self):
        """Test postal webhook with invalid JSON."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b"not json")
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = None

            with pytest.raises(HTTPException) as exc_info:
                await postal_webhook(mock_request, mock_db, x_postal_signature=None)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_postal_webhook_missing_event_type(self):
        """Test postal webhook with missing event type."""
        from fastapi import HTTPException

        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b"{}")
        mock_request.json = AsyncMock(return_value={})

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = None

            with pytest.raises(HTTPException) as exc_info:
                await postal_webhook(mock_request, mock_db, x_postal_signature=None)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_postal_webhook_success(self):
        """Test successful postal webhook."""
        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "MessageSent"}')
        mock_request.json = AsyncMock(return_value={"event": "MessageSent"})

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = None

            with patch("app.api.v1.webhooks.postal_service") as mock_postal:
                mock_postal.process_webhook = AsyncMock(return_value=True)

                result = await postal_webhook(mock_request, mock_db, x_postal_signature=None)

                assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_postal_webhook_processing_failed(self):
        """Test postal webhook when processing fails."""
        from app.api.v1.webhooks import postal_webhook

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "MessageSent"}')
        mock_request.json = AsyncMock(return_value={"event": "MessageSent"})

        mock_db = AsyncMock()

        with patch("app.api.v1.webhooks.settings") as mock_settings:
            mock_settings.postal_webhook_secret = None

            with patch("app.api.v1.webhooks.postal_service") as mock_postal:
                mock_postal.process_webhook = AsyncMock(return_value=False)

                # Should not raise, just log warning
                result = await postal_webhook(mock_request, mock_db, x_postal_signature=None)

                assert result == {"status": "ok"}

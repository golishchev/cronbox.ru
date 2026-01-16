"""Tests for PostalService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest


class TestPostalServiceInit:
    """Tests for PostalService initialization."""

    def test_init_with_settings(self):
        """Test PostalService initializes with settings."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com/"
            mock_settings.postal_api_key = "api-key"
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = "webhook-secret"
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            assert service.api_url == "https://postal.example.com"
            assert service.server_key == "server-key"
            assert service.webhook_secret == "webhook-secret"

    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = "api-key"
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            assert service.is_configured is True

    def test_is_configured_false_no_url(self):
        """Test is_configured returns False when no URL."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = None
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            assert service.is_configured is False

    def test_is_configured_false_no_server_key(self):
        """Test is_configured returns False when no server key."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = None
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            assert service.is_configured is False


class TestPostalServiceSendEmail:
    """Tests for PostalService.send_email."""

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self):
        """Test send_email returns None when not configured."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = None
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = None
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = None

            service = PostalService()
            mock_db = AsyncMock()

            result = await service.send_email(
                mock_db,
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>",
            )

            assert result is None

    @pytest.mark.asyncio
    @patch("app.services.postal.httpx.AsyncClient")
    async def test_send_email_success(self, mock_client_class):
        """Test send_email success."""
        from app.models.email_log import EmailType
        from app.services.postal import PostalService

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"server": "postal-server", "messages": {"test@example.com": {"id": 12345}}},
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = "api-key"
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()
            mock_db.add = MagicMock()

            result = await service.send_email(
                mock_db,
                to="test@example.com",
                subject="Test Subject",
                html="<p>Test body</p>",
                text="Test body",
                email_type=EmailType.OTHER,
            )

            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.postal.httpx.AsyncClient")
    async def test_send_email_api_error(self, mock_client_class):
        """Test send_email handles API error."""
        from app.services.postal import PostalService

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"status": "error", "data": {"message": "Invalid API key"}}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = "api-key"
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()
            mock_db.add = MagicMock()

            result = await service.send_email(
                mock_db,
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>",
            )

            assert result is not None  # Returns email log even on failure
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.postal.httpx.AsyncClient")
    async def test_send_email_http_error(self, mock_client_class):
        """Test send_email handles HTTP error."""
        from app.services.postal import PostalService

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPError("Connection failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = "api-key"
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()
            mock_db.add = MagicMock()

            result = await service.send_email(
                mock_db,
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>",
            )

            assert result is not None  # Returns email log with failure status
            mock_db.commit.assert_called()


class TestPostalServiceWebhookSignature:
    """Tests for webhook signature verification."""

    def test_verify_webhook_signature_no_secret(self):
        """Test verify returns False when no secret configured."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            result = service.verify_webhook_signature(b"payload", "signature")

            assert result is False

    def test_verify_webhook_signature_valid(self):
        """Test verify returns True for valid signature."""
        import hashlib
        import hmac

        secret = "test-secret"
        payload = b'{"event": "MessageSent"}'
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = secret
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            result = service.verify_webhook_signature(payload, expected_sig)

            assert result is True

    def test_verify_webhook_signature_invalid(self):
        """Test verify returns False for invalid signature."""
        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = "test-secret"
            mock_settings.email_from = "noreply@example.com"

            from app.services.postal import PostalService

            service = PostalService()

            result = service.verify_webhook_signature(b"payload", "invalid-signature")

            assert result is False


class TestPostalServiceProcessWebhook:
    """Tests for webhook processing."""

    @pytest.mark.asyncio
    async def test_process_webhook_no_message_id(self):
        """Test webhook processing with no message ID."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            result = await service.process_webhook(mock_db, "MessageSent", {})

            assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_email_not_found(self):
        """Test webhook processing when email log not found."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(mock_db, "MessageSent", {"message": {"id": 12345}})

            assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_message_sent(self):
        """Test webhook processing for MessageSent event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.QUEUED
            mock_email_log.id = uuid4()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(mock_db, "MessageSent", {"message": {"id": 12345}})

            assert result is True
            assert mock_email_log.status == EmailStatus.SENT
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_webhook_message_delivered(self):
        """Test webhook processing for MessageDelivered event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.SENT
            mock_email_log.id = uuid4()
            mock_email_log.mark_delivered = MagicMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(mock_db, "MessageDelivered", {"message": {"id": 12345}})

            assert result is True
            mock_email_log.mark_delivered.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_webhook_message_bounced(self):
        """Test webhook processing for MessageBounced event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.SENT
            mock_email_log.id = uuid4()
            mock_email_log.mark_bounced = MagicMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(
                mock_db,
                "MessageBounced",
                {"message": {"id": 12345}, "bounce": {"type": "hard", "code": "550", "message": "User not found"}},
            )

            assert result is True
            mock_email_log.mark_bounced.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_webhook_message_opened(self):
        """Test webhook processing for MessageLoaded event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.DELIVERED
            mock_email_log.id = uuid4()
            mock_email_log.mark_opened = MagicMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(mock_db, "MessageLoaded", {"message": {"id": 12345}})

            assert result is True
            mock_email_log.mark_opened.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_webhook_message_clicked(self):
        """Test webhook processing for MessageLinkClicked event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.DELIVERED
            mock_email_log.id = uuid4()
            mock_email_log.mark_clicked = MagicMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(
                mock_db, "MessageLinkClicked", {"message": {"id": 12345}, "url": "https://example.com"}
            )

            assert result is True
            mock_email_log.mark_clicked.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_process_webhook_message_held(self):
        """Test webhook processing for MessageHeld event."""
        from app.models.email_log import EmailStatus
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            mock_email_log = MagicMock()
            mock_email_log.status = EmailStatus.SENT
            mock_email_log.id = uuid4()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_email_log
            mock_db.execute.return_value = mock_result

            result = await service.process_webhook(
                mock_db, "MessageHeld", {"message": {"id": 12345, "hold_reason": "Spam detected"}}
            )

            assert result is True
            assert mock_email_log.status == EmailStatus.HELD


class TestPostalServiceConvenienceMethods:
    """Tests for convenience email methods."""

    @pytest.mark.asyncio
    async def test_send_task_failure_notification(self):
        """Test send_task_failure_notification."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = MagicMock()

                await service.send_task_failure_notification(
                    db=mock_db,
                    to="test@example.com",
                    task_name="Test Task",
                    task_type="cron",
                    error_message="Connection timeout",
                    workspace_name="My Workspace",
                    workspace_id=uuid4(),
                    task_url="https://api.example.com/webhook",
                )

                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Task Failed" in call_kwargs["subject"]
                assert "Test Task" in call_kwargs["html"]

    @pytest.mark.asyncio
    async def test_send_task_recovery_notification(self):
        """Test send_task_recovery_notification."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = MagicMock()

                await service.send_task_recovery_notification(
                    db=mock_db,
                    to="test@example.com",
                    task_name="Test Task",
                    task_type="cron",
                    workspace_name="My Workspace",
                    workspace_id=uuid4(),
                )

                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Recovered" in call_kwargs["subject"]

    @pytest.mark.asyncio
    async def test_send_task_success_notification(self):
        """Test send_task_success_notification."""
        from app.services.postal import PostalService

        with patch("app.services.postal.settings") as mock_settings:
            mock_settings.postal_api_url = "https://postal.example.com"
            mock_settings.postal_api_key = None
            mock_settings.postal_server_key = "server-key"
            mock_settings.postal_webhook_secret = None
            mock_settings.email_from = "noreply@example.com"

            service = PostalService()
            mock_db = AsyncMock()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = MagicMock()

                await service.send_task_success_notification(
                    db=mock_db,
                    to="test@example.com",
                    task_name="Test Task",
                    task_type="cron",
                    workspace_name="My Workspace",
                    workspace_id=uuid4(),
                    duration_ms=150,
                )

                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Succeeded" in call_kwargs["subject"]

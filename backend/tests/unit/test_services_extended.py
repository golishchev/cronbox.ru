"""Extended tests for service layer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestTelegramService:
    """Tests for TelegramService."""

    def test_is_configured_false_when_no_token(self):
        """Test is_configured returns False when no token."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        service.bot_token = ""
        assert service.is_configured is False

    def test_is_configured_true_when_token_set(self):
        """Test is_configured returns True with token."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        service.bot_token = "test-bot-token"
        assert service.is_configured is True

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test send_message returns False when not configured."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        service.bot_token = ""

        result = await service.send_message(123456, "Test message")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.telegram.httpx.AsyncClient")
    async def test_send_message_success(self, mock_client_class):
        """Test successful message send."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        service.bot_token = "test-bot-token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.send_message(123456, "Test message")

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.telegram.httpx.AsyncClient")
    async def test_send_message_failure(self, mock_client_class):
        """Test message send failure."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        service.bot_token = "test-bot-token"

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.send_message(123456, "Test message")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.telegram.TelegramService.send_message")
    async def test_send_task_failure_notification(self, mock_send):
        """Test task failure notification."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        mock_send.return_value = True

        result = await service.send_task_failure_notification(
            chat_id=123456,
            task_name="Test Task",
            task_type="cron",
            error_message="Connection refused",
            workspace_name="My Workspace",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Test Task" in call_args[0][1]
        assert "Connection refused" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.services.telegram.TelegramService.send_message")
    async def test_send_task_recovery_notification(self, mock_send):
        """Test task recovery notification."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        mock_send.return_value = True

        result = await service.send_task_recovery_notification(
            chat_id=123456,
            task_name="Test Task",
            task_type="cron",
            workspace_name="My Workspace",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Recovered" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.services.telegram.TelegramService.send_message")
    async def test_send_task_success_notification(self, mock_send):
        """Test task success notification."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        mock_send.return_value = True

        result = await service.send_task_success_notification(
            chat_id=123456,
            task_name="Test Task",
            task_type="cron",
            workspace_name="My Workspace",
            duration_ms=150,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Succeeded" in call_args[0][1]
        assert "150ms" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.services.telegram.TelegramService.send_message")
    async def test_send_subscription_expiring_notification(self, mock_send):
        """Test subscription expiring notification."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        mock_send.return_value = True

        result = await service.send_subscription_expiring_notification(
            chat_id=123456,
            workspace_name="My Workspace",
            days_remaining=7,
            expiration_date="2024-01-15",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Expiring" in call_args[0][1]
        assert "7 day(s)" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("app.services.telegram.TelegramService.send_message")
    async def test_send_subscription_expired_notification(self, mock_send):
        """Test subscription expired notification."""
        from app.services.telegram import TelegramService

        service = TelegramService()
        mock_send.return_value = True

        result = await service.send_subscription_expired_notification(
            chat_id=123456,
            workspace_name="My Workspace",
            tasks_paused=5,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Expired" in call_args[0][1]
        assert "5" in call_args[0][1]


class TestAuthServiceTokens:
    """Tests for AuthService token creation."""

    def test_create_tokens(self):
        """Test creating access and refresh tokens."""
        from app.core.security import decode_token
        from app.services.auth import AuthService

        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"

        tokens = service._create_tokens(mock_user)

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"

        # Verify access token
        payload = decode_token(tokens.access_token)
        assert payload is not None
        assert payload["sub"] == str(mock_user.id)
        assert payload["email"] == mock_user.email
        assert payload["type"] == "access"


class TestEmailService:
    """Tests for EmailService."""

    def test_email_service_is_configured(self):
        """Test email service configuration check."""
        from app.services.email import EmailService

        service = EmailService()

        # Should be based on settings
        assert isinstance(service.is_configured, bool)


class TestWorkerTaskExecution:
    """Tests for worker task execution."""

    @pytest.mark.asyncio
    async def test_execute_http_task_blocked_url(self):
        """Test execute_http_task blocks dangerous URLs."""
        from app.workers.tasks import execute_http_task

        ctx = {}

        # Test localhost blocking
        result = await execute_http_task(
            ctx,
            url="http://localhost/internal",
            method="GET",
        )
        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"

        # Test private IP blocking
        result = await execute_http_task(
            ctx,
            url="http://10.0.0.1/internal",
            method="GET",
        )
        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"

        # Test metadata endpoint blocking
        result = await execute_http_task(
            ctx,
            url="http://169.254.169.254/latest/meta-data/",
            method="GET",
        )
        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_execute_http_task_all_methods(self, mock_client_class):
        """Test execute_http_task with all HTTP methods."""
        from app.workers.tasks import execute_http_task

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            result = await execute_http_task(
                ctx,
                url="https://api.example.com/test",
                method=method,
            )
            assert result["success"] is True
            assert result["status_code"] == 200

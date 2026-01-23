"""Tests for NotificationService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.mark.asyncio
    async def test_get_settings(self):
        """Test getting notification settings."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.workspace_id = workspace_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_settings
        mock_db.execute.return_value = mock_result

        result = await service.get_settings(mock_db, workspace_id)

        assert result == mock_settings

    @pytest.mark.asyncio
    async def test_get_settings_not_found(self):
        """Test getting settings when not found."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_settings(mock_db, uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_settings_existing(self):
        """Test get_or_create returns existing settings."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()

        with patch.object(service, "get_settings", return_value=mock_settings):
            result = await service.get_or_create_settings(mock_db, workspace_id)

            assert result == mock_settings

    @pytest.mark.asyncio
    async def test_get_or_create_settings_creates_new(self):
        """Test get_or_create creates new settings."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is synchronous in SQLAlchemy

        workspace_id = uuid4()

        with patch.object(service, "get_settings", return_value=None):
            result = await service.get_or_create_settings(mock_db, workspace_id)

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workspace_info(self):
        """Test getting workspace info."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_workspace = MagicMock()
        mock_workspace.name = "Test Workspace"
        mock_workspace.owner = MagicMock()
        mock_workspace.owner.preferred_language = "ru"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace
        mock_db.execute.return_value = mock_result

        name, lang = await service._get_workspace_info(mock_db, workspace_id)

        assert name == "Test Workspace"
        assert lang == "ru"

    @pytest.mark.asyncio
    async def test_get_workspace_info_not_found(self):
        """Test workspace info when workspace not found."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        name, lang = await service._get_workspace_info(mock_db, uuid4())

        assert name == "Unknown"
        assert lang == "en"

    @pytest.mark.asyncio
    async def test_send_task_failure_no_settings(self):
        """Test send_task_failure when no settings."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        with patch.object(service, "get_settings", return_value=None):
            # Should not raise
            await service.send_task_failure(mock_db, uuid4(), "Task", "cron", "Error")

    @pytest.mark.asyncio
    async def test_send_task_failure_notifications_disabled(self):
        """Test send_task_failure when notifications disabled."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.notify_on_failure = False

        with patch.object(service, "get_settings", return_value=mock_settings):
            await service.send_task_failure(mock_db, uuid4(), "Task", "cron", "Error")

    @pytest.mark.asyncio
    async def test_send_task_failure_with_telegram(self):
        """Test send_task_failure sends Telegram notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.notify_on_failure = True
        mock_settings.telegram_enabled = True
        mock_settings.telegram_chat_ids = [123456]
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = False

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_templated_telegram") as mock_telegram:
                    await service.send_task_failure(mock_db, workspace_id, "Test Task", "cron", "Error message")

                    mock_telegram.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_task_failure_with_webhook(self):
        """Test send_task_failure sends webhook notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.notify_on_failure = True
        mock_settings.telegram_enabled = False
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = True
        mock_settings.webhook_url = "https://webhook.example.com"
        mock_settings.webhook_secret = "secret"

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_webhook") as mock_webhook:
                    await service.send_task_failure(mock_db, workspace_id, "Test Task", "cron", "Error")

                    mock_webhook.assert_called_once()
                    call_args = mock_webhook.call_args
                    assert call_args[1]["event"] == "task.failed"

    @pytest.mark.asyncio
    async def test_send_task_recovery(self):
        """Test send_task_recovery."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.notify_on_recovery = True
        mock_settings.telegram_enabled = True
        mock_settings.telegram_chat_ids = [123]
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = False

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_templated_telegram") as mock_telegram:
                    await service.send_task_recovery(mock_db, workspace_id, "Test Task", "cron")

                    mock_telegram.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_task_success(self):
        """Test send_task_success."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.notify_on_success = True
        mock_settings.telegram_enabled = False
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = True
        mock_settings.webhook_url = "https://webhook.example.com"
        mock_settings.webhook_secret = None

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_webhook") as mock_webhook:
                    await service.send_task_success(mock_db, workspace_id, "Test Task", "cron", duration_ms=150)

                    mock_webhook.assert_called_once()
                    call_args = mock_webhook.call_args
                    assert call_args[1]["event"] == "task.succeeded"

    @pytest.mark.asyncio
    async def test_send_task_success_disabled(self):
        """Test send_task_success when notify_on_success is disabled."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.notify_on_success = False
        mock_settings.telegram_enabled = True
        mock_settings.telegram_chat_ids = [123]
        mock_settings.email_enabled = True
        mock_settings.email_addresses = ["test@example.com"]
        mock_settings.webhook_enabled = True
        mock_settings.webhook_url = "https://webhook.example.com"
        mock_settings.webhook_secret = None

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_templated_telegram") as mock_telegram:
                    with patch.object(service, "_send_templated_email") as mock_email:
                        with patch.object(service, "_send_webhook") as mock_webhook:
                            await service.send_task_success(mock_db, workspace_id, "Test Task", "cron", duration_ms=150)

                            # Should not send any notifications when notify_on_success is False
                            mock_telegram.assert_not_called()
                            mock_email.assert_not_called()
                            mock_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_subscription_expiring(self):
        """Test send_subscription_expiring."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_settings = MagicMock()
        mock_settings.telegram_enabled = True
        mock_settings.telegram_chat_ids = [123]
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = False

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_templated_telegram") as mock_telegram:
                    await service.send_subscription_expiring(
                        mock_db, workspace_id, days_remaining=7, expiration_date="2024-01-15"
                    )

                    mock_telegram.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_subscription_expired(self):
        """Test send_subscription_expired."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        user_id = uuid4()
        workspace_id = uuid4()

        # Mock workspace query result
        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace
        mock_db.execute.return_value = mock_result

        mock_settings = MagicMock()
        mock_settings.telegram_enabled = False
        mock_settings.email_enabled = False
        mock_settings.webhook_enabled = True
        mock_settings.webhook_url = "https://webhook.example.com"
        mock_settings.webhook_secret = "secret"

        with patch.object(service, "get_settings", return_value=mock_settings):
            with patch.object(service, "_get_workspace_info", return_value=("Workspace", "en")):
                with patch.object(service, "_send_webhook") as mock_webhook:
                    await service.send_subscription_expired(mock_db, user_id, tasks_paused=5)

                    mock_webhook.assert_called_once()
                    call_args = mock_webhook.call_args
                    assert call_args[1]["event"] == "subscription.expired"

    @pytest.mark.asyncio
    @patch("app.services.notifications.httpx.AsyncClient")
    async def test_send_webhook_success(self, mock_client_class):
        """Test successful webhook send."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._send_webhook(
            url="https://webhook.example.com",
            secret="secret123",
            event="test.event",
            data={"key": "value"},
        )

        assert result is True
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["X-Webhook-Secret"] == "secret123"

    @pytest.mark.asyncio
    @patch("app.services.notifications.httpx.AsyncClient")
    async def test_send_webhook_without_secret(self, mock_client_class):
        """Test webhook send without secret."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._send_webhook(
            url="https://webhook.example.com",
            secret=None,
            event="test.event",
            data={},
        )

        assert result is True
        call_kwargs = mock_client.post.call_args[1]
        assert "X-Webhook-Secret" not in call_kwargs["headers"]

    @pytest.mark.asyncio
    @patch("app.services.notifications.httpx.AsyncClient")
    async def test_send_webhook_failure(self, mock_client_class):
        """Test webhook send failure."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._send_webhook(
            url="https://webhook.example.com",
            secret=None,
            event="test.event",
            data={},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_templated_telegram(self):
        """Test sending templated Telegram notification."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        mock_template = MagicMock()

        with patch("app.services.notifications.template_service") as mock_template_service:
            with patch("app.services.notifications.telegram_service") as mock_telegram:
                mock_template_service.get_template = AsyncMock(return_value=mock_template)
                mock_template_service.render.return_value = (None, "Test message")
                mock_telegram.send_message = AsyncMock()

                await service._send_templated_telegram(
                    mock_db,
                    chat_ids=[123, 456],
                    template_code="test_template",
                    language="en",
                    variables={"key": "value"},
                )

                assert mock_telegram.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_templated_email_with_postal(self):
        """Test sending templated email via Postal."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        workspace_id = uuid4()
        mock_template = MagicMock()

        with patch("app.services.notifications.template_service") as mock_template_service:
            with patch("app.services.notifications.postal_service") as mock_postal:
                with patch("app.services.notifications.app_settings") as mock_settings:
                    mock_template_service.get_template = AsyncMock(return_value=mock_template)
                    mock_template_service.render.return_value = ("Subject", "<p>Body</p>")
                    mock_settings.use_postal = True
                    mock_postal.is_configured = True
                    mock_postal.send_email = AsyncMock()

                    await service._send_templated_email(
                        mock_db,
                        to=["test@example.com"],
                        template_code="test_template",
                        language="en",
                        variables={},
                        workspace_id=workspace_id,
                    )

                    mock_postal.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_templated_email_empty_body(self):
        """Test sending templated email with empty body does nothing."""
        from app.services.notifications import NotificationService

        service = NotificationService()
        mock_db = AsyncMock()

        mock_template = MagicMock()

        with patch("app.services.notifications.template_service") as mock_template_service:
            with patch("app.services.notifications.postal_service") as mock_postal:
                mock_template_service.get_template = AsyncMock(return_value=mock_template)
                mock_template_service.render.return_value = ("Subject", "")

                await service._send_templated_email(
                    mock_db,
                    to=["test@example.com"],
                    template_code="test_template",
                    language="en",
                    variables={},
                    workspace_id=uuid4(),
                )

                mock_postal.send_email.assert_not_called()

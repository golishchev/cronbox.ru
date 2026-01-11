"""Unit tests for notifications API endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    mock.owner_id = kwargs.get("owner_id", uuid4())
    return mock


def create_mock_settings(**kwargs):
    """Create mock notification settings."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.workspace_id = kwargs.get("workspace_id", uuid4())
    mock.email_enabled = kwargs.get("email_enabled", False)
    mock.email_addresses = kwargs.get("email_addresses", [])
    mock.telegram_enabled = kwargs.get("telegram_enabled", False)
    mock.telegram_chat_ids = kwargs.get("telegram_chat_ids", [])
    mock.webhook_enabled = kwargs.get("webhook_enabled", False)
    mock.webhook_url = kwargs.get("webhook_url", None)
    mock.webhook_secret = kwargs.get("webhook_secret", None)
    mock.notify_on_success = kwargs.get("notify_on_success", False)
    mock.notify_on_failure = kwargs.get("notify_on_failure", True)
    return mock


class TestGetNotificationSettings:
    """Tests for get_notification_settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_settings_success(self):
        """Test getting notification settings."""
        from app.api.v1.notifications import get_notification_settings

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(workspace_id=mock_workspace.id)

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_or_create_settings = AsyncMock(return_value=mock_settings)

            result = await get_notification_settings(
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result == mock_settings
            mock_service.get_or_create_settings.assert_called_once_with(
                mock_db, mock_workspace.id
            )


class TestUpdateNotificationSettings:
    """Tests for update_notification_settings endpoint."""

    @pytest.mark.asyncio
    async def test_update_settings_success(self):
        """Test updating notification settings."""
        from app.api.v1.notifications import update_notification_settings
        from app.schemas.notification_settings import NotificationSettingsUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(workspace_id=mock_workspace.id)

        data = NotificationSettingsUpdate(
            email_enabled=True,
            email_addresses=["test@example.com"],
        )

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_or_create_settings = AsyncMock(return_value=mock_settings)

            result = await update_notification_settings(
                workspace=mock_workspace,
                data=data,
                db=mock_db,
            )

            assert mock_settings.email_enabled is True
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_settings)


class TestSendTestNotification:
    """Tests for send_test_notification endpoint."""

    @pytest.mark.asyncio
    async def test_settings_not_configured(self):
        """Test sending test notification when settings don't exist."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        data = TestNotificationRequest(channel="telegram")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_telegram_not_enabled(self):
        """Test sending Telegram test when not enabled."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(telegram_enabled=False)
        data = TestNotificationRequest(channel="telegram")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Telegram" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_telegram_success(self):
        """Test successful Telegram test notification."""
        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            telegram_enabled=True,
            telegram_chat_ids=[123456],
        )
        data = TestNotificationRequest(channel="telegram")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with patch("app.api.v1.notifications.telegram_service") as mock_telegram:
                mock_telegram.send_message = AsyncMock(return_value=True)

                result = await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_telegram_send_fails(self):
        """Test Telegram test when send fails."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            telegram_enabled=True,
            telegram_chat_ids=[123456],
        )
        data = TestNotificationRequest(channel="telegram")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with patch("app.api.v1.notifications.telegram_service") as mock_telegram:
                mock_telegram.send_message = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await send_test_notification(
                        workspace=mock_workspace,
                        data=data,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_email_not_enabled(self):
        """Test sending email test when not enabled."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(email_enabled=False)
        data = TestNotificationRequest(channel="email")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Email" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_email_success(self):
        """Test successful email test notification."""
        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            email_enabled=True,
            email_addresses=["test@example.com"],
        )
        data = TestNotificationRequest(channel="email")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with patch("app.api.v1.notifications.email_service") as mock_email:
                mock_email.send_email = AsyncMock(return_value=True)

                result = await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_email_send_fails(self):
        """Test email test when send fails."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            email_enabled=True,
            email_addresses=["test@example.com"],
        )
        data = TestNotificationRequest(channel="email")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with patch("app.api.v1.notifications.email_service") as mock_email:
                mock_email.send_email = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await send_test_notification(
                        workspace=mock_workspace,
                        data=data,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_webhook_not_enabled(self):
        """Test sending webhook test when not enabled."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(webhook_enabled=False)
        data = TestNotificationRequest(channel="webhook")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Webhook" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_webhook_success(self):
        """Test successful webhook test notification."""
        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            webhook_enabled=True,
            webhook_url="https://example.com/webhook",
            webhook_secret="secret123",
        )
        data = TestNotificationRequest(channel="webhook")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)
            mock_service._send_webhook = AsyncMock(return_value=True)

            result = await send_test_notification(
                workspace=mock_workspace,
                data=data,
                db=mock_db,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_webhook_send_fails(self):
        """Test webhook test when send fails."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings(
            webhook_enabled=True,
            webhook_url="https://example.com/webhook",
        )
        data = TestNotificationRequest(channel="webhook")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)
            mock_service._send_webhook = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_unknown_channel(self):
        """Test sending test for unknown channel."""
        from fastapi import HTTPException

        from app.api.v1.notifications import send_test_notification
        from app.schemas.notification_settings import TestNotificationRequest

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_settings = create_mock_settings()
        data = TestNotificationRequest(channel="unknown")

        with patch("app.api.v1.notifications.notification_service") as mock_service:
            mock_service.get_settings = AsyncMock(return_value=mock_settings)

            with pytest.raises(HTTPException) as exc_info:
                await send_test_notification(
                    workspace=mock_workspace,
                    data=data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Unknown channel" in exc_info.value.detail

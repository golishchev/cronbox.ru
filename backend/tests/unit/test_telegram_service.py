"""Tests for TelegramService."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.telegram import TelegramService


class TestTelegramServiceBasics:
    """Tests for TelegramService basic functionality."""

    def test_is_configured_with_token(self):
        """Test is_configured returns True when bot token is set."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"
            service = TelegramService()
            assert service.is_configured is True

    def test_is_not_configured_without_token(self):
        """Test is_configured returns False when bot token is empty."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            service = TelegramService()
            assert service.is_configured is False


class TestTelegramServiceSendMessage:
    """Tests for TelegramService.send_message."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"

            service = TelegramService()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.raise_for_status = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock()

                result = await service.send_message(123456789, "Test message")

                assert result is True
                mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test message sending when bot is not configured."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            service = TelegramService()

            result = await service.send_message(123456789, "Test message")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Test message sending when API returns error."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"

            service = TelegramService()

            # Patch httpx.AsyncClient to raise an exception
            with patch.object(
                service,
                "send_message",
                wraps=service.send_message,
            ):
                with patch("app.services.telegram.httpx.AsyncClient") as mock_client:
                    # Make the context manager raise an exception
                    mock_client.return_value.__aenter__.side_effect = Exception("API error")

                    result = await service.send_message(123456789, "Test message")

                    assert result is False


class TestTelegramServiceNewUserNotification:
    """Tests for TelegramService.send_new_user_notification."""

    @pytest.mark.asyncio
    async def test_send_new_user_notification_success(self):
        """Test successful new user notification."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"
            mock_settings.admin_telegram_id = 123456789

            service = TelegramService()

            with patch.object(service, "send_message", return_value=True) as mock_send:
                result = await service.send_new_user_notification(
                    user_email="test@example.com",
                    user_name="Test User",
                    registration_method="email",
                )

                assert result is True
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == 123456789
                assert "test@example.com" in call_args[0][1]
                assert "Test User" in call_args[0][1]
                assert "email" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_send_new_user_notification_no_admin_id(self):
        """Test new user notification when admin ID is not configured."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"
            mock_settings.admin_telegram_id = None

            service = TelegramService()

            with patch.object(service, "send_message") as mock_send:
                result = await service.send_new_user_notification(
                    user_email="test@example.com",
                    user_name="Test User",
                    registration_method="email",
                )

                assert result is False
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_new_user_notification_otp_method(self):
        """Test new user notification for OTP registration."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"
            mock_settings.admin_telegram_id = 123456789

            service = TelegramService()

            with patch.object(service, "send_message", return_value=True) as mock_send:
                result = await service.send_new_user_notification(
                    user_email="otp@example.com",
                    user_name="OTP User",
                    registration_method="OTP",
                )

                assert result is True
                call_args = mock_send.call_args
                message_text = call_args[0][1]
                assert "OTP" in message_text
                assert "New User Registered" in message_text

    @pytest.mark.asyncio
    async def test_send_new_user_notification_send_failure(self):
        """Test new user notification when send_message fails."""
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token = "123456:ABC"
            mock_settings.admin_telegram_id = 123456789

            service = TelegramService()

            with patch.object(service, "send_message", return_value=False) as mock_send:
                result = await service.send_new_user_notification(
                    user_email="test@example.com",
                    user_name="Test User",
                    registration_method="email",
                )

                assert result is False
                mock_send.assert_called_once()

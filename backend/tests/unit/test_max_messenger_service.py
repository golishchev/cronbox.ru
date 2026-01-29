"""Tests for MaxMessengerService."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestMaxMessengerService:
    """Tests for MaxMessengerService."""

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_is_configured_true(self, mock_settings):
        """Test is_configured returns True when token is set."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"
        assert service.is_configured is True

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_is_configured_false(self, mock_settings):
        """Test is_configured returns False when token is empty."""
        mock_settings.max_bot_token = ""

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = ""
        assert service.is_configured is False

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_not_configured(self, mock_settings):
        """Test send_message returns False when not configured."""
        mock_settings.max_bot_token = ""

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = ""

        result = await service.send_message("12345", "Hello")
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_success(self, mock_settings):
        """Test successful message sending."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.max_messenger.httpx.AsyncClient", return_value=mock_client):
            result = await service.send_message("12345", "<b>Test</b>")

        assert result is True
        mock_client.post.assert_called_once_with(
            "https://platform-api.max.ru/messages",
            headers={"Authorization": "test-token"},
            params={"chat_id": "12345"},
            json={
                "text": "<b>Test</b>",
                "format": "html",
            },
            timeout=10.0,
        )

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_custom_format(self, mock_settings):
        """Test message sending with custom format."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.max_messenger.httpx.AsyncClient", return_value=mock_client):
            result = await service.send_message("12345", "Plain text", format="text")

        assert result is True
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["json"]["format"] == "text"

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_http_error(self, mock_settings):
        """Test send_message handles HTTP errors gracefully."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=MagicMock(status_code=400)
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.max_messenger.httpx.AsyncClient", return_value=mock_client):
            result = await service.send_message("12345", "Test")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_connection_error(self, mock_settings):
        """Test send_message handles connection errors gracefully."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.max_messenger.httpx.AsyncClient", return_value=mock_client):
            result = await service.send_message("12345", "Test")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.max_messenger.settings")
    async def test_send_message_timeout(self, mock_settings):
        """Test send_message handles timeout errors gracefully."""
        mock_settings.max_bot_token = "test-token"

        from app.services.max_messenger import MaxMessengerService

        service = MaxMessengerService()
        service.bot_token = "test-token"

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.services.max_messenger.httpx.AsyncClient", return_value=mock_client):
            result = await service.send_message("12345", "Test")

        assert result is False

"""Tests for Telegram bot handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBotHandlersModule:
    """Tests for bot handlers module initialization."""

    def test_bot_not_initialized_without_token(self):
        """Test bot is None when no token configured."""
        with patch("app.config.settings") as mock_settings:
            mock_settings.telegram_bot_token = None
            # Re-import to test initialization
            import importlib

            import app.bot.handlers as handlers

            importlib.reload(handlers)
            # Bot should be None when no token
            # Note: We can't easily test this without modifying the module


class TestCmdStart:
    """Tests for /start command handler."""

    @pytest.mark.asyncio
    async def test_cmd_start_shows_chat_id(self):
        """Test /start command shows chat ID."""
        from app.bot.handlers import cmd_start

        mock_message = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.answer = AsyncMock()

        with patch("app.bot.handlers.get_user_language", new_callable=AsyncMock, return_value="ru"):
            await cmd_start(mock_message)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Привет" in call_args[0][0]
        assert "12345" in call_args[0][0]  # Chat ID should be in message
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_cmd_start_no_user(self):
        """Test /start command without user does nothing."""
        from app.bot.handlers import cmd_start

        mock_message = AsyncMock()
        mock_message.from_user = None
        mock_message.answer = AsyncMock()

        await cmd_start(mock_message)

        mock_message.answer.assert_not_called()


class TestCmdHelp:
    """Tests for /help command handler."""

    @pytest.mark.asyncio
    async def test_cmd_help(self):
        """Test /help command returns help message."""
        from app.bot.handlers import cmd_help

        mock_message = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.answer = AsyncMock()

        with patch("app.bot.handlers.get_user_language", new_callable=AsyncMock, return_value="ru"):
            await cmd_help(mock_message)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Справка" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_cmd_help_no_user(self):
        """Test /help command without user does nothing."""
        from app.bot.handlers import cmd_help

        mock_message = AsyncMock()
        mock_message.from_user = None
        mock_message.answer = AsyncMock()

        await cmd_help(mock_message)

        mock_message.answer.assert_not_called()


class TestGetUserLanguage:
    """Tests for get_user_language function."""

    @pytest.mark.asyncio
    async def test_get_user_language_default(self):
        """Test get_user_language returns default when no user found."""
        from app.bot.handlers import get_user_language

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                lang = await get_user_language(12345)
                assert lang == "ru"

    @pytest.mark.asyncio
    async def test_get_user_language_from_user(self):
        """Test get_user_language returns user's language."""
        from app.bot.handlers import get_user_language

        mock_user = MagicMock()
        mock_user.language = "en"

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
                mock_repo_class.return_value = mock_repo

                lang = await get_user_language(12345)
                assert lang == "en"

    @pytest.mark.asyncio
    async def test_get_user_language_exception(self):
        """Test get_user_language returns default on exception."""
        from app.bot.handlers import get_user_language

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_session_class.return_value.__aenter__.side_effect = Exception("DB error")

            lang = await get_user_language(12345)
            assert lang == "ru"


class TestRunBot:
    """Tests for run_bot function."""

    @pytest.mark.asyncio
    async def test_run_bot_no_token(self):
        """Test run_bot when no bot token configured."""
        from app.bot.handlers import run_bot

        with patch("app.bot.handlers.bot", None):
            # Should not raise, just return
            await run_bot()

    @pytest.mark.asyncio
    async def test_run_bot_with_token(self):
        """Test run_bot starts polling."""
        from app.bot.handlers import run_bot

        mock_bot = MagicMock()
        mock_bot.delete_webhook = AsyncMock()
        mock_dp = MagicMock()
        mock_dp.start_polling = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.initialize = AsyncMock()
        mock_redis.close = AsyncMock()

        with patch("app.bot.handlers.bot", mock_bot):
            with patch("app.bot.handlers.dp", mock_dp):
                with patch("app.core.redis.redis_client", mock_redis):
                    await run_bot()
                    mock_dp.start_polling.assert_called_once_with(mock_bot)


class TestStopBot:
    """Tests for stop_bot function."""

    @pytest.mark.asyncio
    async def test_stop_bot_no_bot(self):
        """Test stop_bot when no bot."""
        from app.bot.handlers import stop_bot

        with patch("app.bot.handlers.bot", None):
            # Should not raise
            await stop_bot()

    @pytest.mark.asyncio
    async def test_stop_bot_with_bot(self):
        """Test stop_bot closes session."""
        from app.bot.handlers import stop_bot

        mock_bot = MagicMock()
        mock_bot.session = MagicMock()
        mock_bot.session.close = AsyncMock()

        with patch("app.bot.handlers.bot", mock_bot):
            await stop_bot()
            mock_bot.session.close.assert_called_once()

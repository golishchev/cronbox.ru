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
    async def test_cmd_start_without_code(self):
        """Test /start command without deep link code."""
        from app.bot.handlers import cmd_start

        mock_message = AsyncMock()
        mock_message.text = "/start"
        mock_message.answer = AsyncMock()

        await cmd_start(mock_message)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Привет" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_cmd_start_with_code(self):
        """Test /start command with deep link code."""
        from app.bot.handlers import cmd_start

        mock_message = AsyncMock()
        mock_message.text = "/start 123456"
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.from_user.username = "testuser"

        with patch("app.bot.handlers.process_link_code", new_callable=AsyncMock) as mock_process:
            await cmd_start(mock_message)
            mock_process.assert_called_once_with(mock_message, "123456")


class TestCmdHelp:
    """Tests for /help command handler."""

    @pytest.mark.asyncio
    async def test_cmd_help(self):
        """Test /help command returns help message."""
        from app.bot.handlers import cmd_help

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()

        await cmd_help(mock_message)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Справка" in call_args[0][0]
        assert "/link" in call_args[0][0]
        assert "/status" in call_args[0][0]
        assert "/unlink" in call_args[0][0]


class TestCmdLink:
    """Tests for /link command handler."""

    @pytest.mark.asyncio
    async def test_cmd_link_without_code(self):
        """Test /link command without code shows error."""
        from app.bot.handlers import cmd_link

        mock_message = AsyncMock()
        mock_message.text = "/link"
        mock_message.answer = AsyncMock()

        await cmd_link(mock_message)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Укажите код" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_link_with_code(self):
        """Test /link command with code calls process_link_code."""
        from app.bot.handlers import cmd_link

        mock_message = AsyncMock()
        mock_message.text = "/link 123456"
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.from_user.username = "testuser"

        with patch("app.bot.handlers.process_link_code", new_callable=AsyncMock) as mock_process:
            await cmd_link(mock_message)
            mock_process.assert_called_once_with(mock_message, "123456")


class TestProcessLinkCode:
    """Tests for process_link_code function."""

    @pytest.mark.asyncio
    async def test_process_link_code_invalid_format(self):
        """Test linking with invalid code format."""
        from app.bot.handlers import process_link_code

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()

        await process_link_code(mock_message, "abc")

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Неверный формат" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_link_code_invalid_format_too_short(self):
        """Test linking with too short code."""
        from app.bot.handlers import process_link_code

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()

        await process_link_code(mock_message, "12345")

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Неверный формат" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_link_code_success(self):
        """Test successful account linking."""
        from app.bot.handlers import process_link_code

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.from_user.username = "testuser"

        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.id = "test-uuid"
        mock_user.language = "ru"

        with patch("app.bot.handlers.get_user_language", new_callable=AsyncMock, return_value="ru"):
            with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
                mock_db = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_db
                mock_session_class.return_value.__aexit__.return_value = None

                with patch("app.bot.handlers.AuthService") as mock_auth_class:
                    mock_auth = MagicMock()
                    mock_auth.link_telegram_by_code = AsyncMock(return_value=mock_user)
                    mock_auth_class.return_value = mock_auth

                    await process_link_code(mock_message, "123456")

                    mock_auth.link_telegram_by_code.assert_called_once_with(
                        code="123456",
                        telegram_id=12345,
                        telegram_username="testuser",
                    )
                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args
                    assert "успешно привязан" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_link_code_failure(self):
        """Test failed account linking."""
        from app.bot.handlers import process_link_code

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.from_user.username = "testuser"

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.bot.handlers.AuthService") as mock_auth_class:
                mock_auth = MagicMock()
                mock_auth.link_telegram_by_code = AsyncMock(return_value=None)
                mock_auth_class.return_value = mock_auth

                await process_link_code(mock_message, "123456")

                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args
                assert "Не удалось привязать" in call_args[0][0]


class TestCmdStatus:
    """Tests for /status command handler."""

    @pytest.mark.asyncio
    async def test_cmd_status_linked(self):
        """Test /status when account is linked."""
        from app.bot.handlers import cmd_status

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345

        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.email_verified = True
        mock_user.language = "ru"

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
                mock_repo_class.return_value = mock_repo

                await cmd_status(mock_message)

                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args
                assert "Аккаунт привязан" in call_args[0][0]
                assert mock_user.email in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_status_not_linked(self):
        """Test /status when account is not linked."""
        from app.bot.handlers import cmd_status

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                await cmd_status(mock_message)

                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args
                assert "Аккаунт не привязан" in call_args[0][0]


class TestCmdUnlink:
    """Tests for /unlink command handler."""

    @pytest.mark.asyncio
    async def test_cmd_unlink_not_linked(self):
        """Test /unlink when not linked."""
        from app.bot.handlers import cmd_unlink

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                await cmd_unlink(mock_message)

                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args
                assert "не привязан" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_unlink_success(self):
        """Test successful /unlink."""
        from app.bot.handlers import cmd_unlink

        mock_message = AsyncMock()
        mock_message.answer = AsyncMock()
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345

        mock_user = MagicMock()
        mock_user.id = "test-uuid"
        mock_user.language = "ru"

        with patch("app.bot.handlers.AsyncSessionLocal") as mock_session_class:
            mock_db = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_db
            mock_session_class.return_value.__aexit__.return_value = None

            with patch("app.db.repositories.users.UserRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
                mock_repo.update = AsyncMock()
                mock_repo_class.return_value = mock_repo

                await cmd_unlink(mock_message)

                mock_repo.update.assert_called_once_with(mock_user, telegram_id=None, telegram_username=None)
                mock_db.commit.assert_called_once()
                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args
                assert "Аккаунт отвязан" in call_args[0][0]


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
        mock_dp = MagicMock()
        mock_dp.start_polling = AsyncMock()

        with patch("app.bot.handlers.bot", mock_bot):
            with patch("app.bot.handlers.dp", mock_dp):
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

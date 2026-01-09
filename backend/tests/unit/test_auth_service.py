"""Tests for AuthService."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth import AuthService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, UnauthorizedError


class TestAuthServiceRegister:
    """Tests for AuthService.register."""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful user registration."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"

        with patch.object(service.user_repo, "email_exists", return_value=False):
            with patch.object(service.user_repo, "create_user", return_value=mock_user):
                user, tokens = await service.register(
                    email="test@example.com",
                    password="password123",
                    name="Test User",
                )

                assert user == mock_user
                assert tokens.access_token is not None
                assert tokens.refresh_token is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """Test registration with existing email."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch.object(service.user_repo, "email_exists", return_value=True):
            with pytest.raises(ConflictError) as exc_info:
                await service.register(
                    email="existing@example.com",
                    password="password123",
                    name="Test User",
                )

            assert "already registered" in str(exc_info.value.detail)


class TestAuthServiceLogin:
    """Tests for AuthService.login."""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        mock_user.failed_login_attempts = 0
        mock_user.is_locked.return_value = False

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with patch("app.services.auth.verify_password", return_value=True):
                user, tokens = await service.login(
                    email="test@example.com",
                    password="password123",
                )

                assert user == mock_user
                assert tokens.access_token is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """Test login with wrong password."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_locked.return_value = False
        mock_user.failed_login_attempts = 0

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with patch("app.services.auth.verify_password", return_value=False):
                with pytest.raises(UnauthorizedError) as exc_info:
                    await service.login(
                        email="test@example.com",
                        password="wrong_password",
                    )

                assert "Invalid email or password" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self):
        """Test login with non-existent user."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch.object(service.user_repo, "get_by_email", return_value=None):
            with pytest.raises(UnauthorizedError) as exc_info:
                await service.login(
                    email="nonexistent@example.com",
                    password="password123",
                )

            assert "Invalid email or password" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_login_inactive_user(self):
        """Test login with inactive user."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_active = False
        mock_user.is_locked.return_value = False

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with patch("app.services.auth.verify_password", return_value=True):
                with pytest.raises(UnauthorizedError) as exc_info:
                    await service.login(
                        email="test@example.com",
                        password="password123",
                    )

                assert "disabled" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_login_locked_account(self):
        """Test login with locked account."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_locked.return_value = True
        mock_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with pytest.raises(UnauthorizedError) as exc_info:
                await service.login(
                    email="test@example.com",
                    password="password123",
                )

            assert "locked" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_login_resets_failed_attempts(self):
        """Test successful login resets failed attempts counter."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        mock_user.failed_login_attempts = 3
        mock_user.is_locked.return_value = False

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with patch("app.services.auth.verify_password", return_value=True):
                with patch.object(service, "_reset_failed_attempts") as mock_reset:
                    await service.login(
                        email="test@example.com",
                        password="password123",
                    )

                    mock_reset.assert_called_once_with(mock_user)


class TestAuthServiceFailedLogin:
    """Tests for failed login handling."""

    @pytest.mark.asyncio
    async def test_handle_failed_login_increments_counter(self):
        """Test failed login increments counter."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.failed_login_attempts = 0

        with patch("app.services.auth.settings") as mock_settings:
            mock_settings.max_failed_login_attempts = 5
            mock_settings.account_lockout_minutes = 15

            await service._handle_failed_login(mock_user)

            assert mock_user.failed_login_attempts == 1
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_failed_login_locks_account(self):
        """Test account gets locked after max attempts."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.failed_login_attempts = 4  # One more will lock

        with patch("app.services.auth.settings") as mock_settings:
            mock_settings.max_failed_login_attempts = 5
            mock_settings.account_lockout_minutes = 15

            await service._handle_failed_login(mock_user)

            assert mock_user.failed_login_attempts == 5
            assert mock_user.locked_until is not None

    @pytest.mark.asyncio
    async def test_reset_failed_attempts(self):
        """Test resetting failed attempts."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.failed_login_attempts = 3
        mock_user.locked_until = datetime.now(timezone.utc)

        await service._reset_failed_attempts(mock_user)

        assert mock_user.failed_login_attempts == 0
        assert mock_user.locked_until is None
        mock_db.commit.assert_called_once()


class TestAuthServiceRefreshTokens:
    """Tests for AuthService.refresh_tokens."""

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self):
        """Test successful token refresh."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.is_active = True

        with patch("app.services.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(mock_user.id),
                "type": "refresh",
            }
            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                tokens = await service.refresh_tokens("valid_refresh_token")

                assert tokens.access_token is not None
                assert tokens.refresh_token is not None

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(self):
        """Test refresh with invalid token."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.decode_token", return_value=None):
            with pytest.raises(UnauthorizedError) as exc_info:
                await service.refresh_tokens("invalid_token")

            assert "Invalid refresh token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_refresh_tokens_wrong_type(self):
        """Test refresh with access token instead of refresh token."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(uuid4()),
                "type": "access",  # Wrong type
            }

            with pytest.raises(UnauthorizedError) as exc_info:
                await service.refresh_tokens("access_token")

            assert "Invalid token type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_refresh_tokens_user_not_found(self):
        """Test refresh when user not found."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "sub": str(uuid4()),
                "type": "refresh",
            }
            with patch.object(service.user_repo, "get_by_id", return_value=None):
                with pytest.raises(UnauthorizedError) as exc_info:
                    await service.refresh_tokens("valid_token")

                assert "not found or inactive" in str(exc_info.value.detail)


class TestAuthServiceChangePassword:
    """Tests for AuthService.change_password."""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Test successful password change."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.password_hash = "old_hash"

        with patch("app.services.auth.verify_password", return_value=True):
            with patch("app.services.auth.get_password_hash", return_value="new_hash"):
                with patch.object(service.user_repo, "update_password") as mock_update:
                    await service.change_password(
                        mock_user,
                        current_password="old_password",
                        new_password="new_password",
                    )

                    mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self):
        """Test password change with wrong current password."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.password_hash = "hash"

        with patch("app.services.auth.verify_password", return_value=False):
            with pytest.raises(BadRequestError) as exc_info:
                await service.change_password(
                    mock_user,
                    current_password="wrong_password",
                    new_password="new_password",
                )

            assert "incorrect" in str(exc_info.value.detail).lower()


class TestAuthServiceEmailVerification:
    """Tests for email verification."""

    @pytest.mark.asyncio
    async def test_send_email_verification(self):
        """Test generating email verification token."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.set = AsyncMock()

            token = await service.send_email_verification(mock_user)

            assert token is not None
            assert len(token) > 20  # Token should be substantial
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
        """Test successful email verification."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email_verified = False

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with patch.object(service.user_repo, "verify_email", return_value=mock_user):
                    result = await service.verify_email("valid_token")

                    assert result == mock_user
                    mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self):
        """Test email verification with invalid token."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with pytest.raises(BadRequestError) as exc_info:
                await service.verify_email("invalid_token")

            assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(self):
        """Test verifying already verified email."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email_verified = True

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with pytest.raises(BadRequestError) as exc_info:
                    await service.verify_email("valid_token")

                assert "already verified" in str(exc_info.value.detail)


class TestAuthServicePasswordReset:
    """Tests for password reset."""

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self):
        """Test requesting password reset."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            with patch("app.services.auth.redis_client") as mock_redis:
                mock_redis.set = AsyncMock()

                token = await service.request_password_reset("test@example.com")

                assert token is not None
                mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(self):
        """Test password reset for non-existent user."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch.object(service.user_repo, "get_by_email", return_value=None):
            result = await service.request_password_reset("nonexistent@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_request_password_reset_inactive_user(self):
        """Test password reset for inactive user."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.is_active = False

        with patch.object(service.user_repo, "get_by_email", return_value=mock_user):
            result = await service.request_password_reset("inactive@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Test successful password reset."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with patch("app.services.auth.get_password_hash", return_value="new_hash"):
                    with patch.object(service.user_repo, "update_password", return_value=mock_user):
                        result = await service.reset_password("valid_token", "new_password")

                        assert result == mock_user
                        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self):
        """Test password reset with invalid token."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with pytest.raises(BadRequestError) as exc_info:
                await service.reset_password("invalid_token", "new_password")

            assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_reset_password_inactive_account(self):
        """Test password reset for inactive account."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with pytest.raises(BadRequestError) as exc_info:
                    await service.reset_password("valid_token", "new_password")

                assert "disabled" in str(exc_info.value.detail)


class TestAuthServiceTelegram:
    """Tests for Telegram integration."""

    @pytest.mark.asyncio
    async def test_generate_telegram_link_code(self):
        """Test generating Telegram link code."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.set = AsyncMock()

            code = await service.generate_telegram_link_code(mock_user)

            assert code is not None
            assert len(code) == 6
            assert code.isdigit()
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_telegram_by_code_success(self):
        """Test successful Telegram linking."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with patch.object(service.user_repo, "get_by_telegram_id", return_value=None):
                    with patch.object(service.user_repo, "update_telegram", return_value=mock_user):
                        result = await service.link_telegram_by_code(
                            code="123456",
                            telegram_id=12345678,
                            telegram_username="testuser",
                        )

                        assert result == mock_user
                        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_telegram_by_code_invalid_code(self):
        """Test Telegram linking with invalid code."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await service.link_telegram_by_code(
                code="invalid",
                telegram_id=12345678,
                telegram_username="testuser",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_link_telegram_already_linked(self):
        """Test linking Telegram that's already linked to another account."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        user_id = uuid4()
        other_user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        other_user = MagicMock()
        other_user.id = other_user_id

        with patch("app.services.auth.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(user_id))
            mock_redis.delete = AsyncMock()

            with patch.object(service.user_repo, "get_by_id", return_value=mock_user):
                with patch.object(service.user_repo, "get_by_telegram_id", return_value=other_user):
                    result = await service.link_telegram_by_code(
                        code="123456",
                        telegram_id=12345678,
                        telegram_username="testuser",
                    )

                    assert result is None

    @pytest.mark.asyncio
    async def test_unlink_telegram_success(self):
        """Test successful Telegram unlinking."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.telegram_id = 12345678

        with patch.object(service.user_repo, "update", return_value=mock_user):
            result = await service.unlink_telegram(mock_user)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_unlink_telegram_not_linked(self):
        """Test unlinking when no Telegram is linked."""
        mock_db = AsyncMock()
        service = AuthService(mock_db)

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.telegram_id = None

        with pytest.raises(BadRequestError) as exc_info:
            await service.unlink_telegram(mock_user)

        assert "No Telegram" in str(exc_info.value.detail)

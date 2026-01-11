"""Unit tests for auth API endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_user(**kwargs):
    """Create a mock user with default values."""
    mock_user = MagicMock()
    mock_user.id = kwargs.get("id", uuid4())
    mock_user.email = kwargs.get("email", "test@example.com")
    mock_user.name = kwargs.get("name", "Test User")
    mock_user.email_verified = kwargs.get("email_verified", False)
    mock_user.telegram_id = kwargs.get("telegram_id", None)
    mock_user.telegram_username = kwargs.get("telegram_username", None)
    mock_user.is_active = kwargs.get("is_active", True)
    mock_user.is_superuser = kwargs.get("is_superuser", False)
    mock_user.preferred_language = kwargs.get("preferred_language", "ru")
    mock_user.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock_user.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock_user


class TestRegister:
    """Tests for register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful registration."""
        from app.api.v1.auth import register
        from app.schemas.auth import RegisterRequest, TokenResponse

        mock_db = AsyncMock()
        mock_user = create_mock_user(email="test@example.com", name="Test User")

        mock_tokens = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
        )

        request = RegisterRequest(
            email="test@example.com",
            password="password123",
            name="Test User",
        )

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.register = AsyncMock(return_value=(mock_user, mock_tokens))
            mock_auth_class.return_value = mock_auth

            result = await register(data=request, db=mock_db)

            assert result is not None
            mock_auth.register.assert_called_once()


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login."""
        from app.api.v1.auth import login
        from app.schemas.auth import TokenResponse
        from app.schemas.user import UserLogin

        mock_db = AsyncMock()
        mock_user = create_mock_user(email_verified=True)
        mock_tokens = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
        )

        request = UserLogin(
            email="test@example.com",
            password="password123",
        )

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.login = AsyncMock(return_value=(mock_user, mock_tokens))
            mock_auth_class.return_value = mock_auth

            result = await login(data=request, db=mock_db)

            assert result is not None


class TestRefreshToken:
    """Tests for refresh_token endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        from app.api.v1.auth import refresh_token
        from app.schemas.auth import RefreshTokenRequest

        mock_db = AsyncMock()
        mock_tokens = MagicMock()

        request = RefreshTokenRequest(refresh_token="valid_refresh_token")

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.refresh_tokens = AsyncMock(return_value=mock_tokens)
            mock_auth_class.return_value = mock_auth

            result = await refresh_token(data=request, db=mock_db)

            assert result == mock_tokens


class TestGetMe:
    """Tests for get_me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(self):
        """Test getting current user."""
        from app.api.v1.auth import get_me

        mock_user = create_mock_user(email_verified=True)

        result = await get_me(current_user=mock_user)

        assert result is not None


class TestUpdateMe:
    """Tests for update_me endpoint."""

    @pytest.mark.asyncio
    async def test_update_me_no_changes(self):
        """Test updating with no changes returns current user."""
        from app.api.v1.auth import update_me
        from app.schemas.user import UserUpdate

        mock_db = AsyncMock()
        mock_user = create_mock_user(email_verified=True)

        data = UserUpdate()  # Empty update

        result = await update_me(data=data, current_user=mock_user, db=mock_db)

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_me_with_name(self):
        """Test updating user name."""
        from app.api.v1.auth import update_me
        from app.schemas.user import UserUpdate

        mock_db = AsyncMock()
        mock_user = create_mock_user(email_verified=True)
        updated_user = create_mock_user(email_verified=True, name="New Name")

        data = UserUpdate(name="New Name")

        with patch("app.api.v1.auth.UserRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.update = AsyncMock(return_value=updated_user)
            mock_repo_class.return_value = mock_repo

            result = await update_me(data=data, current_user=mock_user, db=mock_db)

            assert result is not None
            mock_repo.update.assert_called_once()


class TestChangePassword:
    """Tests for change_password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Test successful password change."""
        from app.api.v1.auth import change_password
        from app.schemas.auth import PasswordChangeRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        data = PasswordChangeRequest(
            current_password="old_password",
            new_password="new_password123",
        )

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.change_password = AsyncMock()
            mock_auth_class.return_value = mock_auth

            # Should not raise
            await change_password(data=data, current_user=mock_user, db=mock_db)

            mock_auth.change_password.assert_called_once_with(
                user=mock_user,
                current_password="old_password",
                new_password="new_password123",
            )


class TestLogout:
    """Tests for logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self):
        """Test successful logout (no-op for JWT)."""
        from app.api.v1.auth import logout

        mock_user = MagicMock()

        # Should not raise and return None
        result = await logout(current_user=mock_user)

        assert result is None


class TestSendVerificationEmail:
    """Tests for send_verification_email endpoint."""

    @pytest.mark.asyncio
    async def test_send_verification_already_verified(self):
        """Test sending verification when already verified."""
        from app.api.v1.auth import send_verification_email

        mock_db = AsyncMock()
        mock_background = MagicMock()
        mock_user = MagicMock()
        mock_user.email_verified = True

        result = await send_verification_email(
            current_user=mock_user,
            db=mock_db,
            background_tasks=mock_background,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_send_verification_not_verified(self):
        """Test sending verification email."""
        from app.api.v1.auth import send_verification_email

        mock_db = AsyncMock()
        mock_background = MagicMock()
        mock_user = MagicMock()
        mock_user.email_verified = False
        mock_user.name = "Test"
        mock_user.email = "test@example.com"

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.send_email_verification = AsyncMock(return_value="token123")
            mock_auth_class.return_value = mock_auth

            with patch("app.api.v1.auth.settings") as mock_settings:
                mock_settings.cors_origins = ["https://cronbox.ru"]

                await send_verification_email(
                    current_user=mock_user,
                    db=mock_db,
                    background_tasks=mock_background,
                )

                mock_auth.send_email_verification.assert_called_once()
                mock_background.add_task.assert_called_once()


class TestVerifyEmail:
    """Tests for verify_email endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
        """Test successful email verification."""
        from app.api.v1.auth import verify_email
        from app.schemas.auth import EmailVerificationRequest

        mock_db = AsyncMock()
        mock_user = create_mock_user(email_verified=True)

        data = EmailVerificationRequest(token="valid_token")

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.verify_email = AsyncMock(return_value=mock_user)
            mock_auth_class.return_value = mock_auth

            result = await verify_email(data=data, db=mock_db)

            assert result is not None


class TestForgotPassword:
    """Tests for forgot_password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_user_exists(self):
        """Test password reset request for existing user."""
        from app.api.v1.auth import forgot_password
        from app.schemas.auth import PasswordResetRequest

        mock_db = AsyncMock()
        mock_background = MagicMock()

        data = PasswordResetRequest(email="test@example.com")

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.request_password_reset = AsyncMock(return_value="reset_token")
            mock_auth_class.return_value = mock_auth

            with patch("app.api.v1.auth.settings") as mock_settings:
                mock_settings.cors_origins = ["https://cronbox.ru"]

                await forgot_password(
                    data=data,
                    db=mock_db,
                    background_tasks=mock_background,
                )

                mock_auth.request_password_reset.assert_called_once()
                mock_background.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_user_not_found(self):
        """Test password reset for non-existing user (silent)."""
        from app.api.v1.auth import forgot_password
        from app.schemas.auth import PasswordResetRequest

        mock_db = AsyncMock()
        mock_background = MagicMock()

        data = PasswordResetRequest(email="nonexistent@example.com")

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.request_password_reset = AsyncMock(return_value=None)
            mock_auth_class.return_value = mock_auth

            await forgot_password(
                data=data,
                db=mock_db,
                background_tasks=mock_background,
            )

            # Email should NOT be sent for non-existing user
            mock_background.add_task.assert_not_called()


class TestResetPassword:
    """Tests for reset_password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Test successful password reset."""
        from app.api.v1.auth import reset_password
        from app.schemas.auth import PasswordResetConfirm

        mock_db = AsyncMock()

        data = PasswordResetConfirm(
            token="valid_reset_token",
            new_password="new_password123",
        )

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.reset_password = AsyncMock()
            mock_auth_class.return_value = mock_auth

            await reset_password(data=data, db=mock_db)

            mock_auth.reset_password.assert_called_once_with(
                "valid_reset_token",
                "new_password123",
            )


class TestTelegramConnect:
    """Tests for telegram_connect endpoint."""

    @pytest.mark.asyncio
    async def test_telegram_connect_success(self):
        """Test generating Telegram connect code."""
        from app.api.v1.auth import telegram_connect

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.generate_telegram_link_code = AsyncMock(return_value="ABC123")
            mock_auth_class.return_value = mock_auth

            with patch("app.api.v1.auth.settings") as mock_settings:
                mock_settings.telegram_bot_token = "123456:ABC"

                result = await telegram_connect(current_user=mock_user, db=mock_db)

                assert result.code == "ABC123"
                assert result.bot_username == "cronbox_bot"

    @pytest.mark.asyncio
    async def test_telegram_connect_no_token(self):
        """Test Telegram connect without configured token."""
        from app.api.v1.auth import telegram_connect

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.generate_telegram_link_code = AsyncMock(return_value="XYZ789")
            mock_auth_class.return_value = mock_auth

            with patch("app.api.v1.auth.settings") as mock_settings:
                mock_settings.telegram_bot_token = None

                result = await telegram_connect(current_user=mock_user, db=mock_db)

                assert result.code == "XYZ789"
                assert result.bot_username == "cronbox_bot"


class TestTelegramDisconnect:
    """Tests for telegram_disconnect endpoint."""

    @pytest.mark.asyncio
    async def test_telegram_disconnect_success(self):
        """Test unlinking Telegram account."""
        from app.api.v1.auth import telegram_disconnect

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("app.api.v1.auth.AuthService") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.unlink_telegram = AsyncMock()
            mock_auth_class.return_value = mock_auth

            await telegram_disconnect(current_user=mock_user, db=mock_db)

            mock_auth.unlink_telegram.assert_called_once_with(mock_user)

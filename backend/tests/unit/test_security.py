"""Tests for security module."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_email_token,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_string(self):
        """Test that password hash returns a string."""
        password = "securepassword123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_get_password_hash_is_different_each_time(self):
        """Test that hashing same password gives different results (due to salt)."""
        password = "securepassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "mySecureP@ssword!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        password = "correctPassword123"
        wrong_password = "wrongPassword456"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        password = "somePassword"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_get_password_hash_unicode(self):
        """Test password hashing with unicode characters."""
        password = "пароль123密码"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_get_password_hash_special_characters(self):
        """Test password hashing with special characters."""
        password = "P@$$w0rd!#%^&*(){}[]|\\:\";<>,.?/"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = uuid4()
        email = "test@example.com"

        token = create_access_token(user_id, email)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT format: header.payload.signature
        assert token.count(".") == 2

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = uuid4()

        token = create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_decode_access_token(self):
        """Test decoding access token."""
        user_id = uuid4()
        email = "test@example.com"

        token = create_access_token(user_id, email)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_decode_refresh_token(self):
        """Test decoding refresh token."""
        user_id = uuid4()

        token = create_refresh_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        invalid_token = "not.a.valid.token"

        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_expired_token(self):
        """Test decoding expired token returns None."""
        user_id = uuid4()
        email = "test@example.com"

        # Create token with mocked time in the past
        with patch("app.core.security.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc) - timedelta(days=365)
            token = create_access_token(user_id, email)

        # Try to decode - should fail because token is expired
        payload = decode_token(token)
        assert payload is None

    def test_decode_malformed_token(self):
        """Test decoding malformed JWT."""
        malformed_tokens = [
            "",
            "abc",
            "a.b",
            "a.b.c.d",
            "eyJhbGciOiJIUzI1NiJ9.invalid.signature",
        ]

        for token in malformed_tokens:
            payload = decode_token(token)
            assert payload is None, f"Token '{token}' should return None"

    def test_access_token_different_users(self):
        """Test that different users get different tokens."""
        user1_id = uuid4()
        user2_id = uuid4()

        token1 = create_access_token(user1_id, "user1@example.com")
        token2 = create_access_token(user2_id, "user2@example.com")

        assert token1 != token2


class TestEmailVerificationToken:
    """Tests for email verification tokens."""

    def test_create_email_verification_token(self):
        """Test email verification token creation."""
        email = "verify@example.com"

        token = create_email_verification_token(email)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_verify_email_token_valid(self):
        """Test verifying valid email token."""
        email = "verify@example.com"

        token = create_email_verification_token(email)
        result = verify_email_token(token)

        assert result == email

    def test_verify_email_token_invalid(self):
        """Test verifying invalid email token."""
        result = verify_email_token("invalid.token.here")

        assert result is None

    def test_verify_email_token_wrong_type(self):
        """Test verifying token of wrong type."""
        # Create an access token (type: access, not email_verification)
        user_id = uuid4()
        access_token = create_access_token(user_id, "test@example.com")

        result = verify_email_token(access_token)

        assert result is None

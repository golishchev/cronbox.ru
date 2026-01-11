"""Tests for configuration module."""
import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test default configuration values."""
        # Create settings without env file
        with patch.dict(os.environ, {}, clear=False):
            settings = Settings()

            assert settings.app_name == "CronBox"
            assert settings.debug is False
            assert settings.environment == "development"
            assert settings.access_token_expire_minutes == 15
            assert settings.refresh_token_expire_days == 30

    def test_jwt_settings(self):
        """Test JWT configuration."""
        settings = Settings()

        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes > 0
        assert settings.refresh_token_expire_days > 0

    def test_rate_limit_settings(self):
        """Test rate limiting configuration."""
        settings = Settings()

        assert settings.auth_rate_limit_login > 0
        assert settings.auth_rate_limit_register > 0
        assert settings.auth_rate_limit_password_reset > 0

    def test_account_lockout_settings(self):
        """Test account lockout configuration."""
        settings = Settings()

        assert settings.max_failed_login_attempts == 5
        assert settings.account_lockout_minutes == 15

    def test_cors_origins(self):
        """Test CORS origins configuration."""
        settings = Settings()

        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) > 0

    def test_api_prefix(self):
        """Test API prefix configuration."""
        settings = Settings()

        assert settings.api_prefix == "/v1"

    def test_database_url_format(self):
        """Test database URL has correct format."""
        settings = Settings()

        assert "postgresql+asyncpg://" in settings.database_url

    def test_redis_url_format(self):
        """Test Redis URL has correct format."""
        settings = Settings()

        assert "redis://" in settings.redis_url

    def test_email_settings(self):
        """Test email configuration defaults."""
        settings = Settings()

        assert settings.smtp_port == 587
        assert settings.smtp_use_tls is True
        assert "CronBox" in settings.email_from

    def test_settings_cached(self):
        """Test get_settings returns cached instance."""
        # Clear the cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_debug_override(self):
        """Test debug can be overridden."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = Settings()
            assert settings.debug is True

    def test_environment_override(self):
        """Test environment can be overridden."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = Settings()
            assert settings.environment == "production"

    def test_jwt_secret_override(self):
        """Test JWT secret can be overridden."""
        with patch.dict(os.environ, {"JWT_SECRET": "my-secret-key"}):
            settings = Settings()
            assert settings.jwt_secret == "my-secret-key"

    def test_access_token_expire_override(self):
        """Test access token expiration can be overridden."""
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "30"}):
            settings = Settings()
            assert settings.access_token_expire_minutes == 30

    def test_cors_origins_override(self):
        """Test CORS origins can be overridden."""
        with patch.dict(os.environ, {"CORS_ORIGINS": '["https://example.com"]'}):
            settings = Settings()
            assert "https://example.com" in settings.cors_origins

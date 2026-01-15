from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "CronBox"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://cronbox:cronbox@localhost:5432/cronbox"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-jwt-secret"

    # Security settings
    # Rate limiting for auth endpoints (requests per minute)
    auth_rate_limit_login: int = 5
    auth_rate_limit_register: int = 3
    auth_rate_limit_password_reset: int = 3
    # Rate limiting for public endpoints (requests per minute per IP)
    public_rate_limit: int = 30
    # Account lockout
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15

    # OTP settings
    otp_code_length: int = 6
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5
    otp_request_cooldown_seconds: int = 60

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_webhook_secret: str = ""  # For webhook signature verification

    # Telegram
    telegram_bot_token: str = ""

    # Email (SMTP fallback)
    smtp_host: str = "smtp.yandex.ru"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = "CronBox <noreply@cronbox.ru>"

    # Postal (optional, disabled by default)
    postal_api_url: str = ""  # e.g., https://postal.example.com
    postal_api_key: str = ""  # API credential key
    postal_webhook_secret: str = ""  # For webhook signature verification
    postal_server_key: str = ""  # Server key for sending
    use_postal: bool = False  # Set to True to use Postal instead of SMTP

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:3000"

    # API URL (for email links that need backend redirects)
    api_url: str = "http://localhost:8000"

    # API
    api_prefix: str = "/v1"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

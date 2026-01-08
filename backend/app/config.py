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
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://cronbox:cronbox@localhost:5432/cronbox"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Email (SMTP fallback)
    smtp_host: str = "smtp.yandex.ru"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = "CronBox <noreply@cronbox.ru>"

    # Postal (primary email service)
    postal_api_url: str = ""  # e.g., https://postal.example.com
    postal_api_key: str = ""  # API credential key
    postal_webhook_secret: str = ""  # For webhook signature verification
    postal_server_key: str = ""  # Server key for sending
    use_postal: bool = True  # Use Postal instead of SMTP

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # API
    api_prefix: str = "/v1"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

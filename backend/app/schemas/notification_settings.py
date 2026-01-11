"""Notification settings schemas."""
from uuid import UUID

from pydantic import BaseModel


class NotificationSettingsBase(BaseModel):
    """Base notification settings schema."""

    telegram_enabled: bool = False
    telegram_chat_ids: list[str] | None = None

    email_enabled: bool = False
    email_addresses: list[str] | None = None

    webhook_enabled: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None

    notify_on_failure: bool = True
    notify_on_recovery: bool = True
    notify_on_success: bool = False


class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings."""

    telegram_enabled: bool | None = None
    telegram_chat_ids: list[str] | None = None

    email_enabled: bool | None = None
    email_addresses: list[str] | None = None

    webhook_enabled: bool | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None

    notify_on_failure: bool | None = None
    notify_on_recovery: bool | None = None
    notify_on_success: bool | None = None


class NotificationSettingsResponse(NotificationSettingsBase):
    """Response schema for notification settings."""

    id: UUID
    workspace_id: UUID

    class Config:
        from_attributes = True


class TelegramLinkRequest(BaseModel):
    """Request to link Telegram account."""

    code: str


class TelegramLinkResponse(BaseModel):
    """Response for Telegram link."""

    success: bool
    message: str
    chat_id: str | None = None


class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""

    channel: str  # "telegram", "email", "webhook"

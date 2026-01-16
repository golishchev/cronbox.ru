"""Notification template model for multilingual notifications."""

import enum

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel."""

    EMAIL = "email"
    TELEGRAM = "telegram"


class NotificationTemplate(Base, UUIDMixin, TimestampMixin):
    """Notification template for multilingual notifications."""

    __tablename__ = "notification_templates"

    # Template identification
    code: Mapped[str] = mapped_column(String(100), index=True)
    language: Mapped[str] = mapped_column(String(5), index=True)  # ru, en
    channel: Mapped[NotificationChannel] = mapped_column(SQLEnum(NotificationChannel), index=True)

    # Content
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Only for email
    body: Mapped[str] = mapped_column(Text)  # Main text / HTML

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # For admin UI
    variables: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )  # Available variables like ["workspace_name", "task_name"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("code", "language", "channel", name="uq_template_code_lang_channel"),)

    def __repr__(self) -> str:
        return f"<NotificationTemplate {self.code}/{self.language}/{self.channel.value}>"

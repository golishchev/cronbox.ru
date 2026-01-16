from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationSettings(Base, UUIDMixin, TimestampMixin):
    """Notification settings model for a workspace."""

    __tablename__ = "notification_settings"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Telegram
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_ids: Mapped[list[int] | None] = mapped_column(ARRAY(String), nullable=True, default=list)

    # Email
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_addresses: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)

    # Webhook
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # What to notify about
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="notification_settings")

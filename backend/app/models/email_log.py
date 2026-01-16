"""Email log model for tracking sent emails."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class EmailStatus(str, enum.Enum):
    """Email delivery status."""

    QUEUED = "queued"  # Accepted by Postal, in queue
    SENT = "sent"  # Sent to recipient's mail server
    DELIVERED = "delivered"  # Confirmed delivered
    OPENED = "opened"  # Email opened (if tracking enabled)
    CLICKED = "clicked"  # Link clicked (if tracking enabled)
    BOUNCED = "bounced"  # Hard or soft bounce
    FAILED = "failed"  # Failed to send
    HELD = "held"  # Held by Postal (spam, etc.)


class EmailType(str, enum.Enum):
    """Type of email notification."""

    TASK_FAILURE = "task_failure"
    TASK_RECOVERY = "task_recovery"
    TASK_SUCCESS = "task_success"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


class EmailLog(Base, UUIDMixin, TimestampMixin):
    """Email log model - tracks all sent emails and their delivery status."""

    __tablename__ = "email_logs"

    # Workspace (optional, for task-related emails)
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # User who triggered the email (optional)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Email details
    to_email: Mapped[str] = mapped_column(String(255), index=True)
    from_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500))
    email_type: Mapped[EmailType] = mapped_column(
        SQLEnum(EmailType),
        default=EmailType.OTHER,
        index=True,
    )

    # Content (stored for debugging/resend)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Postal tracking
    postal_message_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    postal_server: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status tracking
    status: Mapped[EmailStatus] = mapped_column(
        SQLEnum(EmailStatus),
        default=EmailStatus.QUEUED,
        index=True,
    )
    status_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Delivery timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tracking stats
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)

    # Bounce details
    bounce_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # hard, soft
    bounce_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bounce_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extra metadata
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship()

    def mark_sent(self, postal_message_id: str, postal_server: str | None = None):
        """Mark email as sent."""
        self.status = EmailStatus.SENT
        self.postal_message_id = postal_message_id
        self.postal_server = postal_server
        self.sent_at = datetime.now()

    def mark_delivered(self):
        """Mark email as delivered."""
        self.status = EmailStatus.DELIVERED
        self.delivered_at = datetime.now()

    def mark_opened(self):
        """Mark email as opened."""
        if self.status not in (EmailStatus.BOUNCED, EmailStatus.FAILED):
            self.status = EmailStatus.OPENED
        if not self.opened_at:
            self.opened_at = datetime.now()
        self.open_count += 1

    def mark_clicked(self, url: str | None = None):
        """Mark email link as clicked."""
        if self.status not in (EmailStatus.BOUNCED, EmailStatus.FAILED):
            self.status = EmailStatus.CLICKED
        if not self.clicked_at:
            self.clicked_at = datetime.now()
        self.click_count += 1

    def mark_bounced(self, bounce_type: str, code: str | None, message: str | None):
        """Mark email as bounced."""
        self.status = EmailStatus.BOUNCED
        self.bounced_at = datetime.now()
        self.bounce_type = bounce_type
        self.bounce_code = code
        self.bounce_message = message

    def mark_failed(self, reason: str):
        """Mark email as failed."""
        self.status = EmailStatus.FAILED
        self.failed_at = datetime.now()
        self.status_details = reason

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SSLMonitorStatus(str, enum.Enum):
    """SSL monitor status."""

    PENDING = "pending"  # Initial state, not yet checked
    VALID = "valid"  # Certificate is valid and not expiring soon
    EXPIRING = "expiring"  # Certificate expiring within 14 days
    EXPIRED = "expired"  # Certificate has expired
    INVALID = "invalid"  # Certificate validation failed (chain, hostname, etc.)
    ERROR = "error"  # Connection or other error
    PAUSED = "paused"  # Monitoring paused


class SSLMonitor(Base, UUIDMixin, TimestampMixin):
    """SSL Certificate Monitor model."""

    __tablename__ = "ssl_monitors"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Target
    domain: Mapped[str] = mapped_column(String(255), index=True)
    port: Mapped[int] = mapped_column(Integer, default=443)

    # State
    status: Mapped[SSLMonitorStatus] = mapped_column(
        SQLEnum(
            SSLMonitorStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SSLMonitorStatus.PENDING,
    )
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Certificate info (from last check)
    issuer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(nullable=True)
    days_until_expiry: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # TLS info
    tls_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cipher_suite: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Chain info
    chain_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hostname_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Check tracking
    last_check_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_check_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retry logic (3 retries with 1 hour interval)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    # Notification tracking
    # Stores the last days_until_expiry value for which notification was sent
    # to avoid duplicate notifications (e.g., 14, 7, 3, 1)
    last_notification_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify_on_expiring: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_error: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="ssl_monitors")

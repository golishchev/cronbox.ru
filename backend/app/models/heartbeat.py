import enum
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class HeartbeatStatus(str, enum.Enum):
    """Heartbeat monitor status."""

    WAITING = "waiting"  # First ping not yet received
    HEALTHY = "healthy"  # Pings arriving on time
    LATE = "late"  # Grace period expired, alert sent
    DEAD = "dead"  # No pings for 3+ intervals
    PAUSED = "paused"  # Monitoring paused (maintenance)


class Heartbeat(Base, UUIDMixin, TimestampMixin):
    """Heartbeat monitor model - Dead Man's Switch."""

    __tablename__ = "heartbeats"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Unique ping token for URL
    ping_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(16),
    )

    # Schedule - interval in seconds (e.g., 3600 for 1h)
    expected_interval: Mapped[int] = mapped_column(Integer)
    # Grace period in seconds before alert (e.g., 600 for 10m)
    grace_period: Mapped[int] = mapped_column(Integer, default=600)

    # State
    status: Mapped[HeartbeatStatus] = mapped_column(
        SQLEnum(HeartbeatStatus),
        default=HeartbeatStatus.WAITING,
    )
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Ping tracking
    last_ping_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_expected_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)

    # Alert tracking
    last_alert_at: Mapped[datetime | None] = mapped_column(nullable=True)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notifications - override workspace defaults if needed
    notify_on_late: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="heartbeats")
    pings: Mapped[list["HeartbeatPing"]] = relationship(
        back_populates="heartbeat",
        cascade="all, delete-orphan",
        order_by="desc(HeartbeatPing.created_at)",
    )


class HeartbeatPing(Base, UUIDMixin, TimestampMixin):
    """Record of individual pings received for a heartbeat monitor."""

    __tablename__ = "heartbeat_pings"

    heartbeat_id: Mapped[UUID] = mapped_column(
        ForeignKey("heartbeats.id", ondelete="CASCADE"),
        index=True,
    )

    # Optional payload data from ping
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Source info
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    heartbeat: Mapped["Heartbeat"] = relationship(back_populates="pings")

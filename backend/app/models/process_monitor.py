"""Process Monitor model for tracking long-running processes with START/END signals."""

import enum
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProcessMonitorStatus(str, enum.Enum):
    """Process monitor status."""

    WAITING_START = "waiting_start"  # Waiting for start signal
    RUNNING = "running"  # Start received, waiting for end
    COMPLETED = "completed"  # Successfully completed
    MISSED_START = "missed_start"  # Start not received in time
    MISSED_END = "missed_end"  # End not received within timeout
    PAUSED = "paused"  # Monitoring paused


class ScheduleType(str, enum.Enum):
    """Schedule type for process monitor."""

    CRON = "cron"  # Cron expression (e.g., "0 17 * * *")
    INTERVAL = "interval"  # Interval in seconds
    EXACT_TIME = "exact_time"  # Exact time (e.g., "17:00")


class ConcurrencyPolicy(str, enum.Enum):
    """Concurrency policy for handling overlapping process runs."""

    SKIP = "skip"  # Reject new start if already running (default)
    REPLACE = "replace"  # Timeout current run, start new one


class ProcessMonitorEventType(str, enum.Enum):
    """Process monitor event type."""

    START = "start"  # Start signal received
    END = "end"  # End signal received
    TIMEOUT = "timeout"  # End timeout occurred
    MISSED = "missed"  # Start not received in time


class ProcessMonitor(Base, UUIDMixin, TimestampMixin):
    """Process monitor model - tracks long-running processes with paired START/END signals."""

    __tablename__ = "process_monitors"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Two unique tokens for URL1 (start) and URL2 (end)
    start_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(16),
    )
    end_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(16),
    )

    # Schedule configuration
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SQLEnum(
            ScheduleType,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ScheduleType.CRON,
    )
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "0 17 * * *"
    schedule_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    schedule_exact_time: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "17:00"
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Concurrency policy
    concurrency_policy: Mapped[ConcurrencyPolicy] = mapped_column(
        SQLEnum(ConcurrencyPolicy, values_callable=lambda obj: [e.value for e in obj]),
        default=ConcurrencyPolicy.SKIP,
    )

    # Timeouts (in seconds)
    start_grace_period: Mapped[int] = mapped_column(Integer, default=300)  # 5 minutes
    end_timeout: Mapped[int] = mapped_column(Integer, default=3600)  # 1 hour

    # State
    status: Mapped[ProcessMonitorStatus] = mapped_column(
        SQLEnum(
            ProcessMonitorStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ProcessMonitorStatus.WAITING_START,
    )
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tracking
    last_start_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_end_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_expected_start: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    start_deadline: Mapped[datetime | None] = mapped_column(nullable=True)
    end_deadline: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    current_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # UUID of current run

    # Counters
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # Notification settings
    notify_on_missed_start: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_missed_end: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="process_monitors")
    events: Mapped[list["ProcessMonitorEvent"]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="desc(ProcessMonitorEvent.created_at)",
    )


class ProcessMonitorEvent(Base, UUIDMixin, TimestampMixin):
    """Record of individual events for a process monitor."""

    __tablename__ = "process_monitor_events"

    monitor_id: Mapped[UUID] = mapped_column(
        ForeignKey("process_monitors.id", ondelete="CASCADE"),
        index=True,
    )

    # Event info
    event_type: Mapped[ProcessMonitorEventType] = mapped_column(
        SQLEnum(
            ProcessMonitorEventType,
            values_callable=lambda obj: [e.value for e in obj],
        ),
    )
    run_id: Mapped[str] = mapped_column(String(36), index=True)  # Groups start/end of same run
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Source info
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    monitor: Mapped["ProcessMonitor"] = relationship(back_populates="events")

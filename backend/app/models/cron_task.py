import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class HttpMethod(str, enum.Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"


class TaskStatus(str, enum.Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CronTask(Base, UUIDMixin, TimestampMixin):
    """Cron task model - recurring HTTP requests."""

    __tablename__ = "cron_tasks"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Optional: assign to specific worker (for user-hosted workers)
    # If None, task will be executed by cloud workers
    worker_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # HTTP Request
    url: Mapped[str] = mapped_column(String(2048))
    method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod), default=HttpMethod.GET)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule
    schedule: Mapped[str] = mapped_column(String(100))  # Cron expression
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Execution settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_status: Mapped[TaskStatus | None] = mapped_column(SQLEnum(TaskStatus), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(index=True, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # Notifications
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="cron_tasks")
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="cron_task",
        cascade="all, delete-orphan",
    )

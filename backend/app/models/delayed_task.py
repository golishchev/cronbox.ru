from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus


class DelayedTask(Base, UUIDMixin, TimestampMixin):
    """Delayed task model - one-time HTTP requests at a specific time."""

    __tablename__ = "delayed_tasks"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_delayed_idempotency"),)

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
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # Protocol type (http, icmp, tcp)
    protocol_type: Mapped[ProtocolType] = mapped_column(
        SQLEnum(ProtocolType, values_callable=lambda x: [e.value for e in x], create_type=False),
        default=ProtocolType.HTTP,
    )

    # HTTP Request (used when protocol_type = HTTP)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod), default=HttpMethod.POST)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ICMP/TCP (used when protocol_type = ICMP or TCP)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)  # TCP only
    icmp_count: Mapped[int] = mapped_column(Integer, default=3)  # ICMP only: number of packets

    # Schedule
    execute_at: Mapped[datetime] = mapped_column(index=True)

    # Execution settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # State
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        index=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)

    # Callback
    callback_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="delayed_tasks")

"""Task Chain models for HTTP request chain scheduling."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.cron_task import HttpMethod


class TriggerType(str, enum.Enum):
    """Chain trigger type."""

    CRON = "cron"
    DELAYED = "delayed"
    MANUAL = "manual"


class ChainStatus(str, enum.Enum):
    """Chain execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded, some failed
    CANCELLED = "cancelled"


class TaskChain(Base, UUIDMixin, TimestampMixin):
    """Task Chain model - a sequence of HTTP requests."""

    __tablename__ = "task_chains"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Optional: assign to specific worker
    worker_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # Trigger settings
    trigger_type: Mapped[TriggerType] = mapped_column(
        SQLEnum(TriggerType, values_callable=lambda x: [e.value for e in x], create_type=False),
        default=TriggerType.MANUAL
    )
    schedule: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Cron expression for cron trigger
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    execute_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )  # For delayed trigger

    # Execution settings
    stop_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)  # Total chain timeout

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_status: Mapped[ChainStatus | None] = mapped_column(
        SQLEnum(ChainStatus, values_callable=lambda x: [e.value for e in x], create_type=False),
        nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(index=True, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # Notifications
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_on_partial: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="task_chains")
    steps: Mapped[list["ChainStep"]] = relationship(
        back_populates="chain",
        cascade="all, delete-orphan",
        order_by="ChainStep.step_order",
    )
    executions: Mapped[list["ChainExecution"]] = relationship(
        back_populates="chain",
        cascade="all, delete-orphan",
    )


class ChainStep(Base, UUIDMixin, TimestampMixin):
    """Chain Step model - a single HTTP request in a chain."""

    __tablename__ = "chain_steps"

    chain_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_chains.id", ondelete="CASCADE"),
        index=True,
    )

    # Order and identification
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))

    # HTTP Request (supports {{variable}} placeholders)
    url: Mapped[str] = mapped_column(String(2048))
    method: Mapped[HttpMethod] = mapped_column(
        SQLEnum(HttpMethod, values_callable=lambda x: [e.value for e in x], create_type=False),
        default=HttpMethod.GET
    )
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=5)

    # Condition for execution (skip if not met)
    # Example: {"operator": "status_code_in", "value": [200, 201]}
    # Example: {"operator": "equals", "field": "$.status", "value": "approved"}
    condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Variables to extract from response (JSONPath expressions)
    # Example: {"order_id": "$.data.id", "status": "$.data.status"}
    extract_variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Continue even if this step fails
    continue_on_failure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    chain: Mapped["TaskChain"] = relationship(back_populates="steps")
    step_executions: Mapped[list["StepExecution"]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
    )

"""Chain execution models for tracking chain and step execution history."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin
from app.models.cron_task import HttpMethod
from app.models.task_chain import ChainStatus


class StepStatus(str, enum.Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # Condition not met or chain stopped


class ChainExecution(Base, UUIDMixin):
    """Chain Execution model - stores results of chain executions."""

    __tablename__ = "chain_executions"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    chain_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_chains.id", ondelete="CASCADE"),
        index=True,
    )

    # Execution status
    status: Mapped[ChainStatus] = mapped_column(
        SQLEnum(ChainStatus, values_callable=lambda x: [e.value for e in x], create_type=False),
        default=ChainStatus.PENDING,
    )
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Step counts
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    failed_steps: Mapped[int] = mapped_column(Integer, default=0)
    skipped_steps: Mapped[int] = mapped_column(Integer, default=0)

    # Accumulated variables during execution
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Error info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    chain: Mapped["TaskChain"] = relationship(back_populates="executions")
    step_executions: Mapped[list["StepExecution"]] = relationship(
        back_populates="chain_execution",
        cascade="all, delete-orphan",
        order_by="StepExecution.step_order",
    )


class StepExecution(Base, UUIDMixin):
    """Step Execution model - stores results of individual step executions."""

    __tablename__ = "step_executions"

    chain_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("chain_executions.id", ondelete="CASCADE"),
        index=True,
    )

    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("chain_steps.id", ondelete="SET NULL"),
        nullable=True,  # Step might be deleted after execution
        index=True,
    )

    # Step order at time of execution
    step_order: Mapped[int] = mapped_column(Integer)
    step_name: Mapped[str] = mapped_column(String(255))

    # Execution status
    status: Mapped[StepStatus] = mapped_column(
        SQLEnum(StepStatus, values_callable=lambda x: [e.value for e in x], create_type=False)
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)

    # Request (after variable substitution)
    request_url: Mapped[str] = mapped_column(String(2048))
    request_method: Mapped[HttpMethod] = mapped_column(
        SQLEnum(HttpMethod, values_callable=lambda x: [e.value for e in x], create_type=False)
    )
    request_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Variables extracted from response
    extracted_variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Condition evaluation
    condition_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    condition_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    chain_execution: Mapped["ChainExecution"] = relationship(back_populates="step_executions")
    step: Mapped["ChainStep | None"] = relationship(back_populates="step_executions")

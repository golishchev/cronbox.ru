"""Task Queue model for overlap prevention queue strategy."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class TaskQueue(Base, UUIDMixin):
    """Task Queue model - stores queued tasks for overlap prevention."""

    __tablename__ = "task_queue"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Task reference
    task_type: Mapped[str] = mapped_column(String(20))  # 'cron' or 'chain'
    task_id: Mapped[UUID] = mapped_column(index=True)
    task_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Queue settings
    priority: Mapped[int] = mapped_column(Integer, default=0)
    queued_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    scheduled_for: Mapped[datetime | None] = mapped_column(nullable=True)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)

    # Variables for chain execution
    initial_variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    workspace: Mapped["Workspace"] = relationship()

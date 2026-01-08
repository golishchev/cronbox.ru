"""Worker model for external task execution."""
import secrets
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class WorkerStatus(str, Enum):
    """Worker status enum."""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class Worker(Base, UUIDMixin, TimestampMixin):
    """
    External worker that can execute HTTP tasks.

    Workers register with the API and poll for tasks assigned to them.
    This enables users to run workers on their own infrastructure
    to access internal APIs not reachable from the cloud.
    """

    __tablename__ = "workers"

    # Workspace relation
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Worker info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Authentication - store hashed API key
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # First 8 chars for identification

    # Status
    status: Mapped[WorkerStatus] = mapped_column(
        String(20),
        default=WorkerStatus.OFFLINE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Location/region (optional, for geo-distributed workers)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Heartbeat tracking
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Statistics
    tasks_completed: Mapped[int] = mapped_column(default=0, nullable=False)
    tasks_failed: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="workers")

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key for the worker."""
        return f"wk_{secrets.token_urlsafe(32)}"

    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the prefix of an API key for identification."""
        return api_key[:11] if len(api_key) >= 11 else api_key

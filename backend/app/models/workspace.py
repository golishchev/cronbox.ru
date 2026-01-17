from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Workspace(Base, UUIDMixin, TimestampMixin):
    """Workspace model - container for tasks."""

    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("slug", "owner_id", name="uq_workspaces_slug_owner"),)

    # Identification
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), index=True)

    # Owner
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Blocking (for users who downgraded from paid plan)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Usage counters
    cron_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    delayed_tasks_this_month: Mapped[int] = mapped_column(Integer, default=0)
    task_chains_count: Mapped[int] = mapped_column(Integer, default=0)
    heartbeats_count: Mapped[int] = mapped_column(Integer, default=0)

    # Settings
    default_timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    webhook_secret: Mapped[str] = mapped_column(String(255))

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="workspaces")
    cron_tasks: Mapped[list["CronTask"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    delayed_tasks: Mapped[list["DelayedTask"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    notification_settings: Mapped["NotificationSettings | None"] = relationship(
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
    )
    workers: Mapped[list["Worker"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    task_chains: Mapped[list["TaskChain"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    heartbeats: Mapped[list["Heartbeat"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBase(BaseModel):
    """Base workspace schema."""

    name: str = Field(..., min_length=1, max_length=255)
    default_timezone: str = Field(default="Europe/Moscow", max_length=50)


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace."""

    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace."""

    name: str | None = Field(None, min_length=1, max_length=255)
    default_timezone: str | None = Field(None, max_length=50)


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    owner_id: UUID
    is_blocked: bool = False
    blocked_at: datetime | None = None
    cron_tasks_count: int
    delayed_tasks_this_month: int
    created_at: datetime
    updated_at: datetime


class WorkspaceWithStats(WorkspaceResponse):
    """Workspace with additional statistics."""

    plan_name: str | None = None
    active_cron_tasks: int = 0
    pending_delayed_tasks: int = 0
    executions_today: int = 0
    success_rate_7d: float = 0.0

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.cron_task import HttpMethod, TaskStatus
from app.schemas.cron_task import PaginationMeta


class DelayedTaskBase(BaseModel):
    """Base delayed task schema."""

    url: HttpUrl
    method: HttpMethod = HttpMethod.POST
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    execute_at: datetime
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)
    callback_url: HttpUrl | None = None
    worker_id: UUID | None = Field(
        None,
        description="ID of the external worker to execute this task. If None, cloud workers will be used.",
    )


class DelayedTaskCreate(DelayedTaskBase):
    """Schema for creating a delayed task."""

    idempotency_key: str | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)


class DelayedTaskResponse(BaseModel):
    """Schema for delayed task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    worker_id: UUID | None
    idempotency_key: str | None
    name: str | None
    tags: list
    url: str
    method: HttpMethod
    headers: dict
    body: str | None
    execute_at: datetime
    timeout_seconds: int
    retry_count: int
    retry_delay_seconds: int
    status: TaskStatus
    executed_at: datetime | None
    retry_attempt: int
    callback_url: str | None
    created_at: datetime
    updated_at: datetime


class DelayedTaskListResponse(BaseModel):
    """Schema for delayed task list response."""

    tasks: list[DelayedTaskResponse]
    pagination: PaginationMeta

from datetime import datetime
from uuid import UUID

import pytz
from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator

from app.models.cron_task import HttpMethod, TaskStatus


class CronTaskBase(BaseModel):
    """Base cron task schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    url: HttpUrl
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    schedule: str = Field(..., description="Cron expression (e.g., '0 3 * * *')")
    timezone: str = Field(default="Europe/Moscow")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)
    notify_on_failure: bool = True
    notify_on_recovery: bool = True
    worker_id: UUID | None = Field(
        None,
        description="ID of the external worker to execute this task. If None, cloud workers will be used.",
    )

    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        try:
            croniter(v)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression: {e}") from e
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class CronTaskCreate(CronTaskBase):
    """Schema for creating a cron task."""

    pass


class CronTaskUpdate(BaseModel):
    """Schema for updating a cron task."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    url: HttpUrl | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule: str | None = None
    timezone: str | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_count: int | None = Field(None, ge=0, le=10)
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_recovery: bool | None = None
    worker_id: UUID | None = None

    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            croniter(v)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression: {e}") from e
        return v


class CronTaskResponse(BaseModel):
    """Schema for cron task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    worker_id: UUID | None
    name: str
    description: str | None
    url: str
    method: HttpMethod
    headers: dict
    body: str | None
    schedule: str
    timezone: str
    timeout_seconds: int
    retry_count: int
    retry_delay_seconds: int
    is_active: bool
    is_paused: bool
    last_run_at: datetime | None
    last_status: TaskStatus | None
    next_run_at: datetime | None
    consecutive_failures: int
    notify_on_failure: bool
    notify_on_recovery: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_run_at", "next_run_at", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    limit: int
    total: int
    total_pages: int


class CronTaskListResponse(BaseModel):
    """Schema for cron task list response."""

    tasks: list[CronTaskResponse]
    pagination: PaginationMeta

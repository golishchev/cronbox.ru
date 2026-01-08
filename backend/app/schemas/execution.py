from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.cron_task import HttpMethod, TaskStatus
from app.schemas.cron_task import PaginationMeta


class ExecutionResponse(BaseModel):
    """Schema for execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    task_type: str
    task_id: UUID
    task_name: str | None
    status: TaskStatus
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    retry_attempt: int
    request_url: str
    request_method: HttpMethod
    response_status_code: int | None
    error_message: str | None
    error_type: str | None
    created_at: datetime


class ExecutionDetailResponse(ExecutionResponse):
    """Schema for detailed execution response."""

    request_headers: dict | None
    request_body: str | None
    response_headers: dict | None
    response_body: str | None
    response_size_bytes: int | None


class ExecutionListResponse(BaseModel):
    """Schema for execution list response."""

    executions: list[ExecutionResponse]
    pagination: PaginationMeta


class ExecutionStats(BaseModel):
    """Schema for execution statistics."""

    total: int
    success: int
    failed: int
    success_rate: float
    avg_duration_ms: float | None

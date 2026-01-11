from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

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

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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


class DailyExecutionStats(BaseModel):
    """Schema for daily execution statistics."""

    date: str  # YYYY-MM-DD format
    success: int
    failed: int
    total: int


class DailyExecutionStatsResponse(BaseModel):
    """Schema for daily execution statistics list response."""

    stats: list[DailyExecutionStats]

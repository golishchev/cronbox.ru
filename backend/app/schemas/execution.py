from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.cron_task import HttpMethod
from app.schemas.cron_task import PaginationMeta


class ExecutionResponse(BaseModel):
    """Schema for execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    task_type: str  # 'cron', 'delayed', or 'chain'
    task_id: UUID
    task_name: str | None
    status: str  # TaskStatus values + ChainStatus values (partial, cancelled)
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    retry_attempt: int | None = None  # None for chains
    request_url: str | None = None  # None for chains
    request_method: HttpMethod | None = None  # None for chains
    response_status_code: int | None = None
    error_message: str | None = None
    error_type: str | None = None
    created_at: datetime
    # Chain-specific fields (optional)
    total_steps: int | None = None
    completed_steps: int | None = None
    failed_steps: int | None = None
    skipped_steps: int | None = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ExecutionDetailResponse(ExecutionResponse):
    """Schema for detailed execution response."""

    request_headers: dict | None = None
    request_body: str | None = None
    response_headers: dict | None = None
    response_body: str | None = None
    response_size_bytes: int | None = None
    # Chain execution details (optional)
    chain_variables: dict | None = None


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

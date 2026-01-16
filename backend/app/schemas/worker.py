"""Worker schemas for API serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.worker import WorkerStatus

# === Request schemas ===


class WorkerCreate(BaseModel):
    """Schema for creating a new worker."""

    name: str = Field(..., min_length=1, max_length=255, description="Worker name")
    description: str | None = Field(None, max_length=1000, description="Worker description")


class WorkerUpdate(BaseModel):
    """Schema for updating a worker."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


# === Response schemas ===


class WorkerResponse(BaseModel):
    """Worker response schema (without API key)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: WorkerStatus
    is_active: bool
    api_key_prefix: str
    last_heartbeat: datetime | None
    tasks_completed: int
    tasks_failed: int
    created_at: datetime
    updated_at: datetime


class WorkerCreateResponse(BaseModel):
    """Response when creating a worker (includes API key - only shown once)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    api_key: str = Field(..., description="API key for the worker. Save it - it won't be shown again!")
    api_key_prefix: str
    created_at: datetime


# === Worker task schemas (for polling) ===


class WorkerTaskInfo(BaseModel):
    """Task information for worker execution."""

    task_id: UUID
    task_type: str = Field(..., description="'cron' or 'delayed'")

    # HTTP request details
    url: str
    method: str
    headers: dict = Field(default_factory=dict)
    body: str | None = None

    # Execution settings
    timeout_seconds: int = 30
    retry_count: int = 0
    retry_delay_seconds: int = 60

    # Metadata
    workspace_id: UUID
    task_name: str | None = None


class WorkerTaskResult(BaseModel):
    """Result submitted by worker after task execution."""

    task_id: UUID
    task_type: str = Field(..., description="'cron' or 'delayed'")

    # Response details
    status_code: int | None = None
    response_body: str | None = None
    response_headers: dict | None = None

    # Execution metadata
    started_at: datetime
    finished_at: datetime
    duration_ms: int

    # Error info (if failed)
    error: str | None = None
    error_type: str | None = None  # e.g., "timeout", "connection_error", "http_error"


class WorkerPollResponse(BaseModel):
    """Response for task polling."""

    tasks: list[WorkerTaskInfo] = Field(default_factory=list)
    poll_interval_seconds: int = Field(default=5, description="Suggested interval before next poll")


# === Worker heartbeat ===


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat payload."""

    status: WorkerStatus = WorkerStatus.ONLINE
    current_tasks: int = Field(default=0, description="Number of tasks currently being executed")
    system_info: dict | None = Field(None, description="Optional system info (CPU, memory, etc.)")


class WorkerHeartbeatResponse(BaseModel):
    """Heartbeat response."""

    acknowledged: bool = True
    server_time: datetime

from datetime import datetime
from uuid import UUID

import pytz
from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator, model_validator

from app.models.cron_task import HttpMethod, OverlapPolicy, ProtocolType, TaskStatus


class CronTaskBase(BaseModel):
    """Base cron task schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    # Protocol type (http, icmp, tcp)
    protocol_type: ProtocolType = Field(
        default=ProtocolType.HTTP,
        description="Protocol type: http (HTTP request), icmp (ping), tcp (port check)",
    )

    # HTTP Request fields (required when protocol_type = HTTP)
    url: HttpUrl | None = Field(None, description="URL for HTTP requests")
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None

    # ICMP/TCP fields (required when protocol_type = ICMP or TCP)
    host: str | None = Field(None, max_length=255, description="Host for ICMP/TCP checks (IP or domain)")
    port: int | None = Field(None, ge=1, le=65535, description="Port for TCP checks")
    icmp_count: int = Field(default=3, ge=1, le=10, description="Number of ICMP packets to send")

    # Schedule
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
    # Overlap prevention settings
    overlap_policy: OverlapPolicy = Field(
        default=OverlapPolicy.ALLOW,
        description="Policy for handling overlapping executions: allow, skip, or queue",
    )
    max_instances: int = Field(default=1, ge=1, le=10, description="Maximum concurrent instances")
    max_queue_size: int = Field(default=10, ge=1, le=100, description="Maximum queue size for queue policy")
    execution_timeout: int | None = Field(
        None, ge=60, le=86400, description="Execution timeout in seconds (auto-release running instances)"
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

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str | None) -> str | None:
        """Validate host is not empty if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Host cannot be empty")
        return v.strip() if v else v


class CronTaskCreate(CronTaskBase):
    """Schema for creating a cron task."""

    @model_validator(mode="after")
    def validate_protocol_fields(self) -> "CronTaskCreate":
        """Validate that required fields are present based on protocol_type."""
        if self.protocol_type == ProtocolType.HTTP:
            if not self.url:
                raise ValueError("url is required for HTTP protocol")
        elif self.protocol_type == ProtocolType.ICMP:
            if not self.host:
                raise ValueError("host is required for ICMP protocol")
        elif self.protocol_type == ProtocolType.TCP:
            if not self.host:
                raise ValueError("host is required for TCP protocol")
            if not self.port:
                raise ValueError("port is required for TCP protocol")
        return self


class CronTaskUpdate(BaseModel):
    """Schema for updating a cron task."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    # Protocol type - can be changed
    protocol_type: ProtocolType | None = None

    # HTTP Request fields
    url: HttpUrl | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    body: str | None = None

    # ICMP/TCP fields
    host: str | None = Field(None, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    icmp_count: int | None = Field(None, ge=1, le=10)

    # Schedule
    schedule: str | None = None
    timezone: str | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_count: int | None = Field(None, ge=0, le=10)
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_recovery: bool | None = None
    worker_id: UUID | None = None
    # Overlap prevention settings
    overlap_policy: OverlapPolicy | None = None
    max_instances: int | None = Field(None, ge=1, le=10)
    max_queue_size: int | None = Field(None, ge=1, le=100)
    execution_timeout: int | None = Field(None, ge=60, le=86400)

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

    # Protocol type
    protocol_type: ProtocolType

    # HTTP Request fields
    url: str | None
    method: HttpMethod
    headers: dict
    body: str | None

    # ICMP/TCP fields
    host: str | None
    port: int | None
    icmp_count: int

    # Schedule
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
    # Overlap prevention
    overlap_policy: OverlapPolicy
    max_instances: int
    max_queue_size: int
    execution_timeout: int | None
    running_instances: int
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

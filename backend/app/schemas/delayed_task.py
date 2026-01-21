from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator, model_validator

from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus
from app.schemas.cron_task import PaginationMeta


class DelayedTaskBase(BaseModel):
    """Base delayed task schema."""

    # Protocol type (http, icmp, tcp)
    protocol_type: ProtocolType = Field(
        default=ProtocolType.HTTP,
        description="Protocol type: http (HTTP request), icmp (ping), tcp (port check)",
    )

    # HTTP Request fields (required when protocol_type = HTTP)
    url: HttpUrl | None = Field(None, description="URL for HTTP requests")
    method: HttpMethod = HttpMethod.POST
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None

    # ICMP/TCP fields (required when protocol_type = ICMP or TCP)
    host: str | None = Field(None, max_length=255, description="Host for ICMP/TCP checks (IP or domain)")
    port: int | None = Field(None, ge=1, le=65535, description="Port for TCP checks")
    icmp_count: int = Field(default=3, ge=1, le=10, description="Number of ICMP packets to send")

    # Schedule
    execute_at: datetime
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)
    callback_url: HttpUrl | None = None
    worker_id: UUID | None = Field(
        None,
        description="ID of the external worker to execute this task. If None, cloud workers will be used.",
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str | None) -> str | None:
        """Validate host is not empty if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Host cannot be empty")
        return v.strip() if v else v


class DelayedTaskCreate(DelayedTaskBase):
    """Schema for creating a delayed task."""

    idempotency_key: str | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_protocol_fields(self) -> "DelayedTaskCreate":
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


class DelayedTaskResponse(BaseModel):
    """Schema for delayed task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    worker_id: UUID | None
    idempotency_key: str | None
    name: str | None
    tags: list

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

    @field_serializer("execute_at", "executed_at", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DelayedTaskUpdate(BaseModel):
    """Schema for updating a delayed task."""

    name: str | None = None
    tags: list[str] | None = None

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
    execute_at: datetime | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_count: int | None = Field(None, ge=0, le=10)
    retry_delay_seconds: int | None = Field(None, ge=10, le=3600)
    callback_url: HttpUrl | None = None


class DelayedTaskListResponse(BaseModel):
    """Schema for delayed task list response."""

    tasks: list[DelayedTaskResponse]
    pagination: PaginationMeta


class RescheduleDelayedTaskRequest(BaseModel):
    """Schema for rescheduling a completed delayed task."""

    execute_at: datetime = Field(..., description="New execution time (must be in the future)")

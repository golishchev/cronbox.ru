from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.heartbeat import HeartbeatStatus
from app.schemas.cron_task import PaginationMeta


def parse_interval_to_seconds(interval: str) -> int:
    """Parse interval string like '1h', '30m', '10s' to seconds."""
    interval = interval.strip().lower()

    if interval.endswith("s"):
        return int(interval[:-1])
    elif interval.endswith("m"):
        return int(interval[:-1]) * 60
    elif interval.endswith("h"):
        return int(interval[:-1]) * 3600
    elif interval.endswith("d"):
        return int(interval[:-1]) * 86400
    else:
        # Try to parse as seconds directly
        return int(interval)


class HeartbeatBase(BaseModel):
    """Base heartbeat schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    expected_interval: str = Field(
        ...,
        description="Expected interval between pings (e.g., '1h', '30m', '10s')",
    )
    grace_period: str = Field(
        default="10m",
        description="Grace period before alert (e.g., '10m', '5m')",
    )
    notify_on_late: bool = True
    notify_on_recovery: bool = True

    @field_validator("expected_interval", "grace_period", mode="before")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        """Validate interval format."""
        try:
            seconds = parse_interval_to_seconds(v)
            if seconds < 60:
                raise ValueError("Interval must be at least 60 seconds")
            if seconds > 86400 * 30:  # 30 days max
                raise ValueError("Interval cannot exceed 30 days")
            return v
        except (ValueError, TypeError) as e:
            if "Interval" in str(e):
                raise
            raise ValueError(f"Invalid interval format: {v}. Use format like '1h', '30m', '10s'") from e


class HeartbeatCreate(HeartbeatBase):
    """Schema for creating a heartbeat."""

    pass


class HeartbeatUpdate(BaseModel):
    """Schema for updating a heartbeat."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    expected_interval: str | None = Field(
        None,
        description="Expected interval between pings (e.g., '1h', '30m', '10s')",
    )
    grace_period: str | None = Field(
        None,
        description="Grace period before alert (e.g., '10m', '5m')",
    )
    notify_on_late: bool | None = None
    notify_on_recovery: bool | None = None

    @field_validator("expected_interval", "grace_period", mode="before")
    @classmethod
    def validate_interval(cls, v: str | None) -> str | None:
        """Validate interval format."""
        if v is None:
            return v
        try:
            seconds = parse_interval_to_seconds(v)
            if seconds < 60:
                raise ValueError("Interval must be at least 60 seconds")
            if seconds > 86400 * 30:
                raise ValueError("Interval cannot exceed 30 days")
            return v
        except (ValueError, TypeError) as e:
            if "Interval" in str(e):
                raise
            raise ValueError(f"Invalid interval format: {v}. Use format like '1h', '30m', '10s'") from e


class HeartbeatResponse(BaseModel):
    """Schema for heartbeat response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    ping_token: str
    ping_url: str = ""  # Will be set by the API
    expected_interval: int  # In seconds
    grace_period: int  # In seconds
    status: HeartbeatStatus
    is_paused: bool
    last_ping_at: datetime | None
    next_expected_at: datetime | None
    consecutive_misses: int
    alert_sent: bool
    notify_on_late: bool
    notify_on_recovery: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_ping_at", "next_expected_at", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class HeartbeatListResponse(BaseModel):
    """Schema for heartbeat list response."""

    heartbeats: list[HeartbeatResponse]
    pagination: PaginationMeta


# Ping schemas
class HeartbeatPingCreate(BaseModel):
    """Schema for creating a ping (optional payload)."""

    duration_ms: int | None = Field(None, ge=0)
    status: str | None = Field(None, max_length=50)
    message: str | None = Field(None, max_length=255)
    payload: dict | None = None


class HeartbeatPingResponse(BaseModel):
    """Schema for ping response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    heartbeat_id: UUID
    duration_ms: int | None
    status_message: str | None
    payload: dict | None
    source_ip: str | None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class HeartbeatPingListResponse(BaseModel):
    """Schema for ping list response."""

    pings: list[HeartbeatPingResponse]
    pagination: PaginationMeta


# Simple ping response for public endpoint
class PingSuccessResponse(BaseModel):
    """Response for successful ping."""

    ok: bool = True
    message: str = "pong"
    heartbeat_id: str
    status: HeartbeatStatus

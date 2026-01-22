"""Pydantic schemas for Process Monitors."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.process_monitor import ProcessMonitorEventType, ProcessMonitorStatus, ScheduleType
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


def format_seconds_to_interval(seconds: int) -> str:
    """Convert seconds to human-readable interval string."""
    if seconds >= 86400 and seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    elif seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    elif seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}m"
    else:
        return f"{seconds}s"


class ProcessMonitorBase(BaseModel):
    """Base process monitor schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    schedule_type: ScheduleType = ScheduleType.CRON
    schedule_cron: str | None = Field(
        None,
        description="Cron expression (e.g., '0 17 * * *')",
    )
    schedule_interval: str | None = Field(
        None,
        description="Interval (e.g., '1h', '30m')",
    )
    schedule_exact_time: str | None = Field(
        None,
        description="Exact time (e.g., '17:00')",
    )
    timezone: str = "Europe/Moscow"
    start_grace_period: str = Field(
        default="5m",
        description="Grace period before alert on missed start (e.g., '5m', '10m')",
    )
    end_timeout: str = Field(
        default="1h",
        description="Timeout for process completion (e.g., '1h', '30m')",
    )
    notify_on_missed_start: bool = True
    notify_on_missed_end: bool = True
    notify_on_recovery: bool = True
    notify_on_success: bool = False

    @field_validator("start_grace_period", "end_timeout", "schedule_interval", mode="before")
    @classmethod
    def validate_interval(cls, v: str | None) -> str | None:
        """Validate interval format."""
        if v is None:
            return v
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

    @field_validator("schedule_exact_time", mode="before")
    @classmethod
    def validate_exact_time(cls, v: str | None) -> str | None:
        """Validate exact time format HH:MM."""
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid time format. Use HH:MM")
            hour, minute = int(parts[0]), int(parts[1])
            if hour < 0 or hour > 23:
                raise ValueError("Hour must be between 0 and 23")
            if minute < 0 or minute > 59:
                raise ValueError("Minute must be between 0 and 59")
            return f"{hour:02d}:{minute:02d}"
        except ValueError as e:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM format") from e


class ProcessMonitorCreate(ProcessMonitorBase):
    """Schema for creating a process monitor."""

    pass


class ProcessMonitorUpdate(BaseModel):
    """Schema for updating a process monitor."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    schedule_type: ScheduleType | None = None
    schedule_cron: str | None = None
    schedule_interval: str | None = None
    schedule_exact_time: str | None = None
    timezone: str | None = None
    start_grace_period: str | None = None
    end_timeout: str | None = None
    notify_on_missed_start: bool | None = None
    notify_on_missed_end: bool | None = None
    notify_on_recovery: bool | None = None
    notify_on_success: bool | None = None

    @field_validator("start_grace_period", "end_timeout", "schedule_interval", mode="before")
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

    @field_validator("schedule_exact_time", mode="before")
    @classmethod
    def validate_exact_time(cls, v: str | None) -> str | None:
        """Validate exact time format HH:MM."""
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid time format. Use HH:MM")
            hour, minute = int(parts[0]), int(parts[1])
            if hour < 0 or hour > 23:
                raise ValueError("Hour must be between 0 and 23")
            if minute < 0 or minute > 59:
                raise ValueError("Minute must be between 0 and 59")
            return f"{hour:02d}:{minute:02d}"
        except ValueError as e:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM format") from e


class ProcessMonitorResponse(BaseModel):
    """Schema for process monitor response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    start_token: str
    end_token: str
    start_url: str = ""  # Will be set by the API
    end_url: str = ""  # Will be set by the API
    schedule_type: ScheduleType
    schedule_cron: str | None
    schedule_interval: int | None  # In seconds
    schedule_exact_time: str | None
    timezone: str
    start_grace_period: int  # In seconds
    end_timeout: int  # In seconds
    status: ProcessMonitorStatus
    is_paused: bool
    last_start_at: datetime | None
    last_end_at: datetime | None
    last_duration_ms: int | None
    next_expected_start: datetime | None
    start_deadline: datetime | None
    end_deadline: datetime | None
    current_run_id: str | None
    consecutive_successes: int
    consecutive_failures: int
    notify_on_missed_start: bool
    notify_on_missed_end: bool
    notify_on_recovery: bool
    notify_on_success: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "last_start_at",
        "last_end_at",
        "next_expected_start",
        "start_deadline",
        "end_deadline",
        "created_at",
        "updated_at",
    )
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ProcessMonitorListResponse(BaseModel):
    """Schema for process monitor list response."""

    process_monitors: list[ProcessMonitorResponse]
    pagination: PaginationMeta


# Event schemas
class ProcessMonitorEventCreate(BaseModel):
    """Schema for creating an event (optional payload from ping)."""

    duration_ms: int | None = Field(None, ge=0)
    status: str | None = Field(None, max_length=50)
    message: str | None = Field(None, max_length=255)
    payload: dict | None = None


class ProcessMonitorEventResponse(BaseModel):
    """Schema for event response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    monitor_id: UUID
    event_type: ProcessMonitorEventType
    run_id: str
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


class ProcessMonitorEventListResponse(BaseModel):
    """Schema for event list response."""

    events: list[ProcessMonitorEventResponse]
    pagination: PaginationMeta


# Ping response schemas
class StartPingSuccessResponse(BaseModel):
    """Response for successful start ping."""

    ok: bool = True
    message: str = "start received"
    monitor_id: str
    run_id: str
    status: ProcessMonitorStatus


class EndPingSuccessResponse(BaseModel):
    """Response for successful end ping."""

    ok: bool = True
    message: str = "end received"
    monitor_id: str
    run_id: str
    duration_ms: int | None
    status: ProcessMonitorStatus


class PingErrorResponse(BaseModel):
    """Response for ping errors."""

    ok: bool = False
    error: str
    status: ProcessMonitorStatus | None = None

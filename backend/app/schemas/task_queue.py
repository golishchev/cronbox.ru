"""Pydantic schemas for Task Queue."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class TaskQueueResponse(BaseModel):
    """Schema for task queue item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    task_type: str
    task_id: UUID
    task_name: str | None
    priority: int
    queued_at: datetime
    scheduled_for: datetime | None
    retry_attempt: int
    initial_variables: dict
    created_at: datetime

    @field_serializer("queued_at", "scheduled_for", "created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskQueueListResponse(BaseModel):
    """Schema for task queue list response."""

    items: list[TaskQueueResponse]
    total: int


class OverlapStatsResponse(BaseModel):
    """Schema for overlap prevention statistics."""

    executions_skipped: int = Field(description="Total number of skipped executions")
    executions_queued: int = Field(description="Total number of queued executions")
    current_queue_size: int = Field(description="Current total queue size")
    overlap_rate: float = Field(description="Overlap rate as percentage (skipped / total)")


class TaskOverlapStatusResponse(BaseModel):
    """Schema for task overlap status."""

    task_id: UUID
    task_type: str
    overlap_policy: str
    running_instances: int
    max_instances: int
    queue_size: int
    max_queue_size: int
    can_execute: bool

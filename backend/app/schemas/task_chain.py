"""Pydantic schemas for Task Chains."""

from datetime import datetime
from uuid import UUID

import pytz
from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator

from app.models.chain_execution import StepStatus
from app.models.cron_task import HttpMethod
from app.models.task_chain import ChainStatus, TriggerType

# ============================================================================
# Chain Step Schemas
# ============================================================================


class StepCondition(BaseModel):
    """Condition for step execution."""

    operator: str = Field(
        ...,
        description="Condition operator: 'status_code_in', 'status_code_not_in', 'equals', 'not_equals', 'contains', 'regex'",
    )
    field: str | None = Field(
        None,
        description="JSONPath to extract value from previous response (e.g., '$.data.status'). Required for value comparisons.",
    )
    value: str | int | list[int] | list[str] = Field(
        ...,
        description="Expected value or list of values to compare against.",
    )


class ChainStepBase(BaseModel):
    """Base chain step schema."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl = Field(..., description="URL to call (supports {{variable}} placeholders)")
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = Field(None, description="Request body (supports {{variable}} placeholders)")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_delay_seconds: int = Field(default=5, ge=1, le=300)
    condition: StepCondition | None = Field(
        None,
        description="Condition to check before executing this step",
    )
    extract_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variables to extract from response using JSONPath (e.g., {'order_id': '$.data.id'})",
    )
    continue_on_failure: bool = Field(
        default=False,
        description="Continue to next step even if this step fails",
    )


class ChainStepCreate(ChainStepBase):
    """Schema for creating a chain step."""

    step_order: int = Field(..., ge=0, description="Position of step in the chain (0-based)")


class ChainStepUpdate(BaseModel):
    """Schema for updating a chain step."""

    name: str | None = Field(None, min_length=1, max_length=255)
    url: HttpUrl | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_count: int | None = Field(None, ge=0, le=5)
    retry_delay_seconds: int | None = Field(None, ge=1, le=300)
    condition: StepCondition | None = None
    extract_variables: dict[str, str] | None = None
    continue_on_failure: bool | None = None


class ChainStepResponse(BaseModel):
    """Schema for chain step response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chain_id: UUID
    step_order: int
    name: str
    url: str
    method: HttpMethod
    headers: dict
    body: str | None
    timeout_seconds: int
    retry_count: int
    retry_delay_seconds: int
    condition: dict | None
    extract_variables: dict
    continue_on_failure: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class StepReorderRequest(BaseModel):
    """Schema for reordering steps."""

    step_orders: list[dict[str, int]] = Field(
        ...,
        description="List of {step_id: new_order} mappings",
    )


# ============================================================================
# Task Chain Schemas
# ============================================================================


class TaskChainBase(BaseModel):
    """Base task chain schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    trigger_type: TriggerType = TriggerType.MANUAL
    schedule: str | None = Field(
        None,
        description="Cron expression for cron trigger type",
    )
    timezone: str = Field(default="Europe/Moscow")
    execute_at: datetime | None = Field(
        None,
        description="Execution time for delayed trigger type",
    )
    stop_on_failure: bool = Field(
        default=True,
        description="Stop chain execution when a step fails",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Total chain timeout in seconds",
    )
    notify_on_failure: bool = True
    notify_on_success: bool = False
    notify_on_partial: bool = True
    worker_id: UUID | None = Field(
        None,
        description="ID of external worker. If None, cloud workers will be used.",
    )

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

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class TaskChainCreate(TaskChainBase):
    """Schema for creating a task chain."""

    steps: list[ChainStepBase] = Field(
        default_factory=list,
        description="Steps to create with the chain",
    )


class TaskChainUpdate(BaseModel):
    """Schema for updating a task chain."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    trigger_type: TriggerType | None = None
    schedule: str | None = None
    timezone: str | None = None
    execute_at: datetime | None = None
    stop_on_failure: bool | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=3600)
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    notify_on_partial: bool | None = None
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

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class TaskChainResponse(BaseModel):
    """Schema for task chain response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    worker_id: UUID | None
    name: str
    description: str | None
    tags: list[str]
    trigger_type: TriggerType
    schedule: str | None
    timezone: str
    execute_at: datetime | None
    stop_on_failure: bool
    timeout_seconds: int
    is_active: bool
    is_paused: bool
    last_run_at: datetime | None
    last_status: ChainStatus | None
    next_run_at: datetime | None
    consecutive_failures: int
    notify_on_failure: bool
    notify_on_success: bool
    notify_on_partial: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("execute_at", "last_run_at", "next_run_at", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskChainDetailResponse(TaskChainResponse):
    """Schema for task chain detail response with steps."""

    steps: list[ChainStepResponse] = Field(default_factory=list)


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    limit: int
    total: int
    total_pages: int


class TaskChainListResponse(BaseModel):
    """Schema for task chain list response."""

    chains: list[TaskChainResponse]
    pagination: PaginationMeta


# ============================================================================
# Chain Execution Schemas
# ============================================================================


class StepExecutionResponse(BaseModel):
    """Schema for step execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chain_execution_id: UUID
    step_id: UUID | None
    step_order: int
    step_name: str
    status: StepStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    retry_attempt: int
    request_url: str
    request_method: HttpMethod
    request_headers: dict | None
    request_body: str | None
    response_status_code: int | None
    response_headers: dict | None
    response_body: str | None
    response_size_bytes: int | None
    extracted_variables: dict
    condition_met: bool | None
    condition_details: str | None
    error_message: str | None
    error_type: str | None
    created_at: datetime

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ChainExecutionResponse(BaseModel):
    """Schema for chain execution response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    chain_id: UUID
    status: ChainStatus
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    total_steps: int
    completed_steps: int
    failed_steps: int
    skipped_steps: int
    variables: dict
    error_message: str | None
    created_at: datetime

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ChainExecutionDetailResponse(ChainExecutionResponse):
    """Schema for chain execution detail with step executions."""

    step_executions: list[StepExecutionResponse] = Field(default_factory=list)


class ChainExecutionListResponse(BaseModel):
    """Schema for chain execution list response."""

    executions: list[ChainExecutionResponse]
    pagination: PaginationMeta


# ============================================================================
# Chain Run Request
# ============================================================================


class ChainRunRequest(BaseModel):
    """Schema for manually running a chain."""

    initial_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Initial variables to pass to the chain",
    )

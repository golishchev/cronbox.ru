from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, CurrentWorkspace
from app.db.repositories.executions import ExecutionRepository
from app.models.cron_task import TaskStatus
from app.schemas.cron_task import PaginationMeta
from app.schemas.execution import (
    DailyExecutionStats,
    DailyExecutionStatsResponse,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStats,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/executions", tags=["Executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    task_type: str | None = Query(None, description="Filter by task type (cron/delayed)"),
    task_id: UUID | None = Query(None, description="Filter by specific task ID"),
    status: TaskStatus | None = Query(None, description="Filter by execution status"),
    start_date: datetime | None = Query(None, description="Filter by start date (from)"),
    end_date: datetime | None = Query(None, description="Filter by end date (to)"),
):
    """List executions for a workspace with optional filters."""
    exec_repo = ExecutionRepository(db)
    skip = (page - 1) * limit

    executions = await exec_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
        task_type=task_type,
        task_id=task_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    total = await exec_repo.count_by_workspace(
        workspace_id=workspace.id,
        task_type=task_type,
        task_id=task_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    return ExecutionListResponse(
        executions=[ExecutionResponse.model_validate(ex) for ex in executions],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.get("/stats", response_model=ExecutionStats)
async def get_execution_stats(
    workspace: CurrentWorkspace,
    db: DB,
    task_id: UUID | None = Query(None, description="Filter by specific task ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
):
    """Get execution statistics for a workspace."""
    exec_repo = ExecutionRepository(db)
    stats = await exec_repo.get_stats(
        workspace_id=workspace.id,
        start_date=start_date,
        end_date=end_date,
        task_id=task_id,
    )
    return ExecutionStats(**stats)


@router.get("/stats/daily", response_model=DailyExecutionStatsResponse)
async def get_daily_execution_stats(
    workspace: CurrentWorkspace,
    db: DB,
    days: int = Query(7, ge=1, le=30, description="Number of days (1-30)"),
):
    """Get daily execution statistics for the last N days."""
    exec_repo = ExecutionRepository(db)
    daily_stats = await exec_repo.get_daily_stats(
        workspace_id=workspace.id,
        days=days,
    )
    return DailyExecutionStatsResponse(
        stats=[DailyExecutionStats(**s) for s in daily_stats]
    )


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(
    execution_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get detailed execution information including request/response data."""
    exec_repo = ExecutionRepository(db)
    execution = await exec_repo.get_by_id(execution_id)

    if execution is None or execution.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    return ExecutionDetailResponse.model_validate(execution)

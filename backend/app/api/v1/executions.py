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
    task_type: str | None = Query(None, description="Filter by task type (cron/delayed/chain)"),
    task_id: UUID | None = Query(None, description="Filter by specific task ID"),
    status: TaskStatus | None = Query(None, description="Filter by execution status"),
    start_date: datetime | None = Query(None, description="Filter by start date (from)"),
    end_date: datetime | None = Query(None, description="Filter by end date (to)"),
):
    """List executions for a workspace with optional filters.

    Includes both regular task executions (cron/delayed) and chain executions.
    """
    exec_repo = ExecutionRepository(db)
    skip = (page - 1) * limit

    # Use unified executions that include chains
    executions = await exec_repo.get_unified_executions(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
        task_type=task_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    total = await exec_repo.count_unified_executions(
        workspace_id=workspace.id,
        task_type=task_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    return ExecutionListResponse(
        executions=[ExecutionResponse(**ex) for ex in executions],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit if total > 0 else 1,
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
    execution_type: str | None = Query(None, description="Type of execution (chain for chain executions)"),
):
    """Get detailed execution information including request/response data.

    For chain executions, pass execution_type=chain to get chain-specific details.
    """
    exec_repo = ExecutionRepository(db)

    # Check if this is a chain execution
    if execution_type == "chain":
        from app.db.repositories.chain_executions import ChainExecutionRepository
        from app.models.task_chain import ChainStatus

        chain_exec_repo = ChainExecutionRepository(db)
        chain_execution = await chain_exec_repo.get_with_step_executions(execution_id)

        if chain_execution is None or chain_execution.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chain execution not found",
            )

        # Get chain name
        from app.db.repositories.task_chains import TaskChainRepository

        chain_repo = TaskChainRepository(db)
        chain = await chain_repo.get_by_id(chain_execution.chain_id)
        chain_name = chain.name if chain else "Unknown Chain"

        status_map = {
            ChainStatus.PENDING: "pending",
            ChainStatus.RUNNING: "running",
            ChainStatus.SUCCESS: "success",
            ChainStatus.FAILED: "failed",
            ChainStatus.PARTIAL: "partial",
            ChainStatus.CANCELLED: "cancelled",
        }

        return ExecutionDetailResponse(
            id=chain_execution.id,
            workspace_id=chain_execution.workspace_id,
            task_type="chain",
            task_id=chain_execution.chain_id,
            task_name=chain_name,
            status=status_map.get(chain_execution.status, "unknown"),
            started_at=chain_execution.started_at,
            finished_at=chain_execution.finished_at,
            duration_ms=chain_execution.duration_ms,
            retry_attempt=None,
            request_url=None,
            request_method=None,
            response_status_code=None,
            error_message=chain_execution.error_message,
            error_type=None,
            created_at=chain_execution.created_at,
            total_steps=chain_execution.total_steps,
            completed_steps=chain_execution.completed_steps,
            failed_steps=chain_execution.failed_steps,
            skipped_steps=chain_execution.skipped_steps,
            request_headers=None,
            request_body=None,
            response_headers=None,
            response_body=None,
            response_size_bytes=None,
            chain_variables=chain_execution.variables,
        )

    # Regular execution
    execution = await exec_repo.get_by_id(execution_id)

    if execution is None or execution.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    return ExecutionDetailResponse.model_validate(execution)

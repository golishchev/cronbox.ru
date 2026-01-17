"""API endpoints for Task Queue management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DB, CurrentWorkspace
from app.models.task_queue import TaskQueue
from app.schemas.task_queue import (
    OverlapStatsResponse,
    TaskQueueListResponse,
    TaskQueueResponse,
)
from app.services.overlap import overlap_service

router = APIRouter()


@router.get(
    "/workspaces/{workspace_id}/queue",
    response_model=TaskQueueListResponse,
    summary="List queued tasks",
    description="Get all queued task executions for a workspace.",
)
async def list_queued_tasks(
    workspace: CurrentWorkspace,
    db: DB,
    limit: int = 50,
) -> TaskQueueListResponse:
    """List all queued task executions."""
    items = await overlap_service.get_queued_tasks(db, workspace.id, limit=limit)

    # Get total count
    result = await db.execute(
        select(func.count(TaskQueue.id)).where(TaskQueue.workspace_id == workspace.id)
    )
    total = result.scalar() or 0

    return TaskQueueListResponse(
        items=[TaskQueueResponse.model_validate(item) for item in items],
        total=total,
    )


@router.delete(
    "/workspaces/{workspace_id}/queue/{queue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from queue",
    description="Remove a task execution from the queue.",
)
async def remove_from_queue(
    workspace: CurrentWorkspace,
    queue_id: UUID,
    db: DB,
) -> None:
    """Remove a task from the queue."""
    # Verify the queue item belongs to this workspace
    result = await db.execute(
        select(TaskQueue).where(
            TaskQueue.id == queue_id,
            TaskQueue.workspace_id == workspace.id,
        )
    )
    queue_item = result.scalar_one_or_none()

    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found",
        )

    await db.delete(queue_item)
    await db.commit()


@router.delete(
    "/workspaces/{workspace_id}/queue",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear workspace queue",
    description="Clear all queued task executions for a workspace.",
)
async def clear_workspace_queue(
    workspace: CurrentWorkspace,
    db: DB,
) -> None:
    """Clear all queued tasks for the workspace."""
    from sqlalchemy import delete

    await db.execute(
        delete(TaskQueue).where(TaskQueue.workspace_id == workspace.id)
    )
    await db.commit()


@router.get(
    "/workspaces/{workspace_id}/overlap-stats",
    response_model=OverlapStatsResponse,
    summary="Get overlap statistics",
    description="Get overlap prevention statistics for a workspace.",
)
async def get_overlap_stats(
    workspace: CurrentWorkspace,
    db: DB,
) -> OverlapStatsResponse:
    """Get overlap prevention statistics."""
    # Get current queue size
    result = await db.execute(
        select(func.count(TaskQueue.id)).where(TaskQueue.workspace_id == workspace.id)
    )
    current_queue_size = result.scalar() or 0

    # Calculate overlap rate
    # This would need execution history to be accurate
    # For now, we use skipped count vs total
    total_executions = workspace.executions_skipped + workspace.executions_queued
    overlap_rate = 0.0
    if total_executions > 0:
        overlap_rate = (workspace.executions_skipped / total_executions) * 100

    return OverlapStatsResponse(
        executions_skipped=workspace.executions_skipped,
        executions_queued=workspace.executions_queued,
        current_queue_size=current_queue_size,
        overlap_rate=round(overlap_rate, 2),
    )


@router.post(
    "/workspaces/{workspace_id}/cron/{task_id}/clear-queue",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear cron task queue",
    description="Clear all queued executions for a specific cron task.",
)
async def clear_cron_task_queue(
    workspace: CurrentWorkspace,
    task_id: UUID,
    db: DB,
) -> None:
    """Clear queue for a specific cron task."""
    await overlap_service.clear_task_queue(db, "cron", task_id)
    await db.commit()


@router.post(
    "/workspaces/{workspace_id}/chains/{chain_id}/clear-queue",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear chain queue",
    description="Clear all queued executions for a specific task chain.",
)
async def clear_chain_queue(
    workspace: CurrentWorkspace,
    chain_id: UUID,
    db: DB,
) -> None:
    """Clear queue for a specific task chain."""
    await overlap_service.clear_task_queue(db, "chain", chain_id)
    await db.commit()


@router.get(
    "/workspaces/{workspace_id}/cron/{task_id}/queue",
    response_model=TaskQueueListResponse,
    summary="Get cron task queue",
    description="Get queued executions for a specific cron task.",
)
async def get_cron_task_queue(
    workspace: CurrentWorkspace,
    task_id: UUID,
    db: DB,
) -> TaskQueueListResponse:
    """Get queue for a specific cron task."""
    result = await db.execute(
        select(TaskQueue).where(
            TaskQueue.workspace_id == workspace.id,
            TaskQueue.task_type == "cron",
            TaskQueue.task_id == task_id,
        ).order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
    )
    items = result.scalars().all()

    return TaskQueueListResponse(
        items=[TaskQueueResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get(
    "/workspaces/{workspace_id}/chains/{chain_id}/queue",
    response_model=TaskQueueListResponse,
    summary="Get chain queue",
    description="Get queued executions for a specific task chain.",
)
async def get_chain_queue(
    workspace: CurrentWorkspace,
    chain_id: UUID,
    db: DB,
) -> TaskQueueListResponse:
    """Get queue for a specific task chain."""
    result = await db.execute(
        select(TaskQueue).where(
            TaskQueue.workspace_id == workspace.id,
            TaskQueue.task_type == "chain",
            TaskQueue.task_id == chain_id,
        ).order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
    )
    items = result.scalars().all()

    return TaskQueueListResponse(
        items=[TaskQueueResponse.model_validate(item) for item in items],
        total=len(items),
    )

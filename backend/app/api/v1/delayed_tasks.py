from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, ActiveSubscriptionWorkspace, CurrentWorkspace, UserPlan
from app.db.repositories.delayed_tasks import DelayedTaskRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.cron_task import TaskStatus
from app.schemas.cron_task import PaginationMeta
from app.schemas.delayed_task import (
    DelayedTaskCreate,
    DelayedTaskListResponse,
    DelayedTaskResponse,
    DelayedTaskUpdate,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/delayed", tags=["Delayed Tasks"])


@router.get("", response_model=DelayedTaskListResponse)
async def list_delayed_tasks(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: TaskStatus | None = Query(None),
):
    """List all delayed tasks for a workspace."""
    delayed_repo = DelayedTaskRepository(db)
    skip = (page - 1) * limit

    tasks = await delayed_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
        status=status,
    )
    total = await delayed_repo.count_by_workspace(
        workspace_id=workspace.id,
        status=status,
    )

    return DelayedTaskListResponse(
        tasks=[DelayedTaskResponse.model_validate(task) for task in tasks],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post("", response_model=DelayedTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_delayed_task(
    data: DelayedTaskCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new delayed task.

    If an idempotency_key is provided and a task with the same key exists,
    the existing task is returned instead of creating a new one.
    """
    delayed_repo = DelayedTaskRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Check idempotency key
    if data.idempotency_key:
        existing = await delayed_repo.get_by_idempotency_key(
            workspace.id, data.idempotency_key
        )
        if existing:
            return DelayedTaskResponse.model_validate(existing)

    # Check plan limits
    if workspace.delayed_tasks_this_month >= user_plan.max_delayed_tasks_per_month:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Monthly delayed task limit reached. Your plan allows {user_plan.max_delayed_tasks_per_month} delayed task(s) per month",
        )

    # Validate execute_at is in the future
    now = datetime.utcnow()
    execute_at = data.execute_at.replace(tzinfo=None) if data.execute_at.tzinfo else data.execute_at
    if execute_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="execute_at must be in the future",
        )

    # Create task
    task = await delayed_repo.create(
        workspace_id=workspace.id,
        idempotency_key=data.idempotency_key,
        name=data.name,
        tags=data.tags,
        url=str(data.url),
        method=data.method,
        headers=data.headers,
        body=data.body,
        execute_at=execute_at,
        timeout_seconds=data.timeout_seconds,
        retry_count=data.retry_count,
        retry_delay_seconds=data.retry_delay_seconds,
        callback_url=str(data.callback_url) if data.callback_url else None,
        status=TaskStatus.PENDING,
    )

    # Increment workspace counter
    await workspace_repo.increment_delayed_tasks_count(workspace)
    await db.commit()

    return DelayedTaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=DelayedTaskResponse)
async def get_delayed_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a specific delayed task."""
    delayed_repo = DelayedTaskRepository(db)
    task = await delayed_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delayed task not found",
        )

    return DelayedTaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=DelayedTaskResponse)
async def update_delayed_task(
    task_id: UUID,
    data: DelayedTaskUpdate,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Update a pending delayed task.

    Only pending tasks can be updated. Tasks that are running,
    completed, or cancelled cannot be modified.
    """
    delayed_repo = DelayedTaskRepository(db)
    task = await delayed_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delayed task not found",
        )

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update task with status '{task.status.value}'. Only pending tasks can be updated.",
        )

    # Validate execute_at is in the future if provided
    execute_at = None
    if data.execute_at is not None:
        now = datetime.utcnow()
        execute_at = data.execute_at.replace(tzinfo=None) if data.execute_at.tzinfo else data.execute_at
        if execute_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="execute_at must be in the future",
            )

    task = await delayed_repo.update(
        task=task,
        name=data.name,
        tags=data.tags,
        url=str(data.url) if data.url else None,
        method=data.method,
        headers=data.headers,
        body=data.body,
        execute_at=execute_at,
        timeout_seconds=data.timeout_seconds,
        retry_count=data.retry_count,
        retry_delay_seconds=data.retry_delay_seconds,
        callback_url=str(data.callback_url) if data.callback_url else None,
    )
    await db.commit()

    return DelayedTaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_delayed_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Cancel a pending delayed task.

    Only pending tasks can be cancelled. Tasks that are running,
    completed, or already cancelled cannot be modified.
    """
    delayed_repo = DelayedTaskRepository(db)
    task = await delayed_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delayed task not found",
        )

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status '{task.status.value}'. Only pending tasks can be cancelled.",
        )

    await delayed_repo.cancel(task)
    await db.commit()

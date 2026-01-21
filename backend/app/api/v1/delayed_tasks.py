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
    RescheduleDelayedTaskRequest,
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
        existing = await delayed_repo.get_by_idempotency_key(workspace.id, data.idempotency_key)
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

    # Convert schema to dict, automatically including all fields
    # mode="json" ensures HttpUrl and enums are serialized to primitives
    task_data = data.model_dump(mode="json")

    # Override execute_at with timezone-naive version
    task_data["execute_at"] = execute_at

    # Add system fields
    task_data["workspace_id"] = workspace.id
    task_data["status"] = TaskStatus.PENDING

    # Create task
    task = await delayed_repo.create(**task_data)

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


@router.post("/{task_id}/reschedule", response_model=DelayedTaskResponse, status_code=status.HTTP_201_CREATED)
async def reschedule_delayed_task(
    task_id: UUID,
    data: RescheduleDelayedTaskRequest,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Reschedule a completed delayed task.

    Creates a new task with the same configuration as the original,
    but with a new execution time. Only completed tasks (success, failed, cancelled)
    can be rescheduled.
    """
    delayed_repo = DelayedTaskRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Get original task
    original_task = await delayed_repo.get_by_id(task_id)
    if original_task is None or original_task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delayed task not found",
        )

    # Check task status - only completed tasks can be rescheduled
    if original_task.status not in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule task with status '{original_task.status.value}'. Only completed tasks (success, failed, cancelled) can be rescheduled.",
        )

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

    # Create new task with same configuration
    new_task = await delayed_repo.create(
        workspace_id=workspace.id,
        idempotency_key=None,  # New task, no idempotency key
        name=original_task.name,
        tags=original_task.tags,
        url=original_task.url,
        method=original_task.method,
        headers=original_task.headers,
        body=original_task.body,
        execute_at=execute_at,
        timeout_seconds=original_task.timeout_seconds,
        retry_count=original_task.retry_count,
        retry_delay_seconds=original_task.retry_delay_seconds,
        callback_url=original_task.callback_url,
        status=TaskStatus.PENDING,
        worker_id=original_task.worker_id,
    )

    # Increment workspace counter
    await workspace_repo.increment_delayed_tasks_count(workspace)
    await db.commit()

    return DelayedTaskResponse.model_validate(new_task)


@router.post("/{task_id}/copy", response_model=DelayedTaskResponse, status_code=status.HTTP_201_CREATED)
async def copy_delayed_task(
    task_id: UUID,
    data: RescheduleDelayedTaskRequest,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a copy of an existing delayed task.

    Creates a new task with the same configuration as the original,
    but with a new execution time and "(copy)" appended to the name.
    Any task can be copied regardless of its status.
    """
    delayed_repo = DelayedTaskRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Get original task
    original_task = await delayed_repo.get_by_id(task_id)
    if original_task is None or original_task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delayed task not found",
        )

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

    # Create copy with new name
    new_name = f"{original_task.name} (copy)" if original_task.name else None
    new_task = await delayed_repo.create(
        workspace_id=workspace.id,
        idempotency_key=None,  # New task, no idempotency key
        name=new_name,
        tags=original_task.tags,
        url=original_task.url,
        method=original_task.method,
        headers=original_task.headers,
        body=original_task.body,
        execute_at=execute_at,
        timeout_seconds=original_task.timeout_seconds,
        retry_count=original_task.retry_count,
        retry_delay_seconds=original_task.retry_delay_seconds,
        callback_url=original_task.callback_url,
        status=TaskStatus.PENDING,
        worker_id=original_task.worker_id,
    )

    # Increment workspace counter
    await workspace_repo.increment_delayed_tasks_count(workspace)
    await db.commit()

    return DelayedTaskResponse.model_validate(new_task)

from datetime import datetime
from uuid import UUID

from croniter import croniter
from fastapi import APIRouter, HTTPException, Query, status
import pytz

from app.api.deps import CurrentUser, CurrentWorkspace, DB
from app.db.repositories.cron_tasks import CronTaskRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.db.repositories.plans import PlanRepository
from app.models.cron_task import TaskStatus
from app.schemas.cron_task import (
    CronTaskCreate,
    CronTaskListResponse,
    CronTaskResponse,
    CronTaskUpdate,
    PaginationMeta,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/cron", tags=["Cron Tasks"])


def calculate_next_run(schedule: str, timezone: str) -> datetime:
    """Calculate next run time based on cron schedule and timezone."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    cron = croniter(schedule, now)
    next_run = cron.get_next(datetime)
    # Convert to UTC for storage
    return next_run.astimezone(pytz.UTC).replace(tzinfo=None)


@router.get("", response_model=CronTaskListResponse)
async def list_cron_tasks(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
):
    """List all cron tasks for a workspace."""
    cron_repo = CronTaskRepository(db)
    skip = (page - 1) * limit

    tasks = await cron_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    total = await cron_repo.count_by_workspace(
        workspace_id=workspace.id,
        is_active=is_active,
    )

    return CronTaskListResponse(
        tasks=[CronTaskResponse.model_validate(task) for task in tasks],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post("", response_model=CronTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_cron_task(
    data: CronTaskCreate,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Create a new cron task."""
    cron_repo = CronTaskRepository(db)
    workspace_repo = WorkspaceRepository(db)
    plan_repo = PlanRepository(db)

    # Check plan limits
    workspace_with_plan = await workspace_repo.get_with_plan(workspace.id)
    if workspace_with_plan and workspace_with_plan.plan:
        plan = workspace_with_plan.plan
        current_count = await cron_repo.count_by_workspace(workspace.id)
        if current_count >= plan.max_cron_tasks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cron task limit reached. Your plan allows {plan.max_cron_tasks} cron task(s)",
            )

    # Calculate next run time
    next_run_at = calculate_next_run(data.schedule, data.timezone)

    # Create task
    task = await cron_repo.create(
        workspace_id=workspace.id,
        name=data.name,
        description=data.description,
        url=str(data.url),
        method=data.method,
        headers=data.headers,
        body=data.body,
        schedule=data.schedule,
        timezone=data.timezone,
        timeout_seconds=data.timeout_seconds,
        retry_count=data.retry_count,
        retry_delay_seconds=data.retry_delay_seconds,
        notify_on_failure=data.notify_on_failure,
        notify_on_recovery=data.notify_on_recovery,
        is_active=True,
        is_paused=False,
        next_run_at=next_run_at,
    )

    # Update workspace counter
    await workspace_repo.update_cron_tasks_count(workspace, 1)
    await db.commit()

    return CronTaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=CronTaskResponse)
async def get_cron_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a specific cron task."""
    cron_repo = CronTaskRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    return CronTaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=CronTaskResponse)
async def update_cron_task(
    task_id: UUID,
    data: CronTaskUpdate,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Update a cron task."""
    cron_repo = CronTaskRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # If schedule or timezone changed, recalculate next_run_at
    if "schedule" in update_data or "timezone" in update_data:
        schedule = update_data.get("schedule", task.schedule)
        timezone = update_data.get("timezone", task.timezone)
        update_data["next_run_at"] = calculate_next_run(schedule, timezone)

    # Convert HttpUrl to string if present
    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    if update_data:
        task = await cron_repo.update(task, **update_data)
        await db.commit()

    return CronTaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cron_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a cron task."""
    cron_repo = CronTaskRepository(db)
    workspace_repo = WorkspaceRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    await cron_repo.delete(task)
    await workspace_repo.update_cron_tasks_count(workspace, -1)
    await db.commit()


@router.post("/{task_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_cron_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Manually trigger a cron task execution."""
    cron_repo = CronTaskRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    if not task.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run inactive task",
        )

    # Enqueue task for immediate execution via arq
    try:
        from arq import create_pool
        from app.workers.settings import get_redis_settings

        redis = await create_pool(get_redis_settings())
        await redis.enqueue_job(
            "execute_cron_task",
            task_id=str(task_id),
            retry_attempt=0,
        )
        await redis.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to enqueue task: {str(e)}",
        )

    return {"message": "Task queued for execution", "task_id": str(task_id)}


@router.post("/{task_id}/pause", response_model=CronTaskResponse)
async def pause_cron_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Pause a cron task."""
    cron_repo = CronTaskRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    if task.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already paused",
        )

    task = await cron_repo.pause(task)
    await db.commit()

    return CronTaskResponse.model_validate(task)


@router.post("/{task_id}/resume", response_model=CronTaskResponse)
async def resume_cron_task(
    task_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Resume a paused cron task."""
    cron_repo = CronTaskRepository(db)
    task = await cron_repo.get_by_id(task_id)

    if task is None or task.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cron task not found",
        )

    if not task.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not paused",
        )

    next_run_at = calculate_next_run(task.schedule, task.timezone)
    task = await cron_repo.resume(task, next_run_at)
    await db.commit()

    return CronTaskResponse.model_validate(task)

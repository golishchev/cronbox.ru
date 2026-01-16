import secrets

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, CurrentUser, CurrentWorkspace, UserPlan, VerifiedUser
from app.db.repositories.workspaces import WorkspaceRepository
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceWithStats,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all workspaces for the current user."""
    workspace_repo = WorkspaceRepository(db)
    skip = (page - 1) * limit
    workspaces = await workspace_repo.get_by_owner(
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return [WorkspaceResponse.model_validate(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: VerifiedUser,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new workspace. Requires verified email."""
    workspace_repo = WorkspaceRepository(db)

    # Check if slug is unique for this user
    if await workspace_repo.slug_exists(data.slug, owner_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace with this slug already exists",
        )

    # Check workspace limit based on user's plan
    workspace_count = await workspace_repo.count_by_owner(current_user.id)
    if workspace_count >= user_plan.max_workspaces:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Workspace limit reached. Your plan allows {user_plan.max_workspaces} workspace(s)",
        )

    # Create workspace (no plan_id - plan is at user level now)
    workspace = await workspace_repo.create(
        name=data.name,
        slug=data.slug,
        owner_id=current_user.id,
        default_timezone=data.default_timezone,
        webhook_secret=secrets.token_urlsafe(32),
    )
    await db.commit()

    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceWithStats)
async def get_workspace(
    workspace: CurrentWorkspace,
    current_user: CurrentUser,
    user_plan: UserPlan,
    db: DB,
):
    """Get a specific workspace with statistics."""
    # Calculate additional stats
    from datetime import datetime, timedelta

    from app.db.repositories.cron_tasks import CronTaskRepository
    from app.db.repositories.delayed_tasks import DelayedTaskRepository
    from app.db.repositories.executions import ExecutionRepository
    from app.models.cron_task import TaskStatus

    cron_repo = CronTaskRepository(db)
    delayed_repo = DelayedTaskRepository(db)
    exec_repo = ExecutionRepository(db)

    active_cron = await cron_repo.count_by_workspace(workspace.id, is_active=True)
    pending_delayed = await delayed_repo.count_by_workspace(workspace.id, status=TaskStatus.PENDING)

    # Today's executions
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    exec_today = await exec_repo.count_by_workspace(workspace.id, start_date=today_start)

    # 7-day success rate
    week_ago = datetime.utcnow() - timedelta(days=7)
    stats_7d = await exec_repo.get_stats(workspace.id, start_date=week_ago)

    return WorkspaceWithStats(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        is_blocked=workspace.is_blocked,
        blocked_at=workspace.blocked_at,
        cron_tasks_count=workspace.cron_tasks_count,
        delayed_tasks_this_month=workspace.delayed_tasks_this_month,
        default_timezone=workspace.default_timezone,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        plan_name=user_plan.display_name,
        active_cron_tasks=active_cron,
        pending_delayed_tasks=pending_delayed,
        executions_today=exec_today,
        success_rate_7d=stats_7d["success_rate"],
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    data: WorkspaceUpdate,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Update a workspace."""
    workspace_repo = WorkspaceRepository(db)

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        workspace = await workspace_repo.update(workspace, **update_data)
        await db.commit()

    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a workspace and all its tasks."""
    workspace_repo = WorkspaceRepository(db)
    await workspace_repo.delete(workspace)
    await db.commit()

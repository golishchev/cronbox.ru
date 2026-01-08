"""Admin API endpoints."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DB
from app.models import CronTask, DelayedTask, Execution, User, Workspace, Subscription

router = APIRouter(prefix="/admin", tags=["Admin"])


# Dependency to check if user is admin
async def require_admin(current_user: CurrentUser) -> User:
    """Require current user to be admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


# Response schemas
class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""

    total_users: int
    active_users: int
    verified_users: int
    total_workspaces: int
    total_cron_tasks: int
    active_cron_tasks: int
    total_delayed_tasks: int
    pending_delayed_tasks: int
    total_executions: int
    executions_today: int
    executions_this_week: int
    success_rate: float
    active_subscriptions: int
    revenue_this_month: float


class UserListItem(BaseModel):
    """User list item for admin."""

    id: str
    email: str
    name: str
    is_active: bool
    is_superuser: bool
    email_verified: bool
    telegram_username: str | None
    created_at: datetime
    workspaces_count: int
    tasks_count: int

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class WorkspaceListItem(BaseModel):
    """Workspace list item for admin."""

    id: str
    name: str
    slug: str
    owner_email: str
    owner_name: str
    plan_name: str
    cron_tasks_count: int
    delayed_tasks_count: int
    executions_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceListResponse(BaseModel):
    """Paginated workspace list response."""

    workspaces: list[WorkspaceListItem]
    total: int
    page: int
    page_size: int


class UpdateUserRequest(BaseModel):
    """Request to update user."""

    is_active: bool | None = None
    is_superuser: bool | None = None
    email_verified: bool | None = None


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(admin: AdminUser, db: DB):
    """Get admin dashboard statistics."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # User stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.email_verified == True)
    )

    # Workspace stats
    total_workspaces = await db.scalar(select(func.count(Workspace.id)))

    # Task stats
    total_cron = await db.scalar(select(func.count(CronTask.id)))
    active_cron = await db.scalar(
        select(func.count(CronTask.id)).where(CronTask.is_active == True)
    )
    total_delayed = await db.scalar(select(func.count(DelayedTask.id)))
    pending_delayed = await db.scalar(
        select(func.count(DelayedTask.id)).where(DelayedTask.status == "pending")
    )

    # Execution stats
    total_executions = await db.scalar(select(func.count(Execution.id)))
    executions_today = await db.scalar(
        select(func.count(Execution.id)).where(Execution.started_at >= today)
    )
    executions_this_week = await db.scalar(
        select(func.count(Execution.id)).where(Execution.started_at >= week_ago)
    )

    # Success rate (last 7 days)
    successful = await db.scalar(
        select(func.count(Execution.id)).where(
            Execution.started_at >= week_ago,
            Execution.status == "success",
        )
    )
    total_recent = await db.scalar(
        select(func.count(Execution.id)).where(
            Execution.started_at >= week_ago,
            Execution.status.in_(["success", "failed"]),
        )
    )
    success_rate = (successful / total_recent * 100) if total_recent > 0 else 0

    # Subscription stats
    active_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == "active",
            Subscription.ends_at > now,
        )
    )

    # Revenue (this month) - sum of subscription prices
    revenue = await db.scalar(
        select(func.sum(Subscription.amount)).where(
            Subscription.created_at >= month_start,
            Subscription.status.in_(["active", "cancelled"]),
        )
    ) or 0

    return AdminStatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        verified_users=verified_users or 0,
        total_workspaces=total_workspaces or 0,
        total_cron_tasks=total_cron or 0,
        active_cron_tasks=active_cron or 0,
        total_delayed_tasks=total_delayed or 0,
        pending_delayed_tasks=pending_delayed or 0,
        total_executions=total_executions or 0,
        executions_today=executions_today or 0,
        executions_this_week=executions_this_week or 0,
        success_rate=round(success_rate, 1),
        active_subscriptions=active_subs or 0,
        revenue_this_month=float(revenue),
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: AdminUser,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    """List all users with pagination."""
    offset = (page - 1) * page_size

    # Base query
    query = select(User)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | (User.name.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get users
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    # Get workspace and task counts for each user
    user_items = []
    for user in users:
        workspace_count = await db.scalar(
            select(func.count(Workspace.id)).where(Workspace.owner_id == user.id)
        )
        tasks_count = await db.scalar(
            select(func.count(CronTask.id))
            .join(Workspace)
            .where(Workspace.owner_id == user.id)
        )

        user_items.append(
            UserListItem(
                id=str(user.id),
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                email_verified=user.email_verified,
                telegram_username=user.telegram_username,
                created_at=user.created_at,
                workspaces_count=workspace_count or 0,
                tasks_count=tasks_count or 0,
            )
        )

    return UserListResponse(
        users=user_items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}")
async def get_user(admin: AdminUser, db: DB, user_id: str):
    """Get user details."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    workspace_count = await db.scalar(
        select(func.count(Workspace.id)).where(Workspace.owner_id == user.id)
    )
    tasks_count = await db.scalar(
        select(func.count(CronTask.id))
        .join(Workspace)
        .where(Workspace.owner_id == user.id)
    )

    return UserListItem(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        telegram_username=user.telegram_username,
        created_at=user.created_at,
        workspaces_count=workspace_count or 0,
        tasks_count=tasks_count or 0,
    )


@router.patch("/users/{user_id}")
async def update_user(admin: AdminUser, db: DB, user_id: str, data: UpdateUserRequest):
    """Update user (admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from removing their own admin status
    if str(user.id) == str(admin.id) and data.is_superuser is False:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin status",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    return {"message": "User updated successfully"}


class WorkspaceDetailResponse(BaseModel):
    """Workspace detail response for admin."""

    id: str
    name: str
    slug: str
    owner_id: str
    owner_email: str
    owner_name: str
    plan_name: str
    cron_tasks_count: int
    delayed_tasks_count: int
    executions_count: int
    active_cron_tasks: int
    pending_delayed_tasks: int
    default_timezone: str
    webhook_secret: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateWorkspaceRequest(BaseModel):
    """Request to update workspace by admin."""

    name: str | None = None
    slug: str | None = None
    default_timezone: str | None = None


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    admin: AdminUser,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    """List all workspaces with pagination."""
    offset = (page - 1) * page_size

    # Base query with owner join
    query = select(Workspace).join(User, Workspace.owner_id == User.id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Workspace.name.ilike(search_filter))
            | (Workspace.slug.ilike(search_filter))
            | (User.email.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get workspaces
    query = query.offset(offset).limit(page_size).order_by(Workspace.created_at.desc())
    result = await db.execute(query)
    workspaces = result.scalars().all()

    # Build response with counts
    workspace_items = []
    for ws in workspaces:
        cron_count = await db.scalar(
            select(func.count(CronTask.id)).where(CronTask.workspace_id == ws.id)
        )
        delayed_count = await db.scalar(
            select(func.count(DelayedTask.id)).where(DelayedTask.workspace_id == ws.id)
        )
        exec_count = await db.scalar(
            select(func.count(Execution.id)).where(Execution.workspace_id == ws.id)
        )

        # Get subscription plan
        sub = await db.scalar(
            select(Subscription)
            .where(
                Subscription.workspace_id == ws.id,
                Subscription.status == "active",
            )
            .order_by(Subscription.created_at.desc())
        )
        plan_name = sub.plan_name if sub else "free"

        workspace_items.append(
            WorkspaceListItem(
                id=str(ws.id),
                name=ws.name,
                slug=ws.slug,
                owner_email=ws.owner.email,
                owner_name=ws.owner.name,
                plan_name=plan_name,
                cron_tasks_count=cron_count or 0,
                delayed_tasks_count=delayed_count or 0,
                executions_count=exec_count or 0,
                created_at=ws.created_at,
            )
        )

    return WorkspaceListResponse(
        workspaces=workspace_items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(admin: AdminUser, db: DB, workspace_id: str):
    """Get workspace details by ID."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get counts
    cron_count = await db.scalar(
        select(func.count(CronTask.id)).where(CronTask.workspace_id == workspace.id)
    )
    active_cron = await db.scalar(
        select(func.count(CronTask.id)).where(
            CronTask.workspace_id == workspace.id,
            CronTask.is_active == True,
        )
    )
    delayed_count = await db.scalar(
        select(func.count(DelayedTask.id)).where(
            DelayedTask.workspace_id == workspace.id
        )
    )
    pending_delayed = await db.scalar(
        select(func.count(DelayedTask.id)).where(
            DelayedTask.workspace_id == workspace.id,
            DelayedTask.status == "pending",
        )
    )
    exec_count = await db.scalar(
        select(func.count(Execution.id)).where(Execution.workspace_id == workspace.id)
    )

    # Get subscription plan
    sub = await db.scalar(
        select(Subscription)
        .where(
            Subscription.workspace_id == workspace.id,
            Subscription.status == "active",
        )
        .order_by(Subscription.created_at.desc())
    )
    plan_name = sub.plan_name if sub else "free"

    return WorkspaceDetailResponse(
        id=str(workspace.id),
        name=workspace.name,
        slug=workspace.slug,
        owner_id=str(workspace.owner_id),
        owner_email=workspace.owner.email,
        owner_name=workspace.owner.name,
        plan_name=plan_name,
        cron_tasks_count=cron_count or 0,
        delayed_tasks_count=delayed_count or 0,
        executions_count=exec_count or 0,
        active_cron_tasks=active_cron or 0,
        pending_delayed_tasks=pending_delayed or 0,
        default_timezone=workspace.default_timezone,
        webhook_secret=workspace.webhook_secret,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    admin: AdminUser,
    db: DB,
    workspace_id: str,
    data: UpdateWorkspaceRequest,
):
    """Update workspace by admin."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    update_data = data.model_dump(exclude_unset=True)

    # Check for slug conflict if updating slug
    if "slug" in update_data:
        existing = await db.scalar(
            select(Workspace).where(
                Workspace.slug == update_data["slug"],
                Workspace.id != workspace.id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Slug already in use")

    for key, value in update_data.items():
        setattr(workspace, key, value)

    await db.commit()
    await db.refresh(workspace)

    return {"message": "Workspace updated successfully"}


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(admin: AdminUser, db: DB, workspace_id: str):
    """Delete workspace by admin. This is a destructive operation."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Delete all related data (cascade should handle most, but be explicit)
    await db.delete(workspace)
    await db.commit()

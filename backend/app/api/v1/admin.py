"""Admin API endpoints."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser
from app.models import (
    CronTask,
    DelayedTask,
    Execution,
    Heartbeat,
    Payment,
    Plan,
    SSLMonitor,
    Subscription,
    TaskChain,
    User,
    Workspace,
)
from app.models.notification_template import NotificationChannel, NotificationTemplate
from app.models.payment import PaymentStatus
from app.models.subscription import SubscriptionStatus
from app.services.billing import billing_service
from app.services.template_service import template_service

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
    total_task_chains: int
    active_task_chains: int
    total_heartbeats: int
    active_heartbeats: int
    total_ssl_monitors: int
    active_ssl_monitors: int
    total_executions: int
    executions_today: int
    executions_this_week: int
    success_rate: float
    active_subscriptions: int
    paid_subscriptions: int  # Subscriptions with actual payments (excludes admin-assigned)
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
    last_login_at: datetime | None
    workspaces_count: int
    cron_tasks_count: int
    delayed_tasks_count: int
    task_chains_count: int
    heartbeats_count: int
    ssl_monitors_count: int
    executions_count: int
    plan_name: str
    subscription_ends_at: datetime | None

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
    task_chains_count: int
    heartbeats_count: int
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


class AssignPlanRequest(BaseModel):
    """Request to assign a plan to user."""

    plan_id: str
    duration_days: int = 30  # Default 30 days


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(admin: AdminUser, db: DB):
    """Get admin dashboard statistics."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # User stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True)))
    verified_users = await db.scalar(select(func.count(User.id)).where(User.email_verified.is_(True)))

    # Workspace stats
    total_workspaces = await db.scalar(select(func.count(Workspace.id)))

    # Task stats
    total_cron = await db.scalar(select(func.count(CronTask.id)))
    active_cron = await db.scalar(select(func.count(CronTask.id)).where(CronTask.is_active.is_(True)))
    total_delayed = await db.scalar(select(func.count(DelayedTask.id)))
    pending_delayed = await db.scalar(select(func.count(DelayedTask.id)).where(DelayedTask.status == "pending"))

    # Task chains stats
    total_chains = await db.scalar(select(func.count(TaskChain.id)))
    active_chains = await db.scalar(select(func.count(TaskChain.id)).where(TaskChain.is_active.is_(True)))

    # Heartbeat stats (active = not paused)
    total_heartbeats = await db.scalar(select(func.count(Heartbeat.id)))
    active_heartbeats = await db.scalar(
        select(func.count(Heartbeat.id)).where(Heartbeat.status != "paused")
    )

    # SSL monitor stats (active = not paused)
    total_ssl_monitors = await db.scalar(select(func.count(SSLMonitor.id)))
    active_ssl_monitors = await db.scalar(
        select(func.count(SSLMonitor.id)).where(SSLMonitor.is_paused.is_(False))
    )

    # Execution stats
    total_executions = await db.scalar(select(func.count(Execution.id)))
    executions_today = await db.scalar(select(func.count(Execution.id)).where(Execution.started_at >= today))
    executions_this_week = await db.scalar(select(func.count(Execution.id)).where(Execution.started_at >= week_ago))

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
    success_rate = ((successful or 0) / total_recent * 100) if total_recent else 0

    # Subscription stats
    active_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end > now,
        )
    )

    # Paid subscriptions - count active subscriptions that were paid via YooKassa
    # Admin-assigned subscriptions don't have yookassa_payment_method_id set
    paid_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end > now,
            Subscription.yookassa_payment_method_id.isnot(None),
        )
    )

    # Revenue (this month) - sum of successful payments via payment system only
    # Exclude manual plan assignments by admin (they don't have yookassa_payment_id)
    revenue = (
        await db.scalar(
            select(func.sum(Payment.amount)).where(
                Payment.created_at >= month_start,
                Payment.status == PaymentStatus.SUCCEEDED,
                Payment.yookassa_payment_id.isnot(None),
            )
        )
        or 0
    )

    return AdminStatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        verified_users=verified_users or 0,
        total_workspaces=total_workspaces or 0,
        total_cron_tasks=total_cron or 0,
        active_cron_tasks=active_cron or 0,
        total_delayed_tasks=total_delayed or 0,
        pending_delayed_tasks=pending_delayed or 0,
        total_task_chains=total_chains or 0,
        active_task_chains=active_chains or 0,
        total_heartbeats=total_heartbeats or 0,
        active_heartbeats=active_heartbeats or 0,
        total_ssl_monitors=total_ssl_monitors or 0,
        active_ssl_monitors=active_ssl_monitors or 0,
        total_executions=total_executions or 0,
        executions_today=executions_today or 0,
        executions_this_week=executions_this_week or 0,
        success_rate=round(success_rate, 1),
        active_subscriptions=active_subs or 0,
        paid_subscriptions=paid_subs or 0,
        revenue_this_month=float(revenue) / 100,  # Convert from kopeks to rubles
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
        query = query.where((User.email.ilike(search_filter)) | (User.name.ilike(search_filter)))

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
        workspace_count = await db.scalar(select(func.count(Workspace.id)).where(Workspace.owner_id == user.id))
        cron_tasks_count = await db.scalar(
            select(func.count(CronTask.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )
        delayed_tasks_count = await db.scalar(
            select(func.count(DelayedTask.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )
        task_chains_count = await db.scalar(
            select(func.count(TaskChain.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )
        heartbeats_count = await db.scalar(
            select(func.count(Heartbeat.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )
        ssl_monitors_count = await db.scalar(
            select(func.count(SSLMonitor.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )
        executions_count = await db.scalar(
            select(func.count(Execution.id)).join(Workspace).where(Workspace.owner_id == user.id)
        )

        # Get active subscription
        sub = await db.scalar(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.created_at.desc())
        )
        plan_name = sub.plan.name if sub and sub.plan else "free"
        subscription_ends_at = sub.current_period_end if sub else None

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
                last_login_at=user.last_login_at,
                workspaces_count=workspace_count or 0,
                cron_tasks_count=cron_tasks_count or 0,
                delayed_tasks_count=delayed_tasks_count or 0,
                task_chains_count=task_chains_count or 0,
                heartbeats_count=heartbeats_count or 0,
                ssl_monitors_count=ssl_monitors_count or 0,
                executions_count=executions_count or 0,
                plan_name=plan_name,
                subscription_ends_at=subscription_ends_at,
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

    workspace_count = await db.scalar(select(func.count(Workspace.id)).where(Workspace.owner_id == user.id))
    cron_tasks_count = await db.scalar(
        select(func.count(CronTask.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )
    delayed_tasks_count = await db.scalar(
        select(func.count(DelayedTask.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )
    task_chains_count = await db.scalar(
        select(func.count(TaskChain.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )
    heartbeats_count = await db.scalar(
        select(func.count(Heartbeat.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )
    ssl_monitors_count = await db.scalar(
        select(func.count(SSLMonitor.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )
    executions_count = await db.scalar(
        select(func.count(Execution.id)).join(Workspace).where(Workspace.owner_id == user.id)
    )

    # Get active subscription
    sub = await db.scalar(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.created_at.desc())
    )
    plan_name = sub.plan.name if sub and sub.plan else "free"
    subscription_ends_at = sub.current_period_end if sub else None

    return UserListItem(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        telegram_username=user.telegram_username,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        workspaces_count=workspace_count or 0,
        cron_tasks_count=cron_tasks_count or 0,
        delayed_tasks_count=delayed_tasks_count or 0,
        task_chains_count=task_chains_count or 0,
        heartbeats_count=heartbeats_count or 0,
        ssl_monitors_count=ssl_monitors_count or 0,
        executions_count=executions_count or 0,
        plan_name=plan_name,
        subscription_ends_at=subscription_ends_at,
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


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(admin: AdminUser, db: DB, user_id: str):
    """Delete user and all their data (admin only). This is a destructive operation."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from deleting themselves
    if str(user.id) == str(admin.id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account",
        )

    # Delete user (cascade will handle related data)
    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/subscription")
async def assign_user_plan(
    admin: AdminUser,
    db: DB,
    user_id: str,
    data: AssignPlanRequest,
):
    """Assign a plan to user (creates subscription without payment)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan = await db.get(Plan, data.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Deactivate existing active subscriptions
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    existing_subs = result.scalars().all()
    for sub in existing_subs:
        sub.status = SubscriptionStatus.CANCELLED

    # Create new subscription
    now = datetime.utcnow()
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=data.duration_days),
        cancel_at_period_end=False,
    )
    db.add(subscription)
    await db.commit()

    return {"message": f"Plan '{plan.display_name}' assigned to user for {data.duration_days} days"}


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

    # Base query with owner eager load
    query = select(Workspace).options(selectinload(Workspace.owner))

    if search:
        search_filter = f"%{search}%"
        query = query.join(User, Workspace.owner_id == User.id).where(
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
        cron_count = await db.scalar(select(func.count(CronTask.id)).where(CronTask.workspace_id == ws.id))
        delayed_count = await db.scalar(select(func.count(DelayedTask.id)).where(DelayedTask.workspace_id == ws.id))
        chains_count = await db.scalar(select(func.count(TaskChain.id)).where(TaskChain.workspace_id == ws.id))
        heartbeats_count = await db.scalar(select(func.count(Heartbeat.id)).where(Heartbeat.workspace_id == ws.id))
        exec_count = await db.scalar(select(func.count(Execution.id)).where(Execution.workspace_id == ws.id))

        # Get subscription plan
        sub = await db.scalar(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.user_id == ws.owner_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.created_at.desc())
        )
        plan_name = sub.plan.name if sub and sub.plan else "free"

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
                task_chains_count=chains_count or 0,
                heartbeats_count=heartbeats_count or 0,
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
    result = await db.execute(
        select(Workspace).options(selectinload(Workspace.owner)).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get counts
    cron_count = await db.scalar(select(func.count(CronTask.id)).where(CronTask.workspace_id == workspace.id))
    active_cron = await db.scalar(
        select(func.count(CronTask.id)).where(
            CronTask.workspace_id == workspace.id,
            CronTask.is_active.is_(True),
        )
    )
    delayed_count = await db.scalar(select(func.count(DelayedTask.id)).where(DelayedTask.workspace_id == workspace.id))
    pending_delayed = await db.scalar(
        select(func.count(DelayedTask.id)).where(
            DelayedTask.workspace_id == workspace.id,
            DelayedTask.status == "pending",
        )
    )
    exec_count = await db.scalar(select(func.count(Execution.id)).where(Execution.workspace_id == workspace.id))

    # Get subscription plan (subscription is per-user, not per-workspace)
    sub = await db.scalar(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == workspace.owner_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.created_at.desc())
    )
    plan_name = sub.plan.name if sub and sub.plan else "free"

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


# ============== Plan Management ==============


class PlanListItem(BaseModel):
    """Plan list item for admin."""

    id: str
    name: str
    display_name: str
    description: str | None
    price_monthly: int
    price_yearly: int
    max_cron_tasks: int
    max_delayed_tasks_per_month: int
    max_workspaces: int
    max_execution_history_days: int
    min_cron_interval_minutes: int
    telegram_notifications: bool
    email_notifications: bool
    webhook_callbacks: bool
    custom_headers: bool
    retry_on_failure: bool
    # Task Chains limits
    max_task_chains: int
    max_chain_steps: int
    chain_variable_substitution: bool
    min_chain_interval_minutes: int
    # Heartbeat monitor limits
    max_heartbeats: int
    min_heartbeat_interval_minutes: int
    # SSL monitor limits
    max_ssl_monitors: int
    # Process monitor limits
    max_process_monitors: int
    min_process_monitor_interval_minutes: int
    # Overlap prevention settings
    overlap_prevention_enabled: bool
    max_queue_size: int
    is_active: bool
    is_public: bool
    sort_order: int
    subscriptions_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    """Plan list response."""

    plans: list[PlanListItem]
    total: int


class CreatePlanRequest(BaseModel):
    """Request to create a plan."""

    name: str
    display_name: str
    description: str | None = None
    price_monthly: int = Field(default=0, ge=0)
    price_yearly: int = Field(default=0, ge=0)
    max_cron_tasks: int = Field(default=5, ge=0)
    max_delayed_tasks_per_month: int = Field(default=100, ge=0)
    max_workspaces: int = Field(default=1, ge=1)
    max_execution_history_days: int = Field(default=7, ge=1)
    min_cron_interval_minutes: int = Field(default=5, ge=1)
    telegram_notifications: bool = False
    email_notifications: bool = False
    webhook_callbacks: bool = False
    custom_headers: bool = True
    retry_on_failure: bool = False
    # Task Chains limits
    max_task_chains: int = Field(default=0, ge=0)
    max_chain_steps: int = Field(default=5, ge=1)
    chain_variable_substitution: bool = False
    min_chain_interval_minutes: int = Field(default=15, ge=1)
    # Heartbeat monitor limits
    max_heartbeats: int = Field(default=0, ge=0)
    min_heartbeat_interval_minutes: int = Field(default=5, ge=1)
    # SSL monitor limits
    max_ssl_monitors: int = Field(default=0, ge=0)
    # Process monitor limits
    max_process_monitors: int = Field(default=0, ge=0)
    min_process_monitor_interval_minutes: int = Field(default=5, ge=1)
    # Overlap prevention settings
    overlap_prevention_enabled: bool = False
    max_queue_size: int = Field(default=10, ge=0)
    is_active: bool = True
    is_public: bool = True
    sort_order: int = 0


class UpdatePlanRequest(BaseModel):
    """Request to update a plan."""

    display_name: str | None = None
    description: str | None = None
    price_monthly: int | None = Field(default=None, ge=0)
    price_yearly: int | None = Field(default=None, ge=0)
    max_cron_tasks: int | None = Field(default=None, ge=0)
    max_delayed_tasks_per_month: int | None = Field(default=None, ge=0)
    max_workspaces: int | None = Field(default=None, ge=1)
    max_execution_history_days: int | None = Field(default=None, ge=1)
    min_cron_interval_minutes: int | None = Field(default=None, ge=1)
    telegram_notifications: bool | None = None
    email_notifications: bool | None = None
    webhook_callbacks: bool | None = None
    custom_headers: bool | None = None
    retry_on_failure: bool | None = None
    # Task Chains limits
    max_task_chains: int | None = Field(default=None, ge=0)
    max_chain_steps: int | None = Field(default=None, ge=1)
    chain_variable_substitution: bool | None = None
    min_chain_interval_minutes: int | None = Field(default=None, ge=1)
    # Heartbeat monitor limits
    max_heartbeats: int | None = Field(default=None, ge=0)
    min_heartbeat_interval_minutes: int | None = Field(default=None, ge=1)
    # SSL monitor limits
    max_ssl_monitors: int | None = Field(default=None, ge=0)
    # Process monitor limits
    max_process_monitors: int | None = Field(default=None, ge=0)
    min_process_monitor_interval_minutes: int | None = Field(default=None, ge=1)
    # Overlap prevention settings
    overlap_prevention_enabled: bool | None = None
    max_queue_size: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_public: bool | None = None
    sort_order: int | None = None


@router.get("/plans", response_model=PlanListResponse)
async def list_plans(admin: AdminUser, db: DB):
    """List all plans."""
    result = await db.execute(select(Plan).order_by(Plan.sort_order, Plan.created_at))
    plans = result.scalars().all()

    plan_items = []
    for plan in plans:
        # Count active subscriptions for this plan
        subs_count = await db.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.plan_id == plan.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )

        plan_items.append(
            PlanListItem(
                id=str(plan.id),
                name=plan.name,
                display_name=plan.display_name,
                description=plan.description,
                price_monthly=plan.price_monthly,
                price_yearly=plan.price_yearly,
                max_cron_tasks=plan.max_cron_tasks,
                max_delayed_tasks_per_month=plan.max_delayed_tasks_per_month,
                max_workspaces=plan.max_workspaces,
                max_execution_history_days=plan.max_execution_history_days,
                min_cron_interval_minutes=plan.min_cron_interval_minutes,
                telegram_notifications=plan.telegram_notifications,
                email_notifications=plan.email_notifications,
                webhook_callbacks=plan.webhook_callbacks,
                custom_headers=plan.custom_headers,
                retry_on_failure=plan.retry_on_failure,
                max_task_chains=plan.max_task_chains,
                max_chain_steps=plan.max_chain_steps,
                chain_variable_substitution=plan.chain_variable_substitution,
                min_chain_interval_minutes=plan.min_chain_interval_minutes,
                max_heartbeats=plan.max_heartbeats,
                min_heartbeat_interval_minutes=plan.min_heartbeat_interval_minutes,
                max_ssl_monitors=plan.max_ssl_monitors,
                max_process_monitors=plan.max_process_monitors,
                min_process_monitor_interval_minutes=plan.min_process_monitor_interval_minutes,
                overlap_prevention_enabled=plan.overlap_prevention_enabled,
                max_queue_size=plan.max_queue_size,
                is_active=plan.is_active,
                is_public=plan.is_public,
                sort_order=plan.sort_order,
                subscriptions_count=subs_count or 0,
                created_at=plan.created_at,
            )
        )

    return PlanListResponse(plans=plan_items, total=len(plan_items))


@router.post("/plans", response_model=PlanListItem, status_code=status.HTTP_201_CREATED)
async def create_plan(admin: AdminUser, db: DB, data: CreatePlanRequest):
    """Create a new plan."""
    # Check if name already exists
    existing = await db.scalar(select(Plan).where(Plan.name == data.name))
    if existing:
        raise HTTPException(status_code=409, detail="Plan with this name already exists")

    plan = Plan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    # Invalidate plans cache
    await billing_service.invalidate_plans_cache()

    return PlanListItem(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        max_cron_tasks=plan.max_cron_tasks,
        max_delayed_tasks_per_month=plan.max_delayed_tasks_per_month,
        max_workspaces=plan.max_workspaces,
        max_execution_history_days=plan.max_execution_history_days,
        min_cron_interval_minutes=plan.min_cron_interval_minutes,
        telegram_notifications=plan.telegram_notifications,
        email_notifications=plan.email_notifications,
        webhook_callbacks=plan.webhook_callbacks,
        custom_headers=plan.custom_headers,
        retry_on_failure=plan.retry_on_failure,
        max_task_chains=plan.max_task_chains,
        max_chain_steps=plan.max_chain_steps,
        chain_variable_substitution=plan.chain_variable_substitution,
        min_chain_interval_minutes=plan.min_chain_interval_minutes,
        max_heartbeats=plan.max_heartbeats,
        min_heartbeat_interval_minutes=plan.min_heartbeat_interval_minutes,
        max_ssl_monitors=plan.max_ssl_monitors,
        max_process_monitors=plan.max_process_monitors,
        min_process_monitor_interval_minutes=plan.min_process_monitor_interval_minutes,
        overlap_prevention_enabled=plan.overlap_prevention_enabled,
        max_queue_size=plan.max_queue_size,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        subscriptions_count=0,
        created_at=plan.created_at,
    )


@router.get("/plans/{plan_id}", response_model=PlanListItem)
async def get_plan(admin: AdminUser, db: DB, plan_id: str):
    """Get plan by ID."""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    subs_count = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_id == plan.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )

    return PlanListItem(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        max_cron_tasks=plan.max_cron_tasks,
        max_delayed_tasks_per_month=plan.max_delayed_tasks_per_month,
        max_workspaces=plan.max_workspaces,
        max_execution_history_days=plan.max_execution_history_days,
        min_cron_interval_minutes=plan.min_cron_interval_minutes,
        telegram_notifications=plan.telegram_notifications,
        email_notifications=plan.email_notifications,
        webhook_callbacks=plan.webhook_callbacks,
        custom_headers=plan.custom_headers,
        retry_on_failure=plan.retry_on_failure,
        max_task_chains=plan.max_task_chains,
        max_chain_steps=plan.max_chain_steps,
        chain_variable_substitution=plan.chain_variable_substitution,
        min_chain_interval_minutes=plan.min_chain_interval_minutes,
        max_heartbeats=plan.max_heartbeats,
        min_heartbeat_interval_minutes=plan.min_heartbeat_interval_minutes,
        max_ssl_monitors=plan.max_ssl_monitors,
        max_process_monitors=plan.max_process_monitors,
        min_process_monitor_interval_minutes=plan.min_process_monitor_interval_minutes,
        overlap_prevention_enabled=plan.overlap_prevention_enabled,
        max_queue_size=plan.max_queue_size,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        subscriptions_count=subs_count or 0,
        created_at=plan.created_at,
    )


@router.patch("/plans/{plan_id}", response_model=PlanListItem)
async def update_plan(admin: AdminUser, db: DB, plan_id: str, data: UpdatePlanRequest):
    """Update a plan."""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)

    # Invalidate plans cache
    await billing_service.invalidate_plans_cache()

    subs_count = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_id == plan.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )

    return PlanListItem(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        max_cron_tasks=plan.max_cron_tasks,
        max_delayed_tasks_per_month=plan.max_delayed_tasks_per_month,
        max_workspaces=plan.max_workspaces,
        max_execution_history_days=plan.max_execution_history_days,
        min_cron_interval_minutes=plan.min_cron_interval_minutes,
        telegram_notifications=plan.telegram_notifications,
        email_notifications=plan.email_notifications,
        webhook_callbacks=plan.webhook_callbacks,
        custom_headers=plan.custom_headers,
        retry_on_failure=plan.retry_on_failure,
        max_task_chains=plan.max_task_chains,
        max_chain_steps=plan.max_chain_steps,
        chain_variable_substitution=plan.chain_variable_substitution,
        min_chain_interval_minutes=plan.min_chain_interval_minutes,
        max_heartbeats=plan.max_heartbeats,
        min_heartbeat_interval_minutes=plan.min_heartbeat_interval_minutes,
        max_ssl_monitors=plan.max_ssl_monitors,
        max_process_monitors=plan.max_process_monitors,
        min_process_monitor_interval_minutes=plan.min_process_monitor_interval_minutes,
        overlap_prevention_enabled=plan.overlap_prevention_enabled,
        max_queue_size=plan.max_queue_size,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        subscriptions_count=subs_count or 0,
        created_at=plan.created_at,
    )


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(admin: AdminUser, db: DB, plan_id: str):
    """Delete a plan. Cannot delete plans with active subscriptions."""
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check for active subscriptions
    subs_count = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_id == plan.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    if subs_count and subs_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete plan with {subs_count} active subscription(s)",
        )

    await db.delete(plan)
    await db.commit()

    # Invalidate plans cache
    await billing_service.invalidate_plans_cache()


# ============== Notification Templates ==============


class NotificationTemplateResponse(BaseModel):
    """Notification template response for admin."""

    id: str
    code: str
    language: str
    channel: str
    subject: str | None
    body: str
    description: str | None
    variables: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationTemplateListResponse(BaseModel):
    """Notification template list response."""

    templates: list[NotificationTemplateResponse]
    total: int


class NotificationTemplateUpdate(BaseModel):
    """Request to update a notification template."""

    subject: str | None = None
    body: str | None = None
    is_active: bool | None = None


class TemplatePreviewRequest(BaseModel):
    """Request to preview a template with test data."""

    body: str
    subject: str | None = None
    variables: dict[str, str]


class TemplatePreviewResponse(BaseModel):
    """Template preview response."""

    subject: str | None
    body: str


@router.get("/notification-templates", response_model=NotificationTemplateListResponse)
async def list_notification_templates(
    admin: AdminUser,
    db: DB,
    code: str | None = None,
    language: str | None = None,
    channel: str | None = None,
):
    """List all notification templates with optional filtering."""
    query = select(NotificationTemplate).order_by(
        NotificationTemplate.code,
        NotificationTemplate.language,
        NotificationTemplate.channel,
    )

    if code:
        query = query.where(NotificationTemplate.code == code)
    if language:
        query = query.where(NotificationTemplate.language == language)
    if channel:
        query = query.where(NotificationTemplate.channel == NotificationChannel(channel))

    result = await db.execute(query)
    templates = result.scalars().all()

    template_items = [
        NotificationTemplateResponse(
            id=str(t.id),
            code=t.code,
            language=t.language,
            channel=t.channel.value,
            subject=t.subject,
            body=t.body,
            description=t.description,
            variables=t.variables,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]

    return NotificationTemplateListResponse(
        templates=template_items,
        total=len(template_items),
    )


@router.get("/notification-templates/{template_id}", response_model=NotificationTemplateResponse)
async def get_notification_template(admin: AdminUser, db: DB, template_id: str):
    """Get a notification template by ID."""
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return NotificationTemplateResponse(
        id=str(template.id),
        code=template.code,
        language=template.language,
        channel=template.channel.value,
        subject=template.subject,
        body=template.body,
        description=template.description,
        variables=template.variables,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.patch("/notification-templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_notification_template(
    admin: AdminUser,
    db: DB,
    template_id: str,
    data: NotificationTemplateUpdate,
):
    """Update a notification template (subject, body, is_active)."""
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)

    return NotificationTemplateResponse(
        id=str(template.id),
        code=template.code,
        language=template.language,
        channel=template.channel.value,
        subject=template.subject,
        body=template.body,
        description=template.description,
        variables=template.variables,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("/notification-templates/preview", response_model=TemplatePreviewResponse)
async def preview_notification_template(admin: AdminUser, data: TemplatePreviewRequest):
    """Preview a template with test variables."""
    try:
        rendered_body = data.body.format(**data.variables)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing variable in body: {e}")

    rendered_subject = None
    if data.subject:
        try:
            rendered_subject = data.subject.format(**data.variables)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Missing variable in subject: {e}")

    return TemplatePreviewResponse(subject=rendered_subject, body=rendered_body)


@router.post("/notification-templates/reset/{template_id}", response_model=NotificationTemplateResponse)
async def reset_notification_template(admin: AdminUser, db: DB, template_id: str):
    """Reset a template to its default values."""
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get default template data
    default = template_service.get_default_template(template.code, template.language, template.channel)
    if not default:
        raise HTTPException(
            status_code=404,
            detail="No default template found for this code/language/channel",
        )

    # Reset to default values
    template.subject = default.get("subject")
    template.body = default["body"]
    template.is_active = True

    await db.commit()
    await db.refresh(template)

    return NotificationTemplateResponse(
        id=str(template.id),
        code=template.code,
        language=template.language,
        channel=template.channel.value,
        subject=template.subject,
        body=template.body,
        description=template.description,
        variables=template.variables,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )

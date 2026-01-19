from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, ActiveSubscriptionWorkspace, CurrentWorkspace, UserPlan
from app.db.repositories.ssl_monitors import SSLMonitorRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.ssl_monitor import SSLMonitorStatus
from app.schemas.cron_task import PaginationMeta
from app.schemas.ssl_monitor import (
    SSLMonitorCreate,
    SSLMonitorListResponse,
    SSLMonitorResponse,
    SSLMonitorUpdate,
)
from app.services.ssl_monitor import ssl_monitor_service

router = APIRouter(prefix="/workspaces/{workspace_id}/ssl-monitors", tags=["SSL Monitors"])


@router.get("", response_model=SSLMonitorListResponse)
async def list_ssl_monitors(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all SSL monitors for a workspace."""
    ssl_repo = SSLMonitorRepository(db)
    skip = (page - 1) * limit

    monitors = await ssl_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
    )
    total = await ssl_repo.count_by_workspace(workspace_id=workspace.id)

    return SSLMonitorListResponse(
        monitors=[SSLMonitorResponse.model_validate(m) for m in monitors],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit if total > 0 else 0,
        ),
    )


@router.post("", response_model=SSLMonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_ssl_monitor(
    data: SSLMonitorCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new SSL monitor.

    Creates the monitor and immediately performs the first SSL check.
    """
    ssl_repo = SSLMonitorRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Check plan limits
    if user_plan.max_ssl_monitors == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSL monitoring is not available on your plan",
        )

    current_count = await ssl_repo.count_by_workspace(workspace.id)
    if current_count >= user_plan.max_ssl_monitors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"SSL monitor limit reached. Your plan allows {user_plan.max_ssl_monitors} monitor(s)",
        )

    # Check if domain already exists in workspace
    existing = await ssl_repo.get_by_domain(workspace.id, data.domain)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain {data.domain} is already being monitored",
        )

    # Create monitor with immediate check scheduled
    now = datetime.utcnow()
    monitor = await ssl_repo.create(
        workspace_id=workspace.id,
        name=data.name,
        description=data.description,
        domain=data.domain,
        port=data.port,
        notify_on_expiring=data.notify_on_expiring,
        notify_on_error=data.notify_on_error,
        status=SSLMonitorStatus.PENDING,
        next_check_at=now,  # Immediate check
    )

    # Update workspace counter
    await workspace_repo.update_ssl_monitors_count(workspace, 1)

    # Perform immediate SSL check
    monitor = await ssl_monitor_service.process_check(db, monitor)

    await db.commit()

    return SSLMonitorResponse.model_validate(monitor)


@router.get("/{monitor_id}", response_model=SSLMonitorResponse)
async def get_ssl_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a specific SSL monitor."""
    ssl_repo = SSLMonitorRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    return SSLMonitorResponse.model_validate(monitor)


@router.patch("/{monitor_id}", response_model=SSLMonitorResponse)
async def update_ssl_monitor(
    monitor_id: UUID,
    data: SSLMonitorUpdate,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Update an SSL monitor."""
    ssl_repo = SSLMonitorRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if update_data:
        monitor = await ssl_repo.update(monitor, **update_data)
        await db.commit()

    return SSLMonitorResponse.model_validate(monitor)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ssl_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete an SSL monitor."""
    ssl_repo = SSLMonitorRepository(db)
    workspace_repo = WorkspaceRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    await ssl_repo.delete(monitor)
    await workspace_repo.update_ssl_monitors_count(workspace, -1)
    await db.commit()


@router.post("/{monitor_id}/pause", response_model=SSLMonitorResponse)
async def pause_ssl_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Pause an SSL monitor."""
    ssl_repo = SSLMonitorRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    if monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL monitor is already paused",
        )

    monitor = await ssl_repo.pause(monitor)
    await db.commit()

    return SSLMonitorResponse.model_validate(monitor)


@router.post("/{monitor_id}/resume", response_model=SSLMonitorResponse)
async def resume_ssl_monitor(
    monitor_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Resume a paused SSL monitor."""
    ssl_repo = SSLMonitorRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    if not monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL monitor is not paused",
        )

    monitor = await ssl_repo.resume(monitor)
    await db.commit()

    return SSLMonitorResponse.model_validate(monitor)


@router.post("/{monitor_id}/check", response_model=SSLMonitorResponse)
async def check_ssl_monitor(
    monitor_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Manually trigger an SSL check for a monitor."""
    ssl_repo = SSLMonitorRepository(db)
    monitor = await ssl_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSL monitor not found",
        )

    if monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check a paused monitor. Resume it first.",
        )

    # Perform check
    monitor = await ssl_monitor_service.process_check(db, monitor)
    await db.commit()

    return SSLMonitorResponse.model_validate(monitor)

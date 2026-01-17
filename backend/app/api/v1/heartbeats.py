from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, ActiveSubscriptionWorkspace, CurrentWorkspace, UserPlan
from app.config import settings
from app.db.repositories.heartbeats import HeartbeatPingRepository, HeartbeatRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.heartbeat import HeartbeatStatus
from app.schemas.cron_task import PaginationMeta
from app.schemas.heartbeat import (
    HeartbeatCreate,
    HeartbeatListResponse,
    HeartbeatPingListResponse,
    HeartbeatPingResponse,
    HeartbeatResponse,
    HeartbeatUpdate,
    parse_interval_to_seconds,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/heartbeats", tags=["Heartbeats"])


def build_ping_url(ping_token: str) -> str:
    """Build the public ping URL."""
    base = settings.api_url.rstrip("/")
    return f"{base}/ping/{ping_token}"


def heartbeat_to_response(heartbeat) -> HeartbeatResponse:
    """Convert heartbeat model to response with ping_url."""
    response = HeartbeatResponse.model_validate(heartbeat)
    response.ping_url = build_ping_url(heartbeat.ping_token)
    return response


@router.get("", response_model=HeartbeatListResponse)
async def list_heartbeats(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all heartbeat monitors for a workspace."""
    heartbeat_repo = HeartbeatRepository(db)
    skip = (page - 1) * limit

    heartbeats = await heartbeat_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
    )
    total = await heartbeat_repo.count_by_workspace(workspace_id=workspace.id)

    return HeartbeatListResponse(
        heartbeats=[heartbeat_to_response(h) for h in heartbeats],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post("", response_model=HeartbeatResponse, status_code=status.HTTP_201_CREATED)
async def create_heartbeat(
    data: HeartbeatCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Check plan limits
    current_count = await heartbeat_repo.count_by_workspace(workspace.id)
    if current_count >= user_plan.max_heartbeats:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Heartbeat monitor limit reached. Your plan allows {user_plan.max_heartbeats} heartbeat(s)",
        )

    # Parse intervals
    expected_interval_seconds = parse_interval_to_seconds(data.expected_interval)
    grace_period_seconds = parse_interval_to_seconds(data.grace_period)

    # Check minimum interval
    interval_minutes = expected_interval_seconds // 60
    if interval_minutes < user_plan.min_heartbeat_interval_minutes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Heartbeat interval too short. Your plan requires minimum {user_plan.min_heartbeat_interval_minutes} minute(s)",
        )

    # Calculate initial next_expected_at (now + interval + grace)
    now = datetime.utcnow()
    next_expected_at = datetime.fromtimestamp(
        now.timestamp() + expected_interval_seconds + grace_period_seconds
    )

    # Create heartbeat
    heartbeat = await heartbeat_repo.create(
        workspace_id=workspace.id,
        name=data.name,
        description=data.description,
        expected_interval=expected_interval_seconds,
        grace_period=grace_period_seconds,
        notify_on_late=data.notify_on_late,
        notify_on_recovery=data.notify_on_recovery,
        status=HeartbeatStatus.WAITING,
        next_expected_at=next_expected_at,
    )

    # Update workspace counter
    await workspace_repo.update_heartbeats_count(workspace, 1)
    await db.commit()

    return heartbeat_to_response(heartbeat)


@router.get("/{heartbeat_id}", response_model=HeartbeatResponse)
async def get_heartbeat(
    heartbeat_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a specific heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)

    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    return heartbeat_to_response(heartbeat)


@router.patch("/{heartbeat_id}", response_model=HeartbeatResponse)
async def update_heartbeat(
    heartbeat_id: UUID,
    data: HeartbeatUpdate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Update a heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)

    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Parse intervals if provided
    if "expected_interval" in update_data and update_data["expected_interval"]:
        expected_interval_seconds = parse_interval_to_seconds(update_data["expected_interval"])
        interval_minutes = expected_interval_seconds // 60
        if interval_minutes < user_plan.min_heartbeat_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Heartbeat interval too short. Your plan requires minimum {user_plan.min_heartbeat_interval_minutes} minute(s)",
            )
        update_data["expected_interval"] = expected_interval_seconds

    if "grace_period" in update_data and update_data["grace_period"]:
        update_data["grace_period"] = parse_interval_to_seconds(update_data["grace_period"])

    if update_data:
        heartbeat = await heartbeat_repo.update(heartbeat, **update_data)
        await db.commit()

    return heartbeat_to_response(heartbeat)


@router.delete("/{heartbeat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_heartbeat(
    heartbeat_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    workspace_repo = WorkspaceRepository(db)
    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)

    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    await heartbeat_repo.delete(heartbeat)
    await workspace_repo.update_heartbeats_count(workspace, -1)
    await db.commit()


@router.post("/{heartbeat_id}/pause", response_model=HeartbeatResponse)
async def pause_heartbeat(
    heartbeat_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Pause a heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)

    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    if heartbeat.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heartbeat monitor is already paused",
        )

    heartbeat = await heartbeat_repo.pause(heartbeat)
    await db.commit()

    return heartbeat_to_response(heartbeat)


@router.post("/{heartbeat_id}/resume", response_model=HeartbeatResponse)
async def resume_heartbeat(
    heartbeat_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Resume a paused heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)

    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    if not heartbeat.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heartbeat monitor is not paused",
        )

    heartbeat = await heartbeat_repo.resume(heartbeat)
    await db.commit()

    return heartbeat_to_response(heartbeat)


@router.get("/{heartbeat_id}/pings", response_model=HeartbeatPingListResponse)
async def list_heartbeat_pings(
    heartbeat_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List ping history for a heartbeat monitor."""
    heartbeat_repo = HeartbeatRepository(db)
    ping_repo = HeartbeatPingRepository(db)

    heartbeat = await heartbeat_repo.get_by_id(heartbeat_id)
    if heartbeat is None or heartbeat.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    skip = (page - 1) * limit
    pings = await ping_repo.get_by_heartbeat(
        heartbeat_id=heartbeat_id,
        skip=skip,
        limit=limit,
    )
    total = await ping_repo.count_by_heartbeat(heartbeat_id=heartbeat_id)

    return HeartbeatPingListResponse(
        pings=[HeartbeatPingResponse.model_validate(p) for p in pings],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )

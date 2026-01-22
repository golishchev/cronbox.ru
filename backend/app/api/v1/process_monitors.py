"""Process Monitor CRUD API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, ActiveSubscriptionWorkspace, CurrentWorkspace, UserPlan
from app.config import settings
from app.db.repositories.process_monitors import (
    ProcessMonitorEventRepository,
    ProcessMonitorRepository,
)
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.process_monitor import ProcessMonitorStatus, ScheduleType
from app.schemas.cron_task import PaginationMeta
from app.schemas.process_monitor import (
    ProcessMonitorCreate,
    ProcessMonitorEventListResponse,
    ProcessMonitorEventResponse,
    ProcessMonitorListResponse,
    ProcessMonitorResponse,
    ProcessMonitorUpdate,
    parse_interval_to_seconds,
)
from app.services.process_monitor import process_monitor_service

router = APIRouter(prefix="/workspaces/{workspace_id}/process-monitors", tags=["Process Monitors"])


def build_ping_urls(start_token: str, end_token: str) -> tuple[str, str]:
    """Build the public ping URLs for start and end."""
    base = settings.api_url.rstrip("/")
    return f"{base}/ping/start/{start_token}", f"{base}/ping/end/{end_token}"


def monitor_to_response(monitor) -> ProcessMonitorResponse:
    """Convert process monitor model to response with ping URLs."""
    response = ProcessMonitorResponse.model_validate(monitor)
    response.start_url, response.end_url = build_ping_urls(monitor.start_token, monitor.end_token)
    return response


@router.get("", response_model=ProcessMonitorListResponse)
async def list_process_monitors(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all process monitors for a workspace."""
    monitor_repo = ProcessMonitorRepository(db)
    skip = (page - 1) * limit

    monitors = await monitor_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
    )
    total = await monitor_repo.count_by_workspace(workspace_id=workspace.id)

    return ProcessMonitorListResponse(
        process_monitors=[monitor_to_response(m) for m in monitors],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post("", response_model=ProcessMonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_process_monitor(
    data: ProcessMonitorCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Check plan limits
    current_count = await monitor_repo.count_by_workspace(workspace.id)
    if current_count >= user_plan.max_process_monitors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Process monitor limit reached. Your plan allows {user_plan.max_process_monitors} process monitor(s)",
        )

    # Validate schedule configuration
    if data.schedule_type == ScheduleType.CRON:
        if not data.schedule_cron:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cron expression is required for cron schedule type",
            )
        # Validate cron expression
        try:
            from croniter import croniter

            croniter(data.schedule_cron)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}",
            ) from e
    elif data.schedule_type == ScheduleType.INTERVAL:
        if not data.schedule_interval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interval is required for interval schedule type",
            )
        # Check minimum interval
        interval_seconds = parse_interval_to_seconds(data.schedule_interval)
        interval_minutes = interval_seconds // 60
        if interval_minutes < user_plan.min_process_monitor_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Process monitor interval too short. Your plan requires minimum {user_plan.min_process_monitor_interval_minutes} minute(s)",
            )
    elif data.schedule_type == ScheduleType.EXACT_TIME:
        if not data.schedule_exact_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exact time is required for exact_time schedule type",
            )

    # Parse intervals
    start_grace_period_seconds = parse_interval_to_seconds(data.start_grace_period)
    end_timeout_seconds = parse_interval_to_seconds(data.end_timeout)
    schedule_interval_seconds = (
        parse_interval_to_seconds(data.schedule_interval) if data.schedule_interval else None
    )

    # Create monitor
    monitor = await monitor_repo.create(
        workspace_id=workspace.id,
        name=data.name,
        description=data.description,
        schedule_type=data.schedule_type,
        schedule_cron=data.schedule_cron,
        schedule_interval=schedule_interval_seconds,
        schedule_exact_time=data.schedule_exact_time,
        timezone=data.timezone,
        start_grace_period=start_grace_period_seconds,
        end_timeout=end_timeout_seconds,
        notify_on_missed_start=data.notify_on_missed_start,
        notify_on_missed_end=data.notify_on_missed_end,
        notify_on_recovery=data.notify_on_recovery,
        notify_on_success=data.notify_on_success,
        status=ProcessMonitorStatus.WAITING_START,
    )

    # Calculate initial next_expected_start and start_deadline
    now = datetime.utcnow()
    next_expected_start = process_monitor_service.calculate_next_expected_start(monitor, now)
    if next_expected_start:
        monitor.next_expected_start = next_expected_start
        monitor.start_deadline = datetime.fromtimestamp(
            next_expected_start.timestamp() + start_grace_period_seconds
        )

    # Update workspace counter
    await workspace_repo.update_process_monitors_count(workspace, 1)
    await db.commit()
    await db.refresh(monitor)

    return monitor_to_response(monitor)


@router.get("/{monitor_id}", response_model=ProcessMonitorResponse)
async def get_process_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a specific process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    monitor = await monitor_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    return monitor_to_response(monitor)


@router.patch("/{monitor_id}", response_model=ProcessMonitorResponse)
async def update_process_monitor(
    monitor_id: UUID,
    data: ProcessMonitorUpdate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Update a process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    monitor = await monitor_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Determine the schedule type for validation
    schedule_type = update_data.get("schedule_type", monitor.schedule_type)

    # Validate schedule configuration if type is being changed
    if "schedule_type" in update_data:
        if schedule_type == ScheduleType.CRON:
            cron = update_data.get("schedule_cron", monitor.schedule_cron)
            if not cron:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cron expression is required for cron schedule type",
                )
        elif schedule_type == ScheduleType.INTERVAL:
            interval = update_data.get("schedule_interval", monitor.schedule_interval)
            if not interval:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Interval is required for interval schedule type",
                )
        elif schedule_type == ScheduleType.EXACT_TIME:
            exact_time = update_data.get("schedule_exact_time", monitor.schedule_exact_time)
            if not exact_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Exact time is required for exact_time schedule type",
                )

    # Validate cron expression if provided
    if "schedule_cron" in update_data and update_data["schedule_cron"]:
        try:
            from croniter import croniter

            croniter(update_data["schedule_cron"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}",
            ) from e

    # Parse and validate intervals
    if "schedule_interval" in update_data and update_data["schedule_interval"]:
        interval_seconds = parse_interval_to_seconds(update_data["schedule_interval"])
        interval_minutes = interval_seconds // 60
        if interval_minutes < user_plan.min_process_monitor_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Process monitor interval too short. Your plan requires minimum {user_plan.min_process_monitor_interval_minutes} minute(s)",
            )
        update_data["schedule_interval"] = interval_seconds

    if "start_grace_period" in update_data and update_data["start_grace_period"]:
        update_data["start_grace_period"] = parse_interval_to_seconds(update_data["start_grace_period"])

    if "end_timeout" in update_data and update_data["end_timeout"]:
        update_data["end_timeout"] = parse_interval_to_seconds(update_data["end_timeout"])

    if update_data:
        monitor = await monitor_repo.update(monitor, **update_data)

        # Recalculate next_expected_start if schedule was changed
        schedule_changed = any(
            key in update_data
            for key in ["schedule_type", "schedule_cron", "schedule_interval", "schedule_exact_time", "timezone"]
        )
        if schedule_changed and monitor.status == ProcessMonitorStatus.WAITING_START:
            now = datetime.utcnow()
            next_expected_start = process_monitor_service.calculate_next_expected_start(monitor, now)
            if next_expected_start:
                monitor.next_expected_start = next_expected_start
                monitor.start_deadline = datetime.fromtimestamp(
                    next_expected_start.timestamp() + monitor.start_grace_period
                )

        await db.commit()
        await db.refresh(monitor)

    return monitor_to_response(monitor)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    workspace_repo = WorkspaceRepository(db)
    monitor = await monitor_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    await monitor_repo.delete(monitor)
    await workspace_repo.update_process_monitors_count(workspace, -1)
    await db.commit()


@router.post("/{monitor_id}/pause", response_model=ProcessMonitorResponse)
async def pause_process_monitor(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Pause a process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    monitor = await monitor_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    if monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process monitor is already paused",
        )

    monitor = await monitor_repo.pause(monitor)
    await db.commit()
    await db.refresh(monitor)

    return monitor_to_response(monitor)


@router.post("/{monitor_id}/resume", response_model=ProcessMonitorResponse)
async def resume_process_monitor(
    monitor_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Resume a paused process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    monitor = await monitor_repo.get_by_id(monitor_id)

    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    if not monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process monitor is not paused",
        )

    # Calculate next expected start
    now = datetime.utcnow()
    next_expected_start = process_monitor_service.calculate_next_expected_start(monitor, now)
    if not next_expected_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot calculate next expected start time. Check schedule configuration.",
        )

    monitor = await monitor_repo.resume(monitor, next_expected_start)
    await db.commit()
    await db.refresh(monitor)

    return monitor_to_response(monitor)


@router.get("/{monitor_id}/events", response_model=ProcessMonitorEventListResponse)
async def list_process_monitor_events(
    monitor_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List event history for a process monitor."""
    monitor_repo = ProcessMonitorRepository(db)
    event_repo = ProcessMonitorEventRepository(db)

    monitor = await monitor_repo.get_by_id(monitor_id)
    if monitor is None or monitor.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    skip = (page - 1) * limit
    events = await event_repo.get_by_monitor(
        monitor_id=monitor_id,
        skip=skip,
        limit=limit,
    )
    total = await event_repo.count_by_monitor(monitor_id=monitor_id)

    return ProcessMonitorEventListResponse(
        events=[ProcessMonitorEventResponse.model_validate(e) for e in events],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )

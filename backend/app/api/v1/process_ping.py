"""Public ping endpoints for process monitors.

These endpoints are designed to be as simple as possible:
- GET/POST /ping/start/{token} - Signal process start (no authentication required)
- GET/POST /ping/end/{token} - Signal process end (no authentication required)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.process_monitors import ProcessMonitorRepository
from app.models.process_monitor import ProcessMonitorStatus
from app.schemas.process_monitor import (
    EndPingSuccessResponse,
    ProcessMonitorEventCreate,
    StartPingSuccessResponse,
)
from app.services.process_monitor import process_monitor_service

router = APIRouter(prefix="/ping", tags=["Process Ping"])


@router.get("/start/{start_token}", response_model=StartPingSuccessResponse)
async def ping_start_get(
    start_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Simple GET ping to signal process start.

    This is the simplest way to use process monitoring:
    - Add at start of your script: `curl https://cronbox.ru/ping/start/your-token`
    """
    return await _process_start_ping(start_token, request, db)


@router.post("/start/{start_token}", response_model=StartPingSuccessResponse)
async def ping_start_post(
    start_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    data: ProcessMonitorEventCreate | None = None,
):
    """POST ping to signal process start with optional payload.

    You can include additional information:
    - status: "starting", "ok"
    - message: Any status message
    - payload: Any JSON data

    Example:
    ```
    curl -X POST https://cronbox.ru/ping/start/your-token \\
      -H "Content-Type: application/json" \\
      -d '{"status": "starting", "message": "Backup job started"}'
    ```
    """
    return await _process_start_ping(start_token, request, db, data)


@router.head("/start/{start_token}")
async def ping_start_head(
    start_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """HEAD ping to signal process start - minimal response."""
    await _process_start_ping(start_token, request, db)
    return None


@router.get("/end/{end_token}", response_model=EndPingSuccessResponse)
async def ping_end_get(
    end_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Simple GET ping to signal process end.

    This is the simplest way to use process monitoring:
    - Add at end of your script: `curl https://cronbox.ru/ping/end/your-token`
    """
    return await _process_end_ping(end_token, request, db)


@router.post("/end/{end_token}", response_model=EndPingSuccessResponse)
async def ping_end_post(
    end_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    data: ProcessMonitorEventCreate | None = None,
):
    """POST ping to signal process end with optional payload.

    You can include additional information:
    - duration_ms: How long the process took (in milliseconds)
    - status: "ok", "warning", "error"
    - message: Any status message
    - payload: Any JSON data

    Example:
    ```
    curl -X POST https://cronbox.ru/ping/end/your-token \\
      -H "Content-Type: application/json" \\
      -d '{"duration_ms": 45230, "status": "ok", "message": "Backup completed: 1.2GB"}'
    ```
    """
    return await _process_end_ping(end_token, request, db, data)


@router.head("/end/{end_token}")
async def ping_end_head(
    end_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """HEAD ping to signal process end - minimal response."""
    await _process_end_ping(end_token, request, db)
    return None


async def _process_start_ping(
    start_token: str,
    request: Request,
    db: AsyncSession,
    data: ProcessMonitorEventCreate | None = None,
) -> StartPingSuccessResponse:
    """Process a start ping request."""
    monitor_repo = ProcessMonitorRepository(db)

    # Find monitor by token
    monitor = await monitor_repo.get_by_start_token(start_token)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    # Check if paused
    if monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process monitor is paused",
        )

    # Check if already running (reject duplicate starts)
    if monitor.status == ProcessMonitorStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Process is already running. Cannot accept another start signal.",
        )

    # Get client info
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Process start ping
    try:
        if data:
            event = await process_monitor_service.process_start_ping(
                db=db,
                monitor=monitor,
                status_message=data.status or data.message,
                payload=data.payload,
                source_ip=source_ip,
                user_agent=user_agent,
            )
        else:
            event = await process_monitor_service.process_start_ping(
                db=db,
                monitor=monitor,
                source_ip=source_ip,
                user_agent=user_agent,
            )

        return StartPingSuccessResponse(
            ok=True,
            message="start received",
            monitor_id=str(monitor.id),
            run_id=event.run_id,
            status=monitor.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


async def _process_end_ping(
    end_token: str,
    request: Request,
    db: AsyncSession,
    data: ProcessMonitorEventCreate | None = None,
) -> EndPingSuccessResponse:
    """Process an end ping request."""
    monitor_repo = ProcessMonitorRepository(db)

    # Find monitor by token
    monitor = await monitor_repo.get_by_end_token(end_token)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process monitor not found",
        )

    # Check if paused
    if monitor.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process monitor is paused",
        )

    # Check if running
    if monitor.status != ProcessMonitorStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Process is not running (status: {monitor.status.value}). Cannot accept end signal.",
        )

    # Get client info
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Process end ping
    try:
        if data:
            event = await process_monitor_service.process_end_ping(
                db=db,
                monitor=monitor,
                duration_ms=data.duration_ms,
                status_message=data.status or data.message,
                payload=data.payload,
                source_ip=source_ip,
                user_agent=user_agent,
            )
        else:
            event = await process_monitor_service.process_end_ping(
                db=db,
                monitor=monitor,
                source_ip=source_ip,
                user_agent=user_agent,
            )

        return EndPingSuccessResponse(
            ok=True,
            message="end received",
            monitor_id=str(monitor.id),
            run_id=event.run_id,
            duration_ms=event.duration_ms,
            status=monitor.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

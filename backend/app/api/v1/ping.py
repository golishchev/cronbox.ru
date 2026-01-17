"""Public ping endpoint for heartbeat monitors.

This endpoint is designed to be as simple as possible:
- GET /ping/{token} - Simple ping (no authentication required)
- POST /ping/{token} - Ping with optional payload
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.heartbeats import HeartbeatRepository
from app.schemas.heartbeat import HeartbeatPingCreate, PingSuccessResponse
from app.services.heartbeat import heartbeat_service

router = APIRouter(prefix="/ping", tags=["Ping"])


async def _process_ping(
    ping_token: str,
    request: Request,
    db: AsyncSession,
    data: HeartbeatPingCreate | None = None,
) -> PingSuccessResponse:
    """Process a ping request."""
    heartbeat_repo = HeartbeatRepository(db)

    # Find heartbeat by token
    heartbeat = await heartbeat_repo.get_by_ping_token(ping_token)
    if heartbeat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heartbeat monitor not found",
        )

    # Check if paused
    if heartbeat.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Heartbeat monitor is paused",
        )

    # Get client info
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Process ping
    if data:
        await heartbeat_service.process_ping(
            db=db,
            heartbeat=heartbeat,
            duration_ms=data.duration_ms,
            status_message=data.status or data.message,
            payload=data.payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )
    else:
        await heartbeat_service.process_ping(
            db=db,
            heartbeat=heartbeat,
            source_ip=source_ip,
            user_agent=user_agent,
        )

    return PingSuccessResponse(
        ok=True,
        message="pong",
        heartbeat_id=str(heartbeat.id),
        status=heartbeat.status,
    )


@router.get("/{ping_token}", response_model=PingSuccessResponse)
async def ping_get(
    ping_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Simple GET ping - just hit the URL to register a ping.

    This is the simplest way to use heartbeat monitoring:
    - Add to your cron job: `curl https://cronbox.ru/ping/your-token`
    - Or use any HTTP client to make a GET request
    """
    return await _process_ping(ping_token, request, db)


@router.post("/{ping_token}", response_model=PingSuccessResponse)
async def ping_post(
    ping_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    data: HeartbeatPingCreate | None = None,
):
    """POST ping with optional payload.

    You can include additional information:
    - duration_ms: How long the job took
    - status: "ok", "warning", "error"
    - message: Any status message
    - payload: Any JSON data

    Example:
    ```
    curl -X POST https://cronbox.ru/ping/your-token \\
      -H "Content-Type: application/json" \\
      -d '{"duration_ms": 4523, "status": "ok", "message": "Backed up 1.2GB"}'
    ```
    """
    return await _process_ping(ping_token, request, db, data)


@router.head("/{ping_token}")
async def ping_head(
    ping_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """HEAD ping - minimal response, just registers the ping.

    Some monitoring systems prefer HEAD requests as they have minimal overhead.
    """
    await _process_ping(ping_token, request, db)
    return None

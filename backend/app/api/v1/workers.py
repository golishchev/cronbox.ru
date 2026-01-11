"""Worker management API endpoints."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import DB, CurrentWorker, CurrentWorkspace
from app.schemas.worker import (
    WorkerCreate,
    WorkerCreateResponse,
    WorkerHeartbeat,
    WorkerHeartbeatResponse,
    WorkerPollResponse,
    WorkerResponse,
    WorkerTaskResult,
    WorkerUpdate,
)
from app.services.worker import worker_service

router = APIRouter()


# ============================================================================
# Workspace admin endpoints (authenticated by user JWT)
# ============================================================================


@router.get(
    "/workspaces/{workspace_id}/workers",
    response_model=list[WorkerResponse],
    summary="List workspace workers",
)
async def list_workers(
    workspace: CurrentWorkspace,
    db: DB,
) -> list[WorkerResponse]:
    """Get all workers for the workspace."""
    workers = await worker_service.get_workers_by_workspace(db, workspace.id)
    return [WorkerResponse.model_validate(w) for w in workers]


@router.post(
    "/workspaces/{workspace_id}/workers",
    response_model=WorkerCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new worker",
)
async def create_worker(
    workspace: CurrentWorkspace,
    data: WorkerCreate,
    db: DB,
) -> WorkerCreateResponse:
    """
    Register a new worker for the workspace.

    Returns the worker info with API key. **Save the API key - it won't be shown again!**
    """
    worker, api_key = await worker_service.create_worker(db, workspace.id, data)

    return WorkerCreateResponse(
        id=worker.id,
        workspace_id=worker.workspace_id,
        name=worker.name,
        description=worker.description,
        region=worker.region,
        api_key=api_key,
        api_key_prefix=worker.api_key_prefix,
        created_at=worker.created_at,
    )


@router.get(
    "/workspaces/{workspace_id}/workers/{worker_id}",
    response_model=WorkerResponse,
    summary="Get worker details",
)
async def get_worker(
    workspace: CurrentWorkspace,
    db: DB,
    worker_id: UUID = Path(..., description="Worker ID"),
) -> WorkerResponse:
    """Get worker details."""
    worker = await worker_service.get_worker_by_id(db, worker_id, workspace.id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    return WorkerResponse.model_validate(worker)


@router.patch(
    "/workspaces/{workspace_id}/workers/{worker_id}",
    response_model=WorkerResponse,
    summary="Update worker",
)
async def update_worker(
    workspace: CurrentWorkspace,
    db: DB,
    data: WorkerUpdate,
    worker_id: UUID = Path(..., description="Worker ID"),
) -> WorkerResponse:
    """Update worker settings."""
    worker = await worker_service.get_worker_by_id(db, worker_id, workspace.id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    updated = await worker_service.update_worker(db, worker, data)
    return WorkerResponse.model_validate(updated)


@router.delete(
    "/workspaces/{workspace_id}/workers/{worker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete worker",
)
async def delete_worker(
    workspace: CurrentWorkspace,
    db: DB,
    worker_id: UUID = Path(..., description="Worker ID"),
) -> None:
    """Delete a worker."""
    worker = await worker_service.get_worker_by_id(db, worker_id, workspace.id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    await worker_service.delete_worker(db, worker)


@router.post(
    "/workspaces/{workspace_id}/workers/{worker_id}/regenerate-key",
    response_model=WorkerCreateResponse,
    summary="Regenerate worker API key",
)
async def regenerate_worker_key(
    workspace: CurrentWorkspace,
    db: DB,
    worker_id: UUID = Path(..., description="Worker ID"),
) -> WorkerCreateResponse:
    """
    Regenerate the API key for a worker.

    The old key will be invalidated immediately.
    """
    worker = await worker_service.get_worker_by_id(db, worker_id, workspace.id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    api_key = await worker_service.regenerate_api_key(db, worker)

    return WorkerCreateResponse(
        id=worker.id,
        workspace_id=worker.workspace_id,
        name=worker.name,
        description=worker.description,
        region=worker.region,
        api_key=api_key,
        api_key_prefix=worker.api_key_prefix,
        created_at=worker.created_at,
    )


# ============================================================================
# Worker endpoints (authenticated by X-Worker-Key header)
# ============================================================================


@router.post(
    "/worker/heartbeat",
    response_model=WorkerHeartbeatResponse,
    summary="Send worker heartbeat",
    tags=["worker-api"],
)
async def worker_heartbeat(
    worker: CurrentWorker,
    heartbeat: WorkerHeartbeat,
    db: DB,
) -> WorkerHeartbeatResponse:
    """
    Send a heartbeat to keep the worker marked as online.

    Should be called every 30 seconds.
    """
    await worker_service.update_heartbeat(db, worker, heartbeat)

    return WorkerHeartbeatResponse(
        acknowledged=True,
        server_time=datetime.now(timezone.utc),
    )


@router.get(
    "/worker/tasks",
    response_model=WorkerPollResponse,
    summary="Poll for tasks",
    tags=["worker-api"],
)
async def poll_tasks(
    worker: CurrentWorker,
    max_tasks: int = 10,
) -> WorkerPollResponse:
    """
    Poll for pending tasks assigned to this worker.

    Returns up to `max_tasks` tasks. Call this endpoint regularly
    (suggested interval: 5 seconds) to receive tasks.
    """
    tasks = await worker_service.poll_tasks(worker.id, max_tasks)

    return WorkerPollResponse(
        tasks=tasks,
        poll_interval_seconds=5,
    )


@router.post(
    "/worker/tasks/result",
    status_code=status.HTTP_200_OK,
    summary="Submit task result",
    tags=["worker-api"],
)
async def submit_task_result(
    worker: CurrentWorker,
    result: WorkerTaskResult,
    db: DB,
) -> dict:
    """
    Submit the result of a task execution.

    Call this after executing a task to report the result.
    """
    success = await worker_service.process_task_result(db, worker, result)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process task result",
        )

    return {"status": "ok", "task_id": str(result.task_id)}


@router.get(
    "/worker/info",
    response_model=WorkerResponse,
    summary="Get worker info",
    tags=["worker-api"],
)
async def get_worker_info(
    worker: CurrentWorker,
) -> WorkerResponse:
    """Get current worker information."""
    return WorkerResponse.model_validate(worker)

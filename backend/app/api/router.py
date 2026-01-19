from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    billing,
    cron_tasks,
    delayed_tasks,
    executions,
    heartbeats,
    notifications,
    ping,
    ssl_monitors,
    task_chains,
    task_queue,
    webhooks,
    workers,
    workspaces,
)

api_router = APIRouter()

# Include all API v1 routers
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(cron_tasks.router)
api_router.include_router(delayed_tasks.router)
api_router.include_router(task_chains.router)
api_router.include_router(heartbeats.router)
api_router.include_router(ssl_monitors.router)
api_router.include_router(executions.router)
api_router.include_router(notifications.router)
api_router.include_router(billing.router)
api_router.include_router(webhooks.router)
api_router.include_router(workers.router, tags=["workers"])
api_router.include_router(task_queue.router, tags=["task-queue"])
api_router.include_router(admin.router)

# Public endpoints (no auth required)
# Note: ping router is included directly on the app to avoid /v1 prefix
ping_router = ping.router

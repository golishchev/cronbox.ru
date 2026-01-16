from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    billing,
    cron_tasks,
    delayed_tasks,
    executions,
    notifications,
    task_chains,
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
api_router.include_router(executions.router)
api_router.include_router(notifications.router)
api_router.include_router(billing.router)
api_router.include_router(webhooks.router)
api_router.include_router(workers.router, tags=["workers"])
api_router.include_router(admin.router)

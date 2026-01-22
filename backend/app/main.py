from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.core.rate_limiter import RateLimitMiddleware
from app.core.redis import redis_client
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.database import engine

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User authentication and authorization. Register, login, and manage user sessions.",
    },
    {
        "name": "Workspaces",
        "description": "Workspace management. Create and manage workspaces to organize your scheduled tasks.",
    },
    {
        "name": "Cron Tasks",
        "description": "Recurring HTTP tasks scheduled using cron expressions. Create, update, pause, and delete cron jobs.",
    },
    {
        "name": "Delayed Tasks",
        "description": "One-time HTTP tasks scheduled to run at a specific time. Create tasks that execute once.",
    },
    {
        "name": "Heartbeats",
        "description": "Dead Man's Switch monitoring. Create heartbeat monitors that alert when expected pings are not received.",
    },
    {
        "name": "Ping",
        "description": "Public ping endpoint for heartbeat monitors. Simple GET/POST to register a heartbeat.",
    },
    {
        "name": "Process Monitors",
        "description": "Process monitoring with paired START/END signals. Track long-running processes like backups, ETL jobs, and deployments.",
    },
    {
        "name": "Process Ping",
        "description": "Public ping endpoints for process monitors. Signal process start and end without authentication.",
    },
    {
        "name": "Executions",
        "description": "Task execution history. View logs, status, and results of task executions.",
    },
    {
        "name": "Notifications",
        "description": "Notification channels and settings. Configure email, Telegram, Slack, and webhook notifications.",
    },
    {
        "name": "Billing",
        "description": "Subscription plans and billing management. View plans, manage subscriptions, and handle payments.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook endpoints for external integrations. Receive callbacks from payment providers and other services.",
    },
    {
        "name": "workers",
        "description": "Worker API keys for external task executors. Create and manage API keys for workers.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await redis_client.initialize()
    yield
    # Shutdown
    await redis_client.close()
    await engine.dispose()


app = FastAPI(
    title="CronBox API",
    description="""
# CronBox - HTTP Request Scheduling Service

CronBox is a powerful HTTP request scheduling service that allows you to:

- **Schedule recurring tasks** using cron expressions (e.g., every 5 minutes, daily at 9 AM)
- **Schedule one-time tasks** to execute at a specific date and time
- **Monitor executions** with detailed logs and status tracking
- **Receive notifications** via email, Telegram, Slack, or webhooks
- **Organize tasks** in workspaces for team collaboration

## Authentication

All API endpoints (except `/auth/register` and `/auth/login`) require authentication.
Include the JWT token in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```

## Rate Limits

API requests are rate-limited per workspace:
- **Free plan**: 100 requests/minute
- **Pro plan**: 500 requests/minute
- **Enterprise**: Custom limits

## Need Help?

- Documentation: [https://docs.cronbox.ru](https://docs.cronbox.ru)
- Support: support@cronbox.ru
""",
    version="1.0.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "CronBox Support",
        "email": "support@cronbox.ru",
    },
    license_info={
        "name": "Proprietary",
    },
)

# Security headers middleware (outermost - runs last on response)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware - explicit methods and headers for security
ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Accept-Language",
    "X-Requested-With",
    "X-Worker-Key",
    "X-API-Key",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600,  # Cache preflight for 1 hour
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, default_requests_per_minute=100)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "cronbox"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "CronBox API",
        "version": "1.0.0",
        "docs": f"{settings.api_prefix}/docs",
    }


# Import and include routers
from app.api.router import api_router, ping_router, process_ping_router

app.include_router(api_router, prefix=settings.api_prefix)
# Public ping endpoints at root level (no /v1 prefix for simplicity)
app.include_router(ping_router)
app.include_router(process_ping_router)

# Mount static files for uploads (avatars, etc.)
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# Custom OpenAPI schema with security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=tags_metadata,
        contact=app.contact,
        license_info=app.license_info,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token",
        },
        "APIKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Worker API key for external task executors",
        },
    }

    # Add global security requirement (can be overridden per-endpoint)
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add servers
    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.cronbox.ru", "description": "Production server"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

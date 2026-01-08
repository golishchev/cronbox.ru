"""arq worker settings and configuration."""

from arq.connections import RedisSettings

from app.config import settings


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for arq from URL."""
    from urllib.parse import urlparse

    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:
    """arq worker settings."""

    # Redis connection
    redis_settings = get_redis_settings()

    # Worker configuration
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 600  # 10 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5  # Poll delay in seconds

    # Health check
    health_check_interval = 60  # Seconds between health checks
    health_check_key = "cronbox:worker:health"

    # Queue names
    queue_name = "cronbox:tasks"

    # Import task functions
    functions = [
        "app.workers.tasks.execute_http_task",
        "app.workers.tasks.execute_cron_task",
        "app.workers.tasks.execute_delayed_task",
    ]

    # Startup and shutdown hooks
    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Called on worker startup."""
        from app.db.database import async_session_factory

        # Initialize database session factory
        ctx["db_factory"] = async_session_factory
        print("Worker started successfully")

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Called on worker shutdown."""
        print("Worker shutting down...")

    @staticmethod
    async def on_job_start(ctx: dict) -> None:
        """Called when a job starts."""
        pass

    @staticmethod
    async def on_job_end(ctx: dict) -> None:
        """Called when a job ends."""
        pass

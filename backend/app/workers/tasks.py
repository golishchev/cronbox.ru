"""Worker tasks for executing HTTP requests."""

from datetime import datetime
from uuid import UUID

import httpx
import pytz
import structlog
from croniter import croniter

from app.core.url_validator import (
    SSRFError,
    sanitize_url_for_logging,
    validate_url_for_ssrf,
)
from app.db.repositories.cron_tasks import CronTaskRepository
from app.db.repositories.delayed_tasks import DelayedTaskRepository
from app.db.repositories.executions import ExecutionRepository
from app.models.cron_task import TaskStatus
from app.services.notifications import notification_service

logger = structlog.get_logger()


async def send_task_notification(
    ctx: dict,
    *,
    workspace_id: str,
    task_name: str,
    task_type: str,
    event: str,  # "success", "failure", "recovery"
    duration_ms: int | None = None,
    error_message: str | None = None,
    task_url: str | None = None,
) -> dict:
    """Send task notification asynchronously.

    This runs as a separate job to avoid blocking task execution.
    """
    db_factory = ctx["db_factory"]

    async with db_factory() as db:
        try:
            if event == "success":
                await notification_service.send_task_success(
                    db=db,
                    workspace_id=UUID(workspace_id),
                    task_name=task_name,
                    task_type=task_type,
                    duration_ms=duration_ms,
                )
            elif event == "failure":
                await notification_service.send_task_failure(
                    db=db,
                    workspace_id=UUID(workspace_id),
                    task_name=task_name,
                    task_type=task_type,
                    error_message=error_message,
                    task_url=task_url,
                )
            elif event == "recovery":
                await notification_service.send_task_recovery(
                    db=db,
                    workspace_id=UUID(workspace_id),
                    task_name=task_name,
                    task_type=task_type,
                )

            logger.info(
                "Notification sent",
                event=event,
                task_name=task_name,
                task_type=task_type,
            )
            return {"success": True}

        except Exception as e:
            logger.error(
                "Failed to send notification",
                error=str(e),
                event=event,
                task_name=task_name,
            )
            return {"success": False, "error": str(e)}


async def execute_http_task(
    ctx: dict,
    *,
    url: str,
    method: str,
    headers: dict | None = None,
    body: str | None = None,
    timeout_seconds: int = 30,
) -> dict:
    """Execute an HTTP request and return the result.

    This is the core HTTP execution function used by both cron and delayed tasks.

    Security: URLs are validated against SSRF attacks before execution.
    """
    headers = headers or {}
    start_time = datetime.utcnow()

    # SSRF Protection: Validate URL before making request
    try:
        validate_url_for_ssrf(url)
    except SSRFError as e:
        logger.warning(
            "SSRF validation failed",
            url=sanitize_url_for_logging(url),
            error=e.message,
        )
        return {
            "success": False,
            "status_code": None,
            "headers": None,
            "body": None,
            "size_bytes": None,
            "duration_ms": 0,
            "error": f"URL validation failed: {e.message}",
            "error_type": "ssrf_blocked",
        }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body.encode() if body else None,
            )

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Limit response body size (max 64KB)
        response_body = response.text[:65536] if response.text else None

        return {
            "success": 200 <= response.status_code < 400,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_body,
            "size_bytes": len(response.content) if response.content else 0,
            "duration_ms": duration_ms,
            "error": None,
        }

    except httpx.TimeoutException as e:
        return {
            "success": False,
            "status_code": None,
            "headers": None,
            "body": None,
            "size_bytes": None,
            "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "error": str(e),
            "error_type": "timeout",
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "status_code": None,
            "headers": None,
            "body": None,
            "size_bytes": None,
            "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "error": str(e),
            "error_type": "request_error",
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "headers": None,
            "body": None,
            "size_bytes": None,
            "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "error": str(e),
            "error_type": "unknown",
        }


async def execute_cron_task(
    ctx: dict,
    *,
    task_id: str,
    retry_attempt: int = 0,
) -> dict:
    """Execute a cron task by ID.

    Creates an execution record, performs the HTTP request,
    updates the task status, and schedules retries if needed.
    """
    db_factory = ctx["db_factory"]

    async with db_factory() as db:
        cron_repo = CronTaskRepository(db)
        exec_repo = ExecutionRepository(db)

        # Get the task
        task = await cron_repo.get_by_id(UUID(task_id))
        if not task:
            logger.warning("Cron task not found", task_id=task_id)
            return {"success": False, "error": "Task not found"}

        if not task.is_active or task.is_paused:
            logger.info("Task is not active or paused", task_id=task_id)
            return {"success": False, "error": "Task not active"}

        # Save previous status for recovery detection
        previous_status = task.last_status

        # Create execution record
        execution = await exec_repo.create_execution(
            workspace_id=task.workspace_id,
            task_type="cron",
            task_id=task.id,
            task_name=task.name,
            request_url=task.url,
            request_method=task.method,
            request_headers=task.headers,
            request_body=task.body,
            cron_task_id=task.id,
            retry_attempt=retry_attempt,
        )

        # Log with sanitized URL (credentials removed)
        logger.info(
            "Executing cron task",
            task_id=task_id,
            task_name=task.name,
            url=sanitize_url_for_logging(task.url),
            retry_attempt=retry_attempt,
        )

        # Execute HTTP request
        result = await execute_http_task(
            ctx,
            url=task.url,
            method=task.method.value,
            headers=task.headers,
            body=task.body,
            timeout_seconds=task.timeout_seconds,
        )

        # Determine status
        status = TaskStatus.SUCCESS if result["success"] else TaskStatus.FAILED

        # Update execution record
        await exec_repo.complete_execution(
            execution=execution,
            status=status,
            response_status_code=result.get("status_code"),
            response_headers=result.get("headers"),
            response_body=result.get("body"),
            response_size_bytes=result.get("size_bytes"),
            error_message=result.get("error"),
            error_type=result.get("error_type"),
        )

        # Calculate next run time
        tz = pytz.timezone(task.timezone)
        now = datetime.now(tz)
        cron = croniter(task.schedule, now)
        next_run = cron.get_next(datetime)
        next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

        # Update task status
        await cron_repo.update_last_run(
            task=task,
            status=status,
            run_at=datetime.utcnow(),
            next_run_at=next_run_utc,
        )

        await db.commit()

        logger.info(
            "Cron task execution completed",
            task_id=task_id,
            status=status.value,
            next_run_at=next_run_utc.isoformat(),
        )

        # Enqueue notifications asynchronously (non-blocking)
        # Uses shared Redis pool from ctx (initialized in worker startup)
        redis = ctx["redis"]

        try:
            if result["success"]:
                # Check if this is a recovery (previous status was failed)
                if previous_status == TaskStatus.FAILED:
                    await redis.enqueue_job(
                        "send_task_notification",
                        workspace_id=str(task.workspace_id),
                        task_name=task.name,
                        task_type="cron",
                        event="recovery",
                    )
                # Send success notification
                await redis.enqueue_job(
                    "send_task_notification",
                    workspace_id=str(task.workspace_id),
                    task_name=task.name,
                    task_type="cron",
                    event="success",
                    duration_ms=result.get("duration_ms"),
                )
            else:
                # Only send failure notification on final attempt (no more retries)
                if retry_attempt >= task.retry_count:
                    await redis.enqueue_job(
                        "send_task_notification",
                        workspace_id=str(task.workspace_id),
                        task_name=task.name,
                        task_type="cron",
                        event="failure",
                        error_message=result.get("error"),
                        task_url=sanitize_url_for_logging(task.url),
                    )
        except Exception as e:
            logger.error("Failed to enqueue notification", error=str(e), task_id=task_id)

        # Schedule retry if failed and retries remaining
        if not result["success"] and retry_attempt < task.retry_count:
            await redis.enqueue_job(
                "execute_cron_task",
                task_id=task_id,
                retry_attempt=retry_attempt + 1,
                _defer_by=task.retry_delay_seconds,
            )

            logger.info(
                "Scheduled retry for cron task",
                task_id=task_id,
                retry_attempt=retry_attempt + 1,
                defer_by=task.retry_delay_seconds,
            )

        return {
            "success": result["success"],
            "status_code": result.get("status_code"),
            "duration_ms": result.get("duration_ms"),
            "error": result.get("error"),
        }


async def execute_delayed_task(
    ctx: dict,
    *,
    task_id: str,
    retry_attempt: int = 0,
) -> dict:
    """Execute a delayed task by ID.

    Creates an execution record, performs the HTTP request,
    updates the task status, and handles retries/callbacks.
    """
    db_factory = ctx["db_factory"]

    async with db_factory() as db:
        delayed_repo = DelayedTaskRepository(db)
        exec_repo = ExecutionRepository(db)

        # Get the task
        task = await delayed_repo.get_by_id(UUID(task_id))
        if not task:
            logger.warning("Delayed task not found", task_id=task_id)
            return {"success": False, "error": "Task not found"}

        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            logger.info("Task is not pending/running", task_id=task_id, status=task.status)
            return {"success": False, "error": "Task not pending/running"}

        # Mark as running if not already
        if task.status == TaskStatus.PENDING:
            await delayed_repo.mark_running(task)

        # Create execution record
        execution = await exec_repo.create_execution(
            workspace_id=task.workspace_id,
            task_type="delayed",
            task_id=task.id,
            task_name=task.name,
            request_url=task.url,
            request_method=task.method,
            request_headers=task.headers,
            request_body=task.body,
            retry_attempt=retry_attempt,
        )

        # Log with sanitized URL (credentials removed)
        logger.info(
            "Executing delayed task",
            task_id=task_id,
            task_name=task.name,
            url=sanitize_url_for_logging(task.url),
            retry_attempt=retry_attempt,
        )

        # Execute HTTP request
        result = await execute_http_task(
            ctx,
            url=task.url,
            method=task.method.value,
            headers=task.headers,
            body=task.body,
            timeout_seconds=task.timeout_seconds,
        )

        # Determine status
        status = TaskStatus.SUCCESS if result["success"] else TaskStatus.FAILED

        # Update execution record
        await exec_repo.complete_execution(
            execution=execution,
            status=status,
            response_status_code=result.get("status_code"),
            response_headers=result.get("headers"),
            response_body=result.get("body"),
            response_size_bytes=result.get("size_bytes"),
            error_message=result.get("error"),
            error_type=result.get("error_type"),
        )

        # Update task status
        if result["success"]:
            await delayed_repo.mark_completed(task, TaskStatus.SUCCESS, datetime.utcnow())
        else:
            # Check if we should retry
            if retry_attempt < task.retry_count:
                await delayed_repo.increment_retry(task)
            else:
                await delayed_repo.mark_completed(task, TaskStatus.FAILED, datetime.utcnow())

        await db.commit()

        logger.info(
            "Delayed task execution completed",
            task_id=task_id,
            status=status.value,
        )

        # Enqueue notifications asynchronously (non-blocking)
        # Uses shared Redis pool from ctx (initialized in worker startup)
        redis = ctx["redis"]

        try:
            if result["success"]:
                await redis.enqueue_job(
                    "send_task_notification",
                    workspace_id=str(task.workspace_id),
                    task_name=task.name,
                    task_type="delayed",
                    event="success",
                    duration_ms=result.get("duration_ms"),
                )
            else:
                # Only send failure notification on final attempt (no more retries)
                if retry_attempt >= task.retry_count:
                    await redis.enqueue_job(
                        "send_task_notification",
                        workspace_id=str(task.workspace_id),
                        task_name=task.name,
                        task_type="delayed",
                        event="failure",
                        error_message=result.get("error"),
                        task_url=sanitize_url_for_logging(task.url),
                    )
        except Exception as e:
            logger.error("Failed to enqueue notification", error=str(e), task_id=task_id)

        # Schedule retry if failed and retries remaining
        if not result["success"] and retry_attempt < task.retry_count:
            await redis.enqueue_job(
                "execute_delayed_task",
                task_id=task_id,
                retry_attempt=retry_attempt + 1,
                _defer_by=task.retry_delay_seconds,
            )

            logger.info(
                "Scheduled retry for delayed task",
                task_id=task_id,
                retry_attempt=retry_attempt + 1,
                defer_by=task.retry_delay_seconds,
            )

        # Send callback if configured
        if task.callback_url and result["success"]:
            # TODO: Enqueue callback job
            pass

        return {
            "success": result["success"],
            "status_code": result.get("status_code"),
            "duration_ms": result.get("duration_ms"),
            "error": result.get("error"),
        }

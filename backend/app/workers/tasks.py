"""Worker tasks for executing HTTP requests."""

import asyncio
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
from app.models.cron_task import OverlapPolicy, TaskStatus
from app.services.notifications import notification_service
from app.services.overlap import overlap_service

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

        # Release running instance slot for overlap prevention
        if task.overlap_policy != OverlapPolicy.ALLOW:
            await overlap_service.release_cron_task(db, task)

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


async def execute_chain(
    ctx: dict,
    *,
    chain_id: str,
    initial_variables: dict | None = None,
) -> dict:
    """Execute a task chain by ID.

    Creates chain and step execution records, performs HTTP requests
    for each step with variable substitution, and handles conditions.
    """
    from uuid import UUID

    from app.db.repositories.chain_executions import (
        ChainExecutionRepository,
        StepExecutionRepository,
    )
    from app.db.repositories.task_chains import TaskChainRepository
    from app.models.chain_execution import StepStatus
    from app.models.task_chain import ChainStatus, TriggerType
    from app.services.chain_executor import (
        ChainExecutionContext,
        VariableSubstitutionError,
        evaluate_condition,
        extract_variables_from_response,
        log_chain_execution_complete,
        log_chain_execution_start,
        log_step_execution,
        prepare_step_request,
    )

    db_factory = ctx["db_factory"]
    initial_variables = initial_variables or {}

    async with db_factory() as db:
        chain_repo = TaskChainRepository(db)
        exec_repo = ChainExecutionRepository(db)
        step_exec_repo = StepExecutionRepository(db)

        # Get the chain with steps
        chain = await chain_repo.get_with_steps(UUID(chain_id))
        if not chain:
            logger.warning("Chain not found", chain_id=chain_id)
            return {"success": False, "error": "Chain not found"}

        if not chain.is_active or chain.is_paused:
            logger.info("Chain is not active or paused", chain_id=chain_id)
            return {"success": False, "error": "Chain not active"}

        if not chain.steps:
            logger.info("Chain has no steps", chain_id=chain_id)
            return {"success": False, "error": "Chain has no steps"}

        # Create execution context
        exec_context = ChainExecutionContext(chain, initial_variables)
        log_chain_execution_start(chain, exec_context.variables)

        # Create chain execution record
        chain_execution = await exec_repo.create_execution(
            workspace_id=chain.workspace_id,
            chain_id=chain.id,
            total_steps=len(chain.steps),
            initial_variables=initial_variables,
        )
        await db.commit()

        # Execute each step
        for step in chain.steps:
            step_status = StepStatus.PENDING
            status_code = None
            response_body = None
            extracted_vars = {}
            error_message = None
            error_type = None

            try:
                # Check condition if present
                if step.condition:
                    condition_met, condition_details = evaluate_condition(
                        step.condition,
                        exec_context.previous_status_code,
                        exec_context.previous_response_body,
                    )
                    if not condition_met:
                        # Skip this step
                        await step_exec_repo.mark_as_skipped(
                            chain_execution_id=chain_execution.id,
                            step_id=step.id,
                            step_order=step.step_order,
                            step_name=step.name,
                            request_url=step.url,
                            request_method=step.method.value,
                            condition_details=condition_details,
                        )
                        exec_context.update_from_step_result(StepStatus.SKIPPED)
                        log_step_execution(chain, step, step.step_order, step.url, StepStatus.SKIPPED)
                        continue

                # Prepare request with variable substitution
                try:
                    url, headers, body = prepare_step_request(step, exec_context.variables)
                except VariableSubstitutionError as e:
                    step_status = StepStatus.FAILED
                    error_message = str(e)
                    error_type = "variable_substitution"

                    # Create step execution record for the failure
                    step_execution = await step_exec_repo.create_step_execution(
                        chain_execution_id=chain_execution.id,
                        step_id=step.id,
                        step_order=step.step_order,
                        step_name=step.name,
                        request_url=step.url,
                        request_method=step.method.value,
                        request_headers=step.headers,
                        request_body=step.body,
                    )
                    await step_exec_repo.complete_step_execution(
                        step_execution,
                        status=StepStatus.FAILED,
                        error_message=error_message,
                        error_type=error_type,
                    )
                    exec_context.update_from_step_result(StepStatus.FAILED)
                    log_step_execution(chain, step, step.step_order, step.url, StepStatus.FAILED, error=error_message)

                    if not exec_context.should_continue(step, StepStatus.FAILED):
                        break
                    continue

                # Create step execution record
                step_execution = await step_exec_repo.create_step_execution(
                    chain_execution_id=chain_execution.id,
                    step_id=step.id,
                    step_order=step.step_order,
                    step_name=step.name,
                    request_url=url,
                    request_method=step.method.value,
                    request_headers=headers,
                    request_body=body,
                )

                # Execute HTTP request with retry
                result = None
                for attempt in range(step.retry_count + 1):
                    result = await execute_http_task(
                        ctx,
                        url=url,
                        method=step.method.value,
                        headers=headers,
                        body=body,
                        timeout_seconds=step.timeout_seconds,
                    )
                    if result["success"]:
                        break
                    if attempt < step.retry_count:
                        await asyncio.sleep(step.retry_delay_seconds)

                status_code = result.get("status_code")
                response_body = result.get("body")

                if result["success"]:
                    step_status = StepStatus.SUCCESS
                    # Extract variables from response
                    if step.extract_variables:
                        extracted_vars = extract_variables_from_response(response_body, step.extract_variables)
                else:
                    step_status = StepStatus.FAILED
                    error_message = result.get("error")
                    error_type = result.get("error_type")

                # Complete step execution
                await step_exec_repo.complete_step_execution(
                    step_execution,
                    status=step_status,
                    response_status_code=status_code,
                    response_headers=result.get("headers"),
                    response_body=response_body,
                    response_size_bytes=result.get("size_bytes"),
                    extracted_variables=extracted_vars,
                    condition_met=True if step.condition else None,
                    error_message=error_message,
                    error_type=error_type,
                    retry_attempt=result.get("retry_attempt", 0),
                )

                # Update context
                exec_context.update_from_step_result(
                    step_status,
                    status_code=status_code,
                    response_body=response_body,
                    extracted_variables=extracted_vars,
                )

                log_step_execution(
                    chain,
                    step,
                    step.step_order,
                    url,
                    step_status,
                    duration_ms=result.get("duration_ms"),
                    error=error_message,
                )

                # Check if we should continue
                if step_status == StepStatus.FAILED:
                    if not exec_context.should_continue(step, step_status):
                        exec_context.error_message = f"Chain stopped at step {step.step_order}: {error_message}"
                        break

            except Exception as e:
                logger.error(
                    "Unexpected error executing step",
                    chain_id=chain_id,
                    step_id=str(step.id),
                    error=str(e),
                )
                exec_context.update_from_step_result(StepStatus.FAILED)
                exec_context.error_message = f"Unexpected error at step {step.step_order}: {str(e)}"
                if not exec_context.should_continue(step, StepStatus.FAILED):
                    break

        # Update chain execution with final status
        final_status = exec_context.get_final_status(len(chain.steps))
        await exec_repo.update_step_counts(
            chain_execution,
            completed=exec_context.completed_steps,
            failed=exec_context.failed_steps,
            skipped=exec_context.skipped_steps,
        )
        await exec_repo.update_variables(chain_execution, exec_context.variables)
        await exec_repo.complete_execution(
            chain_execution,
            status=final_status,
            error_message=exec_context.error_message,
        )

        # Calculate next run time for cron chains
        next_run_at = None
        if chain.trigger_type == TriggerType.CRON and chain.schedule:
            tz = pytz.timezone(chain.timezone)
            now = datetime.now(tz)
            cron = croniter(chain.schedule, now)
            next_run = cron.get_next(datetime)
            next_run_at = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

        # Update chain status
        await chain_repo.update_last_run(
            chain=chain,
            status=final_status,
            run_at=exec_context.started_at,
            next_run_at=next_run_at,
        )

        # Release running instance slot for overlap prevention
        from app.models.cron_task import OverlapPolicy

        if chain.overlap_policy != OverlapPolicy.ALLOW:
            await overlap_service.release_chain(db, chain)

        await db.commit()

        # Log completion
        duration_ms = int((datetime.utcnow() - exec_context.started_at).total_seconds() * 1000)
        log_chain_execution_complete(
            chain,
            final_status,
            exec_context.completed_steps,
            exec_context.failed_steps,
            exec_context.skipped_steps,
            duration_ms,
        )

        # Enqueue notifications asynchronously
        redis = ctx["redis"]
        try:
            if final_status == ChainStatus.SUCCESS and chain.notify_on_success:
                await redis.enqueue_job(
                    "send_chain_notification",
                    workspace_id=str(chain.workspace_id),
                    chain_name=chain.name,
                    event="success",
                    duration_ms=duration_ms,
                    completed_steps=exec_context.completed_steps,
                    total_steps=len(chain.steps),
                )
            elif final_status == ChainStatus.FAILED and chain.notify_on_failure:
                await redis.enqueue_job(
                    "send_chain_notification",
                    workspace_id=str(chain.workspace_id),
                    chain_name=chain.name,
                    event="failure",
                    error_message=exec_context.error_message,
                    completed_steps=exec_context.completed_steps,
                    total_steps=len(chain.steps),
                )
            elif final_status == ChainStatus.PARTIAL and chain.notify_on_partial:
                await redis.enqueue_job(
                    "send_chain_notification",
                    workspace_id=str(chain.workspace_id),
                    chain_name=chain.name,
                    event="partial",
                    completed_steps=exec_context.completed_steps,
                    failed_steps=exec_context.failed_steps,
                    total_steps=len(chain.steps),
                )
        except Exception as e:
            logger.error("Failed to enqueue chain notification", error=str(e), chain_id=chain_id)

        return {
            "success": final_status == ChainStatus.SUCCESS,
            "status": final_status.value,
            "completed_steps": exec_context.completed_steps,
            "failed_steps": exec_context.failed_steps,
            "skipped_steps": exec_context.skipped_steps,
            "duration_ms": duration_ms,
            "error": exec_context.error_message,
        }


async def send_chain_notification(
    ctx: dict,
    *,
    workspace_id: str,
    chain_name: str,
    event: str,  # "success", "failure", "partial"
    duration_ms: int | None = None,
    error_message: str | None = None,
    completed_steps: int | None = None,
    failed_steps: int | None = None,
    total_steps: int | None = None,
) -> dict:
    """Send chain notification asynchronously."""
    db_factory = ctx["db_factory"]

    async with db_factory() as db:
        try:
            from uuid import UUID

            from app.services.notifications import notification_service

            await notification_service.send_chain_notification(
                db=db,
                workspace_id=UUID(workspace_id),
                chain_name=chain_name,
                event=event,
                duration_ms=duration_ms,
                error_message=error_message,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                total_steps=total_steps,
            )

            logger.info(
                "Chain notification sent",
                notification_event=event,
                chain_name=chain_name,
            )
            return {"success": True}

        except Exception as e:
            logger.error(
                "Failed to send chain notification",
                error=str(e),
                notification_event=event,
                chain_name=chain_name,
            )
            return {"success": False, "error": str(e)}

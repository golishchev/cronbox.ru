"""Process Monitor service - business logic for process monitoring."""

import uuid
from datetime import datetime, time, timedelta, timezone

import pytz
import structlog
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.executions import ExecutionRepository
from app.db.repositories.process_monitors import (
    ProcessMonitorEventRepository,
    ProcessMonitorRepository,
)
from app.models.cron_task import TaskStatus
from app.models.process_monitor import (
    ConcurrencyPolicy,
    ProcessMonitor,
    ProcessMonitorEvent,
    ProcessMonitorStatus,
    ScheduleType,
)
from app.services.i18n import t
from app.services.notifications import notification_service

logger = structlog.get_logger()


class ProcessMonitorService:
    """Service for process monitoring operations."""

    async def _get_workspace_settings(self, db: AsyncSession, workspace_id: uuid.UUID) -> tuple[str, str]:
        """Get workspace language and timezone."""
        from app.db.repositories.workspaces import WorkspaceRepository

        workspace_repo = WorkspaceRepository(db)
        workspace = await workspace_repo.get_with_owner(workspace_id)

        lang = "en"
        tz = "Europe/Moscow"

        if workspace:
            tz = workspace.default_timezone or "Europe/Moscow"
            if workspace.owner:
                lang = workspace.owner.preferred_language or "en"

        return lang, tz

    def _format_datetime(self, dt: datetime, tz_name: str) -> str:
        """Format datetime in Russian format with workspace timezone."""
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("Europe/Moscow")

        # Convert UTC to workspace timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime("%d.%m.%Y %H:%M:%S")

    def _format_duration(self, ms: int) -> str:
        """Format duration in milliseconds to human-readable string."""
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return f"{ms / 1000:.1f}s"
        elif ms < 3600000:
            return f"{ms / 60000:.1f}m"
        else:
            return f"{ms / 3600000:.1f}h"

    def calculate_next_expected_start(
        self,
        monitor: ProcessMonitor,
        from_time: datetime | None = None,
    ) -> datetime | None:
        """Calculate the next expected start time based on schedule type."""
        if from_time is None:
            from_time = datetime.utcnow()

        try:
            tz = pytz.timezone(monitor.timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("Europe/Moscow")

        # Convert to local time
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=timezone.utc)
        local_time = from_time.astimezone(tz)

        if monitor.schedule_type == ScheduleType.CRON:
            if not monitor.schedule_cron:
                return None
            cron = croniter(monitor.schedule_cron, local_time)
            next_run = cron.get_next(datetime)
            return next_run.astimezone(pytz.UTC).replace(tzinfo=None)

        elif monitor.schedule_type == ScheduleType.INTERVAL:
            if not monitor.schedule_interval:
                return None
            # Next run is current time + interval
            next_run = from_time + timedelta(seconds=monitor.schedule_interval)
            return next_run.replace(tzinfo=None) if next_run.tzinfo else next_run

        elif monitor.schedule_type == ScheduleType.EXACT_TIME:
            if not monitor.schedule_exact_time:
                return None
            # Parse the time
            hour, minute = map(int, monitor.schedule_exact_time.split(":"))
            exact_time = time(hour=hour, minute=minute)

            # Get next occurrence
            local_date = local_time.date()
            local_datetime = datetime.combine(local_date, exact_time)
            local_datetime = tz.localize(local_datetime)

            # If the time has passed today, move to tomorrow
            if local_datetime <= local_time:
                local_datetime = local_datetime + timedelta(days=1)

            return local_datetime.astimezone(pytz.UTC).replace(tzinfo=None)

        return None

    async def process_start_ping(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
        status_message: str | None = None,
        payload: dict | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
    ) -> ProcessMonitorEvent:
        """Process an incoming start ping for a process monitor.

        Returns the created event.
        Raises ValueError if monitor is not in WAITING_START status.
        """
        monitor_repo = ProcessMonitorRepository(db)
        event_repo = ProcessMonitorEventRepository(db)
        execution_repo = ExecutionRepository(db)

        now = datetime.utcnow()

        # Check if monitor is in correct state
        if monitor.status == ProcessMonitorStatus.RUNNING:
            if monitor.concurrency_policy == ConcurrencyPolicy.SKIP:
                raise ValueError("Monitor is already running. Cannot accept another start signal.")
            elif monitor.concurrency_policy == ConcurrencyPolicy.REPLACE:
                # Create timeout event for current run
                await event_repo.create_timeout_event(
                    monitor_id=monitor.id,
                    run_id=monitor.current_run_id or str(uuid.uuid4()),
                )
                # Send missed end notification if enabled
                if monitor.notify_on_missed_end:
                    try:
                        await self._send_missed_end_notification(db, monitor)
                    except Exception as e:
                        logger.error(
                            "Failed to send missed end notification",
                            monitor_id=str(monitor.id),
                            error=str(e),
                        )
                # Continue to start new run (fall through)
                # Note: mark_running() will set status and run_id correctly
        if monitor.status == ProcessMonitorStatus.PAUSED:
            raise ValueError("Monitor is paused. Resume it first.")

        # Check if this is a recovery (was in failure state) BEFORE generating new run_id
        was_failed = monitor.status in (
            ProcessMonitorStatus.MISSED_START,
            ProcessMonitorStatus.MISSED_END,
        )

        # Generate new run_id
        run_id = str(uuid.uuid4())

        # Create start event
        event = await event_repo.create_start_event(
            monitor_id=monitor.id,
            run_id=run_id,
            status_message=status_message,
            payload=payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )

        # Mark monitor as running
        await monitor_repo.mark_running(monitor, now, run_id)

        # Create execution record
        await execution_repo.create(
            workspace_id=monitor.workspace_id,
            task_type="process_monitor",
            task_id=monitor.id,
            task_name=monitor.name,
            process_monitor_id=monitor.id,
            status=TaskStatus.RUNNING,
            started_at=now,
        )

        # Send recovery notification if was in failure state
        if was_failed and monitor.notify_on_recovery:
            try:
                await self._send_recovery_notification(db, monitor)
            except Exception as e:
                logger.error(
                    "Failed to send recovery notification",
                    monitor_id=str(monitor.id),
                    error=str(e),
                )

        # Clean up old events
        await event_repo.delete_old_events(monitor.id, keep_count=100)

        await db.commit()

        logger.info(
            "Processed process monitor start ping",
            monitor_id=str(monitor.id),
            monitor_name=monitor.name,
            run_id=run_id,
            was_failed=was_failed,
        )

        return event

    async def process_end_ping(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
        duration_ms: int | None = None,
        status_message: str | None = None,
        payload: dict | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
    ) -> ProcessMonitorEvent:
        """Process an incoming end ping for a process monitor.

        Returns the created event.
        Raises ValueError if monitor is not in RUNNING status.
        """
        monitor_repo = ProcessMonitorRepository(db)
        event_repo = ProcessMonitorEventRepository(db)
        execution_repo = ExecutionRepository(db)

        now = datetime.utcnow()

        # Check if monitor is in correct state
        if monitor.status != ProcessMonitorStatus.RUNNING:
            raise ValueError(f"Monitor is not running (status: {monitor.status.value}). Cannot accept end signal.")

        if not monitor.current_run_id:
            raise ValueError("Monitor has no active run.")

        run_id = monitor.current_run_id

        # Calculate duration if not provided
        if duration_ms is None and monitor.last_start_at:
            # Remove timezone info if present (PostgreSQL returns timezone-aware datetime)
            last_start_naive = (
                monitor.last_start_at.replace(tzinfo=None) if monitor.last_start_at.tzinfo else monitor.last_start_at
            )
            duration_ms = int((now - last_start_naive).total_seconds() * 1000)

        # Create end event
        event = await event_repo.create_end_event(
            monitor_id=monitor.id,
            run_id=run_id,
            duration_ms=duration_ms,
            status_message=status_message,
            payload=payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )

        # Calculate next expected start
        next_expected_start = self.calculate_next_expected_start(monitor, now)

        # Mark monitor as completed
        await monitor_repo.mark_completed(monitor, now, duration_ms or 0, next_expected_start)

        # Update execution record
        execution = await execution_repo.get_running_execution_by_process_monitor(monitor.id)
        if execution:
            await execution_repo.complete_process_monitor_execution(
                execution,
                status=TaskStatus.SUCCESS,
                duration_ms=duration_ms,
            )

        # Send success notification if enabled
        if monitor.notify_on_success:
            try:
                await self._send_success_notification(db, monitor, duration_ms)
            except Exception as e:
                logger.error(
                    "Failed to send success notification",
                    monitor_id=str(monitor.id),
                    error=str(e),
                )

        await db.commit()

        logger.info(
            "Processed process monitor end ping",
            monitor_id=str(monitor.id),
            monitor_name=monitor.name,
            run_id=run_id,
            duration_ms=duration_ms,
        )

        return event

    async def check_missed_starts(self, db: AsyncSession) -> int:
        """Check for monitors that missed their start signal.

        Returns the number of monitors marked as missed.
        """
        monitor_repo = ProcessMonitorRepository(db)
        event_repo = ProcessMonitorEventRepository(db)
        execution_repo = ExecutionRepository(db)
        now = datetime.utcnow()
        processed = 0

        # Get monitors that are past their start deadline
        monitors = await monitor_repo.get_monitors_waiting_for_start(now, limit=100)

        for monitor in monitors:
            try:
                # Generate a run_id for the missed event
                run_id = str(uuid.uuid4())

                # Create missed event
                await event_repo.create_missed_event(
                    monitor_id=monitor.id,
                    run_id=run_id,
                )

                # Calculate next expected start
                next_expected_start = self.calculate_next_expected_start(monitor, now)

                # Mark as missed
                await monitor_repo.mark_missed_start(monitor, next_expected_start)

                # Create failed execution record
                await execution_repo.create(
                    workspace_id=monitor.workspace_id,
                    task_type="process_monitor",
                    task_id=monitor.id,
                    task_name=monitor.name,
                    process_monitor_id=monitor.id,
                    status=TaskStatus.FAILED,
                    started_at=monitor.next_expected_start or now,
                    finished_at=now,
                    error_message="Start signal not received within grace period",
                )

                # Send notification
                if monitor.notify_on_missed_start:
                    try:
                        await self._send_missed_start_notification(db, monitor)
                    except Exception as e:
                        logger.error(
                            "Failed to send missed start notification",
                            monitor_id=str(monitor.id),
                            error=str(e),
                        )

                await db.commit()
                processed += 1

                logger.warning(
                    "Process monitor missed start",
                    monitor_id=str(monitor.id),
                    monitor_name=monitor.name,
                    consecutive_failures=monitor.consecutive_failures,
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Error processing missed start",
                    monitor_id=str(monitor.id),
                    error=str(e),
                )

        return processed

    async def check_missed_ends(self, db: AsyncSession) -> int:
        """Check for monitors that are running but missed their end signal.

        Returns the number of monitors marked as timed out.
        """
        monitor_repo = ProcessMonitorRepository(db)
        event_repo = ProcessMonitorEventRepository(db)
        execution_repo = ExecutionRepository(db)
        now = datetime.utcnow()
        processed = 0

        # Get monitors that are past their end deadline
        monitors = await monitor_repo.get_monitors_waiting_for_end(now, limit=100)

        for monitor in monitors:
            try:
                run_id = monitor.current_run_id or str(uuid.uuid4())

                # Create timeout event
                await event_repo.create_timeout_event(
                    monitor_id=monitor.id,
                    run_id=run_id,
                )

                # Calculate next expected start
                next_expected_start = self.calculate_next_expected_start(monitor, now)

                # Mark as missed end
                await monitor_repo.mark_missed_end(monitor, next_expected_start)

                # Update execution record to failed
                execution = await execution_repo.get_running_execution_by_process_monitor(monitor.id)
                if execution:
                    # Calculate duration if we have a start time
                    duration_ms = None
                    if monitor.last_start_at:
                        last_start_naive = (
                            monitor.last_start_at.replace(tzinfo=None)
                            if monitor.last_start_at.tzinfo
                            else monitor.last_start_at
                        )
                        duration_ms = int((now - last_start_naive).total_seconds() * 1000)

                    await execution_repo.complete_process_monitor_execution(
                        execution,
                        status=TaskStatus.FAILED,
                        duration_ms=duration_ms,
                        error_message="End signal not received within timeout",
                    )

                # Send notification
                if monitor.notify_on_missed_end:
                    try:
                        await self._send_missed_end_notification(db, monitor)
                    except Exception as e:
                        logger.error(
                            "Failed to send missed end notification",
                            monitor_id=str(monitor.id),
                            error=str(e),
                        )

                await db.commit()
                processed += 1

                logger.warning(
                    "Process monitor missed end (timeout)",
                    monitor_id=str(monitor.id),
                    monitor_name=monitor.name,
                    consecutive_failures=monitor.consecutive_failures,
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Error processing missed end",
                    monitor_id=str(monitor.id),
                    error=str(e),
                )

        return processed

    async def _send_missed_start_notification(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
    ) -> None:
        """Send notification when process monitor misses start signal."""
        lang, tz = await self._get_workspace_settings(db, monitor.workspace_id)
        expected_time = (
            self._format_datetime(monitor.next_expected_start, tz)
            if monitor.next_expected_start
            else t("process_monitor.unknown_time", lang)
        )
        error_message = t(
            "process_monitor.missed_start",
            lang,
            name=monitor.name,
            expected_time=expected_time,
        )

        await notification_service.send_task_failure(
            db=db,
            workspace_id=monitor.workspace_id,
            task_name=monitor.name,
            task_type="process_monitor",
            error_message=error_message,
        )

    async def _send_missed_end_notification(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
    ) -> None:
        """Send notification when process monitor misses end signal (timeout)."""
        lang, tz = await self._get_workspace_settings(db, monitor.workspace_id)
        start_time = (
            self._format_datetime(monitor.last_start_at, tz)
            if monitor.last_start_at
            else t("process_monitor.unknown_time", lang)
        )
        timeout_str = self._format_duration(monitor.end_timeout * 1000)
        error_message = t(
            "process_monitor.missed_end",
            lang,
            name=monitor.name,
            timeout=timeout_str,
            start_time=start_time,
        )

        await notification_service.send_task_failure(
            db=db,
            workspace_id=monitor.workspace_id,
            task_name=monitor.name,
            task_type="process_monitor",
            error_message=error_message,
        )

    async def _send_recovery_notification(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
    ) -> None:
        """Send notification when process monitor recovers."""
        await notification_service.send_task_recovery(
            db=db,
            workspace_id=monitor.workspace_id,
            task_name=monitor.name,
            task_type="process_monitor",
        )

    async def _send_success_notification(
        self,
        db: AsyncSession,
        monitor: ProcessMonitor,
        duration_ms: int | None,
    ) -> None:
        """Send notification when process monitor completes successfully."""
        await notification_service.send_task_success(
            db=db,
            workspace_id=monitor.workspace_id,
            task_name=monitor.name,
            task_type="process_monitor",
            duration_ms=duration_ms,
            task_level_override=True,
        )


# Global instance
process_monitor_service = ProcessMonitorService()

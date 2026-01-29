"""Repository for Process Monitor operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.process_monitor import (
    ProcessMonitor,
    ProcessMonitorEvent,
    ProcessMonitorEventType,
    ProcessMonitorStatus,
)
from app.models.workspace import Workspace


class ProcessMonitorRepository(BaseRepository[ProcessMonitor]):
    """Repository for process monitor operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ProcessMonitor, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProcessMonitor]:
        """Get all process monitors for a workspace."""
        stmt = (
            select(ProcessMonitor)
            .where(ProcessMonitor.workspace_id == workspace_id)
            .order_by(ProcessMonitor.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        """Count process monitors for a workspace."""
        stmt = select(func.count()).select_from(ProcessMonitor).where(ProcessMonitor.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_status(
        self,
        workspace_id: UUID,
        statuses: list[ProcessMonitorStatus],
    ) -> int:
        """Count process monitors for a workspace with given statuses."""
        stmt = (
            select(func.count())
            .select_from(ProcessMonitor)
            .where(
                and_(
                    ProcessMonitor.workspace_id == workspace_id,
                    ProcessMonitor.status.in_(statuses),
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_start_token(self, start_token: str) -> ProcessMonitor | None:
        """Get process monitor by its start token."""
        stmt = select(ProcessMonitor).where(ProcessMonitor.start_token == start_token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_end_token(self, end_token: str) -> ProcessMonitor | None:
        """Get process monitor by its end token."""
        stmt = select(ProcessMonitor).where(ProcessMonitor.end_token == end_token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_monitors_waiting_for_start(
        self,
        now: datetime,
        limit: int = 100,
    ) -> list[ProcessMonitor]:
        """Get monitors that are past their start deadline.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple scheduler instances are running.
        Excludes paused monitors and blocked workspaces.
        """
        stmt = (
            select(ProcessMonitor)
            .join(Workspace, ProcessMonitor.workspace_id == Workspace.id)
            .where(
                and_(
                    ProcessMonitor.is_paused.is_(False),
                    ProcessMonitor.status == ProcessMonitorStatus.WAITING_START,
                    ProcessMonitor.start_deadline.isnot(None),
                    ProcessMonitor.start_deadline <= now,
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(ProcessMonitor.start_deadline)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_monitors_waiting_for_end(
        self,
        now: datetime,
        limit: int = 100,
    ) -> list[ProcessMonitor]:
        """Get monitors that are running but past their end deadline.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple scheduler instances are running.
        Excludes paused monitors and blocked workspaces.
        """
        stmt = (
            select(ProcessMonitor)
            .join(Workspace, ProcessMonitor.workspace_id == Workspace.id)
            .where(
                and_(
                    ProcessMonitor.is_paused.is_(False),
                    ProcessMonitor.status == ProcessMonitorStatus.RUNNING,
                    ProcessMonitor.end_deadline.isnot(None),
                    ProcessMonitor.end_deadline <= now,
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(ProcessMonitor.end_deadline)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_running(
        self,
        monitor: ProcessMonitor,
        now: datetime,
        run_id: str,
    ) -> ProcessMonitor:
        """Mark monitor as running after receiving start signal."""
        from datetime import timedelta

        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.last_start_at = now
        monitor.current_run_id = run_id
        # Set end deadline (now is UTC naive datetime, so add directly)
        monitor.end_deadline = now + timedelta(seconds=monitor.end_timeout)
        # Clear start deadline
        monitor.start_deadline = None

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def mark_completed(
        self,
        monitor: ProcessMonitor,
        now: datetime,
        duration_ms: int,
        next_expected_start: datetime | None,
    ) -> ProcessMonitor:
        """Mark monitor as completed after receiving end signal."""
        from datetime import timedelta

        monitor.status = ProcessMonitorStatus.COMPLETED
        monitor.last_end_at = now
        monitor.last_duration_ms = duration_ms
        monitor.consecutive_successes += 1
        monitor.consecutive_failures = 0
        monitor.current_run_id = None
        monitor.end_deadline = None

        # Set next expected start and deadline
        if next_expected_start:
            monitor.next_expected_start = next_expected_start
            # next_expected_start is UTC naive datetime, so add directly
            monitor.start_deadline = next_expected_start + timedelta(seconds=monitor.start_grace_period)
            # Transition to WAITING_START
            monitor.status = ProcessMonitorStatus.WAITING_START

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def mark_missed_start(
        self,
        monitor: ProcessMonitor,
        next_expected_start: datetime | None,
    ) -> ProcessMonitor:
        """Mark monitor as missed start."""
        from datetime import timedelta

        monitor.status = ProcessMonitorStatus.MISSED_START
        monitor.consecutive_failures += 1
        monitor.consecutive_successes = 0

        # Set next expected start and deadline
        if next_expected_start:
            monitor.next_expected_start = next_expected_start
            # next_expected_start is UTC naive datetime, so add directly
            monitor.start_deadline = next_expected_start + timedelta(seconds=monitor.start_grace_period)
            # Immediately transition to WAITING_START for next cycle
            monitor.status = ProcessMonitorStatus.WAITING_START

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def mark_missed_end(
        self,
        monitor: ProcessMonitor,
        next_expected_start: datetime | None,
    ) -> ProcessMonitor:
        """Mark monitor as missed end (timeout)."""
        from datetime import timedelta

        monitor.status = ProcessMonitorStatus.MISSED_END
        monitor.consecutive_failures += 1
        monitor.consecutive_successes = 0
        monitor.current_run_id = None
        monitor.end_deadline = None

        # Set next expected start and deadline
        if next_expected_start:
            monitor.next_expected_start = next_expected_start
            # next_expected_start is UTC naive datetime, so add directly
            monitor.start_deadline = next_expected_start + timedelta(seconds=monitor.start_grace_period)
            # Immediately transition to WAITING_START for next cycle
            monitor.status = ProcessMonitorStatus.WAITING_START

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def pause(self, monitor: ProcessMonitor) -> ProcessMonitor:
        """Pause a process monitor."""
        monitor.is_paused = True
        monitor.status = ProcessMonitorStatus.PAUSED
        # Clear deadlines
        monitor.start_deadline = None
        monitor.end_deadline = None
        monitor.current_run_id = None

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def resume(
        self,
        monitor: ProcessMonitor,
        next_expected_start: datetime,
    ) -> ProcessMonitor:
        """Resume a paused process monitor."""
        from datetime import timedelta

        monitor.is_paused = False
        monitor.status = ProcessMonitorStatus.WAITING_START
        monitor.consecutive_failures = 0
        monitor.next_expected_start = next_expected_start
        # next_expected_start is UTC naive datetime, so add directly
        monitor.start_deadline = next_expected_start + timedelta(seconds=monitor.start_grace_period)

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor


class ProcessMonitorEventRepository(BaseRepository[ProcessMonitorEvent]):
    """Repository for process monitor event operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ProcessMonitorEvent, db)

    async def get_by_monitor(
        self,
        monitor_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProcessMonitorEvent]:
        """Get events for a process monitor."""
        stmt = (
            select(ProcessMonitorEvent)
            .where(ProcessMonitorEvent.monitor_id == monitor_id)
            .order_by(ProcessMonitorEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_monitor(self, monitor_id: UUID) -> int:
        """Count events for a process monitor."""
        stmt = select(func.count()).select_from(ProcessMonitorEvent).where(ProcessMonitorEvent.monitor_id == monitor_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_run_id(
        self,
        monitor_id: UUID,
        run_id: str,
    ) -> list[ProcessMonitorEvent]:
        """Get all events for a specific run."""
        stmt = (
            select(ProcessMonitorEvent)
            .where(
                and_(
                    ProcessMonitorEvent.monitor_id == monitor_id,
                    ProcessMonitorEvent.run_id == run_id,
                )
            )
            .order_by(ProcessMonitorEvent.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_start_event(
        self,
        monitor_id: UUID,
        run_id: str,
        status_message: str | None = None,
        payload: dict | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
    ) -> ProcessMonitorEvent:
        """Create a start event."""
        return await self.create(
            monitor_id=monitor_id,
            event_type=ProcessMonitorEventType.START,
            run_id=run_id,
            status_message=status_message,
            payload=payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )

    async def create_end_event(
        self,
        monitor_id: UUID,
        run_id: str,
        duration_ms: int | None = None,
        status_message: str | None = None,
        payload: dict | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
    ) -> ProcessMonitorEvent:
        """Create an end event."""
        return await self.create(
            monitor_id=monitor_id,
            event_type=ProcessMonitorEventType.END,
            run_id=run_id,
            duration_ms=duration_ms,
            status_message=status_message,
            payload=payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )

    async def create_timeout_event(
        self,
        monitor_id: UUID,
        run_id: str,
    ) -> ProcessMonitorEvent:
        """Create a timeout event."""
        return await self.create(
            monitor_id=monitor_id,
            event_type=ProcessMonitorEventType.TIMEOUT,
            run_id=run_id,
        )

    async def create_missed_event(
        self,
        monitor_id: UUID,
        run_id: str,
    ) -> ProcessMonitorEvent:
        """Create a missed start event."""
        return await self.create(
            monitor_id=monitor_id,
            event_type=ProcessMonitorEventType.MISSED,
            run_id=run_id,
        )

    async def delete_old_events(
        self,
        monitor_id: UUID,
        keep_count: int = 100,
    ) -> int:
        """Delete old events, keeping only the most recent ones."""
        from sqlalchemy import delete

        # Get IDs to keep
        keep_stmt = (
            select(ProcessMonitorEvent.id)
            .where(ProcessMonitorEvent.monitor_id == monitor_id)
            .order_by(ProcessMonitorEvent.created_at.desc())
            .limit(keep_count)
        )
        keep_result = await self.db.execute(keep_stmt)
        keep_ids = [row[0] for row in keep_result.fetchall()]

        if not keep_ids:
            return 0

        # Delete events not in the keep list
        delete_stmt = delete(ProcessMonitorEvent).where(
            and_(
                ProcessMonitorEvent.monitor_id == monitor_id,
                ProcessMonitorEvent.id.notin_(keep_ids),
            )
        )
        result = await self.db.execute(delete_stmt)
        return result.rowcount

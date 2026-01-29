from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.ssl_monitor import SSLMonitor, SSLMonitorStatus
from app.models.workspace import Workspace


class SSLMonitorRepository(BaseRepository[SSLMonitor]):
    """Repository for SSL monitor operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(SSLMonitor, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SSLMonitor]:
        """Get all SSL monitors for a workspace."""
        stmt = (
            select(SSLMonitor)
            .where(SSLMonitor.workspace_id == workspace_id)
            .order_by(SSLMonitor.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        """Count SSL monitors for a workspace."""
        stmt = select(func.count()).select_from(SSLMonitor).where(SSLMonitor.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_status(
        self,
        workspace_id: UUID,
        statuses: list[SSLMonitorStatus],
    ) -> int:
        """Count SSL monitors for a workspace with given statuses."""
        stmt = (
            select(func.count())
            .select_from(SSLMonitor)
            .where(
                and_(
                    SSLMonitor.workspace_id == workspace_id,
                    SSLMonitor.status.in_(statuses),
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_domain(self, workspace_id: UUID, domain: str) -> SSLMonitor | None:
        """Get SSL monitor by domain within a workspace."""
        stmt = select(SSLMonitor).where(
            and_(
                SSLMonitor.workspace_id == workspace_id,
                SSLMonitor.domain == domain,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_for_check(
        self,
        now: datetime,
        limit: int = 100,
    ) -> list[SSLMonitor]:
        """Get SSL monitors that are due for their daily check.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple scheduler instances are running.
        Excludes paused monitors and blocked workspaces.
        """
        stmt = (
            select(SSLMonitor)
            .join(Workspace, SSLMonitor.workspace_id == Workspace.id)
            .where(
                and_(
                    SSLMonitor.is_paused.is_(False),
                    SSLMonitor.next_check_at.isnot(None),
                    SSLMonitor.next_check_at <= now,
                    SSLMonitor.next_retry_at.is_(None),  # Not in retry mode
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(SSLMonitor.next_check_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_due_for_retry(
        self,
        now: datetime,
        limit: int = 100,
    ) -> list[SSLMonitor]:
        """Get SSL monitors that are due for retry.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions.
        Excludes paused monitors and blocked workspaces.
        """
        stmt = (
            select(SSLMonitor)
            .join(Workspace, SSLMonitor.workspace_id == Workspace.id)
            .where(
                and_(
                    SSLMonitor.is_paused.is_(False),
                    SSLMonitor.next_retry_at.isnot(None),
                    SSLMonitor.next_retry_at <= now,
                    SSLMonitor.retry_count < 3,  # Max 3 retries
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(SSLMonitor.next_retry_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def pause(self, monitor: SSLMonitor) -> SSLMonitor:
        """Pause an SSL monitor."""
        monitor.is_paused = True
        monitor.status = SSLMonitorStatus.PAUSED

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def resume(self, monitor: SSLMonitor) -> SSLMonitor:
        """Resume a paused SSL monitor."""
        monitor.is_paused = False
        monitor.status = SSLMonitorStatus.PENDING
        monitor.retry_count = 0
        monitor.next_retry_at = None
        # Schedule immediate check
        monitor.next_check_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def update_check_result(
        self,
        monitor: SSLMonitor,
        status: SSLMonitorStatus,
        issuer: str | None = None,
        subject: str | None = None,
        serial_number: str | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        days_until_expiry: int | None = None,
        tls_version: str | None = None,
        cipher_suite: str | None = None,
        chain_valid: bool | None = None,
        hostname_match: bool | None = None,
        error: str | None = None,
    ) -> SSLMonitor:
        """Update monitor with check result."""
        now = datetime.utcnow()

        monitor.status = status
        monitor.last_check_at = now
        monitor.last_error = error

        # Certificate info
        monitor.issuer = issuer
        monitor.subject = subject
        monitor.serial_number = serial_number
        monitor.valid_from = valid_from
        monitor.valid_until = valid_until
        monitor.days_until_expiry = days_until_expiry

        # TLS info
        monitor.tls_version = tls_version
        monitor.cipher_suite = cipher_suite

        # Validation info
        monitor.chain_valid = chain_valid
        monitor.hostname_match = hostname_match

        # Reset retry on success or schedule retry on error
        if status in (SSLMonitorStatus.VALID, SSLMonitorStatus.EXPIRING, SSLMonitorStatus.EXPIRED):
            monitor.retry_count = 0
            monitor.next_retry_at = None
            # Schedule next daily check (24 hours from now)
            monitor.next_check_at = datetime.fromtimestamp(now.timestamp() + 86400)
        elif status == SSLMonitorStatus.ERROR:
            # Schedule retry if under limit
            if monitor.retry_count < 3:
                monitor.retry_count += 1
                # Retry in 1 hour
                monitor.next_retry_at = datetime.fromtimestamp(now.timestamp() + 3600)
            else:
                # Max retries reached, schedule next daily check
                monitor.next_retry_at = None
                monitor.next_check_at = datetime.fromtimestamp(now.timestamp() + 86400)

        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

    async def update_notification_sent(
        self,
        monitor: SSLMonitor,
        days_until_expiry: int,
    ) -> SSLMonitor:
        """Update last notification days to prevent duplicate notifications."""
        monitor.last_notification_days = days_until_expiry
        await self.db.flush()
        await self.db.refresh(monitor)
        return monitor

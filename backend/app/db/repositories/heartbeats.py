from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.heartbeat import Heartbeat, HeartbeatPing, HeartbeatStatus
from app.models.workspace import Workspace


class HeartbeatRepository(BaseRepository[Heartbeat]):
    """Repository for heartbeat operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Heartbeat, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Heartbeat]:
        """Get all heartbeats for a workspace."""
        stmt = (
            select(Heartbeat)
            .where(Heartbeat.workspace_id == workspace_id)
            .order_by(Heartbeat.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        """Count heartbeats for a workspace."""
        stmt = (
            select(func.count())
            .select_from(Heartbeat)
            .where(Heartbeat.workspace_id == workspace_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_ping_token(self, ping_token: str) -> Heartbeat | None:
        """Get heartbeat by its ping token."""
        stmt = select(Heartbeat).where(Heartbeat.ping_token == ping_token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_overdue_heartbeats(
        self,
        now: datetime,
        limit: int = 100,
    ) -> list[Heartbeat]:
        """Get heartbeats that are overdue (past next_expected_at + grace_period).

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple scheduler instances are running.
        Excludes paused heartbeats and blocked workspaces.
        """
        stmt = (
            select(Heartbeat)
            .join(Workspace, Heartbeat.workspace_id == Workspace.id)
            .where(
                and_(
                    Heartbeat.is_paused.is_(False),
                    Heartbeat.status.in_([HeartbeatStatus.HEALTHY, HeartbeatStatus.WAITING]),
                    Heartbeat.next_expected_at.isnot(None),
                    Heartbeat.next_expected_at <= now,
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(Heartbeat.next_expected_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_dead_heartbeats(
        self,
        now: datetime,
        missed_count: int = 3,
        limit: int = 100,
    ) -> list[Heartbeat]:
        """Get heartbeats that are LATE and need to transition to DEAD.

        A heartbeat is considered DEAD after 3+ consecutive misses.
        """
        stmt = (
            select(Heartbeat)
            .join(Workspace, Heartbeat.workspace_id == Workspace.id)
            .where(
                and_(
                    Heartbeat.is_paused.is_(False),
                    Heartbeat.status == HeartbeatStatus.LATE,
                    Heartbeat.consecutive_misses >= missed_count,
                    Workspace.is_blocked.is_(False),
                )
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_ping(
        self,
        heartbeat: Heartbeat,
        now: datetime,
    ) -> Heartbeat:
        """Update heartbeat after receiving a ping."""
        heartbeat.last_ping_at = now
        heartbeat.status = HeartbeatStatus.HEALTHY
        heartbeat.consecutive_misses = 0
        heartbeat.alert_sent = False
        # Calculate next expected time
        heartbeat.next_expected_at = datetime.fromtimestamp(
            now.timestamp() + heartbeat.expected_interval + heartbeat.grace_period
        )

        await self.db.flush()
        await self.db.refresh(heartbeat)
        return heartbeat

    async def mark_late(self, heartbeat: Heartbeat) -> Heartbeat:
        """Mark heartbeat as late."""
        heartbeat.status = HeartbeatStatus.LATE
        heartbeat.consecutive_misses += 1
        heartbeat.alert_sent = True
        heartbeat.last_alert_at = datetime.utcnow()
        # Update next expected time for next check
        heartbeat.next_expected_at = datetime.fromtimestamp(
            datetime.utcnow().timestamp() + heartbeat.expected_interval
        )

        await self.db.flush()
        await self.db.refresh(heartbeat)
        return heartbeat

    async def mark_dead(self, heartbeat: Heartbeat) -> Heartbeat:
        """Mark heartbeat as dead."""
        heartbeat.status = HeartbeatStatus.DEAD

        await self.db.flush()
        await self.db.refresh(heartbeat)
        return heartbeat

    async def pause(self, heartbeat: Heartbeat) -> Heartbeat:
        """Pause a heartbeat monitor."""
        heartbeat.is_paused = True
        heartbeat.status = HeartbeatStatus.PAUSED

        await self.db.flush()
        await self.db.refresh(heartbeat)
        return heartbeat

    async def resume(self, heartbeat: Heartbeat) -> Heartbeat:
        """Resume a heartbeat monitor."""
        heartbeat.is_paused = False
        heartbeat.status = HeartbeatStatus.WAITING
        heartbeat.consecutive_misses = 0
        heartbeat.alert_sent = False
        # Set next expected to now + interval + grace (will start fresh)
        now = datetime.utcnow()
        heartbeat.next_expected_at = datetime.fromtimestamp(
            now.timestamp() + heartbeat.expected_interval + heartbeat.grace_period
        )

        await self.db.flush()
        await self.db.refresh(heartbeat)
        return heartbeat


class HeartbeatPingRepository(BaseRepository[HeartbeatPing]):
    """Repository for heartbeat ping operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(HeartbeatPing, db)

    async def get_by_heartbeat(
        self,
        heartbeat_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[HeartbeatPing]:
        """Get pings for a heartbeat."""
        stmt = (
            select(HeartbeatPing)
            .where(HeartbeatPing.heartbeat_id == heartbeat_id)
            .order_by(HeartbeatPing.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_heartbeat(self, heartbeat_id: UUID) -> int:
        """Count pings for a heartbeat."""
        stmt = (
            select(func.count())
            .select_from(HeartbeatPing)
            .where(HeartbeatPing.heartbeat_id == heartbeat_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete_old_pings(
        self,
        heartbeat_id: UUID,
        keep_count: int = 100,
    ) -> int:
        """Delete old pings, keeping only the most recent ones."""
        # Get IDs to keep
        keep_stmt = (
            select(HeartbeatPing.id)
            .where(HeartbeatPing.heartbeat_id == heartbeat_id)
            .order_by(HeartbeatPing.created_at.desc())
            .limit(keep_count)
        )
        keep_result = await self.db.execute(keep_stmt)
        keep_ids = [row[0] for row in keep_result.fetchall()]

        if not keep_ids:
            return 0

        # Delete pings not in the keep list
        from sqlalchemy import delete

        delete_stmt = (
            delete(HeartbeatPing)
            .where(
                and_(
                    HeartbeatPing.heartbeat_id == heartbeat_id,
                    HeartbeatPing.id.notin_(keep_ids),
                )
            )
        )
        result = await self.db.execute(delete_stmt)
        return result.rowcount

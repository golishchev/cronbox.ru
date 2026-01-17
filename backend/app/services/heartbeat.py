"""Heartbeat monitor service - Dead Man's Switch logic."""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.heartbeats import HeartbeatPingRepository, HeartbeatRepository
from app.models.heartbeat import Heartbeat, HeartbeatPing, HeartbeatStatus
from app.services.notifications import notification_service

logger = structlog.get_logger()


class HeartbeatService:
    """Service for heartbeat monitoring operations."""

    async def process_ping(
        self,
        db: AsyncSession,
        heartbeat: Heartbeat,
        duration_ms: int | None = None,
        status_message: str | None = None,
        payload: dict | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
    ) -> HeartbeatPing:
        """Process an incoming ping for a heartbeat monitor."""
        heartbeat_repo = HeartbeatRepository(db)
        ping_repo = HeartbeatPingRepository(db)

        now = datetime.utcnow()
        was_late = heartbeat.status in (HeartbeatStatus.LATE, HeartbeatStatus.DEAD)

        # Create ping record
        ping = await ping_repo.create(
            heartbeat_id=heartbeat.id,
            duration_ms=duration_ms,
            status_message=status_message,
            payload=payload,
            source_ip=source_ip,
            user_agent=user_agent,
        )

        # Update heartbeat state
        await heartbeat_repo.update_ping(heartbeat, now)

        # Send recovery notification if was late/dead
        if was_late and heartbeat.notify_on_recovery:
            try:
                await self._send_recovery_notification(db, heartbeat)
            except Exception as e:
                logger.error(
                    "Failed to send recovery notification",
                    heartbeat_id=str(heartbeat.id),
                    error=str(e),
                )

        # Clean up old pings (keep last 100)
        await ping_repo.delete_old_pings(heartbeat.id, keep_count=100)

        await db.commit()

        logger.info(
            "Processed heartbeat ping",
            heartbeat_id=str(heartbeat.id),
            heartbeat_name=heartbeat.name,
            was_late=was_late,
            status=heartbeat.status.value,
        )

        return ping

    async def check_overdue_heartbeats(self, db: AsyncSession) -> int:
        """Check for overdue heartbeats and mark them as late.

        Returns the number of heartbeats marked as late.
        """
        heartbeat_repo = HeartbeatRepository(db)
        now = datetime.utcnow()
        processed = 0

        # Get overdue heartbeats
        overdue = await heartbeat_repo.get_overdue_heartbeats(now, limit=100)

        for heartbeat in overdue:
            try:
                # Mark as late
                await heartbeat_repo.mark_late(heartbeat)

                # Send alert notification
                if heartbeat.notify_on_late:
                    try:
                        await self._send_late_notification(db, heartbeat)
                    except Exception as e:
                        logger.error(
                            "Failed to send late notification",
                            heartbeat_id=str(heartbeat.id),
                            error=str(e),
                        )

                await db.commit()
                processed += 1

                logger.warning(
                    "Heartbeat marked as late",
                    heartbeat_id=str(heartbeat.id),
                    heartbeat_name=heartbeat.name,
                    consecutive_misses=heartbeat.consecutive_misses,
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Error processing overdue heartbeat",
                    heartbeat_id=str(heartbeat.id),
                    error=str(e),
                )

        return processed

    async def check_dead_heartbeats(self, db: AsyncSession) -> int:
        """Check for heartbeats that should be marked as dead.

        Returns the number of heartbeats marked as dead.
        """
        heartbeat_repo = HeartbeatRepository(db)
        now = datetime.utcnow()
        processed = 0

        # Get heartbeats with 3+ consecutive misses
        dead_candidates = await heartbeat_repo.get_dead_heartbeats(now, missed_count=3, limit=100)

        for heartbeat in dead_candidates:
            try:
                # Mark as dead
                await heartbeat_repo.mark_dead(heartbeat)

                # Send dead notification (using late notification channel)
                if heartbeat.notify_on_late:
                    try:
                        await self._send_dead_notification(db, heartbeat)
                    except Exception as e:
                        logger.error(
                            "Failed to send dead notification",
                            heartbeat_id=str(heartbeat.id),
                            error=str(e),
                        )

                await db.commit()
                processed += 1

                logger.error(
                    "Heartbeat marked as dead",
                    heartbeat_id=str(heartbeat.id),
                    heartbeat_name=heartbeat.name,
                    consecutive_misses=heartbeat.consecutive_misses,
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    "Error processing dead heartbeat",
                    heartbeat_id=str(heartbeat.id),
                    error=str(e),
                )

        return processed

    async def _send_late_notification(
        self,
        db: AsyncSession,
        heartbeat: Heartbeat,
    ) -> None:
        """Send notification when heartbeat becomes late."""
        await notification_service.send_task_failure(
            db=db,
            workspace_id=heartbeat.workspace_id,
            task_name=heartbeat.name,
            task_type="heartbeat",
            error_message=f"Heartbeat monitor '{heartbeat.name}' has not received a ping within the expected interval. "
            f"Last ping: {heartbeat.last_ping_at.isoformat() if heartbeat.last_ping_at else 'never'}",
        )

    async def _send_dead_notification(
        self,
        db: AsyncSession,
        heartbeat: Heartbeat,
    ) -> None:
        """Send notification when heartbeat becomes dead."""
        await notification_service.send_task_failure(
            db=db,
            workspace_id=heartbeat.workspace_id,
            task_name=heartbeat.name,
            task_type="heartbeat",
            error_message=f"Heartbeat monitor '{heartbeat.name}' is DEAD - no pings received for {heartbeat.consecutive_misses} consecutive intervals. "
            f"Last ping: {heartbeat.last_ping_at.isoformat() if heartbeat.last_ping_at else 'never'}",
        )

    async def _send_recovery_notification(
        self,
        db: AsyncSession,
        heartbeat: Heartbeat,
    ) -> None:
        """Send notification when heartbeat recovers."""
        await notification_service.send_task_recovery(
            db=db,
            workspace_id=heartbeat.workspace_id,
            task_name=heartbeat.name,
            task_type="heartbeat",
        )


# Global instance
heartbeat_service = HeartbeatService()

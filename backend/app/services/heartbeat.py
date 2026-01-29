"""Heartbeat monitor service - Dead Man's Switch logic."""

from datetime import datetime, timezone
from uuid import UUID

import pytz
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.heartbeats import HeartbeatPingRepository, HeartbeatRepository
from app.models.heartbeat import Heartbeat, HeartbeatPing, HeartbeatStatus
from app.models.workspace import Workspace
from app.services.i18n import t
from app.services.notifications import notification_service

logger = structlog.get_logger()


class HeartbeatService:
    """Service for heartbeat monitoring operations."""

    async def _get_workspace_language(self, db: AsyncSession, workspace_id: UUID) -> str:
        """Get the preferred language of the workspace owner."""
        result = await db.execute(
            select(Workspace).options(selectinload(Workspace.owner)).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()

        if workspace and workspace.owner:
            return workspace.owner.preferred_language or "en"
        return "en"

    async def _get_workspace_settings(self, db: AsyncSession, workspace_id: UUID) -> tuple[str, str]:
        """Get workspace language and timezone."""
        result = await db.execute(
            select(Workspace).options(selectinload(Workspace.owner)).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()

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
        lang, tz = await self._get_workspace_settings(db, heartbeat.workspace_id)
        last_ping = (
            self._format_datetime(heartbeat.last_ping_at, tz) if heartbeat.last_ping_at else t("heartbeat.never", lang)
        )
        error_message = t("heartbeat.late", lang, name=heartbeat.name, last_ping=last_ping)

        await notification_service.send_task_failure(
            db=db,
            workspace_id=heartbeat.workspace_id,
            task_name=heartbeat.name,
            task_type="heartbeat",
            error_message=error_message,
        )

    async def _send_dead_notification(
        self,
        db: AsyncSession,
        heartbeat: Heartbeat,
    ) -> None:
        """Send notification when heartbeat becomes dead."""
        lang, tz = await self._get_workspace_settings(db, heartbeat.workspace_id)
        last_ping = (
            self._format_datetime(heartbeat.last_ping_at, tz) if heartbeat.last_ping_at else t("heartbeat.never", lang)
        )
        error_message = t(
            "heartbeat.dead",
            lang,
            name=heartbeat.name,
            missed_count=heartbeat.consecutive_misses,
            last_ping=last_ping,
        )

        await notification_service.send_task_failure(
            db=db,
            workspace_id=heartbeat.workspace_id,
            task_name=heartbeat.name,
            task_type="heartbeat",
            error_message=error_message,
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

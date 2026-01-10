from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.cron_task import HttpMethod, TaskStatus
from app.models.execution import Execution


class ExecutionRepository(BaseRepository[Execution]):
    """Repository for execution log operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Execution, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
        task_type: str | None = None,
        task_id: UUID | None = None,
        status: TaskStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Execution]:
        """Get executions for a workspace with filters."""
        stmt = (
            select(Execution)
            .where(Execution.workspace_id == workspace_id)
            .order_by(Execution.started_at.desc())
        )

        if task_type is not None:
            stmt = stmt.where(Execution.task_type == task_type)
        if task_id is not None:
            stmt = stmt.where(Execution.task_id == task_id)
        if status is not None:
            stmt = stmt.where(Execution.status == status)
        if start_date is not None:
            stmt = stmt.where(Execution.started_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(Execution.started_at <= end_date)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        task_type: str | None = None,
        task_id: UUID | None = None,
        status: TaskStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count executions for a workspace with filters."""
        stmt = (
            select(func.count())
            .select_from(Execution)
            .where(Execution.workspace_id == workspace_id)
        )

        if task_type is not None:
            stmt = stmt.where(Execution.task_type == task_type)
        if task_id is not None:
            stmt = stmt.where(Execution.task_id == task_id)
        if status is not None:
            stmt = stmt.where(Execution.status == status)
        if start_date is not None:
            stmt = stmt.where(Execution.started_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(Execution.started_at <= end_date)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_stats(
        self,
        workspace_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        task_id: UUID | None = None,
    ) -> dict:
        """Get execution statistics."""
        base_filter = [Execution.workspace_id == workspace_id]
        if start_date:
            base_filter.append(Execution.started_at >= start_date)
        if end_date:
            base_filter.append(Execution.started_at <= end_date)
        if task_id:
            base_filter.append(Execution.task_id == task_id)

        # Total count
        total_stmt = select(func.count()).select_from(Execution).where(and_(*base_filter))
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar_one()

        # Success count
        success_stmt = (
            select(func.count())
            .select_from(Execution)
            .where(and_(*base_filter, Execution.status == TaskStatus.SUCCESS))
        )
        success_result = await self.db.execute(success_stmt)
        success = success_result.scalar_one()

        # Failed count
        failed_stmt = (
            select(func.count())
            .select_from(Execution)
            .where(and_(*base_filter, Execution.status == TaskStatus.FAILED))
        )
        failed_result = await self.db.execute(failed_stmt)
        failed = failed_result.scalar_one()

        # Average duration
        avg_stmt = (
            select(func.avg(Execution.duration_ms))
            .select_from(Execution)
            .where(and_(*base_filter, Execution.duration_ms != None))
        )
        avg_result = await self.db.execute(avg_stmt)
        avg_duration = avg_result.scalar_one()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": (success / total * 100) if total > 0 else 0.0,
            "avg_duration_ms": float(avg_duration) if avg_duration else None,
        }

    async def create_execution(
        self,
        workspace_id: UUID,
        task_type: str,
        task_id: UUID,
        task_name: str | None,
        request_url: str,
        request_method: HttpMethod,
        request_headers: dict | None = None,
        request_body: str | None = None,
        cron_task_id: UUID | None = None,
        retry_attempt: int = 0,
    ) -> Execution:
        """Create a new execution record."""
        return await self.create(
            workspace_id=workspace_id,
            task_type=task_type,
            task_id=task_id,
            task_name=task_name,
            cron_task_id=cron_task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow(),
            retry_attempt=retry_attempt,
            request_url=request_url,
            request_method=request_method,
            request_headers=request_headers,
            request_body=request_body,
        )

    async def complete_execution(
        self,
        execution: Execution,
        status: TaskStatus,
        response_status_code: int | None = None,
        response_headers: dict | None = None,
        response_body: str | None = None,
        response_size_bytes: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> Execution:
        """Complete an execution record."""
        now = datetime.utcnow()
        execution.status = status
        execution.finished_at = now
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
        execution.response_status_code = response_status_code
        execution.response_headers = response_headers
        execution.response_body = response_body
        execution.response_size_bytes = response_size_bytes
        execution.error_message = error_message
        execution.error_type = error_type

        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def get_daily_stats(
        self,
        workspace_id: UUID,
        days: int = 7,
    ) -> list[dict]:
        """Get daily execution statistics for the last N days."""
        from datetime import timedelta

        # Calculate start date (N days ago, beginning of day UTC)
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

        from sqlalchemy import case

        stmt = (
            select(
                func.date(Execution.started_at).label("date"),
                func.count(case((Execution.status == TaskStatus.SUCCESS, 1))).label("success"),
                func.count(case((Execution.status == TaskStatus.FAILED, 1))).label("failed"),
                func.count().label("total"),
            )
            .where(
                and_(
                    Execution.workspace_id == workspace_id,
                    Execution.started_at >= start_date,
                )
            )
            .group_by(func.date(Execution.started_at))
            .order_by(func.date(Execution.started_at))
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build result with all days (including days with no executions)
        stats_by_date = {str(row.date): {"success": row.success, "failed": row.failed, "total": row.total} for row in rows}

        daily_stats = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            if date_str in stats_by_date:
                daily_stats.append({
                    "date": date_str,
                    "success": stats_by_date[date_str]["success"],
                    "failed": stats_by_date[date_str]["failed"],
                    "total": stats_by_date[date_str]["total"],
                })
            else:
                daily_stats.append({
                    "date": date_str,
                    "success": 0,
                    "failed": 0,
                    "total": 0,
                })

        return daily_stats

    async def cleanup_old_executions(
        self,
        workspace_id: UUID,
        older_than: datetime,
    ) -> int:
        """Delete executions older than given date. Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(Execution).where(
            and_(
                Execution.workspace_id == workspace_id,
                Execution.created_at < older_than,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

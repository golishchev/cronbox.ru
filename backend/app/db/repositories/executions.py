from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.chain_execution import ChainExecution
from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus
from app.models.execution import Execution
from app.models.heartbeat import Heartbeat, HeartbeatPing
from app.models.task_chain import ChainStatus, TaskChain


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
        stmt = select(Execution).where(Execution.workspace_id == workspace_id).order_by(Execution.started_at.desc())

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
        stmt = select(func.count()).select_from(Execution).where(Execution.workspace_id == workspace_id)

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
            select(func.count()).select_from(Execution).where(and_(*base_filter, Execution.status == TaskStatus.FAILED))
        )
        failed_result = await self.db.execute(failed_stmt)
        failed = failed_result.scalar_one()

        # Average duration
        avg_stmt = (
            select(func.avg(Execution.duration_ms))
            .select_from(Execution)
            .where(and_(*base_filter, Execution.duration_ms.is_not(None)))
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
        request_url: str | None = None,
        request_method: HttpMethod | None = None,
        request_headers: dict | None = None,
        request_body: str | None = None,
        cron_task_id: UUID | None = None,
        retry_attempt: int = 0,
        protocol_type: ProtocolType | None = None,
        target_host: str | None = None,
        target_port: int | None = None,
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
            protocol_type=protocol_type,
            target_host=target_host,
            target_port=target_port,
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
        """Complete an HTTP execution record."""
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

    async def complete_icmp_execution(
        self,
        execution: Execution,
        status: TaskStatus,
        packets_sent: int | None = None,
        packets_received: int | None = None,
        packet_loss: float | None = None,
        min_rtt: float | None = None,
        avg_rtt: float | None = None,
        max_rtt: float | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> Execution:
        """Complete an ICMP execution record."""
        now = datetime.utcnow()
        execution.status = status
        execution.finished_at = now
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
        execution.icmp_packets_sent = packets_sent
        execution.icmp_packets_received = packets_received
        execution.icmp_packet_loss = packet_loss
        execution.icmp_min_rtt = min_rtt
        execution.icmp_avg_rtt = avg_rtt
        execution.icmp_max_rtt = max_rtt
        execution.error_message = error_message
        execution.error_type = error_type

        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def complete_tcp_execution(
        self,
        execution: Execution,
        status: TaskStatus,
        connection_time: float | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> Execution:
        """Complete a TCP execution record."""
        now = datetime.utcnow()
        execution.status = status
        execution.finished_at = now
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
        execution.tcp_connection_time = connection_time
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
        stats_by_date = {
            str(row.date): {"success": row.success, "failed": row.failed, "total": row.total} for row in rows
        }

        daily_stats = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            if date_str in stats_by_date:
                daily_stats.append(
                    {
                        "date": date_str,
                        "success": stats_by_date[date_str]["success"],
                        "failed": stats_by_date[date_str]["failed"],
                        "total": stats_by_date[date_str]["total"],
                    }
                )
            else:
                daily_stats.append(
                    {
                        "date": date_str,
                        "success": 0,
                        "failed": 0,
                        "total": 0,
                    }
                )

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

    async def get_unified_executions(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
        task_type: str | None = None,
        task_id: UUID | None = None,
        status: TaskStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Get unified executions from both regular executions and chain executions.

        Returns a list of dicts with unified schema, sorted by started_at desc.
        """
        results = []

        # Get regular executions (cron and delayed) if not filtered to chains only
        if task_type is None or task_type in ("cron", "delayed"):
            stmt = select(Execution).where(Execution.workspace_id == workspace_id).order_by(Execution.started_at.desc())

            if task_type in ("cron", "delayed"):
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
            executions = result.scalars().all()

            for ex in executions:
                results.append(
                    {
                        "id": ex.id,
                        "workspace_id": ex.workspace_id,
                        "task_type": ex.task_type,
                        "task_id": ex.task_id,
                        "task_name": ex.task_name,
                        "status": ex.status.value,
                        "started_at": ex.started_at,
                        "finished_at": ex.finished_at,
                        "duration_ms": ex.duration_ms,
                        "retry_attempt": ex.retry_attempt,
                        "request_url": ex.request_url,
                        "request_method": ex.request_method.value if ex.request_method else None,
                        "response_status_code": ex.response_status_code,
                        "error_message": ex.error_message,
                        "error_type": ex.error_type,
                        "created_at": ex.created_at,
                        "total_steps": None,
                        "completed_steps": None,
                        "failed_steps": None,
                        "skipped_steps": None,
                    }
                )

        # Get chain executions if not filtered to cron/delayed only
        if task_type is None or task_type == "chain":
            chain_stmt = (
                select(ChainExecution, TaskChain.name)
                .join(TaskChain, ChainExecution.chain_id == TaskChain.id)
                .where(ChainExecution.workspace_id == workspace_id)
                .order_by(ChainExecution.started_at.desc())
            )

            if task_id is not None:
                chain_stmt = chain_stmt.where(ChainExecution.chain_id == task_id)

            # Map TaskStatus to ChainStatus for filtering
            if status is not None:
                chain_status_map = {
                    TaskStatus.PENDING: ChainStatus.PENDING,
                    TaskStatus.RUNNING: ChainStatus.RUNNING,
                    TaskStatus.SUCCESS: ChainStatus.SUCCESS,
                    TaskStatus.FAILED: ChainStatus.FAILED,
                }
                if status in chain_status_map:
                    chain_stmt = chain_stmt.where(ChainExecution.status == chain_status_map[status])

            if start_date is not None:
                chain_stmt = chain_stmt.where(ChainExecution.started_at >= start_date)
            if end_date is not None:
                chain_stmt = chain_stmt.where(ChainExecution.started_at <= end_date)

            chain_result = await self.db.execute(chain_stmt)
            chain_executions = chain_result.all()

            for row in chain_executions:
                chain_ex = row[0]
                chain_name = row[1]
                # Map ChainStatus to TaskStatus string
                status_map = {
                    ChainStatus.PENDING: "pending",
                    ChainStatus.RUNNING: "running",
                    ChainStatus.SUCCESS: "success",
                    ChainStatus.FAILED: "failed",
                    ChainStatus.PARTIAL: "partial",
                    ChainStatus.CANCELLED: "cancelled",
                }
                results.append(
                    {
                        "id": chain_ex.id,
                        "workspace_id": chain_ex.workspace_id,
                        "task_type": "chain",
                        "task_id": chain_ex.chain_id,
                        "task_name": chain_name,
                        "status": status_map.get(chain_ex.status, "unknown"),
                        "started_at": chain_ex.started_at,
                        "finished_at": chain_ex.finished_at,
                        "duration_ms": chain_ex.duration_ms,
                        "retry_attempt": None,
                        "request_url": None,
                        "request_method": None,
                        "response_status_code": None,
                        "error_message": chain_ex.error_message,
                        "error_type": None,
                        "created_at": chain_ex.created_at,
                        "total_steps": chain_ex.total_steps,
                        "completed_steps": chain_ex.completed_steps,
                        "failed_steps": chain_ex.failed_steps,
                        "skipped_steps": chain_ex.skipped_steps,
                    }
                )

        # Get heartbeat pings if not filtered to other types
        if task_type is None or task_type == "heartbeat":
            heartbeat_stmt = (
                select(HeartbeatPing, Heartbeat.name)
                .join(Heartbeat, HeartbeatPing.heartbeat_id == Heartbeat.id)
                .where(Heartbeat.workspace_id == workspace_id)
                .order_by(HeartbeatPing.created_at.desc())
            )

            if task_id is not None:
                heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.heartbeat_id == task_id)

            # Heartbeat pings are always "success" - they represent received pings
            if status is not None and status != TaskStatus.SUCCESS:
                pass  # Skip heartbeat pings if filtering for non-success status
            else:
                if start_date is not None:
                    heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.created_at >= start_date)
                if end_date is not None:
                    heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.created_at <= end_date)

                heartbeat_result = await self.db.execute(heartbeat_stmt)
                heartbeat_pings = heartbeat_result.all()

                for row in heartbeat_pings:
                    ping = row[0]
                    heartbeat_name = row[1]
                    results.append(
                        {
                            "id": ping.id,
                            "workspace_id": workspace_id,
                            "task_type": "heartbeat",
                            "task_id": ping.heartbeat_id,
                            "task_name": heartbeat_name,
                            "status": "success",  # Pings are always successful
                            "started_at": ping.created_at,
                            "finished_at": ping.created_at,
                            "duration_ms": ping.duration_ms,
                            "retry_attempt": None,
                            "request_url": None,
                            "request_method": None,
                            "response_status_code": None,
                            "error_message": None,
                            "error_type": None,
                            "created_at": ping.created_at,
                            "total_steps": None,
                            "completed_steps": None,
                            "failed_steps": None,
                            "skipped_steps": None,
                            # Heartbeat-specific fields
                            "source_ip": ping.source_ip,
                            "status_message": ping.status_message,
                        }
                    )

        # Sort by started_at descending
        # Normalize datetimes to naive (remove timezone info) for comparison
        def get_sort_key(x):
            dt = x["started_at"]
            if dt is None:
                return datetime.min
            # Remove timezone info if present to allow comparison
            if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt

        results.sort(key=get_sort_key, reverse=True)

        # Apply pagination
        return results[skip : skip + limit]

    async def count_unified_executions(
        self,
        workspace_id: UUID,
        task_type: str | None = None,
        task_id: UUID | None = None,
        status: TaskStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count unified executions from both regular executions and chain executions."""
        total = 0

        # Count regular executions
        if task_type is None or task_type in ("cron", "delayed"):
            stmt = select(func.count()).select_from(Execution).where(Execution.workspace_id == workspace_id)

            if task_type in ("cron", "delayed"):
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
            total += result.scalar_one()

        # Count chain executions
        if task_type is None or task_type == "chain":
            chain_stmt = (
                select(func.count()).select_from(ChainExecution).where(ChainExecution.workspace_id == workspace_id)
            )

            if task_id is not None:
                chain_stmt = chain_stmt.where(ChainExecution.chain_id == task_id)

            if status is not None:
                chain_status_map = {
                    TaskStatus.PENDING: ChainStatus.PENDING,
                    TaskStatus.RUNNING: ChainStatus.RUNNING,
                    TaskStatus.SUCCESS: ChainStatus.SUCCESS,
                    TaskStatus.FAILED: ChainStatus.FAILED,
                }
                if status in chain_status_map:
                    chain_stmt = chain_stmt.where(ChainExecution.status == chain_status_map[status])

            if start_date is not None:
                chain_stmt = chain_stmt.where(ChainExecution.started_at >= start_date)
            if end_date is not None:
                chain_stmt = chain_stmt.where(ChainExecution.started_at <= end_date)

            chain_result = await self.db.execute(chain_stmt)
            total += chain_result.scalar_one()

        # Count heartbeat pings
        if task_type is None or task_type == "heartbeat":
            # Only count if not filtering for non-success status
            if status is None or status == TaskStatus.SUCCESS:
                heartbeat_stmt = (
                    select(func.count())
                    .select_from(HeartbeatPing)
                    .join(Heartbeat, HeartbeatPing.heartbeat_id == Heartbeat.id)
                    .where(Heartbeat.workspace_id == workspace_id)
                )

                if task_id is not None:
                    heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.heartbeat_id == task_id)

                if start_date is not None:
                    heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.created_at >= start_date)
                if end_date is not None:
                    heartbeat_stmt = heartbeat_stmt.where(HeartbeatPing.created_at <= end_date)

                heartbeat_result = await self.db.execute(heartbeat_stmt)
                total += heartbeat_result.scalar_one()

        return total

    async def get_running_execution_by_process_monitor(
        self,
        process_monitor_id: UUID,
    ) -> Execution | None:
        """Get the most recent running execution for a process monitor."""
        stmt = (
            select(Execution)
            .where(
                Execution.process_monitor_id == process_monitor_id,
                Execution.status == TaskStatus.RUNNING,
            )
            .order_by(Execution.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def complete_process_monitor_execution(
        self,
        execution: Execution,
        status: TaskStatus,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> Execution:
        """Complete a process monitor execution record."""
        now = datetime.utcnow()
        execution.status = status
        execution.finished_at = now
        if duration_ms is not None:
            execution.duration_ms = duration_ms
        if error_message is not None:
            execution.error_message = error_message

        await self.db.flush()
        return execution

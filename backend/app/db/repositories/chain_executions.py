"""Repository for chain execution operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.chain_execution import ChainExecution, StepExecution, StepStatus
from app.models.task_chain import ChainStatus


class ChainExecutionRepository(BaseRepository[ChainExecution]):
    """Repository for chain execution operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ChainExecution, db)

    async def get_by_chain(
        self,
        chain_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChainExecution]:
        """Get all executions for a chain."""
        stmt = (
            select(ChainExecution)
            .where(ChainExecution.chain_id == chain_id)
            .order_by(ChainExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChainExecution]:
        """Get all chain executions for a workspace."""
        stmt = (
            select(ChainExecution)
            .where(ChainExecution.workspace_id == workspace_id)
            .order_by(ChainExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_chain(self, chain_id: UUID) -> int:
        """Count executions for a chain."""
        stmt = select(func.count()).select_from(ChainExecution).where(ChainExecution.chain_id == chain_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        """Count executions for a workspace."""
        stmt = select(func.count()).select_from(ChainExecution).where(ChainExecution.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_with_step_executions(self, execution_id: UUID) -> ChainExecution | None:
        """Get a chain execution with its step executions loaded."""
        stmt = (
            select(ChainExecution)
            .options(selectinload(ChainExecution.step_executions))
            .where(ChainExecution.id == execution_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_execution(
        self,
        workspace_id: UUID,
        chain_id: UUID,
        total_steps: int,
        initial_variables: dict | None = None,
    ) -> ChainExecution:
        """Create a new chain execution record."""
        execution = ChainExecution(
            workspace_id=workspace_id,
            chain_id=chain_id,
            status=ChainStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_steps=total_steps,
            variables=initial_variables or {},
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def complete_execution(
        self,
        execution: ChainExecution,
        status: ChainStatus,
        error_message: str | None = None,
    ) -> ChainExecution:
        """Mark execution as complete."""
        now = datetime.utcnow()
        execution.status = status
        execution.finished_at = now
        # Normalize to naive datetime for comparison
        started_at = execution.started_at.replace(tzinfo=None) if execution.started_at.tzinfo else execution.started_at
        execution.duration_ms = int((now - started_at).total_seconds() * 1000)
        execution.error_message = error_message
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def update_step_counts(
        self,
        execution: ChainExecution,
        completed: int,
        failed: int,
        skipped: int,
    ) -> ChainExecution:
        """Update step counts on execution."""
        execution.completed_steps = completed
        execution.failed_steps = failed
        execution.skipped_steps = skipped
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def update_variables(self, execution: ChainExecution, variables: dict) -> ChainExecution:
        """Update accumulated variables on execution."""
        execution.variables = variables
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def delete_old_executions(self, workspace_id: UUID, keep_days: int) -> int:
        """Delete executions older than keep_days."""
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=keep_days)

        stmt = delete(ChainExecution).where(
            ChainExecution.workspace_id == workspace_id,
            ChainExecution.created_at < cutoff,
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount


class StepExecutionRepository(BaseRepository[StepExecution]):
    """Repository for step execution operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(StepExecution, db)

    async def get_by_chain_execution(self, chain_execution_id: UUID) -> list[StepExecution]:
        """Get all step executions for a chain execution, ordered by step_order."""
        stmt = (
            select(StepExecution)
            .where(StepExecution.chain_execution_id == chain_execution_id)
            .order_by(StepExecution.step_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_step_execution(
        self,
        chain_execution_id: UUID,
        step_id: UUID | None,
        step_order: int,
        step_name: str,
        request_url: str,
        request_method: str,
        request_headers: dict | None = None,
        request_body: str | None = None,
    ) -> StepExecution:
        """Create a new step execution record."""
        from app.models.cron_task import HttpMethod

        step_execution = StepExecution(
            chain_execution_id=chain_execution_id,
            step_id=step_id,
            step_order=step_order,
            step_name=step_name,
            status=StepStatus.RUNNING,
            started_at=datetime.utcnow(),
            request_url=request_url,
            request_method=HttpMethod(request_method),
            request_headers=request_headers,
            request_body=request_body,
        )
        self.db.add(step_execution)
        await self.db.flush()
        await self.db.refresh(step_execution)
        return step_execution

    async def complete_step_execution(
        self,
        step_execution: StepExecution,
        status: StepStatus,
        response_status_code: int | None = None,
        response_headers: dict | None = None,
        response_body: str | None = None,
        response_size_bytes: int | None = None,
        extracted_variables: dict | None = None,
        condition_met: bool | None = None,
        condition_details: str | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        retry_attempt: int = 0,
    ) -> StepExecution:
        """Mark step execution as complete."""
        now = datetime.utcnow()
        step_execution.status = status
        step_execution.finished_at = now
        if step_execution.started_at:
            # Normalize to naive datetime for comparison
            started_at = (
                step_execution.started_at.replace(tzinfo=None)
                if step_execution.started_at.tzinfo
                else step_execution.started_at
            )
            step_execution.duration_ms = int((now - started_at).total_seconds() * 1000)
        step_execution.response_status_code = response_status_code
        step_execution.response_headers = response_headers
        step_execution.response_body = response_body
        step_execution.response_size_bytes = response_size_bytes
        step_execution.extracted_variables = extracted_variables or {}
        step_execution.condition_met = condition_met
        step_execution.condition_details = condition_details
        step_execution.error_message = error_message
        step_execution.error_type = error_type
        step_execution.retry_attempt = retry_attempt
        await self.db.flush()
        await self.db.refresh(step_execution)
        return step_execution

    async def mark_as_skipped(
        self,
        chain_execution_id: UUID,
        step_id: UUID | None,
        step_order: int,
        step_name: str,
        request_url: str,
        request_method: str,
        condition_details: str | None = None,
    ) -> StepExecution:
        """Create a skipped step execution record."""
        from app.models.cron_task import HttpMethod

        step_execution = StepExecution(
            chain_execution_id=chain_execution_id,
            step_id=step_id,
            step_order=step_order,
            step_name=step_name,
            status=StepStatus.SKIPPED,
            started_at=None,
            finished_at=None,
            request_url=request_url,
            request_method=HttpMethod(request_method),
            condition_met=False,
            condition_details=condition_details,
        )
        self.db.add(step_execution)
        await self.db.flush()
        await self.db.refresh(step_execution)
        return step_execution

"""Repository for task chain operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.task_chain import ChainStatus, ChainStep, TaskChain, TriggerType
from app.models.workspace import Workspace


class TaskChainRepository(BaseRepository[TaskChain]):
    """Repository for task chain operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(TaskChain, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[TaskChain]:
        """Get all task chains for a workspace."""
        stmt = select(TaskChain).where(TaskChain.workspace_id == workspace_id).order_by(TaskChain.created_at.desc())
        if is_active is not None:
            stmt = stmt.where(TaskChain.is_active == is_active)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        is_active: bool | None = None,
    ) -> int:
        """Count task chains for a workspace."""
        stmt = select(func.count()).select_from(TaskChain).where(TaskChain.workspace_id == workspace_id)
        if is_active is not None:
            stmt = stmt.where(TaskChain.is_active == is_active)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_with_steps(self, chain_id: UUID) -> TaskChain | None:
        """Get a task chain with its steps loaded."""
        stmt = select(TaskChain).options(selectinload(TaskChain.steps)).where(TaskChain.id == chain_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_chains(self, now: datetime, limit: int = 100) -> list[TaskChain]:
        """Get chains due for execution.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions.
        Excludes chains from blocked workspaces.
        """
        stmt = (
            select(TaskChain)
            .join(Workspace, TaskChain.workspace_id == Workspace.id)
            .options(selectinload(TaskChain.steps))
            .where(
                and_(
                    TaskChain.is_active.is_(True),
                    TaskChain.is_paused.is_(False),
                    TaskChain.trigger_type.in_([TriggerType.CRON, TriggerType.DELAYED]),
                    TaskChain.next_run_at <= now,
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(TaskChain.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_chains_needing_next_run_update(self, limit: int = 100) -> list[TaskChain]:
        """Get active cron chains that need next_run_at calculated."""
        stmt = (
            select(TaskChain)
            .where(
                and_(
                    TaskChain.is_active.is_(True),
                    TaskChain.is_paused.is_(False),
                    TaskChain.trigger_type == TriggerType.CRON,
                    TaskChain.next_run_at.is_(None),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_last_run(
        self,
        chain: TaskChain,
        status: ChainStatus,
        run_at: datetime,
        next_run_at: datetime | None,
    ) -> TaskChain:
        """Update chain after execution."""
        chain.last_run_at = run_at
        chain.last_status = status
        chain.next_run_at = next_run_at

        if status == ChainStatus.SUCCESS:
            chain.consecutive_failures = 0
        elif status in (ChainStatus.FAILED, ChainStatus.PARTIAL):
            chain.consecutive_failures += 1

        # For delayed triggers, deactivate after execution
        if chain.trigger_type == TriggerType.DELAYED:
            chain.is_active = False

        await self.db.flush()
        await self.db.refresh(chain)
        return chain

    async def pause(self, chain: TaskChain) -> TaskChain:
        """Pause a chain."""
        chain.is_paused = True
        await self.db.flush()
        await self.db.refresh(chain)
        return chain

    async def resume(self, chain: TaskChain, next_run_at: datetime | None) -> TaskChain:
        """Resume a chain."""
        chain.is_paused = False
        if next_run_at:
            chain.next_run_at = next_run_at
        await self.db.flush()
        await self.db.refresh(chain)
        return chain

    async def deactivate(self, chain: TaskChain) -> TaskChain:
        """Deactivate a chain."""
        chain.is_active = False
        chain.next_run_at = None
        await self.db.flush()
        await self.db.refresh(chain)
        return chain

    async def copy(self, chain: TaskChain, new_name: str) -> TaskChain:
        """Create a copy of a chain with its steps."""
        # Load steps if not already loaded
        chain_with_steps = await self.get_with_steps(chain.id)
        if not chain_with_steps:
            raise ValueError("Chain not found")

        # Create new chain
        new_chain = TaskChain(
            workspace_id=chain.workspace_id,
            worker_id=chain.worker_id,
            name=new_name,
            description=chain.description,
            tags=chain.tags.copy() if chain.tags else [],
            trigger_type=TriggerType.MANUAL,  # Always start as manual
            schedule=chain.schedule,
            timezone=chain.timezone,
            stop_on_failure=chain.stop_on_failure,
            timeout_seconds=chain.timeout_seconds,
            notify_on_failure=chain.notify_on_failure,
            notify_on_success=chain.notify_on_success,
            notify_on_partial=chain.notify_on_partial,
            is_active=True,
            is_paused=False,
        )
        self.db.add(new_chain)
        await self.db.flush()

        # Copy steps
        for step in chain_with_steps.steps:
            new_step = ChainStep(
                chain_id=new_chain.id,
                step_order=step.step_order,
                name=step.name,
                url=step.url,
                method=step.method,
                headers=step.headers.copy() if step.headers else {},
                body=step.body,
                timeout_seconds=step.timeout_seconds,
                retry_count=step.retry_count,
                retry_delay_seconds=step.retry_delay_seconds,
                condition=step.condition.copy() if step.condition else None,
                extract_variables=step.extract_variables.copy() if step.extract_variables else {},
                continue_on_failure=step.continue_on_failure,
            )
            self.db.add(new_step)

        await self.db.flush()
        await self.db.refresh(new_chain)
        return new_chain


class ChainStepRepository(BaseRepository[ChainStep]):
    """Repository for chain step operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ChainStep, db)

    async def get_by_chain(self, chain_id: UUID) -> list[ChainStep]:
        """Get all steps for a chain, ordered by step_order."""
        stmt = select(ChainStep).where(ChainStep.chain_id == chain_id).order_by(ChainStep.step_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_max_step_order(self, chain_id: UUID) -> int:
        """Get the maximum step order for a chain."""
        stmt = select(func.max(ChainStep.step_order)).where(ChainStep.chain_id == chain_id)
        result = await self.db.execute(stmt)
        max_order = result.scalar_one_or_none()
        return max_order if max_order is not None else -1

    async def count_by_chain(self, chain_id: UUID) -> int:
        """Count steps for a chain."""
        stmt = select(func.count()).select_from(ChainStep).where(ChainStep.chain_id == chain_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def reorder_steps(self, chain_id: UUID, step_orders: list[dict]) -> None:
        """Reorder steps in a chain.

        Args:
            chain_id: The chain ID
            step_orders: List of {"step_id": UUID, "step_order": int}
        """
        for item in step_orders:
            stmt = (
                update(ChainStep)
                .where(
                    and_(
                        ChainStep.chain_id == chain_id,
                        ChainStep.id == item["step_id"],
                    )
                )
                .values(step_order=item["step_order"])
            )
            await self.db.execute(stmt)
        await self.db.flush()

    async def delete_by_chain(self, chain_id: UUID) -> int:
        """Delete all steps for a chain."""
        stmt = delete(ChainStep).where(ChainStep.chain_id == chain_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

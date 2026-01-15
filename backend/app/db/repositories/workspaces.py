from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.plan import Plan
from app.models.workspace import Workspace


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository for workspace operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Workspace, db)

    async def get_by_slug(self, slug: str) -> Workspace | None:
        """Get workspace by slug."""
        stmt = select(Workspace).where(Workspace.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Workspace]:
        """Get all workspaces for an owner."""
        stmt = (
            select(Workspace)
            .where(Workspace.owner_id == owner_id)
            .order_by(Workspace.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count workspaces for an owner."""
        stmt = select(func.count()).select_from(Workspace).where(Workspace.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_with_plan(self, workspace_id: UUID) -> Workspace | None:
        """Get workspace with plan eagerly loaded."""
        stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.plan))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def slug_exists(
        self, slug: str, owner_id: UUID, exclude_id: UUID | None = None
    ) -> bool:
        """Check if slug already exists for the given owner."""
        stmt = select(Workspace.id).where(
            Workspace.slug == slug,
            Workspace.owner_id == owner_id,
        )
        if exclude_id:
            stmt = stmt.where(Workspace.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_cron_tasks_count(self, workspace: Workspace, delta: int) -> Workspace:
        """Update cron tasks count by delta."""
        workspace.cron_tasks_count = max(0, workspace.cron_tasks_count + delta)
        await self.db.flush()
        await self.db.refresh(workspace)
        return workspace

    async def increment_delayed_tasks_count(self, workspace: Workspace) -> Workspace:
        """Increment delayed tasks count for current month."""
        workspace.delayed_tasks_this_month += 1
        await self.db.flush()
        await self.db.refresh(workspace)
        return workspace

    async def reset_monthly_delayed_count(self, workspace_id: UUID) -> None:
        """Reset delayed tasks counter (called at month start)."""
        workspace = await self.get_by_id(workspace_id)
        if workspace:
            workspace.delayed_tasks_this_month = 0
            await self.db.flush()

    async def get_best_plan_for_owner(self, owner_id: UUID) -> Plan | None:
        """Get the best plan among all owner's workspaces (by max_workspaces limit)."""
        stmt = (
            select(Plan)
            .join(Workspace, Workspace.plan_id == Plan.id)
            .where(Workspace.owner_id == owner_id)
            .order_by(Plan.max_workspaces.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

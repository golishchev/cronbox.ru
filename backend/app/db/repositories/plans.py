from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.plan import Plan


class PlanRepository(BaseRepository[Plan]):
    """Repository for plan operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Plan, db)

    async def get_by_name(self, name: str) -> Plan | None:
        """Get plan by name."""
        stmt = select(Plan).where(Plan.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_free_plan(self) -> Plan | None:
        """Get the free plan."""
        return await self.get_by_name("free")

    async def get_public_plans(self) -> list[Plan]:
        """Get all public active plans."""
        stmt = select(Plan).where(Plan.is_active.is_(True), Plan.is_public.is_(True)).order_by(Plan.sort_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def ensure_free_plan_exists(self) -> Plan:
        """Ensure free plan exists, create if not."""
        plan = await self.get_free_plan()
        if plan is None:
            plan = await self.create(
                name="free",
                display_name="Free",
                description="Free plan with basic features",
                price_monthly=0,
                price_yearly=0,
                max_cron_tasks=5,
                max_delayed_tasks_per_month=100,
                max_workspaces=1,
                max_execution_history_days=7,
                min_cron_interval_minutes=5,
                telegram_notifications=False,
                email_notifications=False,
                webhook_callbacks=False,
                custom_headers=True,
                retry_on_failure=False,
                is_active=True,
                is_public=True,
                sort_order=0,
            )
        return plan

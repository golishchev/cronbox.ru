"""Billing service for YooKassa integration."""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.payment import Payment, PaymentStatus
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.workspace import Workspace

logger = structlog.get_logger()


class BillingService:
    """Service for managing subscriptions and payments via YooKassa."""

    def __init__(self):
        self.shop_id = settings.yookassa_shop_id
        self.secret_key = settings.yookassa_secret_key
        self.base_url = "https://api.yookassa.ru/v3"

    @property
    def is_configured(self) -> bool:
        return bool(self.shop_id and self.secret_key)

    def _get_auth(self) -> tuple[str, str]:
        return (self.shop_id, self.secret_key)

    async def get_plans(self, db: AsyncSession, only_public: bool = True) -> list[Plan]:
        """Get all available plans."""
        query = select(Plan).where(Plan.is_active.is_(True))
        if only_public:
            query = query.where(Plan.is_public.is_(True))
        query = query.order_by(Plan.sort_order)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_plan_by_name(self, db: AsyncSession, name: str) -> Plan | None:
        """Get a plan by name."""
        result = await db.execute(select(Plan).where(Plan.name == name))
        return result.scalar_one_or_none()

    async def get_plan_by_id(self, db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
        """Get a plan by ID."""
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def get_user_subscription(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Subscription | None:
        """Get user's subscription."""
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_plan(self, db: AsyncSession, user_id: uuid.UUID) -> Plan:
        """Get user's current plan (from subscription or free)."""
        subscription = await self.get_user_subscription(db, user_id)
        if subscription and subscription.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
        ):
            plan = await self.get_plan_by_id(db, subscription.plan_id)
            if plan:
                return plan
        # Fallback to free plan
        free_plan = await self.get_plan_by_name(db, "free")
        if not free_plan:
            raise RuntimeError("Free plan not found in database")
        return free_plan

    async def create_payment(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_period: str = "monthly",  # 'monthly' or 'yearly'
        return_url: str | None = None,
    ) -> Payment | None:
        """Create a payment for subscription."""
        if not self.is_configured:
            logger.warning("YooKassa not configured")
            return None

        # Get plan
        plan = await self.get_plan_by_id(db, plan_id)
        if not plan:
            logger.error("Plan not found", plan_id=plan_id)
            return None

        # Calculate amount
        amount = plan.price_yearly if billing_period == "yearly" else plan.price_monthly
        if amount == 0:
            logger.error("Cannot create payment for free plan")
            return None

        # Get user's first workspace for payment association
        workspace_result = await db.execute(
            select(Workspace)
            .where(Workspace.owner_id == user_id)
            .order_by(Workspace.created_at.asc())
            .limit(1)
        )
        workspace = workspace_result.scalar_one_or_none()
        if not workspace:
            logger.error("User has no workspace", user_id=user_id)
            return None

        # Convert kopeks to rubles for YooKassa
        amount_value = f"{amount / 100:.2f}"

        # Create payment record
        payment = Payment(
            workspace_id=workspace.id,
            user_id=user_id,
            amount=amount,
            currency="RUB",
            status=PaymentStatus.PENDING,
            description=f"Subscription: {plan.display_name} ({billing_period})",
            extra_data={
                "plan_id": str(plan_id),
                "billing_period": billing_period,
                "user_id": str(user_id),
            },
        )
        db.add(payment)
        await db.flush()

        # Create YooKassa payment
        idempotence_key = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    auth=self._get_auth(),
                    headers={
                        "Idempotence-Key": idempotence_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "amount": {
                            "value": amount_value,
                            "currency": "RUB",
                        },
                        "capture": True,
                        "confirmation": {
                            "type": "redirect",
                            "return_url": return_url or f"{settings.cors_origins[0]}/billing",
                        },
                        "description": payment.description,
                        "metadata": {
                            "payment_id": str(payment.id),
                            "user_id": str(user_id),
                            "plan_id": str(plan_id),
                            "billing_period": billing_period,
                        },
                        "save_payment_method": True,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                yookassa_data = response.json()

                # Update payment with YooKassa data
                payment.yookassa_payment_id = yookassa_data["id"]
                payment.yookassa_confirmation_url = yookassa_data.get(
                    "confirmation", {}
                ).get("confirmation_url")

                await db.commit()
                logger.info(
                    "Payment created",
                    payment_id=str(payment.id),
                    yookassa_id=payment.yookassa_payment_id,
                )
                return payment

        except Exception as e:
            logger.error("Failed to create YooKassa payment", error=str(e))
            await db.rollback()
            return None

    async def handle_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        payment_data: dict,
    ) -> bool:
        """Handle YooKassa webhook notification."""
        yookassa_payment_id = payment_data.get("id")
        if not yookassa_payment_id:
            logger.error("No payment ID in webhook")
            return False

        # Find payment
        result = await db.execute(
            select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning("Payment not found", yookassa_id=yookassa_payment_id)
            return False

        if event_type == "payment.succeeded":
            return await self._handle_payment_succeeded(db, payment, payment_data)
        elif event_type == "payment.canceled":
            return await self._handle_payment_cancelled(db, payment)
        elif event_type == "refund.succeeded":
            return await self._handle_refund_succeeded(db, payment)

        return True

    async def _handle_payment_succeeded(
        self,
        db: AsyncSession,
        payment: Payment,
        payment_data: dict,
    ) -> bool:
        """Handle successful payment."""
        # Idempotency: Check if payment already processed
        if payment.status == PaymentStatus.SUCCEEDED:
            logger.info(
                "Payment already processed (idempotent)",
                payment_id=str(payment.id),
            )
            return True

        if payment.status != PaymentStatus.PENDING:
            logger.warning(
                "Invalid payment status for succeeded event",
                payment_id=str(payment.id),
                current_status=payment.status.value,
            )
            return False

        # Validate amount matches our records
        webhook_amount = payment_data.get("amount", {})
        webhook_amount_value = webhook_amount.get("value", "0")
        webhook_currency = webhook_amount.get("currency", "")

        try:
            webhook_amount_kopeks = int(float(webhook_amount_value) * 100)
        except (ValueError, TypeError):
            logger.error(
                "Invalid amount format in webhook",
                payment_id=str(payment.id),
                webhook_amount=webhook_amount_value,
            )
            return False

        if webhook_amount_kopeks != payment.amount:
            logger.error(
                "Amount mismatch in webhook",
                payment_id=str(payment.id),
                expected_amount=payment.amount,
                webhook_amount=webhook_amount_kopeks,
            )
            return False

        if webhook_currency != payment.currency:
            logger.error(
                "Currency mismatch in webhook",
                payment_id=str(payment.id),
                expected_currency=payment.currency,
                webhook_currency=webhook_currency,
            )
            return False

        # Update payment
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.now(timezone.utc)

        # Save payment method for recurring payments
        payment_method = payment_data.get("payment_method")
        if payment_method:
            payment.yookassa_payment_method = {
                "id": payment_method.get("id"),
                "type": payment_method.get("type"),
                "saved": payment_method.get("saved"),
            }

        # Get plan info from extra_data
        extra_data = payment.extra_data or {}
        plan_id = extra_data.get("plan_id")
        billing_period = extra_data.get("billing_period", "monthly")
        user_id = extra_data.get("user_id") or (str(payment.user_id) if payment.user_id else None)

        if plan_id and user_id:
            # Create or update subscription
            await self._create_or_update_subscription(
                db,
                user_id=uuid.UUID(user_id),
                plan_id=uuid.UUID(plan_id),
                billing_period=billing_period,
                payment_method_id=payment_method.get("id") if payment_method else None,
            )

        await db.commit()
        logger.info("Payment succeeded", payment_id=str(payment.id))
        return True

    async def _handle_payment_cancelled(
        self,
        db: AsyncSession,
        payment: Payment,
    ) -> bool:
        """Handle cancelled payment."""
        payment.status = PaymentStatus.CANCELLED
        await db.commit()
        logger.info("Payment cancelled", payment_id=str(payment.id))
        return True

    async def _handle_refund_succeeded(
        self,
        db: AsyncSession,
        payment: Payment,
    ) -> bool:
        """Handle successful refund."""
        payment.status = PaymentStatus.REFUNDED
        await db.commit()
        logger.info("Payment refunded", payment_id=str(payment.id))
        return True

    async def _create_or_update_subscription(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_period: str,
        payment_method_id: str | None = None,
    ) -> Subscription:
        """Create or update user subscription."""
        now = datetime.now(timezone.utc)

        # Calculate period
        if billing_period == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        # Get existing subscription
        subscription = await self.get_user_subscription(db, user_id)

        if subscription:
            # Update existing subscription
            subscription.plan_id = plan_id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = now
            subscription.current_period_end = period_end
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            if payment_method_id:
                subscription.yookassa_payment_method_id = payment_method_id
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=period_end,
                yookassa_payment_method_id=payment_method_id,
            )
            db.add(subscription)

        # Unblock user's workspaces on upgrade
        plan = await self.get_plan_by_id(db, plan_id)
        if plan:
            await self._unblock_user_workspaces(db, user_id, plan.max_workspaces)

        await db.flush()
        logger.info(
            "Subscription created/updated",
            user_id=str(user_id),
            plan_id=str(plan_id),
        )
        return subscription

    async def cancel_subscription(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        immediately: bool = False,
    ) -> bool:
        """Cancel a user's subscription."""
        subscription = await self.get_user_subscription(db, user_id)
        if not subscription:
            return False

        if immediately:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.now(timezone.utc)

            # Block excess workspaces and pause tasks
            free_plan = await self.get_plan_by_name(db, "free")
            if free_plan:
                await self._block_excess_workspaces(db, user_id, free_plan.max_workspaces)
                # Pause excess tasks in the first (active) workspace
                first_workspace = await self._get_oldest_workspace(db, user_id)
                if first_workspace:
                    await self.auto_pause_excess_tasks(
                        db, first_workspace.id, free_plan.max_cron_tasks
                    )
        else:
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(
            "Subscription cancelled",
            user_id=str(user_id),
            immediately=immediately,
        )
        return True

    async def _get_oldest_workspace(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Workspace | None:
        """Get user's oldest workspace by created_at."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.owner_id == user_id)
            .order_by(Workspace.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _block_excess_workspaces(
        self, db: AsyncSession, user_id: uuid.UUID, max_workspaces: int
    ) -> list[uuid.UUID]:
        """Block workspaces exceeding the limit. Returns list of blocked workspace IDs."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.owner_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
        workspaces = list(result.scalars().all())

        blocked_ids = []
        now = datetime.now(timezone.utc)

        for i, workspace in enumerate(workspaces):
            if i < max_workspaces:
                # Keep active (unblock if was blocked)
                if workspace.is_blocked:
                    workspace.is_blocked = False
                    workspace.blocked_at = None
                    # Resume paused tasks
                    await self._resume_workspace_tasks(db, workspace.id)
            else:
                # Block excess workspaces
                if not workspace.is_blocked:
                    workspace.is_blocked = True
                    workspace.blocked_at = now
                    blocked_ids.append(workspace.id)
                    # Pause all tasks
                    await self._pause_workspace_tasks(db, workspace.id)
                    logger.info(
                        "Workspace blocked",
                        workspace_id=str(workspace.id),
                        user_id=str(user_id),
                    )

        return blocked_ids

    async def _unblock_user_workspaces(
        self, db: AsyncSession, user_id: uuid.UUID, max_workspaces: int
    ) -> int:
        """Unblock workspaces up to the plan limit. Returns count of unblocked."""
        # Count currently active workspaces
        active_count_result = await db.execute(
            select(func.count())
            .select_from(Workspace)
            .where(
                Workspace.owner_id == user_id,
                Workspace.is_blocked.is_(False),
            )
        )
        active_count = active_count_result.scalar_one()

        can_unblock = max_workspaces - active_count
        if can_unblock <= 0:
            return 0

        # Get blocked workspaces ordered by created_at
        result = await db.execute(
            select(Workspace)
            .where(
                Workspace.owner_id == user_id,
                Workspace.is_blocked.is_(True),
            )
            .order_by(Workspace.created_at.asc())
            .limit(can_unblock)
        )
        blocked_workspaces = list(result.scalars().all())

        unblocked = 0
        for workspace in blocked_workspaces:
            workspace.is_blocked = False
            workspace.blocked_at = None
            await self._resume_workspace_tasks(db, workspace.id)
            unblocked += 1
            logger.info(
                "Workspace unblocked",
                workspace_id=str(workspace.id),
                user_id=str(user_id),
            )

        return unblocked

    async def _pause_workspace_tasks(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> int:
        """Pause all active cron tasks in a workspace."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        cron_repo = CronTaskRepository(db)
        active_tasks = await cron_repo.get_by_workspace(
            workspace_id=workspace_id,
            is_active=True,
            limit=1000,
        )

        count = 0
        for task in active_tasks:
            if not task.is_paused:
                await cron_repo.pause(task)
                count += 1
                logger.info(
                    "Task paused (workspace blocked)",
                    task_id=str(task.id),
                    workspace_id=str(workspace_id),
                )

        return count

    async def _resume_workspace_tasks(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> int:
        """Resume paused tasks in a workspace."""
        from app.db.repositories.cron_tasks import CronTaskRepository
        from app.workers.utils import calculate_next_run

        cron_repo = CronTaskRepository(db)
        tasks = await cron_repo.get_by_workspace(
            workspace_id=workspace_id,
            is_active=True,
            limit=1000,
        )

        count = 0
        for task in tasks:
            if task.is_paused:
                next_run = calculate_next_run(task.schedule, task.timezone)
                await cron_repo.resume(task, next_run)
                count += 1
                logger.info(
                    "Task resumed (workspace unblocked)",
                    task_id=str(task.id),
                    workspace_id=str(workspace_id),
                )

        return count

    async def get_payment_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Payment]:
        """Get payment history for a user."""
        result = await db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_expiring_subscriptions(
        self, db: AsyncSession, days_before: int
    ) -> list[Subscription]:
        """Get subscriptions expiring in exactly N days (within that day)."""
        now = datetime.now(timezone.utc)
        target_date = now + timedelta(days=days_before)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.current_period_end >= start_of_day,
                Subscription.current_period_end < end_of_day,
            )
        )
        return list(result.scalars().all())

    async def auto_pause_excess_tasks(
        self, db: AsyncSession, workspace_id: uuid.UUID, max_tasks: int
    ) -> int:
        """Pause cron tasks exceeding the limit. Returns count of paused tasks."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        cron_repo = CronTaskRepository(db)
        # Get all active, non-paused tasks
        active_tasks = await cron_repo.get_by_workspace(
            workspace_id=workspace_id,
            is_active=True,
            limit=1000,
        )
        # Filter to only non-paused tasks
        non_paused_tasks = [t for t in active_tasks if not t.is_paused]

        if len(non_paused_tasks) <= max_tasks:
            return 0

        # Sort by created_at, keep oldest tasks active
        sorted_tasks = sorted(non_paused_tasks, key=lambda t: t.created_at)
        tasks_to_pause = sorted_tasks[max_tasks:]

        count = 0
        for task in tasks_to_pause:
            await cron_repo.pause(task)
            count += 1
            logger.info(
                "Task auto-paused due to plan limit",
                task_id=str(task.id),
                workspace_id=str(workspace_id),
            )

        return count

    async def check_expired_subscriptions(
        self, db: AsyncSession
    ) -> list[tuple[uuid.UUID, int, int]]:
        """Check and mark expired subscriptions.

        Returns list of (user_id, paused_tasks_count, blocked_workspaces_count).
        """
        now = datetime.now(timezone.utc)

        # Find active subscriptions that have expired
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.current_period_end < now,
            )
        )
        subscriptions = result.scalars().all()

        affected_users: list[tuple[uuid.UUID, int, int]] = []
        free_plan = await self.get_plan_by_name(db, "free")

        for subscription in subscriptions:
            if subscription.cancel_at_period_end:
                subscription.status = SubscriptionStatus.CANCELLED
            else:
                subscription.status = SubscriptionStatus.EXPIRED

            paused_count = 0
            blocked_count = 0

            if free_plan:
                # Block excess workspaces
                blocked_ids = await self._block_excess_workspaces(
                    db, subscription.user_id, free_plan.max_workspaces
                )
                blocked_count = len(blocked_ids)

                # Pause excess tasks in first (active) workspace
                first_workspace = await self._get_oldest_workspace(db, subscription.user_id)
                if first_workspace:
                    paused_count = await self.auto_pause_excess_tasks(
                        db, first_workspace.id, free_plan.max_cron_tasks
                    )

            affected_users.append((subscription.user_id, paused_count, blocked_count))

        if affected_users:
            await db.commit()
            logger.info(
                "Expired subscriptions processed",
                count=len(affected_users),
            )

        return affected_users


# Global instance
billing_service = BillingService()

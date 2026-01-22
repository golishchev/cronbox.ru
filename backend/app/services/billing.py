"""Billing service for YooKassa integration."""

import json
import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import redis_client
from app.models.payment import Payment, PaymentStatus
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.services.i18n import t

logger = structlog.get_logger()


def _get_billing_description(plan_name: str, billing_period: str, lang: str, is_auto_renewal: bool = False) -> str:
    """Get localized billing description."""
    period_key = f"billing.period.{billing_period}"
    period_localized = t(period_key, lang)

    if is_auto_renewal:
        return t("billing.auto_renewal", lang, plan_name=plan_name, period=period_localized)
    return t("billing.subscription", lang, plan_name=plan_name, period=period_localized)


def _get_receipt_description(plan_name: str, billing_period: str, lang: str) -> str:
    """Get localized receipt item description."""
    period_key = f"billing.period.{billing_period}"
    period_localized = t(period_key, lang)
    return t("billing.receipt_item", lang, plan_name=plan_name, period=period_localized)


# Cache key for public plans
PLANS_CACHE_KEY = "cache:plans:public"
PLANS_CACHE_TTL = 3600  # 1 hour


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
        """Get all available plans with Redis caching for public plans."""
        # Try cache for public plans only
        if only_public:
            try:
                cached = await redis_client.get(PLANS_CACHE_KEY)
                if cached:
                    plans_data = json.loads(cached)
                    # Reconstruct Plan objects from cached data
                    plans = []
                    for data in plans_data:
                        # Convert id string to UUID
                        data["id"] = UUID(data["id"])
                        plan = Plan(**data)
                        plans.append(plan)
                    return plans
            except Exception as e:
                logger.warning("Failed to get plans from cache", error=str(e))

        # Fetch from database
        query = select(Plan).where(Plan.is_active.is_(True))
        if only_public:
            query = query.where(Plan.is_public.is_(True))
        query = query.order_by(Plan.sort_order)
        result = await db.execute(query)
        plans = list(result.scalars().all())

        # Cache public plans
        if only_public and plans:
            try:
                plans_data = [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "display_name": p.display_name,
                        "description": p.description,
                        "price_monthly": p.price_monthly,
                        "price_yearly": p.price_yearly,
                        "max_cron_tasks": p.max_cron_tasks,
                        "max_delayed_tasks_per_month": p.max_delayed_tasks_per_month,
                        "max_workspaces": p.max_workspaces,
                        "max_execution_history_days": p.max_execution_history_days,
                        "min_cron_interval_minutes": p.min_cron_interval_minutes,
                        "telegram_notifications": p.telegram_notifications,
                        "email_notifications": p.email_notifications,
                        "webhook_callbacks": p.webhook_callbacks,
                        "custom_headers": p.custom_headers,
                        "retry_on_failure": p.retry_on_failure,
                        # Task chain limits
                        "max_task_chains": p.max_task_chains,
                        "max_chain_steps": p.max_chain_steps,
                        "chain_variable_substitution": p.chain_variable_substitution,
                        "min_chain_interval_minutes": p.min_chain_interval_minutes,
                        # Heartbeat monitor limits
                        "max_heartbeats": p.max_heartbeats,
                        "min_heartbeat_interval_minutes": p.min_heartbeat_interval_minutes,
                        # SSL monitor limits
                        "max_ssl_monitors": p.max_ssl_monitors,
                        # Process monitor limits
                        "max_process_monitors": p.max_process_monitors,
                        "min_process_monitor_interval_minutes": p.min_process_monitor_interval_minutes,
                        # Overlap prevention settings
                        "overlap_prevention_enabled": p.overlap_prevention_enabled,
                        "max_queue_size": p.max_queue_size,
                        "is_active": p.is_active,
                        "is_public": p.is_public,
                        "sort_order": p.sort_order,
                    }
                    for p in plans
                ]
                await redis_client.set(PLANS_CACHE_KEY, json.dumps(plans_data), expire=PLANS_CACHE_TTL)
            except Exception as e:
                logger.warning("Failed to cache plans", error=str(e))

        return plans

    async def invalidate_plans_cache(self) -> None:
        """Invalidate the plans cache. Call this after any plan modification."""
        try:
            await redis_client.delete(PLANS_CACHE_KEY)
            logger.info("Plans cache invalidated")
        except Exception as e:
            logger.warning("Failed to invalidate plans cache", error=str(e))

    async def get_plan_by_name(self, db: AsyncSession, name: str) -> Plan | None:
        """Get a plan by name."""
        result = await db.execute(select(Plan).where(Plan.name == name))
        return result.scalar_one_or_none()

    async def get_plan_by_id(self, db: AsyncSession, plan_id: uuid_module.UUID) -> Plan | None:
        """Get a plan by ID."""
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def get_user_subscription(self, db: AsyncSession, user_id: uuid_module.UUID) -> Subscription | None:
        """Get user's subscription."""
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_user_subscription_for_update(
        self, db: AsyncSession, user_id: uuid_module.UUID
    ) -> Subscription | None:
        """Get user's subscription with row-level lock (FOR UPDATE).

        Use this method when modifying subscription to prevent race conditions.
        The lock is held until the transaction commits or rolls back.
        """
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
        return result.scalar_one_or_none()

    async def get_user_plan(self, db: AsyncSession, user_id: uuid_module.UUID) -> Plan:
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
        user_id: uuid_module.UUID,
        plan_id: uuid_module.UUID,
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

        # Calculate base amount for new plan
        new_plan_amount = plan.price_yearly if billing_period == "yearly" else plan.price_monthly
        if new_plan_amount == 0:
            logger.error("Cannot create payment for free plan")
            return None

        # Calculate proration credit from current subscription
        # Use FOR UPDATE lock to prevent race conditions with parallel upgrade requests
        proration_credit = 0
        current_subscription = await self.get_user_subscription_for_update(db, user_id)
        if current_subscription and current_subscription.status == SubscriptionStatus.ACTIVE:
            # Re-validate plan change inside lock to prevent TOCTOU race condition
            # (subscription could have changed between API validation and this point)
            analysis = await self._analyze_plan_change(db, current_subscription, plan_id, billing_period)
            if analysis["is_same_plan"]:
                logger.warning(
                    "Plan change rejected: already on this plan",
                    user_id=str(user_id),
                    plan_id=str(plan_id),
                )
                return None
            if analysis["requires_deferred"]:
                logger.warning(
                    "Plan change rejected: requires deferred change",
                    user_id=str(user_id),
                    plan_id=str(plan_id),
                )
                return None

            proration_credit = analysis.get("proration_credit", 0)
            logger.info(
                "Proration credit calculated",
                user_id=str(user_id),
                credit=proration_credit,
            )

        # Final amount after proration
        amount = max(new_plan_amount - proration_credit, 100)  # Minimum 1 RUB (100 kopeks)

        # Get user for email (required for receipt)
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.error("User not found", user_id=user_id)
            return None
        user_email = user.email
        user_lang = user.preferred_language or "ru"

        # Get user's first workspace for payment association
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc()).limit(1)
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
            description=_get_billing_description(plan.display_name, billing_period, user_lang),
            extra_data={
                "plan_id": str(plan_id),
                "billing_period": billing_period,
                "user_id": str(user_id),
                "new_plan_amount": new_plan_amount,
                "proration_credit": proration_credit,
            },
        )
        db.add(payment)
        await db.flush()

        # Create YooKassa payment
        idempotence_key = str(uuid_module.uuid4())
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
                        "receipt": {
                            "customer": {
                                "email": user_email,
                            },
                            "items": [
                                {
                                    "description": _get_receipt_description(
                                        plan.display_name, billing_period, user_lang
                                    ),
                                    "quantity": "1",
                                    "amount": {
                                        "value": amount_value,
                                        "currency": "RUB",
                                    },
                                    "vat_code": 1,
                                    "payment_mode": "full_payment",
                                    "payment_subject": "service",
                                }
                            ],
                        },
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                yookassa_data = response.json()

                # Update payment with YooKassa data
                payment.yookassa_payment_id = yookassa_data["id"]
                payment.yookassa_confirmation_url = yookassa_data.get("confirmation", {}).get("confirmation_url")

                await db.commit()
                logger.info(
                    "Payment created",
                    payment_id=str(payment.id),
                    yookassa_id=payment.yookassa_payment_id,
                )
                return payment

        except httpx.HTTPStatusError as e:
            logger.error(
                "YooKassa API error",
                error=str(e),
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
            await db.rollback()
            return None
        except Exception as e:
            logger.error("Failed to create YooKassa payment", error=str(e), error_type=type(e).__name__)
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
        result = await db.execute(select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id))
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
                user_id=uuid_module.UUID(user_id),
                plan_id=uuid_module.UUID(plan_id),
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
        user_id: uuid_module.UUID,
        plan_id: uuid_module.UUID,
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

        # Get existing subscription with lock to prevent race conditions
        subscription = await self.get_user_subscription_for_update(db, user_id)

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
        user_id: uuid_module.UUID,
        immediately: bool = False,
    ) -> bool:
        """Cancel a user's subscription."""
        subscription = await self.get_user_subscription_for_update(db, user_id)
        if not subscription:
            return False

        # Clear any scheduled plan change when cancelling
        subscription.scheduled_plan_id = None
        subscription.scheduled_billing_period = None

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
                    await self.auto_pause_excess_tasks(db, first_workspace.id, free_plan.max_cron_tasks)
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

    async def schedule_plan_change(
        self,
        db: AsyncSession,
        user_id: uuid_module.UUID,
        new_plan_id: uuid_module.UUID,
        new_billing_period: str,
    ) -> Subscription | None:
        """
        Schedule a plan change for the end of current billing period.

        Used for downgrades and yearly→monthly transitions.
        """
        subscription = await self.get_user_subscription_for_update(db, user_id)
        if not subscription:
            logger.warning("No subscription to schedule change", user_id=str(user_id))
            return None

        if subscription.status != SubscriptionStatus.ACTIVE:
            logger.warning(
                "Cannot schedule change for non-active subscription",
                user_id=str(user_id),
                status=subscription.status,
            )
            return None

        # Verify plan exists
        new_plan = await self.get_plan_by_id(db, new_plan_id)
        if not new_plan:
            logger.error("Plan not found for scheduled change", plan_id=str(new_plan_id))
            return None

        # Re-validate plan change inside lock to prevent TOCTOU race condition
        analysis = await self._analyze_plan_change(db, subscription, new_plan_id, new_billing_period)
        if analysis["is_same_plan"]:
            logger.warning(
                "Schedule rejected: already on this plan",
                user_id=str(user_id),
                plan_id=str(new_plan_id),
            )
            return None

        # Set scheduled change and clear any cancellation
        subscription.scheduled_plan_id = new_plan_id
        subscription.scheduled_billing_period = new_billing_period
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None

        await db.commit()
        logger.info(
            "Plan change scheduled",
            user_id=str(user_id),
            new_plan_id=str(new_plan_id),
            new_billing_period=new_billing_period,
            effective_date=subscription.current_period_end.isoformat(),
        )

        return subscription

    async def cancel_scheduled_plan_change(
        self,
        db: AsyncSession,
        user_id: uuid_module.UUID,
    ) -> bool:
        """Cancel a scheduled plan change."""
        subscription = await self.get_user_subscription_for_update(db, user_id)
        if not subscription:
            return False

        if not subscription.scheduled_plan_id:
            return False

        subscription.scheduled_plan_id = None
        subscription.scheduled_billing_period = None

        await db.commit()
        logger.info("Scheduled plan change cancelled", user_id=str(user_id))

        return True

    async def _calculate_proration_credit(self, db: AsyncSession, subscription: Subscription) -> int:
        """
        Calculate proration credit for unused days of current subscription.

        Returns credit amount in kopeks.
        """
        now = datetime.now(timezone.utc)

        # If subscription already expired, no credit
        if subscription.current_period_end <= now:
            return 0

        # Get current plan price
        current_plan = await self.get_plan_by_id(db, subscription.plan_id)
        if not current_plan:
            return 0

        # Determine billing period based on subscription duration
        period_days = (subscription.current_period_end - subscription.current_period_start).days
        if period_days <= 0:
            return 0

        is_yearly = period_days > 60
        current_plan_price = current_plan.price_yearly if is_yearly else current_plan.price_monthly

        if current_plan_price == 0:
            return 0

        # Calculate remaining days
        remaining_days = (subscription.current_period_end - now).days
        if remaining_days <= 0:
            return 0

        # Calculate daily rate and credit
        daily_rate = current_plan_price / period_days
        credit = int(daily_rate * remaining_days)

        logger.info(
            "Proration calculated",
            subscription_id=str(subscription.id),
            period_days=period_days,
            remaining_days=remaining_days,
            daily_rate=daily_rate,
            credit=credit,
        )

        return credit

    async def _analyze_plan_change(
        self,
        db: AsyncSession,
        current_subscription: Subscription | None,
        new_plan_id: uuid_module.UUID,
        new_billing_period: str,
    ) -> dict:
        """
        Analyze the type of plan change and determine if it requires deferral.

        Returns:
            {
                "is_same_plan": bool,
                "is_downgrade": bool,
                "is_period_downgrade": bool,  # yearly → monthly
                "requires_deferred": bool,
                "proration_credit": int,
                "remaining_days": int,
                "effective_date": datetime | None,
                "current_is_yearly": bool,
            }
        """
        result = {
            "is_same_plan": False,
            "is_downgrade": False,
            "is_period_downgrade": False,
            "requires_deferred": False,
            "proration_credit": 0,
            "remaining_days": 0,
            "effective_date": None,
            "current_is_yearly": False,
        }

        # No current subscription - simple new subscription
        if not current_subscription or current_subscription.status != SubscriptionStatus.ACTIVE:
            return result

        now = datetime.now(timezone.utc)

        # Calculate remaining days
        if current_subscription.current_period_end > now:
            result["remaining_days"] = (current_subscription.current_period_end - now).days
            result["effective_date"] = current_subscription.current_period_end

        # Determine current billing period
        period_days = (current_subscription.current_period_end - current_subscription.current_period_start).days
        current_is_yearly = period_days > 60
        result["current_is_yearly"] = current_is_yearly

        # Check if same plan and same period
        if current_subscription.plan_id == new_plan_id:
            current_period = "yearly" if current_is_yearly else "monthly"
            if current_period == new_billing_period:
                result["is_same_plan"] = True
                return result

        # Get current and new plan prices
        current_plan = await self.get_plan_by_id(db, current_subscription.plan_id)
        new_plan = await self.get_plan_by_id(db, new_plan_id)

        if not current_plan or not new_plan:
            return result

        # Check for period downgrade (yearly → monthly)
        if current_is_yearly and new_billing_period == "monthly":
            result["is_period_downgrade"] = True
            result["requires_deferred"] = True
            return result

        # Check for plan downgrade (new plan is cheaper)
        # Compare normalized prices (per month)
        current_monthly = current_plan.price_monthly
        new_monthly = new_plan.price_monthly

        if new_monthly < current_monthly:
            result["is_downgrade"] = True
            result["requires_deferred"] = True
            return result

        # Upgrade or same price - calculate proration credit
        result["proration_credit"] = await self._calculate_proration_credit(db, current_subscription)

        return result

    async def _get_oldest_workspace(self, db: AsyncSession, user_id: uuid_module.UUID) -> Workspace | None:
        """Get user's oldest workspace by created_at."""
        result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _block_excess_workspaces(
        self, db: AsyncSession, user_id: uuid_module.UUID, max_workspaces: int
    ) -> list[uuid_module.UUID]:
        """Block workspaces exceeding the limit. Returns list of blocked workspace IDs."""
        result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc())
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

    async def _unblock_user_workspaces(self, db: AsyncSession, user_id: uuid_module.UUID, max_workspaces: int) -> int:
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

    async def _pause_workspace_tasks(self, db: AsyncSession, workspace_id: uuid_module.UUID) -> int:
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

    async def _resume_workspace_tasks(self, db: AsyncSession, workspace_id: uuid_module.UUID) -> int:
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
        user_id: uuid_module.UUID,
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

    async def get_expiring_subscriptions(self, db: AsyncSession, days_before: int) -> list[Subscription]:
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

    async def get_subscriptions_for_renewal(self, db: AsyncSession) -> list[Subscription]:
        """
        Get subscriptions that need auto-renewal.

        Returns active subscriptions that:
        - Have expired or expire within the next hour
        - Have a saved payment method
        - Are not marked for cancellation
        """
        now = datetime.now(timezone.utc)
        renewal_window = now + timedelta(hours=1)

        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.current_period_end <= renewal_window,
                Subscription.yookassa_payment_method_id.isnot(None),
                Subscription.cancel_at_period_end.is_(False),
            )
        )
        return list(result.scalars().all())

    async def auto_pause_excess_tasks(self, db: AsyncSession, workspace_id: uuid_module.UUID, max_tasks: int) -> int:
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

    async def check_expired_subscriptions(self, db: AsyncSession) -> list[tuple[uuid_module.UUID, int, int]]:
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

        affected_users: list[tuple[uuid_module.UUID, int, int]] = []
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
                blocked_ids = await self._block_excess_workspaces(db, subscription.user_id, free_plan.max_workspaces)
                blocked_count = len(blocked_ids)

                # Pause excess tasks in first (active) workspace
                first_workspace = await self._get_oldest_workspace(db, subscription.user_id)
                if first_workspace:
                    paused_count = await self.auto_pause_excess_tasks(db, first_workspace.id, free_plan.max_cron_tasks)

            affected_users.append((subscription.user_id, paused_count, blocked_count))

        if affected_users:
            await db.commit()
            logger.info(
                "Expired subscriptions processed",
                count=len(affected_users),
            )

        return affected_users

    async def get_subscriptions_with_scheduled_changes(self, db: AsyncSession) -> list[Subscription]:
        """
        Get subscriptions with scheduled plan changes that should be applied.

        Returns subscriptions that:
        - Have a scheduled_plan_id
        - Current period has ended
        - Status is ACTIVE (don't apply to cancelled/expired subscriptions)
        """
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Subscription).where(
                Subscription.scheduled_plan_id.isnot(None),
                Subscription.current_period_end <= now,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def apply_scheduled_plan_change(
        self,
        db: AsyncSession,
        subscription: Subscription,
    ) -> bool:
        """
        Apply a scheduled plan change.

        This switches the subscription to the new plan without payment
        (for downgrades the user already paid for the current period).
        """
        if not subscription.scheduled_plan_id:
            return False

        new_plan = await self.get_plan_by_id(db, subscription.scheduled_plan_id)
        if not new_plan:
            logger.error(
                "Scheduled plan not found",
                subscription_id=str(subscription.id),
                plan_id=str(subscription.scheduled_plan_id),
            )
            return False

        old_plan_id = subscription.plan_id
        new_billing_period = subscription.scheduled_billing_period or "monthly"

        # Update subscription to new plan
        now = datetime.now(timezone.utc)
        subscription.plan_id = subscription.scheduled_plan_id

        # Calculate new period based on billing period
        if new_billing_period == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.status = SubscriptionStatus.ACTIVE

        # Clear scheduled change
        subscription.scheduled_plan_id = None
        subscription.scheduled_billing_period = None

        # Handle workspace/task limits for downgrade
        await self._block_excess_workspaces(db, subscription.user_id, new_plan.max_workspaces)
        first_workspace = await self._get_oldest_workspace(db, subscription.user_id)
        if first_workspace:
            await self.auto_pause_excess_tasks(db, first_workspace.id, new_plan.max_cron_tasks)

        await db.commit()

        logger.info(
            "Scheduled plan change applied",
            subscription_id=str(subscription.id),
            user_id=str(subscription.user_id),
            old_plan_id=str(old_plan_id),
            new_plan_id=str(new_plan.id),
            new_billing_period=new_billing_period,
        )

        return True

    async def auto_renew_subscription(
        self,
        db: AsyncSession,
        subscription: Subscription,
    ) -> Payment | None:
        """
        Автоматическое продление подписки с использованием сохранённого метода оплаты.

        Returns:
            Payment если успешно, None если не удалось
        """
        if not self.is_configured:
            logger.warning("YooKassa not configured for auto-renewal")
            return None

        if not subscription.yookassa_payment_method_id:
            logger.info(
                "No saved payment method for subscription",
                subscription_id=str(subscription.id),
                user_id=str(subscription.user_id),
            )
            return None

        # Get plan
        plan = await self.get_plan_by_id(db, subscription.plan_id)
        if not plan:
            logger.error("Plan not found for renewal", plan_id=subscription.plan_id)
            return None

        # Determine billing period based on previous subscription duration
        period_days = (subscription.current_period_end - subscription.current_period_start).days
        billing_period = "yearly" if period_days > 60 else "monthly"
        amount = plan.price_yearly if billing_period == "yearly" else plan.price_monthly

        if amount == 0:
            logger.error("Cannot auto-renew free plan")
            return None

        # Get user for email (required for receipt)
        user_result = await db.execute(select(User).where(User.id == subscription.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.error("User not found for renewal", user_id=subscription.user_id)
            return None
        user_lang = user.preferred_language or "ru"

        # Get workspace for payment
        workspace = await self._get_oldest_workspace(db, subscription.user_id)
        if not workspace:
            logger.error("No workspace for renewal", user_id=subscription.user_id)
            return None

        # Convert kopeks to rubles
        amount_value = f"{amount / 100:.2f}"

        # Create payment record
        payment = Payment(
            workspace_id=workspace.id,
            user_id=subscription.user_id,
            amount=amount,
            currency="RUB",
            status=PaymentStatus.PENDING,
            description=_get_billing_description(plan.display_name, billing_period, user_lang, is_auto_renewal=True),
            extra_data={
                "plan_id": str(plan.id),
                "billing_period": billing_period,
                "user_id": str(subscription.user_id),
                "auto_renewal": True,
            },
        )
        db.add(payment)
        await db.flush()

        # Create YooKassa payment with saved payment method (no confirmation needed)
        idempotence_key = str(uuid_module.uuid4())
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
                        "payment_method_id": subscription.yookassa_payment_method_id,
                        "description": payment.description,
                        "metadata": {
                            "payment_id": str(payment.id),
                            "user_id": str(subscription.user_id),
                            "plan_id": str(plan.id),
                            "billing_period": billing_period,
                            "auto_renewal": "true",
                        },
                        "receipt": {
                            "customer": {
                                "email": user.email,
                            },
                            "items": [
                                {
                                    "description": _get_receipt_description(
                                        plan.display_name, billing_period, user_lang
                                    ),
                                    "quantity": "1",
                                    "amount": {
                                        "value": amount_value,
                                        "currency": "RUB",
                                    },
                                    "vat_code": 1,
                                    "payment_mode": "full_payment",
                                    "payment_subject": "service",
                                }
                            ],
                        },
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                yookassa_data = response.json()

                payment.yookassa_payment_id = yookassa_data["id"]
                payment_status = yookassa_data.get("status")

                if payment_status == "succeeded":
                    # Payment succeeded immediately
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.paid_at = datetime.now(timezone.utc)

                    # Extend subscription
                    now = datetime.now(timezone.utc)
                    if billing_period == "yearly":
                        new_period_end = now + timedelta(days=365)
                    else:
                        new_period_end = now + timedelta(days=30)

                    subscription.current_period_start = now
                    subscription.current_period_end = new_period_end
                    subscription.status = SubscriptionStatus.ACTIVE

                    # Save new payment method if returned
                    payment_method = yookassa_data.get("payment_method")
                    if payment_method and payment_method.get("id"):
                        subscription.yookassa_payment_method_id = payment_method["id"]

                    await db.commit()
                    logger.info(
                        "Subscription auto-renewed successfully",
                        subscription_id=str(subscription.id),
                        user_id=str(subscription.user_id),
                        payment_id=str(payment.id),
                    )
                    return payment

                elif payment_status == "pending":
                    # Payment is pending (waiting for confirmation)
                    await db.commit()
                    logger.info(
                        "Auto-renewal payment pending",
                        subscription_id=str(subscription.id),
                        payment_id=str(payment.id),
                    )
                    return payment

                else:
                    # Payment failed or cancelled
                    payment.status = PaymentStatus.FAILED
                    await db.commit()
                    logger.warning(
                        "Auto-renewal payment failed",
                        subscription_id=str(subscription.id),
                        payment_status=payment_status,
                    )
                    return None

        except httpx.HTTPStatusError as e:
            logger.error(
                "YooKassa API error during auto-renewal",
                error=str(e),
                status_code=e.response.status_code,
                response_body=e.response.text,
                subscription_id=str(subscription.id),
            )
            payment.status = PaymentStatus.FAILED
            await db.commit()
            return None
        except Exception as e:
            logger.error(
                "Failed to auto-renew subscription",
                error=str(e),
                error_type=type(e).__name__,
                subscription_id=str(subscription.id),
            )
            await db.rollback()
            return None

    async def check_pending_payments(
        self,
        db: AsyncSession,
        timeout_minutes: int = 20,
    ) -> int:
        """
        Check and update status of old pending payments via YooKassa API.

        Returns count of payments that were updated.
        """
        if not self.is_configured:
            return 0

        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=timeout_minutes)

        # Find old pending payments
        result = await db.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at < cutoff_time,
                Payment.yookassa_payment_id.isnot(None),
            )
        )
        pending_payments = list(result.scalars().all())

        if not pending_payments:
            return 0

        updated_count = 0

        async with httpx.AsyncClient() as client:
            for payment in pending_payments:
                try:
                    # Check payment status via YooKassa API
                    response = await client.get(
                        f"{self.base_url}/payments/{payment.yookassa_payment_id}",
                        auth=self._get_auth(),
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    yookassa_data = response.json()

                    yookassa_status = yookassa_data.get("status")

                    # Map YooKassa status to our status
                    if yookassa_status == "succeeded":
                        payment.status = PaymentStatus.SUCCEEDED
                        payment.paid_at = datetime.now(timezone.utc)
                        updated_count += 1
                        logger.info(
                            "Payment status updated to succeeded",
                            payment_id=str(payment.id),
                        )
                    elif yookassa_status == "canceled":
                        payment.status = PaymentStatus.CANCELLED
                        updated_count += 1
                        logger.info(
                            "Payment status updated to cancelled",
                            payment_id=str(payment.id),
                        )
                    elif yookassa_status == "waiting_for_capture":
                        # Payment authorized but not captured - this shouldn't happen with capture=true
                        logger.warning(
                            "Payment waiting for capture",
                            payment_id=str(payment.id),
                        )
                    # If still pending in YooKassa, leave as is

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        # Payment not found in YooKassa - mark as cancelled
                        payment.status = PaymentStatus.CANCELLED
                        updated_count += 1
                        logger.warning(
                            "Payment not found in YooKassa, marking as cancelled",
                            payment_id=str(payment.id),
                        )
                    else:
                        logger.error(
                            "Error checking payment status",
                            payment_id=str(payment.id),
                            error=str(e),
                        )
                except Exception as e:
                    logger.error(
                        "Error checking payment status",
                        payment_id=str(payment.id),
                        error=str(e),
                    )

        if updated_count:
            await db.commit()
            logger.info("Updated pending payments", count=updated_count)

        return updated_count


# Global instance
billing_service = BillingService()

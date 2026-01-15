"""Billing API endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, UserPlan, VerifiedUser, get_db
from app.schemas.billing import (
    CancelSubscriptionRequest,
    CreatePaymentRequest,
    PaymentResponse,
    PlanResponse,
    PricePreviewRequest,
    PricePreviewResponse,
    SubscriptionResponse,
)
from app.services.billing import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """Get all available subscription plans."""
    plans = await billing_service.get_plans(db)
    return plans


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific plan by ID."""
    plan = await billing_service.get_plan_by_id(db, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    return plan


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    current_user: CurrentUser,
    user_plan: UserPlan,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription."""
    subscription = await billing_service.get_user_subscription(db, current_user.id)

    if not subscription:
        return None

    # Include plan in response
    response = SubscriptionResponse.model_validate(subscription)
    response.plan = PlanResponse.model_validate(user_plan)

    return response


@router.post("/preview-price", response_model=PricePreviewResponse)
async def preview_price(
    request: PricePreviewRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Preview price with proration for plan upgrade/change."""
    # Get plan
    plan = await billing_service.get_plan_by_id(db, request.plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Calculate base price
    plan_price = plan.price_yearly if request.billing_period == "yearly" else plan.price_monthly

    # Get current subscription and analyze change
    subscription = await billing_service.get_user_subscription(db, current_user.id)
    analysis = await billing_service._analyze_plan_change(
        db, subscription, request.plan_id, request.billing_period
    )

    # Determine final amount based on analysis
    if analysis["requires_deferred"]:
        # Deferred changes don't have proration - user pays full price at period end
        final_amount = plan_price
        proration_credit = 0
    else:
        proration_credit = analysis["proration_credit"]
        final_amount = max(plan_price - proration_credit, 100)  # Minimum 1 RUB

    return PricePreviewResponse(
        plan_price=plan_price,
        proration_credit=proration_credit,
        final_amount=final_amount,
        remaining_days=analysis["remaining_days"],
        is_same_plan=analysis["is_same_plan"],
        is_downgrade=analysis["is_downgrade"],
        is_period_downgrade=analysis["is_period_downgrade"],
        requires_deferred=analysis["requires_deferred"],
        effective_date=analysis["effective_date"],
    )


@router.post("/subscribe", response_model=PaymentResponse)
async def create_subscription_payment(
    request: CreatePaymentRequest,
    current_user: VerifiedUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a payment to subscribe to a plan. Requires verified email."""
    # Analyze the plan change first (validation before payment system check)
    subscription = await billing_service.get_user_subscription(db, current_user.id)
    analysis = await billing_service._analyze_plan_change(
        db, subscription, request.plan_id, request.billing_period
    )

    # Reject same plan
    if analysis["is_same_plan"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to this plan",
        )

    # Reject deferred changes via this endpoint
    if analysis["requires_deferred"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plan change requires scheduling. Use /schedule-plan-change endpoint.",
        )

    # Check if YooKassa is configured (only after validation passes)
    if not billing_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system is not configured",
        )

    payment = await billing_service.create_payment(
        db,
        user_id=current_user.id,
        plan_id=request.plan_id,
        billing_period=request.billing_period,
        return_url=request.return_url,
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment",
        )

    return payment


@router.post("/schedule-plan-change", response_model=SubscriptionResponse)
async def schedule_plan_change(
    request: CreatePaymentRequest,
    current_user: VerifiedUser,
    db: AsyncSession = Depends(get_db),
):
    """Schedule a plan change for the end of current billing period.

    Used for downgrades and yearly→monthly transitions.
    Requires verified email.
    """
    # Verify plan exists
    plan = await billing_service.get_plan_by_id(db, request.plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Analyze the plan change
    subscription = await billing_service.get_user_subscription(db, current_user.id)
    analysis = await billing_service._analyze_plan_change(
        db, subscription, request.plan_id, request.billing_period
    )

    # Reject same plan
    if analysis["is_same_plan"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to this plan",
        )

    # Only allow deferred changes via this endpoint
    if not analysis["requires_deferred"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plan change does not require scheduling. Use /subscribe endpoint.",
        )

    updated_subscription = await billing_service.schedule_plan_change(
        db,
        user_id=current_user.id,
        new_plan_id=request.plan_id,
        new_billing_period=request.billing_period,
    )

    if not updated_subscription:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule plan change",
        )

    # Include plan in response
    user_plan = await billing_service.get_user_plan(db, current_user.id)
    response = SubscriptionResponse.model_validate(updated_subscription)
    response.plan = PlanResponse.model_validate(user_plan)

    return response


@router.post("/cancel-scheduled-change")
async def cancel_scheduled_change(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled plan change."""
    success = await billing_service.cancel_scheduled_plan_change(db, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scheduled plan change to cancel",
        )

    return {"message": "Scheduled plan change cancelled"}


@router.post("/subscription/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Cancel current user's subscription."""
    subscription = await billing_service.get_user_subscription(db, current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription",
        )

    success = await billing_service.cancel_subscription(
        db, current_user.id, immediately=request.immediately
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )

    return {"message": "Subscription cancelled successfully"}


@router.get("/payments", response_model=list[PaymentResponse])
async def get_payment_history(
    current_user: CurrentUser,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for current user."""
    payments = await billing_service.get_payment_history(
        db, current_user.id, limit=limit, offset=offset
    )

    return payments

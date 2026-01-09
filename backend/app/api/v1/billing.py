"""Billing API endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, UserPlan, get_db
from app.schemas.billing import (
    CancelSubscriptionRequest,
    CreatePaymentRequest,
    PaymentResponse,
    PlanResponse,
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


@router.post("/subscribe", response_model=PaymentResponse)
async def create_subscription_payment(
    request: CreatePaymentRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a payment to subscribe to a plan."""
    # Check if YooKassa is configured
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

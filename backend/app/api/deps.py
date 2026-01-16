from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.database import get_db
from app.db.repositories.users import UserRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.models.worker import Worker
from app.models.workspace import Workspace

security = HTTPBearer()
worker_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


async def get_verified_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify their email is verified."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "email_not_verified",
                "message": "Please verify your email address to continue",
            },
        )
    return current_user


async def get_workspace(
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Get workspace by ID and verify user has access."""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_by_id(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user owns the workspace
    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workspace",
        )

    return workspace


async def get_user_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Plan:
    """Get current user's plan from their subscription or free plan."""
    from app.services.billing import billing_service

    return await billing_service.get_user_plan(db, current_user.id)


async def get_current_worker(
    x_worker_key: Annotated[str | None, Header(alias="X-Worker-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """Get current authenticated worker from API key header."""
    if not x_worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Key header",
        )

    # Import here to avoid circular imports
    from app.services.worker import worker_service

    worker = await worker_service.authenticate_worker(db, x_worker_key)

    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker API key",
        )

    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker is disabled",
        )

    return worker


async def require_active_subscription(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """
    Check that workspace is not blocked and user has valid subscription.
    Returns 403 if workspace is blocked (soft-block for downgraded users).
    Returns 402 Payment Required if subscription is expired/cancelled.

    Free plan users (no subscription) are allowed to continue
    within their limits (limits are checked separately in endpoints).
    """
    # Check if workspace is blocked
    if workspace.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "workspace_blocked",
                "message": "This workspace is blocked. Upgrade your plan to unlock it.",
            },
        )

    # Get subscription for USER (not workspace)
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    subscription = result.scalar_one_or_none()

    # No subscription = free plan, allowed (limits checked in endpoints)
    if subscription is None:
        return workspace

    # Active or past_due subscription - allowed
    if subscription.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE):
        return workspace

    # Expired or cancelled - block write operations
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "error": "subscription_expired",
            "message": "Your subscription has expired. Please renew to create or modify tasks.",
            "subscription_status": subscription.status.value,
        },
    )


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(get_verified_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentWorkspace = Annotated[Workspace, Depends(get_workspace)]
ActiveSubscriptionWorkspace = Annotated[Workspace, Depends(require_active_subscription)]
CurrentWorker = Annotated[Worker, Depends(get_current_worker)]
UserPlan = Annotated[Plan, Depends(get_user_plan)]
DB = Annotated[AsyncSession, Depends(get_db)]

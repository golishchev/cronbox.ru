from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DB
from app.schemas.auth import (
    LoginResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.user import UserLogin, UserResponse, UserUpdate
from app.db.repositories.users import UserRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: RegisterRequest, db: DB):
    """Register a new user account."""
    auth_service = AuthService(db)
    user, tokens = await auth_service.register(
        email=data.email,
        password=data.password,
        name=data.name,
    )

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: UserLogin, db: DB):
    """Login with email and password."""
    auth_service = AuthService(db)
    user, tokens = await auth_service.login(
        email=data.email,
        password=data.password,
    )

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: DB):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_tokens(data.refresh_token)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, current_user: CurrentUser, db: DB):
    """Update current user profile."""
    user_repo = UserRepository(db)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return UserResponse.model_validate(current_user)

    updated_user = await user_repo.update(current_user, **update_data)
    return UserResponse.model_validate(updated_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Change current user's password."""
    auth_service = AuthService(db)
    await auth_service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser):
    """Logout current user.

    Note: With JWT tokens, logout is handled client-side by removing the token.
    This endpoint can be used to invalidate refresh tokens if needed.
    """
    # In a more sophisticated implementation, you could:
    # 1. Add the refresh token to a blacklist in Redis
    # 2. Invalidate all user sessions
    # For now, this is a no-op since JWT is stateless
    pass

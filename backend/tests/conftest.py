"""Test configuration and fixtures."""

# Test database URL (use separate test database)
# Only replace the database name at the end of the URL, not user/password
import re
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.redis import redis_client
from app.core.security import create_access_token, get_password_hash
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.plan import Plan
from app.models.user import User

TEST_DATABASE_URL = re.sub(r"/cronbox$", "/cronbox_test", settings.database_url)


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis client
    await redis_client.initialize()

    yield engine

    # Close Redis
    await redis_client.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Clean all tables before each test
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))

    # Flush Redis completely (cache + rate limiter keys)
    try:
        await redis_client.client.flushdb()
    except Exception:
        pass  # Ignore if Redis not available

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def free_plan(db_session: AsyncSession) -> Plan:
    """Create a free plan for testing."""
    plan = Plan(
        name="free",
        display_name="Free",
        description="Free plan with basic features",
        price_monthly=0,
        price_yearly=0,
        max_cron_tasks=3,
        max_delayed_tasks_per_month=100,
        max_workspaces=1,
        max_execution_history_days=7,
        min_cron_interval_minutes=5,
        telegram_notifications=False,
        email_notifications=False,
        webhook_callbacks=False,
        custom_headers=True,
        retry_on_failure=False,
        # Chain limits
        max_task_chains=3,
        max_chain_steps=5,
        chain_variable_substitution=True,
        min_chain_interval_minutes=5,
        is_active=True,
        is_public=True,
        sort_order=0,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def pro_plan(db_session: AsyncSession) -> Plan:
    """Create a pro plan for testing."""
    plan = Plan(
        name="pro",
        display_name="Pro",
        description="Pro plan with advanced features",
        price_monthly=99900,
        price_yearly=999000,
        max_cron_tasks=50,
        max_delayed_tasks_per_month=5000,
        max_workspaces=5,
        max_execution_history_days=90,
        min_cron_interval_minutes=1,
        telegram_notifications=True,
        email_notifications=True,
        webhook_callbacks=True,
        custom_headers=True,
        retry_on_failure=True,
        # Chain limits
        max_task_chains=20,
        max_chain_steps=20,
        chain_variable_substitution=True,
        min_chain_interval_minutes=1,
        is_active=True,
        is_public=True,
        sort_order=1,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, free_plan: Plan) -> User:
    """Create a test user with verified email."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        name="Test User",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Get authorization headers for test user."""
    token = create_access_token(user_id=test_user.id, email=test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, auth_headers: dict) -> AsyncClient:
    """Create an authenticated test client."""
    client.headers.update(auth_headers)
    return client

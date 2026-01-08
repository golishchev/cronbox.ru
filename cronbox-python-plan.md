# CronBox.ru — План разработки (Python)

> Полноценный production-ready сервис планирования HTTP-запросов
> **Стек: Python + FastAPI + arq + PostgreSQL + Redis**

---

## 1. Обзор проекта

### 1.1 Что это

**CronBox** — SaaS-платформа для планирования HTTP-запросов:
- **Cron-задачи**: повторяющиеся запросы по расписанию (каждый час, каждый день в 3:00, и т.д.)
- **Delayed-запросы**: одноразовые запросы, выполняемые в указанное время

### 1.2 Целевая аудитория

- Разработчики, которым нужен простой cron без инфраструктуры
- Владельцы SaaS, которым нужны отложенные уведомления
- Малый бизнес с интеграциями (1C, CRM, маркетплейсы)

### 1.3 Ключевые преимущества

- Российский сервис (оплата в рублях, сервера в РФ)
- Два продукта в одном (cron + delayed)
- Telegram-уведомления
- Простой API и документация на русском

---

## 2. Архитектура системы

### 2.1 Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                           КЛИЕНТЫ                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ Web App  │  │   API    │  │  Webhook │                          │
│  │ (React)  │  │ Clients  │  │ Callbacks│                          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                          │
└───────┼─────────────┼─────────────┼────────────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX (Reverse Proxy)                        │
│                    SSL Termination, Rate Limiting                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Server  │     │   API Server    │     │   API Server    │
│   (FastAPI)   │     │   (FastAPI)     │     │   (FastAPI)     │
│   + Uvicorn   │     │   + Uvicorn     │     │   + Uvicorn     │
└───────┬───────┘     └────────┬────────┘     └────────┬────────┘
        │                      │                       │
        └──────────────────────┼───────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL   │    │     Redis       │    │   S3/MinIO      │
│  (Primary DB) │    │  (Cache/Queue)  │    │   (Logs/Files)  │
└───────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SCHEDULER SERVICE                           │
│  ┌─────────────────┐  ┌─────────────────┐                          │
│  │  Cron Ticker    │  │  arq Workers    │                          │
│  │  (APScheduler)  │  │  (HTTP Executor)│                          │
│  └────────┬────────┘  └────────┬────────┘                          │
│           │                    │                                    │
│           └────────────────────┘                                    │
│                    │                                                │
│                    ▼                                                │
│            ┌──────────────┐                                        │
│            │    httpx     │  (async HTTP client)                   │
│            │   aiohttp    │                                        │
│            └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram    │    │     Email       │    │    Webhook      │
│   (aiogram)   │    │   (Resend)      │    │   (callbacks)   │
└───────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 Компоненты системы

| Компонент | Назначение | Технология |
|-----------|------------|------------|
| API Server | REST API, авторизация, CRUD | FastAPI + Uvicorn |
| Scheduler | Планирование задач | APScheduler |
| Workers | Выполнение HTTP-запросов | arq (async) |
| Telegram Bot | Уведомления, привязка | aiogram 3 |
| Web App | Пользовательский интерфейс | React + TypeScript |
| Admin Panel | Управление системой | React + TypeScript |
| Database | Хранение данных | PostgreSQL 16 |
| Cache/Queue | Кэш, очереди | Redis 7 |

---

## 3. Технологический стек

### 3.1 Backend (Python 3.12)

```toml
# pyproject.toml - основные зависимости

[project]
name = "cronbox"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    # Web Framework
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "alembic>=1.13.1",
    
    # Redis & Queue
    "redis>=5.0.1",
    "arq>=0.25.0",
    
    # HTTP Client
    "httpx>=0.26.0",
    "aiohttp>=3.9.1",
    
    # Auth & Security
    "pyjwt>=2.8.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    
    # Validation
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "email-validator>=2.1.0",
    
    # Cron & Scheduling
    "croniter>=2.0.1",
    "apscheduler>=3.10.4",
    "pytz>=2023.3",
    
    # Telegram
    "aiogram>=3.3.0",
    
    # Email
    "resend>=0.7.0",
    
    # Payments
    "yookassa>=3.1.0",
    
    # Utils
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
    "orjson>=3.9.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.4",
    "pytest-asyncio>=0.23.3",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",  # for TestClient
    "ruff>=0.1.11",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
]
```

### 3.2 Почему эти библиотеки

| Библиотека | Назначение | Почему выбрана |
|------------|------------|----------------|
| **FastAPI** | Web Framework | Async, типизация, автодокументация OpenAPI |
| **SQLAlchemy 2.0** | ORM | Async support, миграции через Alembic |
| **arq** | Task Queue | Лёгкий, async-native, Redis-based |
| **httpx** | HTTP Client | Async, API как у requests |
| **aiogram 3** | Telegram Bot | Async, современный API |
| **APScheduler** | Cron scheduler | Гибкий, cron expressions |
| **Pydantic v2** | Validation | Быстрый, интеграция с FastAPI |
| **structlog** | Logging | Structured JSON logs |

### 3.3 arq vs Celery vs Dramatiq

| Критерий | arq | Celery | Dramatiq |
|----------|-----|--------|----------|
| Async-native | ✅ | ❌ | ❌ |
| Простота | ✅ | ❌ | ⚠️ |
| Зависимости | Минимум | Много | Средне |
| Redis-only | ✅ | ❌ | ✅ |
| Retry logic | ✅ | ✅ | ✅ |
| Cron jobs | ✅ | ✅ | ❌ |
| **Для CronBox** | ✅ Идеально | Overkill | Подходит |

**arq** — идеальный выбор: минималистичный, async, отлично работает с FastAPI.

### 3.4 Frontend (без изменений)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.8.0",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "react-hook-form": "^7.48.2",
    "zod": "^3.22.4",
    "date-fns": "^2.30.0",
    "cronstrue": "^2.48.0",
    "recharts": "^2.10.3",
    "lucide-react": "^0.294.0",
    "tailwindcss": "^3.3.6"
  }
}
```

---

## 4. Структура проекта

```
cronbox/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Pydantic Settings
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependencies (get_db, get_current_user)
│   │   │   ├── router.py           # Main router
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── workspaces.py
│   │   │       ├── cron_tasks.py
│   │   │       ├── delayed_tasks.py
│   │   │       ├── executions.py
│   │   │       ├── billing.py
│   │   │       ├── notifications.py
│   │   │       └── webhooks.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # JWT, password hashing
│   │   │   ├── redis.py            # Redis client
│   │   │   └── exceptions.py       # Custom exceptions
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # AsyncSession, engine
│   │   │   ├── base.py             # Base model
│   │   │   └── repositories/       # Repository pattern
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── users.py
│   │   │       ├── workspaces.py
│   │   │       ├── cron_tasks.py
│   │   │       └── delayed_tasks.py
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── workspace.py
│   │   │   ├── cron_task.py
│   │   │   ├── delayed_task.py
│   │   │   ├── execution.py
│   │   │   ├── subscription.py
│   │   │   └── payment.py
│   │   │
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── workspace.py
│   │   │   ├── cron_task.py
│   │   │   ├── delayed_task.py
│   │   │   ├── execution.py
│   │   │   └── billing.py
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── cron.py
│   │   │   ├── delayed.py
│   │   │   ├── executor.py         # HTTP execution logic
│   │   │   ├── billing.py
│   │   │   └── notifications.py
│   │   │
│   │   └── workers/                # arq workers
│   │       ├── __init__.py
│   │       ├── settings.py         # arq WorkerSettings
│   │       ├── tasks.py            # Task definitions
│   │       └── scheduler.py        # APScheduler integration
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_cron.py
│   │   └── test_delayed.py
│   │
│   ├── scripts/
│   │   ├── create_admin.py
│   │   └── seed_plans.py
│   │
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── docker-compose.dev.yml
│
├── frontend/                       # React app (без изменений)
│   ├── src/
│   ├── package.json
│   └── Dockerfile
│
├── nginx/
│   └── conf.d/
│       └── cronbox.conf
│
├── docker-compose.yml              # Development
├── docker-compose.prod.yml         # Production
├── .github/
│   └── workflows/
│       └── deploy.yml
├── .env.example
└── README.md
```

---

## 5. База данных

### 5.1 SQLAlchemy Models

```python
# app/models/base.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class UUIDMixin:
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
```

```python
# app/models/user.py
from uuid import UUID
from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255))
    
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
    )
```

```python
# app/models/workspace.py
from uuid import UUID
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"
    
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"))
    
    # Usage counters
    cron_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    delayed_tasks_this_month: Mapped[int] = mapped_column(Integer, default=0)
    
    # Settings
    default_timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    webhook_secret: Mapped[str] = mapped_column(String(255))
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="workspaces")
    plan: Mapped["Plan"] = relationship()
    cron_tasks: Mapped[list["CronTask"]] = relationship(back_populates="workspace")
    delayed_tasks: Mapped[list["DelayedTask"]] = relationship(back_populates="workspace")
```

```python
# app/models/cron_task.py
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin
import enum


class HttpMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CronTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cron_tasks"
    
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True
    )
    
    # Identification
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # HTTP Request
    url: Mapped[str] = mapped_column(String(2048))
    method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod), default=HttpMethod.GET)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(Text)
    
    # Schedule
    schedule: Mapped[str] = mapped_column(String(100))  # Cron expression
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    
    # Execution settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60)
    
    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column()
    last_status: Mapped[TaskStatus | None] = mapped_column(SQLEnum(TaskStatus))
    next_run_at: Mapped[datetime | None] = mapped_column(index=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    
    # Notifications
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="cron_tasks")
    executions: Mapped[list["Execution"]] = relationship(back_populates="cron_task")
```

```python
# app/models/delayed_task.py
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin
from app.models.cron_task import HttpMethod, TaskStatus


class DelayedTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "delayed_tasks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_delayed_idempotency"),
    )
    
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True
    )
    
    # Identification
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # HTTP Request
    url: Mapped[str] = mapped_column(String(2048))
    method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod), default=HttpMethod.POST)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(Text)
    
    # Schedule
    execute_at: Mapped[datetime] = mapped_column(index=True)
    
    # Execution settings
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60)
    
    # State
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        index=True
    )
    executed_at: Mapped[datetime | None] = mapped_column()
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)
    
    # Callback
    callback_url: Mapped[str | None] = mapped_column(String(2048))
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="delayed_tasks")
```

```python
# app/models/execution.py
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin
from app.models.cron_task import HttpMethod, TaskStatus


class Execution(Base, UUIDMixin):
    __tablename__ = "executions"
    
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True
    )
    
    # Task reference
    task_type: Mapped[str] = mapped_column(String(20))  # 'cron' or 'delayed'
    task_id: Mapped[UUID] = mapped_column(index=True)
    task_name: Mapped[str | None] = mapped_column(String(255))
    
    # Cron task relationship (optional)
    cron_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cron_tasks.id", ondelete="SET NULL")
    )
    
    # Execution details
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus))
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)
    
    # Request
    request_url: Mapped[str] = mapped_column(String(2048))
    request_method: Mapped[HttpMethod] = mapped_column(SQLEnum(HttpMethod))
    request_headers: Mapped[dict | None] = mapped_column(JSONB)
    request_body: Mapped[str | None] = mapped_column(Text)
    
    # Response
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict | None] = mapped_column(JSONB)
    response_body: Mapped[str | None] = mapped_column(Text)  # First N bytes
    response_size_bytes: Mapped[int | None] = mapped_column(Integer)
    
    # Error
    error_message: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(100))
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    cron_task: Mapped["CronTask | None"] = relationship(back_populates="executions")
```

### 5.2 Database Setup

```python
# app/db/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## 6. API Implementation

### 6.1 Main Application

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import settings
from app.api.router import api_router
from app.core.redis import redis_client
from app.db.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_client.initialize()
    yield
    # Shutdown
    await redis_client.close()
    await engine.dispose()


app = FastAPI(
    title="CronBox API",
    version="1.0.0",
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### 6.2 Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "CronBox"
    debug: bool = False
    secret_key: str
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    
    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    
    # Email (Resend)
    resend_api_key: str = ""
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

### 6.3 Authentication

```python
# app/core/security.py
from datetime import datetime, timedelta
from uuid import UUID
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: UUID, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
```

```python
# app/api/deps.py
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.db.repositories.users import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = UUID(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
```

### 6.4 Cron Tasks Router

```python
# app/api/v1/cron_tasks.py
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Query
from app.api.deps import CurrentUser, DB
from app.schemas.cron_task import (
    CronTaskCreate,
    CronTaskUpdate,
    CronTaskResponse,
    CronTaskListResponse
)
from app.services.cron import CronService
from app.db.repositories.workspaces import WorkspaceRepository

router = APIRouter(prefix="/workspaces/{workspace_id}/cron", tags=["Cron Tasks"])


@router.get("", response_model=CronTaskListResponse)
async def list_cron_tasks(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
):
    """List all cron tasks in workspace"""
    # Check workspace access
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    tasks, total = await cron_service.list_tasks(
        workspace_id=workspace_id,
        page=page,
        limit=limit,
        status=status,
        search=search
    )
    
    return CronTaskListResponse(
        tasks=tasks,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )


@router.post("", response_model=CronTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_cron_task(
    workspace_id: UUID,
    task_in: CronTaskCreate,
    current_user: CurrentUser,
    db: DB,
):
    """Create a new cron task"""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    
    # Check plan limits
    can_create, error = await cron_service.check_can_create(workspace)
    if not can_create:
        raise HTTPException(status_code=403, detail=error)
    
    task = await cron_service.create_task(workspace_id, task_in)
    return task


@router.get("/{task_id}", response_model=CronTaskResponse)
async def get_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Get a specific cron task"""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    task = await cron_service.get_task(task_id, workspace_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.patch("/{task_id}", response_model=CronTaskResponse)
async def update_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    task_in: CronTaskUpdate,
    current_user: CurrentUser,
    db: DB,
):
    """Update a cron task"""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    task = await cron_service.update_task(task_id, workspace_id, task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Delete a cron task"""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    deleted = await cron_service.delete_task(task_id, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/run", response_model=dict)
async def run_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Trigger immediate execution of a cron task"""
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_user_workspace(workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cron_service = CronService(db)
    execution_id = await cron_service.trigger_run(task_id, workspace_id)
    
    return {"execution_id": str(execution_id), "status": "queued"}


@router.post("/{task_id}/pause", response_model=CronTaskResponse)
async def pause_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Pause a cron task"""
    cron_service = CronService(db)
    task = await cron_service.set_paused(task_id, workspace_id, paused=True)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/resume", response_model=CronTaskResponse)
async def resume_cron_task(
    workspace_id: UUID,
    task_id: UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Resume a paused cron task"""
    cron_service = CronService(db)
    task = await cron_service.set_paused(task_id, workspace_id, paused=False)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

### 6.5 Pydantic Schemas

```python
# app/schemas/cron_task.py
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from croniter import croniter
from app.models.cron_task import HttpMethod, TaskStatus


class CronTaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    url: HttpUrl
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    schedule: str = Field(..., description="Cron expression (e.g., '0 3 * * *')")
    timezone: str = "Europe/Moscow"
    timeout_seconds: int = Field(10, ge=1, le=300)
    retry_count: int = Field(0, ge=0, le=10)
    retry_delay_seconds: int = Field(60, ge=10, le=3600)
    notify_on_failure: bool = True
    notify_on_recovery: bool = True
    
    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        try:
            croniter(v)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression: {e}")
        return v
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        import pytz
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v


class CronTaskCreate(CronTaskBase):
    pass


class CronTaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    url: HttpUrl | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule: str | None = None
    timezone: str | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_count: int | None = Field(None, ge=0, le=10)
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_recovery: bool | None = None


class CronTaskResponse(CronTaskBase):
    id: UUID
    workspace_id: UUID
    is_active: bool
    is_paused: bool
    last_run_at: datetime | None
    last_status: TaskStatus | None
    next_run_at: datetime | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class CronTaskListResponse(BaseModel):
    tasks: list[CronTaskResponse]
    pagination: PaginationMeta
```

---

## 7. Scheduler & Workers (arq)

### 7.1 arq Worker Settings

```python
# app/workers/settings.py
from arq.connections import RedisSettings
from app.config import settings


def get_redis_settings() -> RedisSettings:
    """Parse Redis URL and return arq RedisSettings"""
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:
    """arq Worker Settings"""
    
    redis_settings = get_redis_settings()
    
    # Import functions
    functions = [
        "app.workers.tasks.execute_http_task",
        "app.workers.tasks.send_notification",
    ]
    
    # Cron jobs (built-in arq feature)
    cron_jobs = [
        # Check for due tasks every 10 seconds
        # cron(coroutine, hour=None, minute=None, second=None, ...)
    ]
    
    # Worker settings
    max_jobs = 50
    job_timeout = 300  # 5 minutes max
    keep_result = 3600  # 1 hour
    retry_jobs = True
    max_tries = 3
    
    # Health check
    health_check_interval = 30
```

### 7.2 Task Definitions

```python
# app/workers/tasks.py
import httpx
import structlog
from uuid import UUID
from datetime import datetime
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.execution import Execution
from app.models.cron_task import CronTask, TaskStatus
from app.models.delayed_task import DelayedTask
from app.services.notifications import NotificationService

logger = structlog.get_logger()


async def execute_http_task(
    ctx: dict,
    task_type: str,  # "cron" or "delayed"
    task_id: str,
    workspace_id: str,
    url: str,
    method: str,
    headers: dict,
    body: str | None,
    timeout: int,
    retry_count: int,
    retry_attempt: int = 0,
    callback_url: str | None = None,
) -> dict:
    """
    Execute an HTTP request for a scheduled task.
    This is the main worker function called by arq.
    """
    
    execution_id = UUID(ctx.get("job_id", str(UUID())))
    started_at = datetime.utcnow()
    
    logger.info(
        "Executing HTTP task",
        task_type=task_type,
        task_id=task_id,
        url=url,
        method=method,
        retry_attempt=retry_attempt
    )
    
    # Prepare execution record
    execution_data = {
        "id": execution_id,
        "workspace_id": UUID(workspace_id),
        "task_type": task_type,
        "task_id": UUID(task_id),
        "started_at": started_at,
        "request_url": url,
        "request_method": method,
        "request_headers": headers,
        "request_body": body,
        "retry_attempt": retry_attempt,
    }
    
    # Execute HTTP request
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Add custom headers
            request_headers = {
                "User-Agent": "CronBox/1.0",
                "X-CronBox-Task-ID": task_id,
                "X-CronBox-Execution-ID": str(execution_id),
                **headers
            }
            
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                content=body if body else None,
            )
            
            finished_at = datetime.utcnow()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            
            # Determine status
            if 200 <= response.status_code < 300:
                status = TaskStatus.SUCCESS
                error_message = None
                error_type = None
            else:
                status = TaskStatus.FAILED
                error_message = f"HTTP {response.status_code}"
                error_type = "http_error"
            
            execution_data.update({
                "status": status,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "response_status_code": response.status_code,
                "response_headers": dict(response.headers),
                "response_body": response.text[:10000],  # Limit to 10KB
                "response_size_bytes": len(response.content),
                "error_message": error_message,
                "error_type": error_type,
            })
            
    except httpx.TimeoutException:
        execution_data.update({
            "status": TaskStatus.FAILED,
            "finished_at": datetime.utcnow(),
            "duration_ms": timeout * 1000,
            "error_message": "Request timeout",
            "error_type": "timeout",
        })
        
    except httpx.RequestError as e:
        execution_data.update({
            "status": TaskStatus.FAILED,
            "finished_at": datetime.utcnow(),
            "error_message": str(e),
            "error_type": "network_error",
        })
    
    # Save execution to database
    async with AsyncSessionLocal() as db:
        await save_execution(db, execution_data)
        await update_task_status(db, task_type, UUID(task_id), execution_data)
    
    # Handle retry if failed
    if execution_data["status"] == TaskStatus.FAILED and retry_attempt < retry_count:
        redis: ArqRedis = ctx["redis"]
        await redis.enqueue_job(
            "execute_http_task",
            task_type=task_type,
            task_id=task_id,
            workspace_id=workspace_id,
            url=url,
            method=method,
            headers=headers,
            body=body,
            timeout=timeout,
            retry_count=retry_count,
            retry_attempt=retry_attempt + 1,
            callback_url=callback_url,
            _defer_by=60,  # Retry after 60 seconds
        )
    
    # Send callback for delayed tasks
    if callback_url and task_type == "delayed":
        await send_callback(callback_url, execution_data)
    
    return {"status": execution_data["status"].value, "execution_id": str(execution_id)}


async def save_execution(db: AsyncSession, execution_data: dict):
    """Save execution record to database"""
    execution = Execution(**execution_data)
    db.add(execution)
    await db.commit()


async def update_task_status(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
    execution_data: dict
):
    """Update task status after execution"""
    from sqlalchemy import select, update
    
    if task_type == "cron":
        # Update cron task
        status = execution_data["status"]
        
        if status == TaskStatus.SUCCESS:
            # Reset consecutive failures
            stmt = (
                update(CronTask)
                .where(CronTask.id == task_id)
                .values(
                    last_status=status,
                    last_run_at=execution_data["started_at"],
                    consecutive_failures=0
                )
            )
        else:
            # Increment consecutive failures
            stmt = (
                update(CronTask)
                .where(CronTask.id == task_id)
                .values(
                    last_status=status,
                    last_run_at=execution_data["started_at"],
                    consecutive_failures=CronTask.consecutive_failures + 1
                )
            )
        
        await db.execute(stmt)
        await db.commit()
        
        # Check if notification needed
        task = await db.get(CronTask, task_id)
        if task:
            await check_and_send_notification(db, task, execution_data)
    
    elif task_type == "delayed":
        # Update delayed task
        stmt = (
            update(DelayedTask)
            .where(DelayedTask.id == task_id)
            .values(
                status=execution_data["status"],
                executed_at=execution_data["finished_at"]
            )
        )
        await db.execute(stmt)
        await db.commit()


async def check_and_send_notification(
    db: AsyncSession,
    task: CronTask,
    execution_data: dict
):
    """Check if notification should be sent and send it"""
    status = execution_data["status"]
    
    if status == TaskStatus.FAILED and task.notify_on_failure:
        # Send failure notification
        notification_service = NotificationService(db)
        await notification_service.send_task_failed(task, execution_data)
    
    elif status == TaskStatus.SUCCESS and task.consecutive_failures > 0 and task.notify_on_recovery:
        # Task recovered from failure
        notification_service = NotificationService(db)
        await notification_service.send_task_recovered(task, execution_data)


async def send_callback(callback_url: str, execution_data: dict):
    """Send webhook callback for delayed task result"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                callback_url,
                json={
                    "event": "task.completed",
                    "task_id": str(execution_data["task_id"]),
                    "execution_id": str(execution_data["id"]),
                    "status": execution_data["status"].value,
                    "response_status_code": execution_data.get("response_status_code"),
                    "duration_ms": execution_data.get("duration_ms"),
                    "error_message": execution_data.get("error_message"),
                }
            )
    except Exception as e:
        logger.error("Failed to send callback", url=callback_url, error=str(e))


async def send_notification(
    ctx: dict,
    notification_type: str,
    workspace_id: str,
    data: dict,
):
    """Background task for sending notifications"""
    async with AsyncSessionLocal() as db:
        notification_service = NotificationService(db)
        
        if notification_type == "task_failed":
            await notification_service.send_task_failed_notification(
                workspace_id=UUID(workspace_id),
                **data
            )
        elif notification_type == "task_recovered":
            await notification_service.send_task_recovered_notification(
                workspace_id=UUID(workspace_id),
                **data
            )
```

### 7.3 Scheduler (APScheduler + arq)

```python
# app/workers/scheduler.py
import asyncio
import structlog
from datetime import datetime, timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from croniter import croniter
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.cron_task import CronTask
from app.models.delayed_task import DelayedTask, TaskStatus
from app.workers.settings import get_redis_settings

logger = structlog.get_logger()


class TaskScheduler:
    """
    Main scheduler that:
    1. Periodically checks for due cron tasks
    2. Periodically checks for due delayed tasks
    3. Enqueues them to arq for execution
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.redis_pool = None
        self._running = False
    
    async def start(self):
        """Start the scheduler"""
        logger.info("Starting task scheduler")
        
        # Connect to Redis
        self.redis_pool = await create_pool(get_redis_settings())
        
        # Add jobs
        self.scheduler.add_job(
            self.process_due_cron_tasks,
            IntervalTrigger(seconds=10),
            id="process_cron",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.process_due_delayed_tasks,
            IntervalTrigger(seconds=5),
            id="process_delayed",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.update_next_run_times,
            IntervalTrigger(minutes=1),
            id="update_next_run",
            replace_existing=True
        )
        
        self.scheduler.start()
        self._running = True
        
        logger.info("Task scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping task scheduler")
        self._running = False
        self.scheduler.shutdown(wait=True)
        if self.redis_pool:
            await self.redis_pool.close()
        logger.info("Task scheduler stopped")
    
    async def process_due_cron_tasks(self):
        """Find and enqueue cron tasks that are due"""
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            
            # Find tasks where next_run_at <= now
            stmt = select(CronTask).where(
                and_(
                    CronTask.is_active == True,
                    CronTask.is_paused == False,
                    CronTask.next_run_at <= now
                )
            ).limit(100)
            
            result = await db.execute(stmt)
            tasks = result.scalars().all()
            
            for task in tasks:
                await self.enqueue_cron_task(db, task)
            
            if tasks:
                logger.info(f"Enqueued {len(tasks)} cron tasks")
    
    async def enqueue_cron_task(self, db: AsyncSession, task: CronTask):
        """Enqueue a single cron task for execution"""
        try:
            # Enqueue to arq
            job = await self.redis_pool.enqueue_job(
                "execute_http_task",
                task_type="cron",
                task_id=str(task.id),
                workspace_id=str(task.workspace_id),
                url=str(task.url),
                method=task.method.value,
                headers=task.headers or {},
                body=task.body,
                timeout=task.timeout_seconds,
                retry_count=task.retry_count,
            )
            
            # Calculate next run time
            import pytz
            tz = pytz.timezone(task.timezone)
            cron = croniter(task.schedule, datetime.now(tz))
            next_run = cron.get_next(datetime)
            
            # Update task
            task.next_run_at = next_run.replace(tzinfo=None)  # Store as UTC
            await db.commit()
            
            logger.debug(
                "Enqueued cron task",
                task_id=str(task.id),
                job_id=job.job_id,
                next_run=task.next_run_at.isoformat()
            )
            
        except Exception as e:
            logger.error("Failed to enqueue cron task", task_id=str(task.id), error=str(e))
    
    async def process_due_delayed_tasks(self):
        """Find and enqueue delayed tasks that are due"""
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            
            # Find pending tasks where execute_at <= now
            stmt = select(DelayedTask).where(
                and_(
                    DelayedTask.status == TaskStatus.PENDING,
                    DelayedTask.execute_at <= now
                )
            ).limit(100)
            
            result = await db.execute(stmt)
            tasks = result.scalars().all()
            
            for task in tasks:
                await self.enqueue_delayed_task(db, task)
            
            if tasks:
                logger.info(f"Enqueued {len(tasks)} delayed tasks")
    
    async def enqueue_delayed_task(self, db: AsyncSession, task: DelayedTask):
        """Enqueue a single delayed task for execution"""
        try:
            # Mark as running
            task.status = TaskStatus.RUNNING
            await db.commit()
            
            # Enqueue to arq
            await self.redis_pool.enqueue_job(
                "execute_http_task",
                task_type="delayed",
                task_id=str(task.id),
                workspace_id=str(task.workspace_id),
                url=str(task.url),
                method=task.method.value,
                headers=task.headers or {},
                body=task.body,
                timeout=task.timeout_seconds,
                retry_count=task.retry_count,
                callback_url=task.callback_url,
            )
            
            logger.debug("Enqueued delayed task", task_id=str(task.id))
            
        except Exception as e:
            logger.error("Failed to enqueue delayed task", task_id=str(task.id), error=str(e))
            task.status = TaskStatus.PENDING  # Reset status
            await db.commit()
    
    async def update_next_run_times(self):
        """Update next_run_at for tasks that don't have it set"""
        async with AsyncSessionLocal() as db:
            import pytz
            
            stmt = select(CronTask).where(
                and_(
                    CronTask.is_active == True,
                    CronTask.next_run_at == None
                )
            )
            
            result = await db.execute(stmt)
            tasks = result.scalars().all()
            
            for task in tasks:
                try:
                    tz = pytz.timezone(task.timezone)
                    cron = croniter(task.schedule, datetime.now(tz))
                    task.next_run_at = cron.get_next(datetime).replace(tzinfo=None)
                except Exception as e:
                    logger.error("Failed to calculate next run", task_id=str(task.id), error=str(e))
            
            await db.commit()


# Entry point for running scheduler
async def run_scheduler():
    """Run the scheduler as a standalone process"""
    scheduler = TaskScheduler()
    await scheduler.start()
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
```

---

## 8. Notifications

### 8.1 Notification Service

```python
# app/services/notifications.py
import structlog
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workspace import Workspace
from app.models.cron_task import CronTask
from app.models.notification_settings import NotificationSettings

logger = structlog.get_logger()


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._telegram_bot = None
        self._email_sender = None
    
    @property
    def telegram_bot(self):
        if self._telegram_bot is None:
            from app.services.telegram import TelegramBot
            self._telegram_bot = TelegramBot()
        return self._telegram_bot
    
    @property
    def email_sender(self):
        if self._email_sender is None:
            from app.services.email import EmailSender
            self._email_sender = EmailSender()
        return self._email_sender
    
    async def get_notification_settings(self, workspace_id: UUID) -> NotificationSettings | None:
        stmt = select(NotificationSettings).where(
            NotificationSettings.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def send_task_failed(self, task: CronTask, execution_data: dict):
        """Send notification when task fails"""
        settings = await self.get_notification_settings(task.workspace_id)
        if not settings:
            return
        
        # Get workspace for owner info
        workspace = await self.db.get(Workspace, task.workspace_id)
        if not workspace:
            return
        
        notification_data = {
            "task_name": task.name,
            "task_id": str(task.id),
            "url": str(task.url),
            "error_message": execution_data.get("error_message", "Unknown error"),
            "status_code": execution_data.get("response_status_code"),
            "consecutive_failures": task.consecutive_failures + 1,
            "workspace_name": workspace.name,
            "workspace_id": str(workspace.id),
        }
        
        # Send via enabled channels
        if settings.telegram_enabled and settings.telegram_chat_ids:
            for chat_id in settings.telegram_chat_ids:
                try:
                    await self.telegram_bot.send_task_failed(chat_id, notification_data)
                except Exception as e:
                    logger.error("Failed to send Telegram notification", error=str(e))
        
        if settings.email_enabled and settings.email_addresses:
            for email in settings.email_addresses:
                try:
                    await self.email_sender.send_task_failed(email, notification_data)
                except Exception as e:
                    logger.error("Failed to send email notification", error=str(e))
        
        if settings.webhook_enabled and settings.webhook_url:
            try:
                await self.send_webhook(settings.webhook_url, settings.webhook_secret, {
                    "event": "task.failed",
                    "data": notification_data
                })
            except Exception as e:
                logger.error("Failed to send webhook notification", error=str(e))
    
    async def send_task_recovered(self, task: CronTask, execution_data: dict):
        """Send notification when task recovers from failure"""
        settings = await self.get_notification_settings(task.workspace_id)
        if not settings:
            return
        
        workspace = await self.db.get(Workspace, task.workspace_id)
        if not workspace:
            return
        
        notification_data = {
            "task_name": task.name,
            "task_id": str(task.id),
            "url": str(task.url),
            "previous_failures": task.consecutive_failures,
            "workspace_name": workspace.name,
            "workspace_id": str(workspace.id),
        }
        
        if settings.telegram_enabled and settings.telegram_chat_ids:
            for chat_id in settings.telegram_chat_ids:
                try:
                    await self.telegram_bot.send_task_recovered(chat_id, notification_data)
                except Exception as e:
                    logger.error("Failed to send Telegram notification", error=str(e))
        
        if settings.email_enabled and settings.email_addresses:
            for email in settings.email_addresses:
                try:
                    await self.email_sender.send_task_recovered(email, notification_data)
                except Exception as e:
                    logger.error("Failed to send email notification", error=str(e))
    
    async def send_webhook(self, url: str, secret: str, payload: dict):
        """Send webhook notification"""
        import httpx
        import hmac
        import hashlib
        import json
        import time
        
        timestamp = int(time.time())
        body = json.dumps(payload)
        
        # Create signature
        signature_payload = f"{timestamp}.{body}"
        signature = hmac.new(
            secret.encode(),
            signature_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-CronBox-Signature": f"sha256={signature}",
                    "X-CronBox-Timestamp": str(timestamp),
                }
            )
```

### 8.2 Telegram Bot

```python
# app/services/telegram.py
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.config import settings

bot = Bot(token=settings.telegram_bot_token, parse_mode=ParseMode.HTML)


class TelegramBot:
    def __init__(self):
        self.bot = bot
    
    async def send_task_failed(self, chat_id: int, data: dict):
        """Send task failed notification"""
        text = f"""
🔴 <b>Task Failed</b>

<b>Task:</b> {self._escape(data['task_name'])}
<b>URL:</b> <code>{self._escape(data['url'])}</code>
<b>Error:</b> {self._escape(data['error_message'])}
<b>Failures:</b> {data['consecutive_failures']} in a row

<a href="https://cronbox.ru/w/{data['workspace_id']}/cron/{data['task_id']}">View Task</a>
"""
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True
        )
    
    async def send_task_recovered(self, chat_id: int, data: dict):
        """Send task recovered notification"""
        text = f"""
🟢 <b>Task Recovered</b>

<b>Task:</b> {self._escape(data['task_name'])}
<b>URL:</b> <code>{self._escape(data['url'])}</code>
<b>Previous failures:</b> {data['previous_failures']}

The task is now working correctly.
"""
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True
        )
    
    def _escape(self, text: str) -> str:
        """Escape HTML special characters"""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


# Bot command handlers for linking accounts
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот CronBox.\n\n"
        "Используй /link <код> чтобы привязать аккаунт.\n"
        "Код можно получить в настройках cronbox.ru"
    )


@dp.message(Command("link"))
async def cmd_link(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Используй: /link <код>\n"
            "Код можно получить в настройках cronbox.ru"
        )
        return
    
    code = args[1].strip()
    
    # Here we would verify the code and link the account
    # This requires access to the database
    from app.services.auth import AuthService
    from app.db.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        auth_service = AuthService(db)
        user = await auth_service.link_telegram_by_code(
            code=code,
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username
        )
        
        if user:
            await message.answer(
                f"✅ Аккаунт {user.email} успешно привязан!\n"
                "Теперь вы будете получать уведомления здесь."
            )
        else:
            await message.answer(
                "❌ Неверный или истёкший код.\n"
                "Получите новый код в настройках cronbox.ru"
            )


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    await message.answer("✅ Бот работает нормально")


async def run_bot():
    """Run the Telegram bot"""
    await dp.start_polling(bot)
```

### 8.3 Email Service

```python
# app/services/email.py
import resend
from app.config import settings

resend.api_key = settings.resend_api_key


class EmailSender:
    def __init__(self):
        self.from_email = "CronBox <noreply@cronbox.ru>"
    
    async def send_task_failed(self, to: str, data: dict):
        """Send task failed email"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #EF4444; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
        .field {{ margin-bottom: 12px; }}
        .label {{ font-weight: 600; color: #374151; }}
        .value {{ color: #6b7280; }}
        .button {{ 
            display: inline-block; 
            background: #3B82F6; 
            color: white; 
            padding: 12px 24px; 
            border-radius: 6px; 
            text-decoration: none;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">🔴 Task Failed</h2>
        </div>
        <div class="content">
            <div class="field">
                <span class="label">Task:</span>
                <span class="value">{data['task_name']}</span>
            </div>
            <div class="field">
                <span class="label">URL:</span>
                <span class="value">{data['url']}</span>
            </div>
            <div class="field">
                <span class="label">Error:</span>
                <span class="value">{data['error_message']}</span>
            </div>
            <div class="field">
                <span class="label">Consecutive failures:</span>
                <span class="value">{data['consecutive_failures']}</span>
            </div>
            <a href="https://cronbox.ru/w/{data['workspace_id']}/cron/{data['task_id']}" class="button">
                View Task
            </a>
        </div>
    </div>
</body>
</html>
"""
        
        resend.Emails.send({
            "from": self.from_email,
            "to": to,
            "subject": f"⚠️ Task Failed: {data['task_name']}",
            "html": html,
        })
    
    async def send_task_recovered(self, to: str, data: dict):
        """Send task recovered email"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #10B981; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">🟢 Task Recovered</h2>
        </div>
        <div class="content">
            <p><strong>{data['task_name']}</strong> is now working correctly.</p>
            <p>Previous failures: {data['previous_failures']}</p>
        </div>
    </div>
</body>
</html>
"""
        
        resend.Emails.send({
            "from": self.from_email,
            "to": to,
            "subject": f"✅ Task Recovered: {data['task_name']}",
            "html": html,
        })
```

---

## 9. Billing (YooKassa)

```python
# app/services/billing.py
from uuid import UUID
from datetime import datetime, timedelta
from yookassa import Configuration, Payment
from yookassa.domain.models import Amount, Confirmation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.payment import Payment as PaymentModel, PaymentStatus
from app.models.plan import Plan
from app.models.workspace import Workspace

# Configure YooKassa
Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_subscription_payment(
        self,
        workspace_id: UUID,
        plan_id: UUID,
        return_url: str,
    ) -> str:
        """Create a payment for subscription and return confirmation URL"""
        
        # Get plan
        plan = await self.db.get(Plan, plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        workspace = await self.db.get(Workspace, workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        
        # Create payment record
        payment_record = PaymentModel(
            workspace_id=workspace_id,
            amount=plan.price_monthly,
            currency="RUB",
            status=PaymentStatus.PENDING,
            description=f"Подписка CronBox {plan.display_name}",
            metadata={
                "plan_id": str(plan_id),
                "workspace_id": str(workspace_id),
            }
        )
        self.db.add(payment_record)
        await self.db.flush()
        
        # Create YooKassa payment
        payment = Payment.create({
            "amount": {
                "value": f"{plan.price_monthly / 100:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": f"Подписка CronBox {plan.display_name}",
            "save_payment_method": True,  # For recurring payments
            "metadata": {
                "payment_id": str(payment_record.id),
                "workspace_id": str(workspace_id),
                "plan_id": str(plan_id),
            }
        })
        
        # Update payment record with YooKassa ID
        payment_record.yookassa_payment_id = payment.id
        payment_record.yookassa_confirmation_url = payment.confirmation.confirmation_url
        await self.db.commit()
        
        return payment.confirmation.confirmation_url
    
    async def handle_payment_succeeded(self, yookassa_payment: dict):
        """Handle successful payment webhook from YooKassa"""
        
        payment_id = yookassa_payment["metadata"]["payment_id"]
        workspace_id = UUID(yookassa_payment["metadata"]["workspace_id"])
        plan_id = UUID(yookassa_payment["metadata"]["plan_id"])
        
        # Get or create subscription
        stmt = select(Subscription).where(
            Subscription.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        
        if subscription:
            # Update existing subscription
            subscription.plan_id = plan_id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = now
            subscription.current_period_end = period_end
            subscription.cancel_at_period_end = False
        else:
            # Create new subscription
            subscription = Subscription(
                workspace_id=workspace_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=period_end,
            )
            self.db.add(subscription)
        
        # Save payment method for recurring
        if yookassa_payment.get("payment_method", {}).get("saved"):
            subscription.yookassa_payment_method_id = yookassa_payment["payment_method"]["id"]
        
        # Update payment record
        stmt = select(PaymentModel).where(
            PaymentModel.id == UUID(payment_id)
        )
        result = await self.db.execute(stmt)
        payment_record = result.scalar_one_or_none()
        
        if payment_record:
            payment_record.status = PaymentStatus.SUCCEEDED
            payment_record.paid_at = now
            payment_record.yookassa_payment_method = yookassa_payment.get("payment_method")
        
        # Update workspace plan
        workspace = await self.db.get(Workspace, workspace_id)
        if workspace:
            workspace.plan_id = plan_id
        
        await self.db.commit()
    
    async def cancel_subscription(self, workspace_id: UUID) -> Subscription:
        """Cancel subscription at period end"""
        stmt = select(Subscription).where(
            Subscription.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError("No active subscription")
        
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = datetime.utcnow()
        await self.db.commit()
        
        return subscription
    
    async def renew_subscriptions(self):
        """Renew expiring subscriptions (run daily)"""
        
        # Find subscriptions expiring in 3 days
        expiry_threshold = datetime.utcnow() + timedelta(days=3)
        
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= expiry_threshold,
            Subscription.cancel_at_period_end == False,
            Subscription.yookassa_payment_method_id != None
        )
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()
        
        for subscription in subscriptions:
            await self._process_renewal(subscription)
    
    async def _process_renewal(self, subscription: Subscription):
        """Process automatic renewal for a subscription"""
        plan = await self.db.get(Plan, subscription.plan_id)
        if not plan:
            return
        
        try:
            # Create recurring payment
            payment = Payment.create({
                "amount": {
                    "value": f"{plan.price_monthly / 100:.2f}",
                    "currency": "RUB"
                },
                "capture": True,
                "payment_method_id": subscription.yookassa_payment_method_id,
                "description": f"Автопродление подписки CronBox {plan.display_name}",
                "metadata": {
                    "workspace_id": str(subscription.workspace_id),
                    "plan_id": str(plan.id),
                    "renewal": "true"
                }
            })
            
            # Payment will be processed via webhook
            
        except Exception as e:
            # Mark subscription as past_due
            subscription.status = SubscriptionStatus.PAST_DUE
            await self.db.commit()
            
            # Send notification about failed payment
            # ...
```

---

## 10. Docker & Deployment

### 10.1 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -m -u 1000 cronbox
USER cronbox

# Default command (API server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # ===================
  # API
  # ===================
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://cronbox:${DB_PASSWORD}@postgres:5432/cronbox
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}
      - YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - RESEND_API_KEY=${RESEND_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 512M

  # ===================
  # SCHEDULER
  # ===================
  scheduler:
    build: ./backend
    command: ["python", "-m", "app.workers.scheduler"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://cronbox:${DB_PASSWORD}@postgres:5432/cronbox
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      replicas: 1

  # ===================
  # ARQ WORKER
  # ===================
  worker:
    build: ./backend
    command: ["arq", "app.workers.settings.WorkerSettings"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://cronbox:${DB_PASSWORD}@postgres:5432/cronbox
      - REDIS_URL=redis://redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - RESEND_API_KEY=${RESEND_API_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # ===================
  # TELEGRAM BOT
  # ===================
  telegram-bot:
    build: ./backend
    command: ["python", "-m", "app.services.telegram"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://cronbox:${DB_PASSWORD}@postgres:5432/cronbox
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    depends_on:
      - postgres
    restart: unless-stopped

  # ===================
  # FRONTEND
  # ===================
  frontend:
    build:
      context: ./frontend
      args:
        - VITE_API_URL=https://api.cronbox.ru
    restart: unless-stopped

  # ===================
  # NGINX
  # ===================
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certbot/conf:/etc/letsencrypt:ro
    depends_on:
      - api
      - frontend
    restart: unless-stopped

  # ===================
  # POSTGRESQL
  # ===================
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=cronbox
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=cronbox
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cronbox"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ===================
  # REDIS
  # ===================
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 11. План разработки по этапам

### Этап 1: MVP Core (3-4 недели)

```
Неделя 1-2: Backend Core
├── [ ] Инициализация проекта Python + FastAPI
├── [ ] Структура проекта
├── [ ] PostgreSQL + SQLAlchemy models
├── [ ] Alembic миграции
├── [ ] Redis подключение
├── [ ] Auth: регистрация, логин, JWT
├── [ ] CRUD Workspaces
├── [ ] CRUD Cron Tasks
├── [ ] CRUD Delayed Tasks
├── [ ] API Keys генерация/валидация
└── [ ] Базовые тесты (pytest)

Неделя 3: Scheduler & Workers
├── [ ] APScheduler setup
├── [ ] arq workers
├── [ ] HTTP executor (httpx)
├── [ ] Retry logic
├── [ ] Execution logging
└── [ ] Интеграционные тесты

Неделя 4: Frontend MVP
├── [ ] Vite + React + TypeScript setup
├── [ ] Auth pages (login, register)
├── [ ] Dashboard (базовый)
├── [ ] Cron tasks list/create/edit
├── [ ] Delayed tasks list/create
├── [ ] Executions list
└── [ ] API integration (React Query)
```

### Этап 2: Billing + Notifications (2-3 недели)

```
Неделя 5: Биллинг
├── [ ] Models: Plan, Subscription, Payment
├── [ ] YooKassa интеграция
├── [ ] Webhook обработка
├── [ ] Страница выбора тарифа
├── [ ] История платежей
├── [ ] Лимиты по тарифам
└── [ ] Автопродление

Неделя 6: Уведомления
├── [ ] Email через Resend
├── [ ] Telegram бот (aiogram)
├── [ ] Привязка Telegram
├── [ ] Уведомления о сбоях
├── [ ] Уведомления о восстановлении
├── [ ] Настройки уведомлений (UI)
└── [ ] Outgoing webhooks
```

### Этап 3: Polish + Admin (2 недели)

```
Неделя 7: Доработки
├── [ ] Улучшение UI/UX
├── [ ] Cron expression builder
├── [ ] Детальная статистика
├── [ ] API документация (OpenAPI)
├── [ ] Rate limiting
└── [ ] Error handling

Неделя 8: Admin + Deploy
├── [ ] Admin panel
├── [ ] Docker production setup
├── [ ] CI/CD (GitHub Actions)
├── [ ] SSL + домен
├── [ ] Мониторинг (Prometheus + Grafana)
└── [ ] Логирование (structlog)
```

### Этап 4: Launch (1 неделя)

```
Неделя 9: Запуск
├── [ ] Security audit
├── [ ] Performance testing
├── [ ] Backup strategy
├── [ ] User documentation
├── [ ] Landing page
├── [ ] Хабр статья
└── [ ] Soft launch
```

---

## 12. Команды для Claude Code

### Инициализация проекта

```bash
# Создать структуру проекта
mkdir -p cronbox/{backend,frontend,nginx/conf.d}
cd cronbox/backend

# Инициализировать Python проект
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy asyncpg alembic redis arq httpx pydantic pydantic-settings passlib python-jose croniter apscheduler aiogram resend yookassa structlog orjson pytest pytest-asyncio

# Создать структуру
mkdir -p app/{api/v1,core,db/repositories,models,schemas,services,workers}
touch app/__init__.py app/main.py app/config.py
```

### Запуск для разработки

```bash
# База данных
docker compose up -d postgres redis

# Миграции
alembic upgrade head

# API сервер
uvicorn app.main:app --reload --port 8000

# arq worker (отдельный терминал)
arq app.workers.settings.WorkerSettings

# Scheduler (отдельный терминал)
python -m app.workers.scheduler
```

---

## 13. Критическая оценка

### ✅ Что сделано:

1. **Полный Python-стек** — FastAPI, SQLAlchemy 2.0, arq, все async
2. **Структура проекта** — готова к реализации
3. **Все модели** — User, Workspace, CronTask, DelayedTask, Execution, Payment
4. **API роутеры** — с примерами кода
5. **Scheduler + Workers** — APScheduler + arq
6. **Уведомления** — Telegram (aiogram), Email (Resend), Webhooks
7. **Биллинг** — YooKassa с рекуррентными платежами
8. **Docker** — готовые конфиги для prod
9. **План разработки** — 9 недель с задачами

### ⚠️ Отличия от Go-версии:

| Аспект | Go | Python |
|--------|-----|--------|
| Потребление памяти | ~20 MB/worker | ~50-80 MB/worker |
| Параллелизм | goroutines | asyncio (достаточно) |
| Деплой | 1 бинарник | Docker + venv |
| Скорость разработки | Медленнее | **Быстрее** |
| Твоё понимание кода | ❌ | ✅ |

### 📊 Готовность: **95%**

План полностью готов к реализации с Claude Code.

---

**Готов начать разработку! 🚀**

Скажи "начинай" — и я создам первые файлы проекта.

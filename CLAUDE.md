# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CronBox is an HTTP request scheduling service with cron and delayed task capabilities. The project consists of three main parts:
- **Backend** (`/backend`): Python FastAPI application with SQLAlchemy, Redis, and APScheduler
- **Frontend** (`/frontend`): React 19 control panel with Vite, TailwindCSS, and Zustand
- **Landing** (`/landing`): Next.js marketing site

## Development Commands

### Start all services (recommended)
```bash
make dev          # Starts API, scheduler, worker, bot, frontend, and landing
make stop         # Stop all services
```

### Individual services
```bash
make dev-backend    # API server (port 8000)
make dev-frontend   # Control panel (port 3000)
make dev-landing    # Landing page (port 3001)
make dev-scheduler  # Task scheduler
make dev-worker     # Task executor
make dev-bot        # Telegram bot
```

### Infrastructure
```bash
make infra        # Start PostgreSQL + Redis via Docker
```

### Testing
```bash
# Backend tests (requires test DB)
make test-db                              # Create test database
cd backend && uv run pytest tests -v      # Run all tests
cd backend && uv run pytest tests/test_auth.py -v  # Single test file
cd backend && uv run pytest tests -v -k "test_name"  # Single test

# Frontend tests
cd frontend && npm run test               # Run all tests
cd frontend && npm run test:watch         # Watch mode
cd frontend && npm run test:coverage      # With coverage
```

### Linting & Type Checking
```bash
# Backend
cd backend && uv run ruff check .         # Linting
cd backend && uv run ruff format .        # Formatting
cd backend && uv run mypy app --ignore-missing-imports

# Frontend
cd frontend && npm run lint               # ESLint
cd frontend && npm run build              # Includes TypeScript check
```

### Database Migrations
```bash
cd backend
uv run alembic upgrade head                               # Apply migrations
uv run alembic revision --autogenerate -m "description"   # Create migration
uv run alembic downgrade -1                               # Rollback last
```

## Architecture

### Backend Structure (`/backend/app`)

**Layered Architecture:**
- `api/v1/` - FastAPI route handlers (thin layer, delegates to services)
- `services/` - Business logic (auth, billing, notifications, worker)
- `db/repositories/` - Data access layer (SQLAlchemy queries)
- `models/` - SQLAlchemy ORM models
- `schemas/` - Pydantic request/response models
- `core/` - Cross-cutting concerns (security, redis, rate limiter)

**Dependency Injection Pattern** (see `api/deps.py`):
```python
from app.api.deps import CurrentUser, DB, CurrentWorkspace

@router.get("/items")
async def list_items(user: CurrentUser, db: DB):
    ...
```

Key type aliases: `CurrentUser`, `VerifiedUser`, `CurrentWorkspace`, `ActiveSubscriptionWorkspace`, `DB`, `UserPlan`

**Key Services:**
- `auth.py` - JWT auth, OAuth (Yandex, GitHub), email verification
- `billing.py` - YooKassa payments, subscriptions, plan limits
- `notifications.py` - Email, Telegram, Slack, webhook notifications
- `worker.py` - HTTP task execution logic

### Frontend Structure (`/frontend/src`)

**State Management:** Zustand stores in `/stores`
- `authStore.ts` - User authentication state
- `workspaceStore.ts` - Current workspace selection
- `uiStore.ts` - UI preferences (sidebar, theme)

**API Layer:** `/api` directory with typed API clients
- Uses axios with interceptors for auth tokens
- Consistent error handling pattern

**Routing:** Hash-based routing in `App.tsx` (not React Router)
- Auth routes: login, register, verify-email, otp-login
- Protected routes: dashboard, cron, delayed, executions, etc.

**UI Components:** Radix UI primitives with TailwindCSS
- Components in `/components/ui` follow shadcn/ui patterns

### Landing (`/landing`)

Next.js 14+ with App Router, MDX for blog content.

## Key Patterns

### Adding a New API Endpoint
1. Create Pydantic schemas in `schemas/`
2. Add repository methods in `db/repositories/`
3. Implement business logic in `services/`
4. Create route handler in `api/v1/`
5. Include router in `api/router.py`

### Adding a New Frontend Page
1. Create page component in `pages/`
2. Add lazy import in `App.tsx`
3. Add route type and handler in `App.tsx`
4. Update navigation in `components/layout/`

### Environment Variables
Backend: `/backend/.env` (see `.env.example`)
Frontend: Uses Vite env vars (VITE_* prefix)
Landing: `/landing/.env.example`

## Testing Patterns

**Backend:** pytest-asyncio with fixtures in `conftest.py`
- Use `async_client` fixture for API tests
- Use `test_db` for database tests
- Tests are in `tests/` (integration) and `tests/unit/`

**Frontend:** Vitest with React Testing Library
- Tests colocated in `__tests__/` directories
- MSW for API mocking in `src/test/`

## Porduction

  - CI автоматически деплоит при push в main в github
  - SSH доступ: ssh cronbox
  - Авторизуешшься под su - cronbox
  - Путь на сервере: /opt/cronbox
  - Контейнеры называются cronbox-*
  - Можешь подключаться и проверять работу и логи после успешного деплоя
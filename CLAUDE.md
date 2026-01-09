# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CronBox.ru is an HTTP request scheduling SaaS platform. Users can schedule recurring cron tasks or one-time delayed tasks, monitor execution history, and receive notifications via email, Telegram, or webhooks.

## Common Commands

### Backend (Python/FastAPI)
```bash
# Dependencies (uses uv package manager)
uv sync --frozen

# Linting and type checking
uv run ruff check .
uv run mypy app --ignore-missing-imports

# Testing
uv run pytest tests -v --cov=app --cov-report=xml

# Database migrations
uv run alembic upgrade head
uv run alembic downgrade -1

# Run services (via CLI entry points defined in pyproject.toml)
cronbox-server       # Start FastAPI API server
cronbox-worker       # Start arq task worker
cronbox-scheduler    # Start task scheduler
```

### Frontend (React/TypeScript/Vite)
```bash
cd frontend
npm install
npm run dev          # Dev server on port 3000
npm run build        # Production build
npm run lint         # ESLint check
```

### Development with Make
```bash
make dev             # Start full stack (backend + frontend + infrastructure)
make dev-backend     # Backend only
make dev-frontend    # Frontend only
make infra           # Start PostgreSQL + Redis containers
make stop            # Stop all services
```

## Architecture

### Multi-Process Backend
The backend runs as three separate processes:
1. **API Server** (Uvicorn/FastAPI) - REST API on port 8000
2. **Scheduler** - Polls database every 5-10 seconds for due tasks, enqueues them to Redis
3. **Worker Pool** (arq) - Consumes from Redis queue, executes HTTP requests, stores results

### Key Backend Directories
- `backend/app/api/v1/` - API endpoints organized by resource
- `backend/app/models/` - SQLAlchemy ORM models (all inherit from `Base` with UUID pk + timestamps)
- `backend/app/schemas/` - Pydantic request/response schemas
- `backend/app/services/` - Business logic (auth, billing, email, notifications)
- `backend/app/workers/` - Task scheduler and arq worker functions
- `backend/app/db/repositories/` - Data access layer

### Key Frontend Directories
- `frontend/src/api/` - Axios API client modules
- `frontend/src/pages/` - Route page components
- `frontend/src/components/ui/` - Radix UI wrapped components
- `frontend/src/stores/` - Zustand state stores (auth, workspace, ui)

### Data Flow for Task Execution
1. User creates cron/delayed task via API
2. Scheduler polls PostgreSQL for tasks where `next_run_at <= now`
3. Scheduler enqueues task to Redis via arq
4. Worker executes HTTP request, stores execution record
5. Worker sends notifications based on user settings

### Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Redis, arq
- **Frontend**: React 19, TypeScript, Vite, TanStack Router/Query, Zustand, Radix UI, Tailwind CSS
- **Auth**: JWT with 15-min access tokens, 30-day refresh tokens
- **Payments**: YooKassa (Russian payment processor)
- **Email**: Postal API (primary) with SMTP fallback
- **Notifications**: Telegram (aiogram), webhooks

## Environment Variables

Key variables needed (see `.env.example` for full list):
- `DATABASE_URL` - PostgreSQL connection string (asyncpg)
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - Secret for JWT signing
- `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` - Payment processing
- `TELEGRAM_BOT_TOKEN` - Telegram notifications
- `POSTAL_API_URL`, `POSTAL_API_KEY` - Email service

## Database

PostgreSQL with async SQLAlchemy. Migrations in `backend/alembic/versions/`. Apply with `uv run alembic upgrade head`.

Core models: User, Workspace, CronTask, DelayedTask, Execution, NotificationSettings, Plan, Subscription, Payment, Worker

## API Documentation

Swagger UI available at `http://localhost:8000/v1/docs` when running locally.

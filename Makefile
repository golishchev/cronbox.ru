.PHONY: dev dev-backend dev-frontend infra stop test test-cov lint

# Start all dev services (backend + frontend in background)
dev: infra
	@echo "Starting API server..."
	@cd backend && uv run python -m app.cli server &
	@echo "Starting scheduler..."
	@cd backend && uv run python -m app.cli scheduler &
	@echo "Starting worker..."
	@cd backend && uv run python -m app.cli worker &
	@echo "Starting frontend..."
	@cd frontend && npm run dev &
	@echo ""
	@echo "Dev servers started:"
	@echo "  API:       http://localhost:8000"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Scheduler: running"
	@echo "  Worker:    running"
	@echo ""
	@echo "Run 'make stop' to stop all services"

# Infrastructure (PostgreSQL + Redis)
infra:
	docker-compose up -d

# Backend dev server (foreground)
dev-backend:
	cd backend && uv run python -m app.cli server

# Scheduler (foreground)
dev-scheduler:
	cd backend && uv run python -m app.cli scheduler

# Worker (foreground)
dev-worker:
	cd backend && uv run python -m app.cli worker

# Frontend dev server (foreground)
dev-frontend:
	cd frontend && npm run dev

# Stop all services
stop:
	-docker-compose down
	-pkill -f "app.cli server" 2>/dev/null || true
	-pkill -f "app.cli scheduler" 2>/dev/null || true
	-pkill -f "app.cli worker" 2>/dev/null || true
	-pkill -f "uvicorn" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true
	@echo "All services stopped"

# Run all tests
test:
	cd backend && uv run pytest tests -v
	cd frontend && npm run test

# Run tests with coverage
test-cov:
	cd backend && uv run pytest tests -v --cov=app --cov-report=term-missing
	cd frontend && npm run test:coverage

# Lint and type check
lint:
	cd backend && uv run ruff check .
	cd backend && uv run mypy app --ignore-missing-imports

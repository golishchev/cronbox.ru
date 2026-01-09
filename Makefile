.PHONY: dev dev-backend dev-frontend infra stop logs

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

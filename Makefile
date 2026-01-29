.PHONY: dev dev-backend dev-frontend dev-landing infra stop test test-cov lint test-db backup restore backup-list dev-max-bot

# Start all dev services (backend + frontend + landing in background)
dev: infra
	@echo "Starting API server..."
	@cd backend && uv run python -m app.cli server &
	@echo "Starting scheduler..."
	@cd backend && uv run python -m app.cli scheduler &
	@echo "Starting worker..."
	@cd backend && uv run python -m app.cli worker &
	@echo "Starting Telegram bot..."
	@cd backend && uv run python -m app.cli bot &
	@echo "Starting MAX bot..."
	@cd backend && uv run python -m app.cli max-bot &
	@echo "Starting frontend (control panel)..."
	@cd frontend && npm run dev &
	@echo "Starting landing page..."
	@cd landing && npm run dev &
	@echo ""
	@echo "Dev servers started:"
	@echo "  API:       http://localhost:8000"
	@echo "  Frontend:  http://localhost:3000 (cp.cronbox.ru)"
	@echo "  Landing:   http://localhost:3001 (cronbox.ru)"
	@echo "  Scheduler: running"
	@echo "  Worker:    running"
	@echo "  Bot:       running"
	@echo "  Max Bot:   running"
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

# Telegram bot (foreground)
dev-bot:
	cd backend && uv run python -m app.cli bot

# MAX bot (foreground)
dev-max-bot:
	cd backend && uv run python -m app.cli max-bot

# Frontend dev server (foreground)
dev-frontend:
	cd frontend && npm run dev

# Landing page dev server (foreground)
dev-landing:
	cd landing && npm run dev

# Stop all services
stop:
	@echo "Stopping Python processes..."
	-pkill -f "app.cli server" 2>/dev/null || true
	-pkill -f "app.cli scheduler" 2>/dev/null || true
	-pkill -f "app.cli worker" 2>/dev/null || true
	-pkill -f "app.cli bot" 2>/dev/null || true
	-pkill -f "app.cli max-bot" 2>/dev/null || true
	-pkill -f "uvicorn" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true
	-pkill -f "next dev" 2>/dev/null || true
	@sleep 1
	@echo "Stopping Docker containers..."
	-docker-compose down
	@echo "All services stopped"

# Create test database if not exists
test-db: infra
	@docker exec cronbox-postgres psql -U cronbox -tc "SELECT 1 FROM pg_database WHERE datname = 'cronbox_test'" | grep -q 1 || \
		docker exec cronbox-postgres psql -U cronbox -c "CREATE DATABASE cronbox_test;"

# Run all tests
test: test-db
	cd backend && uv run pytest tests -v
	cd frontend && npm run test

# Run tests with coverage
test-cov: test-db
	cd backend && uv run pytest tests -v --cov=app --cov-report=term-missing
	cd frontend && npm run test:coverage

# Lint and type check
lint:
	cd backend && uv run ruff check .
	cd backend && uv run mypy app --ignore-missing-imports
	cd frontend && npm run lint
	cd landing && npm run lint

# Backup database and uploads (for dev environment)
backup:
	@mkdir -p backups
	@echo "Backing up database..."
	@docker exec cronbox-postgres pg_dump -U cronbox cronbox | gzip > backups/db_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "Backup complete: backups/db_$$(date +%Y%m%d_%H%M%S).sql.gz"

# Restore from latest backup (for dev environment)
restore:
	@./scripts/restore.sh --latest

# List available backups
backup-list:
	@./scripts/restore.sh --list

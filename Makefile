.PHONY: dev dev-backend dev-frontend infra stop logs

# Start all dev services (backend + frontend in background)
dev: infra
	@echo "Starting backend..."
	@cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	@cd frontend && npm run dev &
	@echo ""
	@echo "Dev servers started:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo ""
	@echo "Run 'make stop' to stop all services"

# Infrastructure (PostgreSQL + Redis)
infra:
	docker-compose up -d

# Backend dev server (foreground)
dev-backend:
	cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev server (foreground)
dev-frontend:
	cd frontend && npm run dev

# Stop all services
stop:
	-docker-compose down
	-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true
	@echo "All services stopped"

#!/bin/bash
# CronBox Deployment Script
# Usage: ./deploy.sh [service] [tag]

set -euo pipefail

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
REGISTRY="${CI_REGISTRY:-registry.gitlab.com}"
PROJECT="${CI_PROJECT_PATH:-cronbox/cronbox.ru}"
TAG="${2:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Health check function
health_check() {
    local service=$1
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy"; then
            log_info "$service is healthy!"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done

    log_error "$service failed health check after $max_attempts attempts"
    return 1
}

# Deploy single service
deploy_service() {
    local service=$1
    log_info "Deploying $service..."

    # Pull latest image
    docker compose -f "$COMPOSE_FILE" pull "$service"

    # Rolling update
    docker compose -f "$COMPOSE_FILE" up -d --no-deps "$service"

    # Wait for health
    health_check "$service"
}

# Deploy all services
deploy_all() {
    log_info "Starting full deployment..."

    # Pull all images
    log_info "Pulling images..."
    docker compose -f "$COMPOSE_FILE" pull

    # Deploy in order: infrastructure first, then app
    log_info "Deploying services..."

    # API (with rolling update for replicas)
    docker compose -f "$COMPOSE_FILE" up -d --no-deps api
    sleep 5

    # Workers
    docker compose -f "$COMPOSE_FILE" up -d --no-deps worker scheduler

    # Frontend services
    docker compose -f "$COMPOSE_FILE" up -d --no-deps frontend landing

    log_info "Deployment complete!"
}

# Rollback to previous version
rollback() {
    local service=$1
    log_warn "Rolling back $service..."

    docker compose -f "$COMPOSE_FILE" up -d --no-deps "$service"

    log_info "Rollback complete"
}

# Show status
status() {
    docker compose -f "$COMPOSE_FILE" ps
}

# Main
case "${1:-all}" in
    api|frontend|landing|worker|scheduler)
        deploy_service "$1"
        ;;
    all)
        deploy_all
        ;;
    status)
        status
        ;;
    rollback)
        if [ -z "${2:-}" ]; then
            log_error "Usage: $0 rollback <service>"
            exit 1
        fi
        rollback "$2"
        ;;
    *)
        echo "Usage: $0 {api|frontend|landing|worker|scheduler|all|status|rollback <service>}"
        exit 1
        ;;
esac

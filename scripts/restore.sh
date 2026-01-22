#!/bin/bash
# CronBox Restore Script
# Restores database and uploads from backup files
#
# Usage:
#   ./restore.sh                           # Interactive mode - shows available backups
#   ./restore.sh db_20250122_030000.sql.gz # Restore specific database backup
#   ./restore.sh --latest                  # Restore latest backup

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/cronbox/backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-cronbox-postgres}"
UPLOADS_VOLUME="${UPLOADS_VOLUME:-cronbox_uploads_data}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# List available backups
list_backups() {
    echo "Available database backups:"
    echo "----------------------------------------"
    local count=0
    for f in $(ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null); do
        count=$((count + 1))
        local size
        size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)
        local date
        date=$(basename "$f" | sed 's/db_\([0-9]*\)_\([0-9]*\).*/\1 \2/' | sed 's/\(....\)\(..\)\(..\) \(..\)\(..\)\(..\)/\1-\2-\3 \4:\5:\6/')
        printf "%2d. %s (%s) - %s\n" "$count" "$(basename "$f")" "$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B")" "$date"
    done

    if [ "$count" -eq 0 ]; then
        echo "No backups found in $BACKUP_DIR"
        return 1
    fi

    echo ""
    echo "Available uploads backups:"
    echo "----------------------------------------"
    count=0
    for f in $(ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null); do
        count=$((count + 1))
        local size
        size=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)
        printf "%2d. %s (%s)\n" "$count" "$(basename "$f")" "$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B")"
    done

    if [ "$count" -eq 0 ]; then
        echo "No uploads backups found"
    fi
}

# Get latest backup file
get_latest_backup() {
    local type=$1
    ls -t "$BACKUP_DIR"/${type}_*.gz 2>/dev/null | head -1
}

# Restore database
restore_database() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi

    log "Restoring database from: $(basename "$backup_file")"
    log "WARNING: This will OVERWRITE the current database!"

    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        return 1
    fi

    log "Stopping dependent services..."
    docker stop cronbox-api cronbox-worker cronbox-scheduler cronbox-bot 2>/dev/null || true

    log "Dropping existing database..."
    docker exec "$POSTGRES_CONTAINER" dropdb -U cronbox --if-exists cronbox || true

    log "Creating fresh database..."
    docker exec "$POSTGRES_CONTAINER" createdb -U cronbox cronbox

    log "Restoring from backup..."
    gunzip -c "$backup_file" | docker exec -i "$POSTGRES_CONTAINER" psql -U cronbox cronbox

    log "Starting services..."
    docker start cronbox-api cronbox-worker cronbox-scheduler cronbox-bot 2>/dev/null || true

    log "Database restore complete!"
}

# Restore uploads
restore_uploads() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi

    log "Restoring uploads from: $(basename "$backup_file")"
    log "WARNING: This will OVERWRITE current uploads!"

    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        return 1
    fi

    log "Clearing existing uploads..."
    docker run --rm -v "${UPLOADS_VOLUME}:/data" alpine sh -c "rm -rf /data/*"

    log "Restoring from backup..."
    docker run --rm \
        -v "${UPLOADS_VOLUME}:/data" \
        -v "$(dirname "$backup_file"):/backup:ro" \
        alpine tar xzf "/backup/$(basename "$backup_file")" -C /data

    log "Uploads restore complete!"
}

# Main
main() {
    if [ ! -d "$BACKUP_DIR" ]; then
        error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi

    case "${1:-}" in
        --latest)
            log "Restoring from latest backups..."

            local db_backup
            db_backup=$(get_latest_backup "db")
            if [ -n "$db_backup" ]; then
                restore_database "$db_backup"
            else
                error "No database backups found"
            fi

            local uploads_backup
            uploads_backup=$(get_latest_backup "uploads")
            if [ -n "$uploads_backup" ]; then
                restore_uploads "$uploads_backup"
            else
                log "No uploads backups found, skipping"
            fi
            ;;

        --list)
            list_backups
            ;;

        db_*.sql.gz)
            restore_database "$BACKUP_DIR/$1"
            ;;

        uploads_*.tar.gz)
            restore_uploads "$BACKUP_DIR/$1"
            ;;

        "")
            list_backups
            echo ""
            echo "Usage:"
            echo "  $0 --latest                    Restore latest backup"
            echo "  $0 --list                      List available backups"
            echo "  $0 db_YYYYMMDD_HHMMSS.sql.gz   Restore specific database"
            echo "  $0 uploads_YYYYMMDD.tar.gz     Restore specific uploads"
            ;;

        *)
            # Try as full path
            if [ -f "$1" ]; then
                case "$1" in
                    *db_*.sql.gz)
                        restore_database "$1"
                        ;;
                    *uploads_*.tar.gz)
                        restore_uploads "$1"
                        ;;
                    *)
                        error "Unknown backup type: $1"
                        exit 1
                        ;;
                esac
            else
                error "File not found: $1"
                exit 1
            fi
            ;;
    esac
}

main "$@"

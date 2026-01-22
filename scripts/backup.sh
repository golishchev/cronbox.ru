#!/bin/bash
# CronBox Backup Script with Process Monitor Integration
# Runs daily via cron, sends START/END pings to CronBox for monitoring
#
# Setup:
# 1. Create a Process Monitor in CronBox UI with schedule "0 3 * * *" (3:00 AM daily)
# 2. Copy the START and END tokens from the monitor
# 3. Set them as environment variables or edit this script
# 4. Add to crontab: 0 3 * * * /opt/cronbox/scripts/backup.sh >> /var/log/cronbox-backup.log 2>&1

set -euo pipefail

# ==========================================
# Configuration
# ==========================================

# CronBox API URL
API_URL="${API_URL:-https://api.cronbox.ru}"

# Process Monitor tokens (get from CronBox UI)
# Create a Process Monitor named "Daily Backup" with cron "0 3 * * *"
BACKUP_START_TOKEN="${BACKUP_START_TOKEN:-}"
BACKUP_END_TOKEN="${BACKUP_END_TOKEN:-}"

# Backup settings
BACKUP_DIR="${BACKUP_DIR:-/opt/cronbox/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-cronbox-postgres}"
UPLOADS_VOLUME="${UPLOADS_VOLUME:-cronbox_uploads_data}"

# ==========================================
# Functions
# ==========================================

DATE=$(date +%Y%m%d_%H%M%S)
START_TIME=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Send start ping to CronBox
send_start_ping() {
    if [ -z "$BACKUP_START_TOKEN" ]; then
        log "WARNING: BACKUP_START_TOKEN not set, skipping monitoring"
        return 0
    fi

    log "Sending START ping to CronBox..."
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/ping/start/${BACKUP_START_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"message": "Backup started"}' 2>/dev/null) || true

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log "START ping sent successfully"
        return 0
    else
        log "WARNING: START ping failed (HTTP $http_code): $body"
        return 1
    fi
}

# Send end ping to CronBox with duration and payload
send_end_ping() {
    local status=$1
    local db_size=$2
    local uploads_size=$3
    local duration_ms=$4
    local message=$5

    if [ -z "$BACKUP_END_TOKEN" ]; then
        log "WARNING: BACKUP_END_TOKEN not set, skipping monitoring"
        return 0
    fi

    log "Sending END ping to CronBox..."

    # Build payload JSON
    local payload
    payload=$(cat <<EOF
{
    "duration_ms": ${duration_ms},
    "status": "${status}",
    "message": "${message}",
    "payload": {
        "database_size_bytes": ${db_size},
        "uploads_size_bytes": ${uploads_size},
        "backup_dir": "${BACKUP_DIR}",
        "retention_days": ${RETENTION_DAYS}
    }
}
EOF
)

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/ping/end/${BACKUP_END_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || true

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log "END ping sent successfully"
        return 0
    else
        log "WARNING: END ping failed (HTTP $http_code): $body"
        return 1
    fi
}

# Format bytes to human readable
format_bytes() {
    local bytes=$1
    if command -v numfmt &> /dev/null; then
        numfmt --to=iec-i --suffix=B "$bytes" 2>/dev/null || echo "${bytes} bytes"
    else
        echo "${bytes} bytes"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    find "$BACKUP_DIR" -name "*.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    log "Cleanup complete"
}

# ==========================================
# Main backup function
# ==========================================

main() {
    log "=========================================="
    log "Starting CronBox backup"
    log "=========================================="

    # Send start ping
    send_start_ping || true

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    local db_file="${BACKUP_DIR}/db_${DATE}.sql.gz"
    local uploads_file="${BACKUP_DIR}/uploads_${DATE}.tar.gz"
    local db_size=0
    local uploads_size=0
    local status="ok"
    local errors=""

    # ==========================================
    # Backup PostgreSQL
    # ==========================================
    log "Backing up PostgreSQL database..."
    if docker exec "$POSTGRES_CONTAINER" pg_dump -U cronbox cronbox 2>/dev/null | gzip > "$db_file"; then
        # Get file size (works on both Linux and macOS)
        if [ -f "$db_file" ]; then
            db_size=$(stat -c%s "$db_file" 2>/dev/null || stat -f%z "$db_file" 2>/dev/null || echo 0)
            log "Database backup complete: $db_file ($(format_bytes $db_size))"
        fi
    else
        log "ERROR: Database backup failed!"
        status="error"
        errors="${errors}Database backup failed. "
        rm -f "$db_file"
    fi

    # ==========================================
    # Backup uploads volume
    # ==========================================
    log "Backing up uploads..."
    if docker run --rm \
        -v "${UPLOADS_VOLUME}:/data:ro" \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/uploads_${DATE}.tar.gz" -C /data . 2>/dev/null; then
        if [ -f "$uploads_file" ]; then
            uploads_size=$(stat -c%s "$uploads_file" 2>/dev/null || stat -f%z "$uploads_file" 2>/dev/null || echo 0)
            log "Uploads backup complete: $uploads_file ($(format_bytes $uploads_size))"
        fi
    else
        log "WARNING: Uploads backup failed (volume may not exist)"
        rm -f "$uploads_file"
        uploads_size=0
        # Don't mark as error if only uploads failed
        if [ "$status" = "ok" ]; then
            status="warning"
            errors="${errors}Uploads backup skipped. "
        fi
    fi

    # ==========================================
    # Cleanup old backups
    # ==========================================
    cleanup_old_backups

    # ==========================================
    # Calculate duration and send end ping
    # ==========================================
    local end_time
    end_time=$(date +%s)
    local duration_sec=$((end_time - START_TIME))
    local duration_ms=$((duration_sec * 1000))

    # Build message
    local message
    if [ "$status" = "ok" ]; then
        message="Backup completed successfully. DB: $(format_bytes $db_size), Uploads: $(format_bytes $uploads_size)"
    elif [ "$status" = "warning" ]; then
        message="Backup completed with warnings. ${errors}DB: $(format_bytes $db_size)"
    else
        message="Backup failed. ${errors}"
    fi

    # Send end ping
    send_end_ping "$status" "$db_size" "$uploads_size" "$duration_ms" "$message" || true

    # ==========================================
    # Summary
    # ==========================================
    log "=========================================="
    log "Backup completed in ${duration_sec}s"
    log "Status: ${status}"
    log "Database: $(format_bytes $db_size)"
    log "Uploads: $(format_bytes $uploads_size)"
    log "Files retained: $(find "$BACKUP_DIR" -name "*.gz" 2>/dev/null | wc -l | tr -d ' ')"
    log "=========================================="

    if [ "$status" = "error" ]; then
        exit 1
    fi
}

# ==========================================
# Run
# ==========================================
main "$@"

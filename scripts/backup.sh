#!/bin/bash
# Database backup script for API Gateway
# Supports PostgreSQL backups with retention policy

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '#' | xargs)
fi

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-api_gateway}"
DB_USER="${DB_USER:-gateway_user}"
DB_PASSWORD="${DB_PASSWORD:-gateway_password}"

# Backup configuration
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"
BACKUP_LOG="$BACKUP_DIR/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$BACKUP_LOG"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$BACKUP_LOG"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$BACKUP_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$BACKUP_LOG"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log "Starting database backup..."
log "Database: $DB_NAME"
log "Host: $DB_HOST:$DB_PORT"
log "Backup file: $BACKUP_FILE"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    error "pg_dump command not found. Please install PostgreSQL client tools."
    exit 1
fi

# Perform backup
export PGPASSWORD="$DB_PASSWORD"

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    | gzip > "$BACKUP_FILE" 2>> "$BACKUP_LOG"; then

    success "Database backup completed successfully"

    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup size: $BACKUP_SIZE"

    # Verify backup file
    if [ -s "$BACKUP_FILE" ]; then
        success "Backup file verified (non-empty)"
    else
        error "Backup file is empty!"
        exit 1
    fi
else
    error "Database backup failed"
    exit 1
fi

# Clean up old backups (retention policy)
log "Applying retention policy (keeping last $RETENTION_DAYS days)..."

find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete 2>> "$BACKUP_LOG"

OLD_BACKUPS=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f | wc -l)
log "Total backups retained: $OLD_BACKUPS"

# Optional: Upload to cloud storage
if [ -n "$BACKUP_S3_BUCKET" ]; then
    log "Uploading backup to S3..."
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_S3_BUCKET/gateway-backups/" 2>> "$BACKUP_LOG"; then
            success "Backup uploaded to S3"
        else
            warning "Failed to upload backup to S3"
        fi
    else
        warning "AWS CLI not found, skipping S3 upload"
    fi
fi

# Create backup manifest
MANIFEST_FILE="$BACKUP_DIR/manifest.json"
cat > "$MANIFEST_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "database": "$DB_NAME",
  "host": "$DB_HOST",
  "backup_file": "$(basename "$BACKUP_FILE")",
  "backup_size": "$BACKUP_SIZE",
  "retention_days": $RETENTION_DAYS,
  "total_backups": $OLD_BACKUPS
}
EOF

log "Backup manifest created: $MANIFEST_FILE"

# Send notification (optional)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Database backup completed: $BACKUP_FILE ($BACKUP_SIZE)\"}" \
        2>> "$BACKUP_LOG" || true
fi

success "Backup process completed successfully"
log "=========================================="

exit 0

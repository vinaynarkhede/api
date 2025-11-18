#!/bin/bash
# Database restore script for API Gateway
# Restores PostgreSQL database from backup file

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"

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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

usage() {
    cat << EOF
Usage: $0 [BACKUP_FILE]

Restore PostgreSQL database from backup file.

Arguments:
    BACKUP_FILE    Path to backup file (.sql or .sql.gz)
                   If not provided, lists available backups

Environment Variables:
    DB_HOST        Database host (default: localhost)
    DB_PORT        Database port (default: 5432)
    DB_NAME        Database name (default: api_gateway)
    DB_USER        Database user (default: gateway_user)
    DB_PASSWORD    Database password
    BACKUP_DIR     Backup directory (default: ./backups)

Examples:
    # List available backups
    $0

    # Restore from specific backup
    $0 backups/api_gateway_20240115_120000.sql.gz

    # Restore latest backup
    $0 latest
EOF
    exit 1
}

list_backups() {
    log "Available backups in $BACKUP_DIR:"
    echo ""

    if [ ! -d "$BACKUP_DIR" ]; then
        error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi

    BACKUPS=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f | sort -r)

    if [ -z "$BACKUPS" ]; then
        warning "No backups found"
        exit 0
    fi

    COUNT=1
    while IFS= read -r backup; do
        SIZE=$(du -h "$backup" | cut -f1)
        DATE=$(stat -c %y "$backup" | cut -d' ' -f1-2)
        echo "  [$COUNT] $(basename "$backup") - $SIZE - $DATE"
        COUNT=$((COUNT + 1))
    done <<< "$BACKUPS"

    echo ""
    log "Use: $0 [BACKUP_FILE] to restore"
}

get_latest_backup() {
    find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f | sort -r | head -n1
}

confirm_restore() {
    warning "⚠️  WARNING: This will REPLACE the current database!"
    warning "Database: $DB_NAME"
    warning "Host: $DB_HOST:$DB_PORT"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi
}

# Main script

# Check if backup file is provided
if [ $# -eq 0 ]; then
    list_backups
    exit 0
fi

BACKUP_FILE="$1"

# Handle "latest" argument
if [ "$BACKUP_FILE" == "latest" ]; then
    BACKUP_FILE=$(get_latest_backup)
    if [ -z "$BACKUP_FILE" ]; then
        error "No backups found"
        exit 1
    fi
    log "Using latest backup: $(basename "$BACKUP_FILE")"
fi

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log "Restore Configuration:"
log "  Database: $DB_NAME"
log "  Host: $DB_HOST:$DB_PORT"
log "  Backup file: $BACKUP_FILE"
log "  Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""

# Confirm before proceeding
confirm_restore

# Check if psql is available
if ! command -v psql &> /dev/null; then
    error "psql command not found. Please install PostgreSQL client tools."
    exit 1
fi

# Set password
export PGPASSWORD="$DB_PASSWORD"

log "Starting database restore..."

# Step 1: Create backup of current database (safety measure)
SAFETY_BACKUP="$BACKUP_DIR/${DB_NAME}_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
log "Creating safety backup of current database..."

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain --no-owner --no-acl | gzip > "$SAFETY_BACKUP" 2>/dev/null; then
    success "Safety backup created: $(basename "$SAFETY_BACKUP")"
else
    warning "Could not create safety backup (database may not exist yet)"
fi

# Step 2: Drop existing connections
log "Terminating existing connections..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    2>/dev/null || true

# Step 3: Drop and recreate database
log "Recreating database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

if [ $? -ne 0 ]; then
    error "Failed to recreate database"
    exit 1
fi

success "Database recreated"

# Step 4: Restore from backup
log "Restoring data from backup..."

if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Compressed backup
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
else
    # Uncompressed backup
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
fi

if [ $? -ne 0 ]; then
    error "Database restore failed"
    error "Safety backup available at: $SAFETY_BACKUP"
    exit 1
fi

success "Database restored successfully"

# Step 5: Verify restore
log "Verifying restore..."
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

if [ "$TABLE_COUNT" -gt 0 ]; then
    success "Verification passed - Found $TABLE_COUNT tables"
else
    warning "Verification warning - No tables found"
fi

# Step 6: Run migrations (optional)
if [ -f "$PROJECT_ROOT/alembic.ini" ]; then
    log "Running migrations to ensure schema is up to date..."
    cd "$PROJECT_ROOT"
    alembic upgrade head 2>/dev/null || warning "Migration failed or not needed"
fi

success "Restore process completed successfully"
log "=========================================="

# Send notification (optional)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Database restored from: $(basename "$BACKUP_FILE")\"}" \
        2>/dev/null || true
fi

exit 0

#!/bin/bash
# Database migration script

set -e

echo "Running database migrations..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Run Alembic migrations
alembic upgrade head

echo "Migrations completed successfully!"

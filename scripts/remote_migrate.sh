#!/bin/bash
# Remote migration script - to be executed on VPS
# This script will be uploaded and executed on production server

set -e

PROJECT_DIR="${1:-/var/www/Sentinel}"
cd "$PROJECT_DIR" || exit 1

echo "=========================================="
echo "REMOTE MIGRATION SCRIPT"
echo "=========================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if migration script exists
if [ ! -f "scripts/migrate_to_modular.py" ]; then
    echo "ERROR: Migration script not found!"
    echo "Please ensure scripts/migrate_to_modular.py exists"
    exit 1
fi

# Run migration
echo "Running migration..."
source venv/bin/activate
python3 scripts/migrate_to_modular.py "$PROJECT_DIR"

echo ""
echo "Migration completed!"

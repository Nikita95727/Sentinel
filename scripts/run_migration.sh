#!/bin/bash
# One-command migration script for VPS
# Usage: ./scripts/run_migration.sh

set -e

PROJECT_DIR="${1:-/var/www/Sentinel}"
cd "$PROJECT_DIR" || exit 1

echo "=========================================="
echo "🚀 MIGRATION TO MODULAR ARCHITECTURE"
echo "=========================================="
echo "Project: $PROJECT_DIR"
echo ""

# Step 1: Backup check
echo "Step 1: Checking current state..."
if [ -d "storage/trades" ] && [ "$(ls -A storage/trades/*.jsonl 2>/dev/null)" ]; then
    TRADE_COUNT=$(ls -1 storage/trades/*.jsonl 2>/dev/null | wc -l)
    echo "  ✅ Found $TRADE_COUNT trade files to migrate"
else
    echo "  ℹ️  No trade files found (first run or already migrated)"
fi

# Step 2: Run migration
echo ""
echo "Step 2: Running migration script..."
if [ -f "scripts/migrate_to_modular.py" ]; then
    source venv/bin/activate 2>/dev/null || true
    python3 scripts/migrate_to_modular.py "$PROJECT_DIR"
    echo "  ✅ Migration completed"
else
    echo "  ❌ Migration script not found!"
    exit 1
fi

# Step 3: Update .env
echo ""
echo "Step 3: Updating .env configuration..."
if [ -f ".env" ]; then
    if ! grep -q "ENABLE_CONSERVATIVE_MODULE" .env; then
        echo "ENABLE_CONSERVATIVE_MODULE=true" >> .env
        echo "  ✅ Added ENABLE_CONSERVATIVE_MODULE=true"
    fi
    if ! grep -q "ENABLE_LAUNCH_SNIPER_MODULE" .env; then
        echo "ENABLE_LAUNCH_SNIPER_MODULE=false" >> .env
        echo "  ✅ Added ENABLE_LAUNCH_SNIPER_MODULE=false"
    fi
else
    echo "  ⚠️  .env file not found"
fi

# Step 4: Restart bot
echo ""
echo "Step 4: Restarting bot..."
if command -v pm2 &> /dev/null; then
    pm2 restart ecosystem.config.js || pm2 start ecosystem.config.js
    sleep 3
    pm2 status
    echo "  ✅ Bot restarted"
else
    echo "  ⚠️  PM2 not found - restart manually"
fi

echo ""
echo "=========================================="
echo "✅ MIGRATION COMPLETED"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Check bot status: pm2 status"
echo "  2. Check logs: pm2 logs sentinel"
echo "  3. Verify data: ls -la storage/conservative/trades/"
echo ""


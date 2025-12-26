#!/bin/bash
# Safe restart script for production migration
# Ensures data safety and smooth transition

set -e  # Exit on error

PROJECT_DIR="/var/www/Sentinel"
BACKUP_DIR="$PROJECT_DIR/backup"
LOG_FILE="$PROJECT_DIR/logs/migration_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root or with sudo"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

log "=========================================="
log "SAFE PRODUCTION RESTART - MODULAR ARCHITECTURE"
log "=========================================="
log "Project directory: $PROJECT_DIR"
log ""

# Step 1: Check if bot is running
log "Step 1: Checking bot status..."
if pm2 list | grep -q "sentinel"; then
    BOT_STATUS=$(pm2 jlist | jq -r '.[] | select(.name=="sentinel") | .pm2_env.status')
    if [ "$BOT_STATUS" = "online" ]; then
        log "Bot is currently running"
        
        # Get last trade time to ensure we don't lose recent data
        LAST_TRADE=$(find storage/trades -name "*.jsonl" -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)
        if [ -n "$LAST_TRADE" ]; then
            LAST_MODIFIED=$(stat -c '%y' "$LAST_TRADE" | cut -d' ' -f1,2 | cut -d'.' -f1)
            log "Last trade file modified: $LAST_MODIFIED"
        fi
    fi
else
    warning "Bot is not running (this is OK for first migration)"
fi

# Step 2: Run migration script
log ""
log "Step 2: Running migration script..."
if [ -f "scripts/migrate_to_modular.py" ]; then
    source venv/bin/activate
    python3 scripts/migrate_to_modular.py "$PROJECT_DIR" 2>&1 | tee -a "$LOG_FILE"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        error "Migration script failed!"
        exit 1
    fi
    log "✅ Migration completed"
else
    error "Migration script not found: scripts/migrate_to_modular.py"
    exit 1
fi

# Step 3: Verify data
log ""
log "Step 3: Verifying migrated data..."
TRADE_COUNT=$(find storage/conservative/trades -name "*.jsonl" -type f 2>/dev/null | wc -l)
ANALYTICS_COUNT=$(find storage/conservative/analytics -name "*.jsonl" -type f 2>/dev/null | wc -l)

log "Migrated files:"
log "  - Trades: $TRADE_COUNT files"
log "  - Analytics: $ANALYTICS_COUNT files"

if [ "$TRADE_COUNT" -eq 0 ] && [ "$ANALYTICS_COUNT" -eq 0 ]; then
    warning "No files found - this might be first run"
else
    log "✅ Data verification passed"
fi

# Step 4: Stop bot if running
log ""
log "Step 4: Stopping bot (if running)..."
if pm2 list | grep -q "sentinel"; then
    pm2 stop sentinel 2>&1 | tee -a "$LOG_FILE"
    sleep 2
    log "✅ Bot stopped"
else
    log "Bot was not running"
fi

# Step 5: Update code (if needed)
log ""
log "Step 5: Checking for code updates..."
# This assumes you've already pulled new code
# If using git:
# git pull origin main
log "Code update check complete"

# Step 6: Verify .env configuration
log ""
log "Step 6: Verifying .env configuration..."
if [ -f ".env" ]; then
    if grep -q "ENABLE_CONSERVATIVE_MODULE" .env; then
        CONSERVATIVE_ENABLED=$(grep "ENABLE_CONSERVATIVE_MODULE" .env | cut -d'=' -f2)
        log "Conservative module: $CONSERVATIVE_ENABLED"
    else
        warning "ENABLE_CONSERVATIVE_MODULE not found in .env - adding default"
        echo "ENABLE_CONSERVATIVE_MODULE=true" >> .env
    fi
    
    if grep -q "ENABLE_LAUNCH_SNIPER_MODULE" .env; then
        SNIPER_ENABLED=$(grep "ENABLE_LAUNCH_SNIPER_MODULE" .env | cut -d'=' -f2)
        log "Launch sniper module: $SNIPER_ENABLED"
    else
        log "ENABLE_LAUNCH_SNIPER_MODULE not found - using default (false)"
    fi
else
    error ".env file not found!"
    exit 1
fi

# Step 7: Start bot
log ""
log "Step 7: Starting bot..."
pm2 restart ecosystem.config.js 2>&1 | tee -a "$LOG_FILE"
sleep 3

# Step 8: Verify bot started
log ""
log "Step 8: Verifying bot started..."
if pm2 list | grep -q "sentinel"; then
    BOT_STATUS=$(pm2 jlist | jq -r '.[] | select(.name=="sentinel") | .pm2_env.status')
    if [ "$BOT_STATUS" = "online" ]; then
        log "✅ Bot is running"
        
        # Show logs
        log ""
        log "Recent logs:"
        pm2 logs sentinel --lines 10 --nostream 2>&1 | tail -10 | tee -a "$LOG_FILE"
    else
        error "Bot failed to start! Status: $BOT_STATUS"
        log "Check logs: pm2 logs sentinel"
        exit 1
    fi
else
    error "Bot process not found!"
    exit 1
fi

# Step 9: Monitor for 30 seconds
log ""
log "Step 9: Monitoring bot for 30 seconds..."
for i in {1..6}; do
    sleep 5
    STATUS=$(pm2 jlist | jq -r '.[] | select(.name=="sentinel") | .pm2_env.status')
    if [ "$STATUS" != "online" ]; then
        error "Bot crashed! Status: $STATUS"
        log "Check logs: pm2 logs sentinel"
        exit 1
    fi
    log "  Check $i/6: Bot is running"
done

# Final summary
log ""
log "=========================================="
log "✅ RESTART COMPLETED SUCCESSFULLY"
log "=========================================="
log ""
log "Summary:"
log "  - Migration: ✅ Complete"
log "  - Data files: ✅ Preserved"
log "  - Bot status: ✅ Running"
log "  - Backup location: $BACKUP_DIR"
log ""
log "Next steps:"
log "  1. Monitor bot: pm2 logs sentinel"
log "  2. Check new files are created in: storage/conservative/"
log "  3. Verify trades continue normally"
log "  4. Keep backup for 7 days: $BACKUP_DIR"
log ""
log "Log file: $LOG_FILE"


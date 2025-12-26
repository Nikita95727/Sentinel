#!/bin/bash
# Status check script for Sentinel bot with modular architecture
# Monitors both conservative and launch_sniper modules

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="${1:-$(pwd)}"
cd "$PROJECT_DIR" || exit 1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SENTINEL BOT STATUS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check PM2 status
if command -v pm2 &> /dev/null; then
    echo -e "${BLUE}🤖 Bot Process:${NC}"
    pm2 status | grep -E "sentinel|name" || echo "  No PM2 processes found"
    echo ""
fi

# Check if bot is running via process
if pgrep -f "main.py" > /dev/null; then
    PID=$(pgrep -f "main.py" | head -1)
    echo -e "${GREEN}✅ Bot is running (PID: $PID)${NC}"
    echo ""
else
    echo -e "${RED}❌ Bot is not running${NC}"
    echo ""
fi

# Module status
echo -e "${BLUE}📊 MODULE STATUS${NC}"
echo "----------------------------------------"

# Conservative module
echo -e "${BLUE}Conservative Module:${NC}"
if [ -d "storage/conservative" ]; then
    TRADE_COUNT=$(find storage/conservative/trades -name "*.jsonl" -type f 2>/dev/null | wc -l)
    ANALYTICS_COUNT=$(find storage/conservative/analytics -name "*.jsonl" -type f 2>/dev/null | wc -l)
    LATEST_TRADE=$(find storage/conservative/trades -name "*.jsonl" -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)
    
    if [ -n "$LATEST_TRADE" ]; then
        LATEST_TIME=$(stat -c '%y' "$LATEST_TRADE" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo -e "  ${GREEN}✅ Active${NC}"
        echo -e "  Trades: $TRADE_COUNT files"
        echo -e "  Analytics: $ANALYTICS_COUNT files"
        echo -e "  Latest: $LATEST_TIME"
    else
        echo -e "  ${YELLOW}⚠️  No data files${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  Storage directory not found${NC}"
fi
echo ""

# Launch sniper module
echo -e "${BLUE}Launch Sniper Module:${NC}"
if [ -d "storage/launch_sniper" ]; then
    TRADE_COUNT=$(find storage/launch_sniper -name "*.jsonl" -type f 2>/dev/null | wc -l)
    LATEST_FILE=$(find storage/launch_sniper -name "*.jsonl" -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)
    
    if [ -n "$LATEST_FILE" ]; then
        LATEST_TIME=$(stat -c '%y' "$LATEST_FILE" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo -e "  ${GREEN}✅ Active${NC}"
        echo -e "  Files: $TRADE_COUNT"
        echo -e "  Latest: $LATEST_TIME"
    else
        echo -e "  ${YELLOW}⚠️  No data files${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  Storage directory not found${NC}"
fi
echo ""

# Recent logs
echo -e "${BLUE}📋 Recent Logs:${NC}"
if [ -d "logs" ]; then
    LATEST_LOG=$(find logs -name "*.log" -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)
    if [ -n "$LATEST_LOG" ]; then
        echo "  Last 5 lines from $LATEST_LOG:"
        tail -5 "$LATEST_LOG" 2>/dev/null | sed 's/^/  /' || echo "  (cannot read log file)"
    else
        echo "  No log files found"
    fi
else
    echo "  No logs directory"
fi
echo ""

# System resources
echo -e "${BLUE}💻 System Resources:${NC}"
if command -v pm2 &> /dev/null; then
    pm2 status | grep sentinel | awk '{print "  CPU: "$10", MEM: "$11}'
fi
echo ""

echo -e "${BLUE}========================================${NC}"

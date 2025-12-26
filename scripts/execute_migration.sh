#!/bin/bash
# Execute migration on VPS via SSH
# Usage: ./scripts/execute_migration.sh [user@host] [project_path]

set -e

# Default values
VPS_HOST="${1:-root@$(hostname -I | awk '{print $1}')}"
PROJECT_PATH="${2:-/var/www/Sentinel}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MIGRATION TO MODULAR ARCHITECTURE${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "VPS: $VPS_HOST"
echo "Project path: $PROJECT_PATH"
echo ""

# Check if we can connect
echo "Testing SSH connection..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes "$VPS_HOST" "echo 'Connection OK'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ Cannot connect to $VPS_HOST${NC}"
    echo ""
    echo "Please provide VPS details:"
    echo "  ./scripts/execute_migration.sh user@vps_ip /var/www/Sentinel"
    exit 1
fi

# Upload migration scripts
echo ""
echo "Uploading migration scripts..."
scp scripts/migrate_to_modular.py "$VPS_HOST:$PROJECT_PATH/scripts/" || {
    echo -e "${YELLOW}⚠️  Script already exists or upload failed${NC}"
}

scp scripts/safe_restart.sh "$VPS_HOST:$PROJECT_PATH/scripts/" || {
    echo -e "${YELLOW}⚠️  Script already exists or upload failed${NC}"
}

# Make scripts executable
echo ""
echo "Making scripts executable..."
ssh "$VPS_HOST" "chmod +x $PROJECT_PATH/scripts/migrate_to_modular.py $PROJECT_PATH/scripts/safe_restart.sh"

# Execute migration
echo ""
echo -e "${GREEN}Starting migration on VPS...${NC}"
echo ""

ssh -t "$VPS_HOST" "cd $PROJECT_PATH && sudo ./scripts/safe_restart.sh"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ MIGRATION COMPLETED${NC}"
echo -e "${GREEN}========================================${NC}"


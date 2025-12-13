#!/bin/bash
# Deploy VitaeRules to Raspberry Pi 5
# Usage: ./deploy_to_pi5.sh [pi_user@pi_ip]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PI_HOST="${1:-core@homeassistant.local}"
PROJECT_DIR="VitaeRules"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  VitaeRules - Raspberry Pi 5 Deployment${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}📡 Connecting to: ${PI_HOST}${NC}"
echo ""

# SSH into Pi5 and execute commands
ssh "$PI_HOST" bash << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd VitaeRules

echo -e "${YELLOW}🔄 Step 1: Pulling latest changes from Git...${NC}"
git pull origin main

echo -e "${YELLOW}🐳 Step 2: Stopping current container...${NC}"
docker compose down || docker stop vitaerules || true

echo -e "${YELLOW}🔧 Step 3: Updating .env with minimax-m2:cloud model...${NC}"
if grep -q "^OLLAMA_MODEL=" .env; then
    sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=minimax-m2:cloud/' .env
else
    echo "OLLAMA_MODEL=minimax-m2:cloud" >> .env
fi

echo -e "${YELLOW}📦 Step 4: Rebuilding Docker image (this copies the .env file)...${NC}"
docker compose build --no-cache

echo -e "${YELLOW}🚀 Step 5: Starting VitaeRules container...${NC}"
docker compose up -d

echo -e "${YELLOW}⏳ Step 6: Waiting for bot to start...${NC}"
sleep 5

echo -e "${YELLOW}📋 Step 7: Checking container status...${NC}"
docker ps | grep vitaerules

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📊 To view logs:${NC}"
echo "   docker logs -f vitaerules"
echo ""
echo -e "${YELLOW}🔄 To restart:${NC}"
echo "   docker compose restart"
echo ""

ENDSSH

echo -e "${GREEN}🎉 Deployment finished! Your bot is running on the Pi5.${NC}"
echo ""

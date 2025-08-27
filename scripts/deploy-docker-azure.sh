#!/bin/bash
# Deploy Docker Images from GHCR to Azure App Services
# This script updates Azure App Services to use the latest Docker images

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Docker Deployment to Azure ===${NC}"
echo ""

# Configuration
RESOURCE_GROUP="rg-cybermat-prd"
API_APP="api-cybermat-prd"
WEB_APP="web-cybermat-prd"
GHCR_REPO="ghcr.io/valeriisysoiev"

# Get latest commit SHA
LATEST_SHA=$(git rev-parse HEAD)
echo -e "${GREEN}Latest commit SHA: $LATEST_SHA${NC}"
echo ""

# Check if logged in to Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

echo -e "${GREEN}Step 1: Configure API App for GHCR${NC}"
echo "Setting API app to use Docker image from GHCR..."

# Configure API app for Docker
az webapp config container set \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --docker-custom-image-name "$GHCR_REPO/aecma-api:$LATEST_SHA" \
    --docker-registry-server-url "https://ghcr.io" \
    2>/dev/null || {
        echo -e "${YELLOW}Note: API image may not exist yet. Using latest tag.${NC}"
        az webapp config container set \
            --resource-group $RESOURCE_GROUP \
            --name $API_APP \
            --docker-custom-image-name "$GHCR_REPO/aecma-api:latest" \
            --docker-registry-server-url "https://ghcr.io" \
            2>/dev/null || echo -e "${RED}Failed to configure API app${NC}"
    }

# Set startup command for API
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --startup-file "python simple_start.py" \
    2>/dev/null || echo "Startup command update skipped"

echo -e "${GREEN}Step 2: Configure Web App for GHCR${NC}"
echo "Setting Web app to use Docker image from GHCR..."

# Configure Web app for Docker
az webapp config container set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --docker-custom-image-name "$GHCR_REPO/aecma-web:$LATEST_SHA" \
    --docker-registry-server-url "https://ghcr.io" \
    2>/dev/null || {
        echo -e "${YELLOW}Note: Using latest tag.${NC}"
        az webapp config container set \
            --resource-group $RESOURCE_GROUP \
            --name $WEB_APP \
            --docker-custom-image-name "$GHCR_REPO/aecma-web:latest" \
            --docker-registry-server-url "https://ghcr.io" \
            2>/dev/null || echo -e "${RED}Failed to configure Web app${NC}"
    }

# Set startup command for Web
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --startup-file "npm run start" \
    2>/dev/null || echo "Startup command update skipped"

echo ""
echo -e "${GREEN}Step 3: Configure Environment Variables${NC}"

# Set environment variables for API
echo "Configuring API environment variables..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --settings \
    PORT=8000 \
    AUTH_MODE=demo \
    DATA_BACKEND=local \
    STORAGE_MODE=local \
    RAG_MODE=off \
    ENVIRONMENT=production \
    BUILD_SHA="$LATEST_SHA" \
    2>/dev/null || echo "API settings update skipped"

# Set environment variables for Web
echo "Configuring Web environment variables..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --settings \
    PORT=3000 \
    NODE_ENV=production \
    AUTH_MODE=demo \
    PROXY_TARGET_API_BASE_URL="https://$API_APP.azurewebsites.net" \
    BUILD_SHA="$LATEST_SHA" \
    2>/dev/null || echo "Web settings update skipped"

echo ""
echo -e "${GREEN}Step 4: Restart Applications${NC}"

echo -n "Restarting API app... "
az webapp restart --resource-group $RESOURCE_GROUP --name $API_APP && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

echo -n "Restarting Web app... "
az webapp restart --resource-group $RESOURCE_GROUP --name $WEB_APP && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

echo ""
echo -e "${GREEN}Step 5: Wait for Applications to Start${NC}"
echo "Waiting 30 seconds for apps to initialize..."
sleep 30

echo ""
echo -e "${GREEN}Step 6: Verify Deployment${NC}"

# Check API health
echo -n "Checking API health... "
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$API_APP.azurewebsites.net/api/health || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API returned status $API_STATUS${NC}"
    echo "  Check logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $API_APP"
fi

# Check Web app
echo -n "Checking Web app... "
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$WEB_APP.azurewebsites.net || echo "000")
if [ "$WEB_STATUS" = "200" ] || [ "$WEB_STATUS" = "307" ]; then
    echo -e "${GREEN}✓ Web app is responding${NC}"
else
    echo -e "${YELLOW}⚠ Web returned status $WEB_STATUS${NC}"
    echo "  Check logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $WEB_APP"
fi

echo ""
echo -e "${BLUE}=== Deployment Summary ===${NC}"
echo ""
echo "API URL: https://$API_APP.azurewebsites.net"
echo "Web URL: https://$WEB_APP.azurewebsites.net"
echo ""
echo -e "${GREEN}Docker images deployed from GitHub Container Registry${NC}"
echo ""
echo "To monitor logs:"
echo "  API: az webapp log tail --resource-group $RESOURCE_GROUP --name $API_APP"
echo "  Web: az webapp log tail --resource-group $RESOURCE_GROUP --name $WEB_APP"
echo ""
echo "To run health check:"
echo "  ./scripts/health-check-prod.sh"
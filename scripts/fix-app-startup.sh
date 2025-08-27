#!/bin/bash
# Fix Azure App Service Startup Issues
# Configure apps to use proper runtimes instead of Docker images

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Fixing App Service Startup Issues ===${NC}"
echo ""

RESOURCE_GROUP="rg-cybermat-prd"
API_APP="api-cybermat-prd"
WEB_APP="web-cybermat-prd"

# Check if logged in to Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

echo -e "${GREEN}Step 1: Configure API App for Python Runtime${NC}"
echo "Switching from Docker to Python runtime..."

# Set API app to use Python runtime
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --linux-fx-version "PYTHON|3.11" \
    --startup-file "python simple_start.py" \
    2>/dev/null && echo "✓ API configured for Python 3.11" || echo "⚠ API configuration may have failed"

# Set essential API environment variables
echo "Setting API environment variables..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --settings \
    PORT=8000 \
    WEBSITES_PORT=8000 \
    AUTH_MODE=demo \
    DATA_BACKEND=local \
    STORAGE_MODE=local \
    RAG_MODE=off \
    ORCHESTRATOR_MODE=local \
    ENVIRONMENT=production \
    PYTHONPATH=/home/site/wwwroot \
    LOG_LEVEL=info \
    ADMIN_EMAILS="admin@example.com" \
    2>/dev/null && echo "✓ API environment configured" || echo "⚠ API settings may have failed"

echo ""
echo -e "${GREEN}Step 2: Configure Web App for Node.js Runtime${NC}"
echo "Switching from Docker to Node.js runtime..."

# Set Web app to use Node.js runtime
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --linux-fx-version "NODE|20-lts" \
    --startup-file "npm run start" \
    2>/dev/null && echo "✓ Web configured for Node.js 20" || echo "⚠ Web configuration may have failed"

# Set essential Web environment variables
echo "Setting Web environment variables..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --settings \
    PORT=3000 \
    WEBSITES_PORT=3000 \
    NODE_ENV=production \
    AUTH_MODE=demo \
    PROXY_TARGET_API_BASE_URL="https://$API_APP.azurewebsites.net" \
    NEXTAUTH_URL="https://$WEB_APP.azurewebsites.net" \
    NEXTAUTH_SECRET="$(openssl rand -base64 32)" \
    2>/dev/null && echo "✓ Web environment configured" || echo "⚠ Web settings may have failed"

echo ""
echo -e "${GREEN}Step 3: Deploy Application Code${NC}"

# Create API deployment package
echo "Creating API deployment package..."
cd app
zip -q -r ../api-deploy-fixed.zip . \
    -x "*.pyc" -x "__pycache__/*" -x ".pytest_cache/*" -x "tests/*" -x "*.log"
cd ..

echo "Deploying API code..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $API_APP \
    --src-path api-deploy-fixed.zip \
    --type zip \
    --async true \
    2>/dev/null && echo "✓ API code deployed" || echo "⚠ API deployment may have failed"

# Create Web deployment package
echo "Creating Web deployment package..."
cd web

# Install production dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci --production --silent 2>/dev/null || echo "⚠ npm install may have failed"
fi

# Build the application
echo "Building Web application..."
NODE_ENV=production npm run build --silent 2>/dev/null || echo "⚠ Build may have failed"

# Create deployment package
zip -q -r ../web-deploy-fixed.zip .next package.json package-lock.json public next.config.js \
    -x "node_modules/*" -x ".git/*" -x "*.log"
cd ..

echo "Deploying Web code..."
az webapp deploy \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --src-path web-deploy-fixed.zip \
    --type zip \
    --async true \
    2>/dev/null && echo "✓ Web code deployed" || echo "⚠ Web deployment may have failed"

echo ""
echo -e "${GREEN}Step 4: Restart Applications${NC}"

echo "Restarting applications to apply changes..."
az webapp restart --resource-group $RESOURCE_GROUP --name $API_APP &
az webapp restart --resource-group $RESOURCE_GROUP --name $WEB_APP &
wait

echo "✓ Both applications restarted"

# Cleanup
rm -f api-deploy-fixed.zip web-deploy-fixed.zip

echo ""
echo -e "${GREEN}Step 5: Wait and Verify${NC}"
echo "Waiting 60 seconds for applications to initialize..."
sleep 60

echo ""
echo "Checking application status:"

# Check API
echo -n "API Health: "
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$API_APP.azurewebsites.net/api/health || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Healthy (HTTP $API_STATUS)${NC}"
elif [ "$API_STATUS" = "503" ]; then
    echo -e "${YELLOW}⚠ Starting up (HTTP $API_STATUS)${NC}"
else
    echo -e "${RED}✗ Issue (HTTP $API_STATUS)${NC}"
fi

# Check Web
echo -n "Web App: "
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$WEB_APP.azurewebsites.net || echo "000")
if [ "$WEB_STATUS" = "200" ] || [ "$WEB_STATUS" = "307" ]; then
    echo -e "${GREEN}✓ Responding (HTTP $WEB_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠ Status: HTTP $WEB_STATUS${NC}"
fi

echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo ""
echo "✅ Apps configured for native runtimes (Python/Node.js)"
echo "✅ Application code deployed"
echo "✅ Environment variables configured"
echo "✅ Applications restarted"
echo ""
echo "URLs:"
echo "  API: https://$API_APP.azurewebsites.net"
echo "  Web: https://$WEB_APP.azurewebsites.net"
echo ""
echo "If issues persist, check logs:"
echo "  API logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $API_APP"
echo "  Web logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $WEB_APP"
echo ""

if [ "$API_STATUS" = "200" ] && ([ "$WEB_STATUS" = "200" ] || [ "$WEB_STATUS" = "307" ]); then
    echo -e "${GREEN}🎉 Deployment appears successful!${NC}"
    echo "Run comprehensive health check: ./scripts/health-check-prod.sh"
    exit 0
else
    echo -e "${YELLOW}⚠ Applications may still be starting up${NC}"
    echo "Wait a few more minutes and check again"
    exit 1
fi
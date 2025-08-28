#!/bin/bash
# Fix Azure App Service startup configuration for production

set -e

echo "Fixing Azure App Service startup configuration..."

# API Configuration
echo "Configuring API startup..."
az webapp config set \
  --resource-group rg-cybermat-prd \
  --name api-cybermat-prd \
  --startup-file "python start_prod.py"

# Ensure Python version is correct
az webapp config set \
  --resource-group rg-cybermat-prd \
  --name api-cybermat-prd \
  --linux-fx-version "PYTHON|3.11"

# Enable application logging
az webapp log config \
  --resource-group rg-cybermat-prd \
  --name api-cybermat-prd \
  --application-logging filesystem \
  --detailed-error-messages true \
  --failed-request-tracing true \
  --level information

# Configure always-on to prevent cold starts
az webapp config set \
  --resource-group rg-cybermat-prd \
  --name api-cybermat-prd \
  --always-on true

# Web Configuration
echo "Configuring Web startup..."
az webapp config set \
  --resource-group rg-cybermat-prd \
  --name web-cybermat-prd \
  --startup-file "npm run start"

# Ensure Node version is correct
az webapp config set \
  --resource-group rg-cybermat-prd \
  --name web-cybermat-prd \
  --linux-fx-version "NODE|20-lts"

echo "Restarting applications..."
az webapp restart --resource-group rg-cybermat-prd --name api-cybermat-prd
az webapp restart --resource-group rg-cybermat-prd --name web-cybermat-prd

echo "Configuration updated. Waiting for services to start..."
sleep 30

# Check health
echo "Checking API health..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api-cybermat-prd.azurewebsites.net/api/health || echo "000")
if [ "$API_STATUS" = "200" ]; then
  echo "✅ API is healthy (HTTP $API_STATUS)"
else
  echo "❌ API health check failed (HTTP $API_STATUS)"
fi

echo "Checking Web health..."
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://web-cybermat-prd.azurewebsites.net || echo "000")
if [ "$WEB_STATUS" = "200" ] || [ "$WEB_STATUS" = "307" ]; then
  echo "✅ Web is responding (HTTP $WEB_STATUS)"
else
  echo "❌ Web check failed (HTTP $WEB_STATUS)"
fi

echo "Done!"
#!/bin/bash
# Azure Login and Resource Setup Helper
# Run this script locally to set up your Azure resources

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}=== IMPORTANT SECURITY NOTICE ===${NC}"
echo "If you've shared your password anywhere, please change it immediately!"
echo "Visit: https://account.microsoft.com/security"
echo ""
echo -e "${BLUE}=== Azure Setup Helper ===${NC}"
echo ""

# Login to Azure
echo -e "${GREEN}Step 1: Login to Azure${NC}"
echo "Please login with your credentials:"
az login --allow-no-subscriptions

# Get account info
ACCOUNT_INFO=$(az account show 2>/dev/null || echo "{}")
if [ "$ACCOUNT_INFO" = "{}" ]; then
    echo -e "${YELLOW}No active subscriptions found. You may need to create one.${NC}"
    echo "Visit: https://azure.microsoft.com/en-us/free/"
    exit 1
fi

SUBSCRIPTION_ID=$(echo $ACCOUNT_INFO | jq -r '.id')
SUBSCRIPTION_NAME=$(echo $ACCOUNT_INFO | jq -r '.name')
USER_EMAIL=$(echo $ACCOUNT_INFO | jq -r '.user.name')

echo -e "${GREEN}Logged in as: $USER_EMAIL${NC}"
echo -e "${GREEN}Subscription: $SUBSCRIPTION_NAME${NC}"
echo ""

# Create Resource Group
echo -e "${GREEN}Step 2: Create Resource Group${NC}"
RESOURCE_GROUP="rg-cybermat-prd"
LOCATION="eastus"

echo "Creating resource group: $RESOURCE_GROUP in $LOCATION..."
az group create --name $RESOURCE_GROUP --location $LOCATION 2>/dev/null || echo "Resource group already exists"

# Create App Service Plan
echo -e "${GREEN}Step 3: Create App Service Plan${NC}"
APP_SERVICE_PLAN="plan-cybermat-prd"

az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --sku B1 \
    --is-linux \
    2>/dev/null || echo "App Service Plan already exists"

# Create Web Apps
echo -e "${GREEN}Step 4: Create Web Apps${NC}"

# API App
echo "Creating API app..."
az webapp create \
    --name api-cybermat-prd \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --runtime "PYTHON:3.11" \
    2>/dev/null || echo "API app already exists"

# Web App
echo "Creating Web app..."
az webapp create \
    --name web-cybermat-prd \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --runtime "NODE:20-lts" \
    2>/dev/null || echo "Web app already exists"

# Create Storage Account
echo -e "${GREEN}Step 5: Create Storage Account${NC}"
STORAGE_ACCOUNT="stcybermatprd"

az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    2>/dev/null || echo "Storage account already exists"

# Get Storage Connection String
STORAGE_CONNECTION=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query connectionString -o tsv)

# Create Cosmos DB (Free Tier)
echo -e "${GREEN}Step 6: Create Cosmos DB (Free Tier)${NC}"
COSMOS_ACCOUNT="cosmos-cybermat-prd"

echo "Creating Cosmos DB account (this may take a few minutes)..."
az cosmosdb create \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --enable-free-tier true \
    --default-consistency-level "Session" \
    2>/dev/null || echo "Cosmos DB already exists"

# Get Cosmos DB credentials
COSMOS_ENDPOINT=$(az cosmosdb show \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query documentEndpoint -o tsv)

COSMOS_KEY=$(az cosmosdb keys list \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query primaryMasterKey -o tsv)

# Update GitHub Secrets with real values
echo -e "${GREEN}Step 7: Updating GitHub Secrets${NC}"

update_secret() {
    echo -n "Updating $1... "
    echo "$2" | gh secret set "$1" && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}Failed${NC}"
}

update_secret "AZURE_STORAGE_CONNECTION_STRING" "$STORAGE_CONNECTION"
update_secret "COSMOS_DB_ENDPOINT" "$COSMOS_ENDPOINT"
update_secret "COSMOS_DB_KEY" "$COSMOS_KEY"
update_secret "ADMIN_EMAILS" "$USER_EMAIL"

# Summary
echo ""
echo -e "${BLUE}=== Setup Summary ===${NC}"
echo -e "${GREEN}✅ Resource Group: $RESOURCE_GROUP${NC}"
echo -e "${GREEN}✅ App Service Plan: $APP_SERVICE_PLAN${NC}"
echo -e "${GREEN}✅ API App: api-cybermat-prd${NC}"
echo -e "${GREEN}✅ Web App: web-cybermat-prd${NC}"
echo -e "${GREEN}✅ Storage Account: $STORAGE_ACCOUNT${NC}"
echo -e "${GREEN}✅ Cosmos DB: $COSMOS_ACCOUNT${NC}"
echo ""
echo -e "${YELLOW}Note: OpenAI and Cognitive Search require manual setup in Azure Portal${NC}"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Redeploy the application: gh workflow run 'Deploy to Production'"
echo "2. Verify deployment: ./scripts/health-check-prod.sh"
echo ""
echo -e "${RED}IMPORTANT: Change your password if it was shared!${NC}"
echo "Visit: https://account.microsoft.com/security"
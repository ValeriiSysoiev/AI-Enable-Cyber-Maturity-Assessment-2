#!/bin/bash
# Azure Secrets Setup Script
# This script helps create and configure all required Azure secrets for the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Azure Secrets Setup Script ===${NC}"
echo "This script will help you create and configure Azure secrets for GitHub Actions"
echo ""

# Function to prompt for input with default value
prompt_with_default() {
    local prompt=$1
    local default=$2
    local varname=$3
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        eval $varname="${input:-$default}"
    else
        read -p "$prompt: " input
        eval $varname="$input"
    fi
}

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI is not installed. Please install it first:${NC}"
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI is not installed. Please install it first:${NC}"
    echo "https://cli.github.com/manual/installation"
    exit 1
fi

# Login to Azure if needed
echo -e "${GREEN}Step 1: Azure Authentication${NC}"
if ! az account show &>/dev/null; then
    echo "Please login to Azure:"
    az login
fi

# Get subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo -e "${GREEN}Using subscription: $SUBSCRIPTION_NAME${NC}"
echo ""

# Collect configuration
echo -e "${GREEN}Step 2: Resource Configuration${NC}"
prompt_with_default "Enter Resource Group name" "rg-cybermat-prd" RESOURCE_GROUP
prompt_with_default "Enter API Container App name" "api-cybermat-prd-aca" API_CONTAINER_APP_NAME
prompt_with_default "Enter Web App Service name" "web-cybermat-prd" WEB_APP_NAME
prompt_with_default "Enter Cosmos DB account name" "cosmos-cybermat-prd" COSMOS_ACCOUNT
prompt_with_default "Enter Storage Account name" "stcybermatprd" STORAGE_ACCOUNT
prompt_with_default "Enter Service Bus namespace" "sb-cybermat-prd" SERVICE_BUS
prompt_with_default "Enter OpenAI resource name" "oai-cybermat-prd" OPENAI_RESOURCE
prompt_with_default "Enter Search service name" "search-cybermat-prd" SEARCH_SERVICE
echo ""

# Create Service Principal for GitHub Actions
echo -e "${GREEN}Step 3: Creating Service Principal for GitHub Actions${NC}"
SP_NAME="sp-github-actions-cybermat"

# Check if service principal already exists
SP_EXISTS=$(az ad sp list --display-name $SP_NAME --query "[0].appId" -o tsv 2>/dev/null || echo "")

if [ -n "$SP_EXISTS" ]; then
    echo -e "${YELLOW}Service Principal already exists. Using existing one.${NC}"
    CLIENT_ID=$SP_EXISTS
    # Reset password for existing SP
    SP_CREDENTIALS=$(az ad sp credential reset --id $CLIENT_ID --years 2)
    CLIENT_SECRET=$(echo $SP_CREDENTIALS | jq -r '.password')
else
    echo "Creating new Service Principal..."
    SP_CREDENTIALS=$(az ad sp create-for-rbac \
        --name $SP_NAME \
        --role "Contributor" \
        --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
        --years 2 \
        --sdk-auth)
    
    CLIENT_ID=$(echo $SP_CREDENTIALS | jq -r '.clientId')
    CLIENT_SECRET=$(echo $SP_CREDENTIALS | jq -r '.clientSecret')
fi

# Create AZURE_CREDENTIALS JSON
AZURE_CREDENTIALS=$(cat <<EOF
{
  "clientId": "$CLIENT_ID",
  "clientSecret": "$CLIENT_SECRET",
  "subscriptionId": "$SUBSCRIPTION_ID",
  "tenantId": "$TENANT_ID"
}
EOF
)

echo -e "${GREEN}Service Principal created/updated successfully${NC}"
echo ""

# Get Azure AD App registration details
echo -e "${GREEN}Step 4: Azure AD Configuration${NC}"
echo "Do you have an existing Azure AD App registration for authentication? (y/n)"
read -r HAS_AAD_APP

if [ "$HAS_AAD_APP" = "y" ]; then
    prompt_with_default "Enter Azure AD Client ID" "" AZURE_AD_CLIENT_ID
    prompt_with_default "Enter Azure AD Client Secret" "" AZURE_AD_CLIENT_SECRET
else
    echo "Creating new Azure AD App registration..."
    APP_NAME="aecma-auth-prd"
    
    # Create app registration
    APP_INFO=$(az ad app create \
        --display-name $APP_NAME \
        --sign-in-audience "AzureADMyOrg" \
        --web-redirect-uris "https://$WEB_APP_NAME.azurewebsites.net/api/auth/callback/azure-ad" \
        --enable-access-token-issuance true \
        --enable-id-token-issuance true)
    
    AZURE_AD_CLIENT_ID=$(echo $APP_INFO | jq -r '.appId')
    
    # Create client secret
    SECRET_INFO=$(az ad app credential reset --id $AZURE_AD_CLIENT_ID --years 2)
    AZURE_AD_CLIENT_SECRET=$(echo $SECRET_INFO | jq -r '.password')
    
    echo -e "${GREEN}Azure AD App registration created${NC}"
fi

# Get resource connection strings
echo -e "${GREEN}Step 5: Getting Azure Resource Connection Strings${NC}"

# Cosmos DB
echo -n "Getting Cosmos DB connection info... "
if az cosmosdb show --name $COSMOS_ACCOUNT --resource-group $RESOURCE_GROUP &>/dev/null; then
    COSMOS_ENDPOINT=$(az cosmosdb show --name $COSMOS_ACCOUNT --resource-group $RESOURCE_GROUP --query documentEndpoint -o tsv)
    COSMOS_KEY=$(az cosmosdb keys list --name $COSMOS_ACCOUNT --resource-group $RESOURCE_GROUP --query primaryMasterKey -o tsv)
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    COSMOS_ENDPOINT="https://$COSMOS_ACCOUNT.documents.azure.com:443/"
    COSMOS_KEY="<COSMOS_KEY_PLACEHOLDER>"
fi

# Storage Account
echo -n "Getting Storage Account connection string... "
if az storage account show --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP &>/dev/null; then
    STORAGE_CONNECTION=$(az storage account show-connection-string --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --query connectionString -o tsv)
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    STORAGE_CONNECTION="<STORAGE_CONNECTION_PLACEHOLDER>"
fi

# Service Bus
echo -n "Getting Service Bus connection string... "
if az servicebus namespace show --name $SERVICE_BUS --resource-group $RESOURCE_GROUP &>/dev/null; then
    SERVICE_BUS_CONNECTION=$(az servicebus namespace authorization-rule keys list \
        --name RootManageSharedAccessKey \
        --namespace-name $SERVICE_BUS \
        --resource-group $RESOURCE_GROUP \
        --query primaryConnectionString -o tsv)
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    SERVICE_BUS_CONNECTION="<SERVICE_BUS_CONNECTION_PLACEHOLDER>"
fi

# OpenAI
echo -n "Getting OpenAI endpoint and key... "
if az cognitiveservices account show --name $OPENAI_RESOURCE --resource-group $RESOURCE_GROUP &>/dev/null; then
    OPENAI_ENDPOINT=$(az cognitiveservices account show --name $OPENAI_RESOURCE --resource-group $RESOURCE_GROUP --query properties.endpoint -o tsv)
    OPENAI_KEY=$(az cognitiveservices account keys list --name $OPENAI_RESOURCE --resource-group $RESOURCE_GROUP --query key1 -o tsv)
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    OPENAI_ENDPOINT="https://$OPENAI_RESOURCE.openai.azure.com/"
    OPENAI_KEY="<OPENAI_KEY_PLACEHOLDER>"
fi

# Cognitive Search
echo -n "Getting Search service endpoint and key... "
if az search service show --name $SEARCH_SERVICE --resource-group $RESOURCE_GROUP &>/dev/null; then
    SEARCH_ENDPOINT="https://$SEARCH_SERVICE.search.windows.net"
    SEARCH_KEY=$(az search admin-key show --service-name $SEARCH_SERVICE --resource-group $RESOURCE_GROUP --query primaryKey -o tsv)
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    SEARCH_ENDPOINT="https://$SEARCH_SERVICE.search.windows.net"
    SEARCH_KEY="<SEARCH_KEY_PLACEHOLDER>"
fi

# Generate NextAuth secret
echo -e "${GREEN}Step 6: Generating NextAuth Secret${NC}"
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Admin emails
echo -e "${GREEN}Step 7: Admin Configuration${NC}"
prompt_with_default "Enter admin email addresses (comma-separated)" "admin@example.com" ADMIN_EMAILS

echo ""
echo -e "${GREEN}Step 8: Setting GitHub Secrets${NC}"
echo "Adding secrets to GitHub repository..."

# Function to set GitHub secret
set_github_secret() {
    local name=$1
    local value=$2
    echo -n "Setting $name... "
    if echo "$value" | gh secret set "$name" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Failed (might already exist)${NC}"
    fi
}

# Set all secrets
set_github_secret "AZURE_CREDENTIALS" "$AZURE_CREDENTIALS"
set_github_secret "AZURE_RESOURCE_GROUP" "$RESOURCE_GROUP"
set_github_secret "AZURE_AD_CLIENT_ID" "$AZURE_AD_CLIENT_ID"
set_github_secret "AZURE_AD_TENANT_ID" "$TENANT_ID"
set_github_secret "AZURE_AD_CLIENT_SECRET" "$AZURE_AD_CLIENT_SECRET"
set_github_secret "NEXTAUTH_SECRET" "$NEXTAUTH_SECRET"
set_github_secret "NEXTAUTH_URL" "https://$WEB_APP_NAME.azurewebsites.net"
set_github_secret "ADMIN_EMAILS" "$ADMIN_EMAILS"
set_github_secret "COSMOS_DB_ENDPOINT" "$COSMOS_ENDPOINT"
set_github_secret "COSMOS_DB_KEY" "$COSMOS_KEY"
set_github_secret "AZURE_STORAGE_CONNECTION_STRING" "$STORAGE_CONNECTION"
set_github_secret "AZURE_SERVICE_BUS_CONNECTION_STRING" "$SERVICE_BUS_CONNECTION"
set_github_secret "AZURE_OPENAI_ENDPOINT" "$OPENAI_ENDPOINT"
set_github_secret "AZURE_OPENAI_API_KEY" "$OPENAI_KEY"
set_github_secret "AZURE_SEARCH_ENDPOINT" "$SEARCH_ENDPOINT"
set_github_secret "AZURE_SEARCH_KEY" "$SEARCH_KEY"
set_github_secret "PROXY_TARGET_API_BASE_URL" "https://$API_CONTAINER_APP_NAME.icystone-69c102b0.westeurope.azurecontainerapps.io"
set_github_secret "API_BASE_URL" "https://$API_CONTAINER_APP_NAME.icystone-69c102b0.westeurope.azurecontainerapps.io"
set_github_secret "WEB_BASE_URL" "https://$WEB_APP_NAME.azurewebsites.net"

echo ""
echo -e "${GREEN}Step 9: Creating .env.production file${NC}"
cat > .env.production <<EOF
# Production Environment Configuration
# Generated on $(date)

# Azure Resources
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_TENANT_ID=$TENANT_ID

# API Configuration
API_BASE_URL=https://$API_CONTAINER_APP_NAME.icystone-69c102b0.westeurope.azurecontainerapps.io
PROXY_TARGET_API_BASE_URL=https://$API_CONTAINER_APP_NAME.icystone-69c102b0.westeurope.azurecontainerapps.io
WEB_BASE_URL=https://$WEB_APP_NAME.azurewebsites.net

# Authentication (AAD)
AUTH_MODE=aad
AZURE_AD_CLIENT_ID=$AZURE_AD_CLIENT_ID
AZURE_AD_TENANT_ID=$TENANT_ID
AZURE_AD_CLIENT_SECRET=$AZURE_AD_CLIENT_SECRET
NEXTAUTH_URL=https://$WEB_APP_NAME.azurewebsites.net
NEXTAUTH_SECRET=$NEXTAUTH_SECRET

# Admin Configuration
ADMIN_EMAILS=$ADMIN_EMAILS

# Database & Storage
DATA_BACKEND=cosmos
STORAGE_MODE=azure
AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION
COSMOS_DB_ENDPOINT=$COSMOS_ENDPOINT
COSMOS_DB_KEY=$COSMOS_KEY
COSMOS_DB_DATABASE=cybermat-prd

# Service Bus
AZURE_SERVICE_BUS_CONNECTION_STRING=$SERVICE_BUS_CONNECTION
SERVICE_BUS_NAMESPACE=$SERVICE_BUS

# OpenAI & RAG
RAG_MODE=azure
AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=$OPENAI_KEY
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
AZURE_OPENAI_CHAT_MODEL=gpt-4

# Search
AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT
AZURE_SEARCH_KEY=$SEARCH_KEY
AZURE_SEARCH_INDEX_NAME=cybermat-documents

# Performance & Monitoring
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_CACHE=true

# Environment
NODE_ENV=production
ENVIRONMENT=production
EOF

echo -e "${GREEN}.env.production file created${NC}"
echo ""

# Summary
echo -e "${BLUE}=== Setup Complete ===${NC}"
echo ""
echo -e "${GREEN}✅ GitHub secrets have been configured${NC}"
echo -e "${GREEN}✅ Service Principal created/updated${NC}"
echo -e "${GREEN}✅ .env.production file generated${NC}"
echo ""

# Check for placeholders
if grep -q "PLACEHOLDER" .env.production; then
    echo -e "${YELLOW}⚠ Warning: Some resources were not found in Azure${NC}"
    echo "Please create the missing resources and update the .env.production file"
    echo ""
fi

echo -e "${GREEN}Next Steps:${NC}"
echo "1. Review .env.production for any placeholder values"
echo "2. Create any missing Azure resources"
echo "3. Run deployment: gh workflow run 'Deploy to Production' --ref main"
echo "4. Verify deployment: ./scripts/health-check-prod.sh"
echo ""
echo -e "${GREEN}Service Principal Details (save these):${NC}"
echo "Client ID: $CLIENT_ID"
echo "Tenant ID: $TENANT_ID"
echo ""
echo -e "${BLUE}Setup script completed successfully!${NC}"
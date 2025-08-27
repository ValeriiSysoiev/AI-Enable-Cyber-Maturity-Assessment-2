#!/bin/bash
# Validate GitHub Secrets Configuration
# This script checks if all required secrets are configured in the GitHub repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GitHub Secrets Validation ===${NC}"
echo ""

# Required secrets list
REQUIRED_SECRETS=(
    "AZURE_CREDENTIALS"
    "AZURE_RESOURCE_GROUP"
    "AZURE_AD_CLIENT_ID"
    "AZURE_AD_TENANT_ID"
    "AZURE_AD_CLIENT_SECRET"
    "NEXTAUTH_SECRET"
    "NEXTAUTH_URL"
    "ADMIN_EMAILS"
    "COSMOS_DB_ENDPOINT"
    "COSMOS_DB_KEY"
    "AZURE_STORAGE_CONNECTION_STRING"
    "AZURE_SERVICE_BUS_CONNECTION_STRING"
    "AZURE_OPENAI_ENDPOINT"
    "AZURE_OPENAI_API_KEY"
    "AZURE_SEARCH_ENDPOINT"
    "AZURE_SEARCH_KEY"
    "PROXY_TARGET_API_BASE_URL"
    "API_BASE_URL"
    "WEB_BASE_URL"
)

# Optional secrets
OPTIONAL_SECRETS=(
    "AZURE_CONTAINER_REGISTRY"
    "API_CONTAINER_APP"
    "WEB_CONTAINER_APP"
)

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI is not installed. Please install it first:${NC}"
    echo "https://cli.github.com/manual/installation"
    exit 1
fi

# Get list of configured secrets
echo "Fetching configured secrets..."
CONFIGURED_SECRETS=$(gh secret list --json name -q '.[].name' 2>/dev/null || echo "")

if [ -z "$CONFIGURED_SECRETS" ]; then
    echo -e "${YELLOW}Warning: Could not fetch secrets. Make sure you have permissions.${NC}"
    echo "You may need to run: gh auth refresh -s admin:org"
    echo ""
fi

# Function to check if secret exists
check_secret() {
    local secret_name=$1
    local required=$2
    
    if echo "$CONFIGURED_SECRETS" | grep -q "^$secret_name$"; then
        echo -e "${GREEN}✓${NC} $secret_name"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC} $secret_name ${RED}(MISSING - REQUIRED)${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠${NC} $secret_name ${YELLOW}(Optional)${NC}"
            return 0
        fi
    fi
}

# Check required secrets
echo -e "${BLUE}Required Secrets:${NC}"
MISSING_REQUIRED=0
for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! check_secret "$secret" "true"; then
        ((MISSING_REQUIRED++))
    fi
done

echo ""
echo -e "${BLUE}Optional Secrets:${NC}"
for secret in "${OPTIONAL_SECRETS[@]}"; do
    check_secret "$secret" "false"
done

# Validate Azure CLI login
echo ""
echo -e "${BLUE}Azure CLI Status:${NC}"
if az account show &>/dev/null; then
    SUBSCRIPTION=$(az account show --query name -o tsv)
    echo -e "${GREEN}✓${NC} Logged in to: $SUBSCRIPTION"
else
    echo -e "${YELLOW}⚠${NC} Not logged in to Azure CLI"
fi

# Test deployment readiness
echo ""
echo -e "${BLUE}Deployment Readiness:${NC}"

if [ $MISSING_REQUIRED -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All required secrets configured"
    DEPLOYMENT_READY=true
else
    echo -e "${RED}✗${NC} Missing $MISSING_REQUIRED required secrets"
    DEPLOYMENT_READY=false
fi

# Check if resources exist in Azure (if logged in)
if az account show &>/dev/null && [ -n "$CONFIGURED_SECRETS" ]; then
    echo ""
    echo -e "${BLUE}Azure Resource Validation:${NC}"
    
    # Try to get resource group from secrets or environment
    if [ -f .env.production ]; then
        source .env.production
    fi
    
    if [ -n "$AZURE_RESOURCE_GROUP" ]; then
        echo -n "Checking resource group $AZURE_RESOURCE_GROUP... "
        if az group show --name "$AZURE_RESOURCE_GROUP" &>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            
            # Check for App Services
            echo -n "Checking App Services... "
            APP_COUNT=$(az webapp list --resource-group "$AZURE_RESOURCE_GROUP" --query "length([])" -o tsv 2>/dev/null || echo "0")
            if [ "$APP_COUNT" -gt 0 ]; then
                echo -e "${GREEN}✓${NC} ($APP_COUNT found)"
            else
                echo -e "${YELLOW}⚠${NC} (None found)"
            fi
            
            # Check for Cosmos DB
            echo -n "Checking Cosmos DB... "
            COSMOS_COUNT=$(az cosmosdb list --resource-group "$AZURE_RESOURCE_GROUP" --query "length([])" -o tsv 2>/dev/null || echo "0")
            if [ "$COSMOS_COUNT" -gt 0 ]; then
                echo -e "${GREEN}✓${NC} ($COSMOS_COUNT found)"
            else
                echo -e "${YELLOW}⚠${NC} (None found)"
            fi
            
        else
            echo -e "${RED}✗${NC} (Not found)"
        fi
    fi
fi

# Summary
echo ""
echo -e "${BLUE}=== Validation Summary ===${NC}"
echo ""

if [ "$DEPLOYMENT_READY" = true ]; then
    echo -e "${GREEN}✅ Ready for deployment!${NC}"
    echo ""
    echo "You can now run:"
    echo "  gh workflow run 'Deploy to Production' --ref main"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Not ready for deployment${NC}"
    echo ""
    echo "To configure missing secrets, run:"
    echo "  ./scripts/setup-azure-secrets.sh"
    echo ""
    echo "Or manually set secrets with:"
    echo "  gh secret set SECRET_NAME"
    echo ""
    exit 1
fi
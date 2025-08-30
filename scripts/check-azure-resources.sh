#!/bin/bash
# Check Azure Resources Status
# This script checks if required Azure resources exist

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Azure Resource Status Check ===${NC}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Subscription: $SUBSCRIPTION${NC}"
echo ""

# Resource Group
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-cybermat-prd}"
echo -e "${BLUE}Checking Resource Group: $RESOURCE_GROUP${NC}"

if az group show --name $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}✓ Resource group exists${NC}"
    LOCATION=$(az group show --name $RESOURCE_GROUP --query location -o tsv)
    echo "  Location: $LOCATION"
else
    echo -e "${RED}✗ Resource group does not exist${NC}"
    echo "  To create: az group create --name $RESOURCE_GROUP --location eastus"
fi

echo ""

# Container Apps (primary deployment target)
echo -e "${BLUE}Checking Container Apps:${NC}"

check_container_app() {
    local app_name=$1
    echo -n "  $app_name: "
    if az containerapp show --resource-group $RESOURCE_GROUP --name $app_name &>/dev/null; then
        echo -e "${GREEN}✓ Exists${NC}"
        # Get ingress URL
        URL=$(az containerapp show --resource-group $RESOURCE_GROUP --name $app_name --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null)
        if [ -n "$URL" ]; then
            echo "    URL: https://$URL"
        fi
    else
        echo -e "${RED}✗ Does not exist${NC}"
    fi
}

check_container_app "api-cybermat-prd-aca"
check_container_app "web-cybermat-prd-aca"

echo ""

# Storage Account
echo -e "${BLUE}Checking Storage Account:${NC}"
STORAGE_ACCOUNT="stcybermatprd"
echo -n "  $STORAGE_ACCOUNT: "
if az storage account show --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist (optional)${NC}"
fi

echo ""

# Cosmos DB
echo -e "${BLUE}Checking Cosmos DB:${NC}"
COSMOS_ACCOUNT="cosmos-cybermat-prd"
echo -n "  $COSMOS_ACCOUNT: "
if az cosmosdb show --name $COSMOS_ACCOUNT --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist (optional)${NC}"
fi

echo ""

# Service Bus
echo -e "${BLUE}Checking Service Bus:${NC}"
SERVICE_BUS="sb-cybermat-prd"
echo -n "  $SERVICE_BUS: "
if az servicebus namespace show --name $SERVICE_BUS --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist (optional)${NC}"
fi

echo ""

# OpenAI
echo -e "${BLUE}Checking OpenAI Service:${NC}"
OPENAI_RESOURCE="oai-cybermat-prd"
echo -n "  $OPENAI_RESOURCE: "
if az cognitiveservices account show --name $OPENAI_RESOURCE --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist (optional)${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo ""

# Check minimum requirements
MIN_REQUIREMENTS_MET=true
if ! az group show --name $RESOURCE_GROUP &>/dev/null; then
    MIN_REQUIREMENTS_MET=false
fi
if ! az webapp show --resource-group $RESOURCE_GROUP --name "api-cybermat-prd" &>/dev/null; then
    MIN_REQUIREMENTS_MET=false
fi
if ! az webapp show --resource-group $RESOURCE_GROUP --name "web-cybermat-prd" &>/dev/null; then
    MIN_REQUIREMENTS_MET=false
fi

if [ "$MIN_REQUIREMENTS_MET" = true ]; then
    echo -e "${GREEN}✅ Minimum requirements met for deployment${NC}"
    echo ""
    echo "You can deploy with:"
    echo "  gh workflow run 'Deploy to Production'"
else
    echo -e "${RED}❌ Missing required resources${NC}"
    echo ""
    echo "To create required resources, run:"
    echo "  ./scripts/azure-login-setup.sh"
    echo ""
    echo "Or create manually:"
    echo "  az group create --name $RESOURCE_GROUP --location eastus"
    echo "  az webapp create --name api-cybermat-prd --resource-group $RESOURCE_GROUP --runtime 'PYTHON:3.11'"
    echo "  az webapp create --name web-cybermat-prd --resource-group $RESOURCE_GROUP --runtime 'NODE:20-lts'"
fi
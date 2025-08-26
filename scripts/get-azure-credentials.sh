#!/bin/bash
# Script to help generate Azure credentials for GitHub Actions
# Run this if you have Azure CLI access and want to create/get service principal

set -euo pipefail

echo "🔧 Azure Credentials Helper for GitHub Actions"
echo "=============================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

echo "✅ Azure CLI is ready"
echo ""

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo "📋 Current Azure Context:"
echo "   Subscription: $SUBSCRIPTION_NAME"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo "   Tenant ID: $TENANT_ID"
echo ""

# Service Principal name
SP_NAME="sp-github-actions-cybermat-prod"
RESOURCE_GROUP="rg-cybermat-prd"

echo "🔐 Creating/Getting Service Principal: $SP_NAME"
echo ""

# Check if service principal exists
if az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv &> /dev/null; then
    echo "ℹ️  Service Principal already exists"
    CLIENT_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv)
    echo "   Client ID: $CLIENT_ID"
    echo ""
    echo "⚠️  You'll need to create a new client secret in Azure Portal:"
    echo "   1. Go to Azure Portal > Azure Active Directory > App registrations"
    echo "   2. Find '$SP_NAME'"
    echo "   3. Go to 'Certificates & secrets'"
    echo "   4. Create a new client secret"
    echo ""
else
    echo "🆕 Creating new Service Principal..."
    
    # Create service principal with contributor role on resource group
    SP_OUTPUT=$(az ad sp create-for-rbac \
        --name "$SP_NAME" \
        --role contributor \
        --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
        --json-auth)
    
    echo "✅ Service Principal created successfully!"
    echo ""
    
    # Extract values
    CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r '.clientId')
    CLIENT_SECRET=$(echo "$SP_OUTPUT" | jq -r '.clientSecret')
    
    echo "📋 Service Principal Details:"
    echo "   Client ID: $CLIENT_ID"
    echo "   Client Secret: $CLIENT_SECRET (save this - it won't be shown again!)"
    echo ""
    
    # Generate the AZURE_CREDENTIALS JSON
    echo "🔐 AZURE_CREDENTIALS JSON for GitHub Secrets:"
    echo "=============================================="
    echo "$SP_OUTPUT"
    echo ""
fi

# Check for Container Registry
echo "📦 Checking for Container Registry..."
ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")

if [ -n "$ACR_NAME" ]; then
    echo "✅ Found Container Registry: $ACR_NAME"
else
    echo "⚠️  No Container Registry found in $RESOURCE_GROUP"
    echo "   You may need to create one or check the resource group name"
fi

echo ""
echo "📝 Summary - Add these secrets to GitHub:"
echo "========================================="
echo "Repository: https://github.com/ValeriiSysoiev/AI-Enable-Cyber-Maturity-Assessment-2/settings/secrets/actions"
echo ""
echo "1. AZURE_CREDENTIALS:"
if [ -n "${SP_OUTPUT:-}" ]; then
    echo "$SP_OUTPUT"
else
    echo "{\"clientId\":\"$CLIENT_ID\",\"clientSecret\":\"YOUR_NEW_SECRET\",\"subscriptionId\":\"$SUBSCRIPTION_ID\",\"tenantId\":\"$TENANT_ID\"}"
fi
echo ""
echo "2. AZURE_CONTAINER_REGISTRY: ${ACR_NAME:-YOUR_REGISTRY_NAME}"
echo "3. AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "4. API_CONTAINER_APP: api-cybermat-prd"
echo "5. WEB_CONTAINER_APP: web-cybermat-prd"
echo ""
echo "✅ Once configured, your deployments will work automatically!"

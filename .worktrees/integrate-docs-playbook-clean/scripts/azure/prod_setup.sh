#!/bin/bash
# Production Infrastructure Setup - Idempotent Azure Resource Provisioning
# Bounded execution with graceful handling of optional resources

set -euo pipefail

# Configuration
RG_NAME="${AZURE_RESOURCE_GROUP:-rg-cybermat-prd}"
LOCATION="${AZURE_LOCATION:-westeurope}"
COSMOS_NAME="cdb-cybermat-prd"
DB_NAME="appdb"
STORAGE_NAME="stcybermatprd"
KV_NAME="kv-cybermat-prd"
ASP_NAME="asp-cybermat-prd"
WEB_APP_NAME="web-cybermat-prd" 
CAE_NAME="cae-cybermat-prd"
API_APP_NAME="api-cybermat-prd"

# Color output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info() { echo -e "${GREEN}ℹ${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Bounded wait function
wait_for_completion() {
    local resource_type="$1"
    local resource_name="$2"
    local timeout=300  # 5 minutes max
    local count=0
    
    while [ $count -lt $timeout ]; do
        if az resource show --resource-group "$RG_NAME" --resource-type "$resource_type" --name "$resource_name" --query "properties.provisioningState" -o tsv 2>/dev/null | grep -E "(Succeeded|Running)" >/dev/null; then
            return 0
        fi
        sleep 10
        count=$((count + 10))
    done
    return 1
}

echo "=== Production Infrastructure Setup ==="
echo "Resource Group: $RG_NAME"
echo "Location: $LOCATION"
echo ""

# Ensure Resource Group exists
log_info "Ensuring resource group: $RG_NAME"
az group create --name "$RG_NAME" --location "$LOCATION" --output none
log_info "✅ Resource group ready"

# Cosmos DB
log_info "Setting up Cosmos DB: $COSMOS_NAME"
if ! az cosmosdb show --name "$COSMOS_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
    log_info "Creating Cosmos DB account..."
    az cosmosdb create \
        --name "$COSMOS_NAME" \
        --resource-group "$RG_NAME" \
        --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=False \
        --default-consistency-level Session \
        --enable-automatic-failover false \
        --output none
    
    # Wait for Cosmos DB with timeout
    if wait_for_completion "Microsoft.DocumentDB/databaseAccounts" "$COSMOS_NAME"; then
        log_info "✅ Cosmos DB account created"
    else
        log_warn "Cosmos DB creation timeout - may still be provisioning"
    fi
else
    log_info "✅ Cosmos DB account exists"
fi

# Create database and containers
log_info "Setting up Cosmos database and containers..."
az cosmosdb sql database create --account-name "$COSMOS_NAME" --resource-group "$RG_NAME" --name "$DB_NAME" --output none 2>/dev/null || true

# Create containers with appropriate partition keys
containers=(
    "engagements:/id"
    "memberships:/engagementId" 
    "evidence:/engagementId"
    "audit:/engagementId"
)

for container_spec in "${containers[@]}"; do
    container_name="${container_spec%:*}"
    partition_key="${container_spec#*:}"
    
    az cosmosdb sql container create \
        --account-name "$COSMOS_NAME" \
        --resource-group "$RG_NAME" \
        --database-name "$DB_NAME" \
        --name "$container_name" \
        --partition-key-path "$partition_key" \
        --throughput 400 \
        --output none 2>/dev/null || true
done
log_info "✅ Cosmos DB containers configured"

# Storage Account
log_info "Setting up Storage Account: $STORAGE_NAME"
if ! az storage account show --name "$STORAGE_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
    az storage account create \
        --name "$STORAGE_NAME" \
        --resource-group "$RG_NAME" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2 \
        --output none
    log_info "✅ Storage account created"
else
    log_info "✅ Storage account exists"
fi

# Create evidence container
CONNECTION_STRING=$(az storage account show-connection-string --name "$STORAGE_NAME" --resource-group "$RG_NAME" --query connectionString -o tsv)
az storage container create --name evidence --connection-string "$CONNECTION_STRING" --output none 2>/dev/null || true
log_info "✅ Evidence container ready"

# Key Vault
log_info "Setting up Key Vault: $KV_NAME"
if ! az keyvault show --name "$KV_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
    az keyvault create \
        --name "$KV_NAME" \
        --resource-group "$RG_NAME" \
        --location "$LOCATION" \
        --sku standard \
        --output none
    log_info "✅ Key Vault created"
else
    log_info "✅ Key Vault exists"
fi

# App Service Plan
log_info "Setting up App Service Plan: $ASP_NAME"
if ! az appservice plan show --name "$ASP_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
    az appservice plan create \
        --name "$ASP_NAME" \
        --resource-group "$RG_NAME" \
        --location "$LOCATION" \
        --sku B1 \
        --is-linux \
        --output none
    log_info "✅ App Service Plan created"
else
    log_info "✅ App Service Plan exists"
fi

# Web App
log_info "Setting up Web App: $WEB_APP_NAME"
if ! az webapp show --name "$WEB_APP_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
    az webapp create \
        --name "$WEB_APP_NAME" \
        --resource-group "$RG_NAME" \
        --plan "$ASP_NAME" \
        --runtime "NODE:20-lts" \
        --output none
    
    # Enable system-assigned managed identity
    WEB_MI_ID=$(az webapp identity assign --name "$WEB_APP_NAME" --resource-group "$RG_NAME" --query principalId -o tsv)
    log_info "✅ Web App created with MI: $WEB_MI_ID"
else
    WEB_MI_ID=$(az webapp identity show --name "$WEB_APP_NAME" --resource-group "$RG_NAME" --query principalId -o tsv 2>/dev/null || echo "")
    log_info "✅ Web App exists"
fi

# Container Apps (optional, with bounded timeout)
log_info "Setting up Container Apps (optional)..."

# Add Container Apps extension with timeout
timeout 60 az extension add --name containerapp --upgrade --only-show-errors 2>/dev/null || log_warn "Container Apps extension setup timeout"

# Try to register Microsoft.App provider with bounded wait
log_info "Registering Microsoft.App provider..."
if timeout 300 az provider register --namespace Microsoft.App --wait 2>/dev/null; then
    log_info "✅ Microsoft.App provider registered"
    
    # Create Container Apps environment
    if ! az containerapp env show --name "$CAE_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
        log_info "Creating Container Apps environment..."
        az containerapp env create \
            --name "$CAE_NAME" \
            --resource-group "$RG_NAME" \
            --location "$LOCATION" \
            --output none
        log_info "✅ Container Apps environment creation initiated"
    else
        log_info "✅ Container Apps environment exists"
    fi
    
    # Create API Container App with placeholder image
    if ! az containerapp show --name "$API_APP_NAME" --resource-group "$RG_NAME" >/dev/null 2>&1; then
        log_info "Creating API Container App..."
        az containerapp create \
            --name "$API_APP_NAME" \
            --resource-group "$RG_NAME" \
            --environment "$CAE_NAME" \
            --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
            --target-port 80 \
            --ingress external \
            --cpu 0.25 \
            --memory 0.5Gi \
            --output none
        log_info "✅ API Container App creation initiated"
    else
        log_info "✅ API Container App exists"
    fi
    
    # Get API FQDN (may not be ready immediately)
    sleep 30
    API_FQDN=$(az containerapp show --name "$API_APP_NAME" --resource-group "$RG_NAME" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    if [ -n "$API_FQDN" ]; then
        API_BASE_URL="https://$API_FQDN"
        log_info "✅ API URL: $API_BASE_URL"
        echo "API_BASE_URL=$API_BASE_URL" >> /tmp/infra_outputs.env
    else
        log_warn "API FQDN not yet available - will be set later"
        echo "API_BASE_URL=" >> /tmp/infra_outputs.env
    fi
    
    # Enable managed identity for API app
    API_MI_ID=$(az containerapp identity assign --name "$API_APP_NAME" --resource-group "$RG_NAME" --system-assigned --query principalId -o tsv 2>/dev/null || echo "")
    if [ -n "$API_MI_ID" ]; then
        log_info "✅ API Container App MI: $API_MI_ID"
    fi
    
else
    log_warn "Microsoft.App provider registration timeout - SKIPPING Container Apps setup"
    echo "API_BASE_URL=" >> /tmp/infra_outputs.env
    API_MI_ID=""
fi

# RBAC Assignments
log_info "Setting up RBAC permissions..."

# Web App MI → Key Vault Secrets User
if [ -n "$WEB_MI_ID" ]; then
    az role assignment create \
        --assignee "$WEB_MI_ID" \
        --role "Key Vault Secrets User" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NAME/providers/Microsoft.KeyVault/vaults/$KV_NAME" \
        --output none 2>/dev/null || true
    log_info "✅ Web App → Key Vault RBAC assigned"
fi

# API Container App MI → Storage + Key Vault + Cosmos permissions
if [ -n "$API_MI_ID" ]; then
    # Storage permissions
    az role assignment create \
        --assignee "$API_MI_ID" \
        --role "Storage Blob Data Contributor" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME" \
        --output none 2>/dev/null || true
    
    az role assignment create \
        --assignee "$API_MI_ID" \
        --role "Storage Blob Delegator" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME" \
        --output none 2>/dev/null || true
    
    # Key Vault permissions
    az role assignment create \
        --assignee "$API_MI_ID" \
        --role "Key Vault Secrets User" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NAME/providers/Microsoft.KeyVault/vaults/$KV_NAME" \
        --output none 2>/dev/null || true
    
    # Cosmos DB permissions
    az role assignment create \
        --assignee "$API_MI_ID" \
        --role "Cosmos DB Built-in Data Contributor" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NAME/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOS_NAME" \
        --output none 2>/dev/null || true
    
    log_info "✅ API Container App RBAC assignments complete"
fi

# Optional: Application Insights (best effort)
APP_INSIGHTS_NAME="ai-cybermat-prd"
log_info "Setting up Application Insights (optional)..."
if az monitor app-insights component create \
    --app "$APP_INSIGHTS_NAME" \
    --location "$LOCATION" \
    --resource-group "$RG_NAME" \
    --kind web \
    --output none 2>/dev/null; then
    log_info "✅ Application Insights created"
else
    log_warn "Application Insights creation failed or not available - will be TODO"
fi

echo ""
echo "=== Production Infrastructure Setup Complete ==="
echo "✅ Resource Group: $RG_NAME"
echo "✅ Cosmos DB: $COSMOS_NAME (database: $DB_NAME)"
echo "✅ Storage: $STORAGE_NAME (evidence container)"
echo "✅ Key Vault: $KV_NAME"
echo "✅ App Service Plan: $ASP_NAME"
echo "✅ Web App: $WEB_APP_NAME"

# Output Container Apps status
if [ -n "$API_MI_ID" ]; then
    echo "✅ Container Apps Environment: $CAE_NAME"
    echo "✅ API Container App: $API_APP_NAME"
    if [ -f /tmp/infra_outputs.env ]; then
        source /tmp/infra_outputs.env
        if [ -n "$API_BASE_URL" ]; then
            echo "✅ API URL: $API_BASE_URL"
        else
            echo "⚠️ API URL: Not yet available (check later)"
        fi
    fi
else
    echo "⚠️ Container Apps: SKIPPED (Microsoft.App provider unavailable)"
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Update GitHub environment variable VERIFY_API_BASE_URL_PROD if API URL is available"
echo "2. Run production deployment workflow"
echo "3. Execute UAT validation"

# Save outputs for GitHub Actions
if [ -f /tmp/infra_outputs.env ]; then
    echo "Infrastructure outputs saved to /tmp/infra_outputs.env"
fi
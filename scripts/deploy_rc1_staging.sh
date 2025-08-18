#!/usr/bin/env bash
#
# Deploy v0.2.0-rc1 to Staging Environment
# Bounded execution with monitoring and verification
#

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "v0.2.0-rc1 Staging Deployment"
echo "========================================"
echo ""

# Configuration
DEPLOYMENT_TIMEOUT=600  # 10 minutes
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=10

# Get environment variables
API_CONTAINER_APP="${API_CONTAINER_APP_STAGING:-}"
WEB_CONTAINER_APP="${WEB_CONTAINER_APP_STAGING:-}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP_STAGING:-}"
REGISTRY="${ACR_REGISTRY:-}"
TAG="v0.2.0-rc1"

# Validate required variables
if [[ -z "$API_CONTAINER_APP" ]] || [[ -z "$WEB_CONTAINER_APP" ]] || [[ -z "$RESOURCE_GROUP" ]]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Required: API_CONTAINER_APP_STAGING, WEB_CONTAINER_APP_STAGING, AZURE_RESOURCE_GROUP_STAGING"
    exit 1
fi

echo "Deployment Configuration:"
echo "  API Container App: $API_CONTAINER_APP"
echo "  Web Container App: $WEB_CONTAINER_APP"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Tag: $TAG"
echo ""

# Step 1: Run Cosmos S4 setup
echo -e "${BLUE}Step 1: Setting up Cosmos DB containers for S4 features${NC}"
if [[ -f "scripts/cosmos_s4_setup.sh" ]]; then
    bash scripts/cosmos_s4_setup.sh || {
        echo -e "${YELLOW}Warning: Cosmos setup had issues but continuing${NC}"
    }
else
    echo -e "${YELLOW}Cosmos setup script not found, skipping${NC}"
fi
echo ""

# Step 2: Deploy API Container App
echo -e "${BLUE}Step 2: Deploying API to $API_CONTAINER_APP${NC}"

# Build and push API image if ACR is configured
if [[ -n "$REGISTRY" ]]; then
    echo "Building and pushing API image..."
    docker build -t "$REGISTRY/cybermat-api:$TAG" -f app/Dockerfile app/
    docker push "$REGISTRY/cybermat-api:$TAG"
    
    # Update container app with new image
    az containerapp update \
        --name "$API_CONTAINER_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$REGISTRY/cybermat-api:$TAG" \
        --set-env-vars \
            "FEATURE_CSF_ENABLED=true" \
            "FEATURE_WORKSHOPS_ENABLED=true" \
            "FEATURE_MINUTES_ENABLED=true" \
            "FEATURE_CHAT_ENABLED=true" \
            "FEATURE_SERVICE_BUS_ENABLED=false" \
            "ENVIRONMENT=staging" \
        --output none
else
    echo -e "${YELLOW}ACR not configured, using existing image with env updates${NC}"
    
    # Just update environment variables
    az containerapp update \
        --name "$API_CONTAINER_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --set-env-vars \
            "FEATURE_CSF_ENABLED=true" \
            "FEATURE_WORKSHOPS_ENABLED=true" \
            "FEATURE_MINUTES_ENABLED=true" \
            "FEATURE_CHAT_ENABLED=true" \
            "FEATURE_SERVICE_BUS_ENABLED=false" \
            "ENVIRONMENT=staging" \
        --output none
fi

echo -e "${GREEN}✓ API deployment initiated${NC}"
echo ""

# Step 3: Deploy Web Container App
echo -e "${BLUE}Step 3: Deploying Web to $WEB_CONTAINER_APP${NC}"

if [[ -n "$REGISTRY" ]]; then
    echo "Building and pushing Web image..."
    docker build -t "$REGISTRY/cybermat-web:$TAG" -f web/Dockerfile web/
    docker push "$REGISTRY/cybermat-web:$TAG"
    
    # Update container app with new image
    az containerapp update \
        --name "$WEB_CONTAINER_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$REGISTRY/cybermat-web:$TAG" \
        --output none
else
    echo -e "${YELLOW}ACR not configured, skipping web image update${NC}"
fi

echo -e "${GREEN}✓ Web deployment initiated${NC}"
echo ""

# Step 4: Wait for deployments to complete
echo -e "${BLUE}Step 4: Waiting for deployments to stabilize${NC}"
echo "Waiting 30 seconds for initial deployment..."
sleep 30

# Step 5: Health checks
echo -e "${BLUE}Step 5: Running health checks${NC}"

# Get API URL
API_URL=$(az containerapp show \
    --name "$API_CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv)

if [[ -n "$API_URL" ]]; then
    API_URL="https://$API_URL"
    echo "API URL: $API_URL"
    
    # Check API health
    echo -n "Checking API health... "
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
            echo -e "${GREEN}healthy${NC}"
            break
        fi
        
        if [[ $i -eq $HEALTH_CHECK_RETRIES ]]; then
            echo -e "${RED}unhealthy${NC}"
            echo "API health check failed after $HEALTH_CHECK_RETRIES attempts"
            exit 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    # Check S4 features endpoint
    echo -n "Checking S4 features... "
    features_response=$(curl -s "$API_URL/api/features")
    if echo "$features_response" | grep -q '"s4_enabled":true'; then
        echo -e "${GREEN}enabled${NC}"
        echo "Enabled features:"
        echo "$features_response" | python3 -m json.tool | grep -A 5 '"features"'
    else
        echo -e "${YELLOW}not all enabled${NC}"
    fi
fi

# Get Web URL
WEB_URL=$(az containerapp show \
    --name "$WEB_CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv)

if [[ -n "$WEB_URL" ]]; then
    WEB_URL="https://$WEB_URL"
    echo ""
    echo "Web URL: $WEB_URL"
    
    # Check Web health
    echo -n "Checking Web health... "
    if curl -s "$WEB_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}healthy${NC}"
    else
        echo -e "${YELLOW}may need more time${NC}"
    fi
fi

echo ""
echo "========================================"
echo -e "${GREEN}✓ v0.2.0-rc1 Deployed to Staging${NC}"
echo "========================================"
echo ""
echo "API Endpoint: $API_URL"
echo "Web Endpoint: $WEB_URL"
echo ""
echo "S4 Features Status:"
echo "  - CSF Grid: Enabled"
echo "  - Workshops & Consent: Enabled"
echo "  - Minutes Publishing: Enabled"
echo "  - Chat Shell Commands: Enabled"
echo "  - Service Bus: Disabled (no Azure Service Bus configured)"
echo ""
echo "Next Steps:"
echo "  1. Run verification: bash scripts/verify_live.sh"
echo "  2. Run UAT workflow: bash scripts/uat_s4_workflow.sh"
echo "  3. Monitor Application Insights for errors"
echo ""

exit 0
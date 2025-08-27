#!/bin/bash
# Azure Deployment Script for AI-Enabled Cyber Maturity Assessment
# This script deploys both API and Web applications to Azure App Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Azure Deployment Script ===${NC}"

# Check required environment variables
check_env() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}Error: $1 is not set${NC}"
        exit 1
    fi
}

# Load environment variables
if [ -f .env.production ]; then
    echo -e "${GREEN}Loading production environment variables...${NC}"
    export $(cat .env.production | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}Warning: .env.production not found. Using existing environment variables.${NC}"
fi

# Verify required variables
echo -e "${GREEN}Checking required environment variables...${NC}"
check_env "AZURE_RESOURCE_GROUP"
check_env "API_BASE_URL"
check_env "WEB_BASE_URL"

# Parse URLs to get app names
API_APP_NAME=$(echo $API_BASE_URL | sed 's|https://||' | sed 's|\..*||')
WEB_APP_NAME=$(echo $WEB_BASE_URL | sed 's|https://||' | sed 's|\..*||')

echo -e "${GREEN}Deployment Configuration:${NC}"
echo "  Resource Group: $AZURE_RESOURCE_GROUP"
echo "  API App: $API_APP_NAME"
echo "  Web App: $WEB_APP_NAME"

# Function to deploy API
deploy_api() {
    echo -e "${GREEN}Deploying API to $API_APP_NAME...${NC}"
    
    # Build API zip package
    echo "Building API package..."
    cd app
    zip -r ../api-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".pytest_cache/*" -x "tests/*"
    cd ..
    
    # Deploy to Azure
    echo "Deploying to Azure App Service..."
    az webapp deploy \
        --resource-group $AZURE_RESOURCE_GROUP \
        --name $API_APP_NAME \
        --src-path api-deploy.zip \
        --type zip \
        --async false
    
    # Set environment variables
    echo "Configuring API environment variables..."
    az webapp config appsettings set \
        --resource-group $AZURE_RESOURCE_GROUP \
        --name $API_APP_NAME \
        --settings \
        AUTH_MODE=$AUTH_MODE \
        DATA_BACKEND=$DATA_BACKEND \
        STORAGE_MODE=$STORAGE_MODE \
        RAG_MODE=$RAG_MODE \
        AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
        AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT \
        ENABLE_S4_FEATURES=$ENABLE_S4_FEATURES \
        LOG_LEVEL=$LOG_LEVEL \
        ENVIRONMENT=$ENVIRONMENT
    
    # Restart the app
    echo "Restarting API..."
    az webapp restart --resource-group $AZURE_RESOURCE_GROUP --name $API_APP_NAME
    
    # Clean up
    rm -f api-deploy.zip
    
    echo -e "${GREEN}API deployment complete!${NC}"
}

# Function to deploy Web
deploy_web() {
    echo -e "${GREEN}Deploying Web to $WEB_APP_NAME...${NC}"
    
    # Build Web application
    echo "Building Web application..."
    cd web
    npm install
    npm run build
    
    # Create deployment package
    echo "Creating deployment package..."
    zip -r ../web-deploy.zip .next package.json package-lock.json public -x "node_modules/*"
    cd ..
    
    # Deploy to Azure
    echo "Deploying to Azure App Service..."
    az webapp deploy \
        --resource-group $AZURE_RESOURCE_GROUP \
        --name $WEB_APP_NAME \
        --src-path web-deploy.zip \
        --type zip \
        --async false
    
    # Set environment variables
    echo "Configuring Web environment variables..."
    az webapp config appsettings set \
        --resource-group $AZURE_RESOURCE_GROUP \
        --name $WEB_APP_NAME \
        --settings \
        AUTH_MODE=$AUTH_MODE \
        AZURE_AD_CLIENT_ID=$AZURE_AD_CLIENT_ID \
        AZURE_AD_TENANT_ID=$AZURE_AD_TENANT_ID \
        NEXTAUTH_URL=$NEXTAUTH_URL \
        PROXY_TARGET_API_BASE_URL=$PROXY_TARGET_API_BASE_URL \
        NODE_ENV=$NODE_ENV
    
    # Set startup command for Next.js
    az webapp config set \
        --resource-group $AZURE_RESOURCE_GROUP \
        --name $WEB_APP_NAME \
        --startup-file "npm run start"
    
    # Restart the app
    echo "Restarting Web..."
    az webapp restart --resource-group $AZURE_RESOURCE_GROUP --name $WEB_APP_NAME
    
    # Clean up
    rm -f web-deploy.zip
    
    echo -e "${GREEN}Web deployment complete!${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${GREEN}Verifying deployment...${NC}"
    
    # Check API health
    echo "Checking API health..."
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $API_BASE_URL/api/health || echo "000")
    if [ "$API_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ API is healthy${NC}"
    else
        echo -e "${RED}✗ API health check failed (HTTP $API_STATUS)${NC}"
    fi
    
    # Check Web health
    echo "Checking Web application..."
    WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $WEB_BASE_URL || echo "000")
    if [ "$WEB_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Web application is responding${NC}"
    else
        echo -e "${YELLOW}⚠ Web application returned HTTP $WEB_STATUS${NC}"
    fi
    
    # Check version
    echo "Checking API version..."
    VERSION_INFO=$(curl -s $API_BASE_URL/api/version | jq -r '.git_sha' 2>/dev/null || echo "unknown")
    echo "  Deployed version: $VERSION_INFO"
}

# Main deployment flow
main() {
    echo -e "${GREEN}Starting deployment process...${NC}"
    
    # Check Azure CLI is logged in
    if ! az account show &>/dev/null; then
        echo -e "${RED}Error: Not logged in to Azure CLI${NC}"
        echo "Please run: az login"
        exit 1
    fi
    
    # Deploy based on arguments
    case "${1:-all}" in
        api)
            deploy_api
            ;;
        web)
            deploy_web
            ;;
        all)
            deploy_api
            deploy_web
            ;;
        verify)
            verify_deployment
            exit 0
            ;;
        *)
            echo "Usage: $0 [api|web|all|verify]"
            exit 1
            ;;
    esac
    
    # Verify deployment
    sleep 10
    verify_deployment
    
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
}

# Run main function
main "$@"
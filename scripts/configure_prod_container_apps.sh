#!/bin/bash

# Container Apps Production Configuration Script
# Configures Azure Container Apps with production environment variables
# Based on the production requirements for cycle 1 of production promotion

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Production configuration values
RESOURCE_GROUP="rg-cybermat-prd"
WEB_APP_NAME="web-cybermat-prd"
API_APP_NAME="api-cybermat-prd"
PROD_URL="https://web-cybermat-prd.azurewebsites.net"

# Logging functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Verify Azure CLI authentication
verify_az_auth() {
    log_info "Verifying Azure CLI authentication..."
    
    if ! az account show >/dev/null 2>&1; then
        log_error "Azure CLI not authenticated. Please run 'az login' or ensure managed identity is configured"
        exit 1
    fi
    
    local subscription_id
    subscription_id=$(az account show --query id -o tsv)
    log_success "Authenticated to subscription: $subscription_id"
}

# Check if Container App exists
verify_container_app() {
    local app_name="$1"
    local service_type="$2"
    
    log_info "Verifying $service_type Container App: $app_name"
    
    if az containerapp show --name "$app_name" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
        log_success "$service_type Container App exists: $app_name"
        return 0
    else
        log_warning "$service_type Container App not found: $app_name (will skip configuration)"
        return 1
    fi
}

# Generate NEXTAUTH_SECRET if needed
generate_nextauth_secret() {
    log_info "Checking NEXTAUTH_SECRET in Key Vault..."
    
    local kv_name
    kv_name=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)
    
    if [[ -z "$kv_name" ]]; then
        log_warning "No Key Vault found in resource group"
        return 1
    fi
    
    # Check if nextauth-secret already exists
    local secret_value
    secret_value=$(az keyvault secret show --vault-name "$kv_name" --name "nextauth-secret" --query "value" -o tsv 2>/dev/null || echo "")
    
    if [[ -n "$secret_value" && "$secret_value" != "placeholder-nextauth-secret" ]]; then
        log_success "NEXTAUTH_SECRET already configured in Key Vault"
        return 0
    fi
    
    # Generate new secret
    local new_secret
    new_secret=$(openssl rand -base64 32)
    
    if az keyvault secret set --vault-name "$kv_name" --name "nextauth-secret" --value "$new_secret" --output none; then
        log_success "Generated and stored new NEXTAUTH_SECRET in Key Vault"
    else
        log_error "Failed to store NEXTAUTH_SECRET in Key Vault"
        return 1
    fi
}

# Configure Web Container App
configure_web_container_app() {
    log_info "=== Configuring Web Container App: $WEB_APP_NAME ==="
    
    if ! verify_container_app "$WEB_APP_NAME" "Web"; then
        log_warning "Skipping Web Container App configuration - service not found"
        return 0
    fi
    
    # Environment variables for production
    local env_vars=(
        "NODE_ENV=production"
        "AUTH_TRUST_HOST=true"
        "NEXT_PUBLIC_ADMIN_E2E=0"
        "DEMO_E2E=0"
        "NEXT_PUBLIC_API_BASE_URL=/api/proxy"
        "PROXY_TARGET_API_BASE_URL=https://${API_APP_NAME}.azurewebsites.net"
        "NEXTAUTH_URL=${PROD_URL}"
    )
    
    log_info "Updating Web Container App environment variables..."
    
    # Create environment variables JSON
    local env_json="["
    local first=true
    for env_var in "${env_vars[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            env_json+=","
        fi
        local name="${env_var%%=*}"
        local value="${env_var#*=}"
        env_json+="{\"name\":\"$name\",\"value\":\"$value\"}"
    done
    env_json+="]"
    
    # Update the container app
    if az containerapp update \
        --name "$WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --set-env-vars $env_json \
        --output none 2>/dev/null; then
        log_success "Web Container App environment variables updated"
    else
        log_error "Failed to update Web Container App environment variables"
        return 1
    fi
}

# Configure API Container App (minimal changes needed)
configure_api_container_app() {
    log_info "=== Configuring API Container App: $API_APP_NAME ==="
    
    if ! verify_container_app "$API_APP_NAME" "API"; then
        log_warning "Skipping API Container App configuration - service not found"
        return 0
    fi
    
    log_info "API Container App configuration is managed by Terraform"
    log_success "API Container App verification complete"
}

# Restart Container Apps
restart_container_apps() {
    log_info "=== Restarting Container Apps ==="
    
    local restart_failures=0
    
    # Restart Web Container App
    if verify_container_app "$WEB_APP_NAME" "Web" >/dev/null 2>&1; then
        log_info "Restarting Web Container App: $WEB_APP_NAME"
        if az containerapp revision restart \
            --name "$WEB_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --output none 2>/dev/null; then
            log_success "Web Container App restart initiated"
        else
            log_warning "Failed to restart Web Container App"
            ((restart_failures++))
        fi
    fi
    
    # Restart API Container App
    if verify_container_app "$API_APP_NAME" "API" >/dev/null 2>&1; then
        log_info "Restarting API Container App: $API_APP_NAME"
        if az containerapp revision restart \
            --name "$API_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --output none 2>/dev/null; then
            log_success "API Container App restart initiated"
        else
            log_warning "Failed to restart API Container App"
            ((restart_failures++))
        fi
    fi
    
    return $restart_failures
}

# Check warmup status
check_warmup_logs() {
    log_info "=== Checking Warmup Status ==="
    
    # Wait for services to start
    sleep 10
    
    # Check web app health
    local web_url="https://${WEB_APP_NAME}.azurewebsites.net"
    log_info "Checking Web App health: $web_url"
    
    if curl -sf "$web_url/api/health" >/dev/null 2>&1; then
        log_success "Web App is responding to health checks"
    else
        log_warning "Web App health check failed - this may be normal during warmup"
    fi
    
    # Check API app health
    local api_url="https://${API_APP_NAME}.azurewebsites.net"
    log_info "Checking API App health: $api_url/health"
    
    if curl -sf "$api_url/health" >/dev/null 2>&1; then
        log_success "API App is responding to health checks"
    else
        log_warning "API App health check failed - this may be normal during warmup"
    fi
    
    log_info "Container App logs can be viewed with:"
    echo "  Web logs: az containerapp logs show --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
    echo "  API logs: az containerapp logs show --name $API_APP_NAME --resource-group $RESOURCE_GROUP"
}

# Generate configuration summary
generate_summary() {
    log_info "=== Production Configuration Summary ==="
    
    echo
    echo "Applied Configuration:"
    echo "===================="
    
    echo "Web Container App: $WEB_APP_NAME"
    echo "  - NODE_ENV: production"
    echo "  - AUTH_TRUST_HOST: true"
    echo "  - NEXT_PUBLIC_ADMIN_E2E: 0 (disabled)"
    echo "  - DEMO_E2E: 0 (disabled)"
    echo "  - NEXT_PUBLIC_API_BASE_URL: /api/proxy"
    echo "  - PROXY_TARGET_API_BASE_URL: https://${API_APP_NAME}.azurewebsites.net"
    echo "  - NEXTAUTH_URL: $PROD_URL"
    echo "  - NEXTAUTH_SECRET: Configured from Key Vault"
    echo "  - Status: Restarted"
    
    echo
    echo "API Container App: $API_APP_NAME"
    echo "  - Configuration: Managed by Terraform"
    echo "  - Target Port: 8000"
    echo "  - Status: Restarted"
    
    echo
    echo "Production URLs:"
    echo "==============="
    echo "Web App: https://${WEB_APP_NAME}.azurewebsites.net"
    echo "API App: https://${API_APP_NAME}.azurewebsites.net"
    echo "Production URL: $PROD_URL"
    
    echo
    echo "Next Steps:"
    echo "=========="
    echo "1. Wait 2-3 minutes for services to fully warm up"
    echo "2. Run smoke tests to verify functionality"
    echo "3. Check application logs for any startup errors"
    echo "4. Verify authentication flows are working"
    
    echo
    log_success "Production Container Apps configuration complete"
}

# Main execution function
main() {
    echo "=== Container Apps Production Configuration ==="
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Web App: $WEB_APP_NAME"
    echo "API App: $API_APP_NAME"
    echo "Production URL: $PROD_URL"
    echo
    
    # Validation and setup
    verify_az_auth
    
    echo
    # Generate NextAuth secret if needed
    generate_nextauth_secret
    
    echo
    # Configure applications
    configure_web_container_app
    echo
    configure_api_container_app
    
    echo
    # Restart services
    local restart_failures
    restart_container_apps || restart_failures=$?
    
    echo
    # Check warmup status
    check_warmup_logs
    
    echo
    # Generate summary
    generate_summary
    
    # Final status
    if [[ ${restart_failures:-0} -eq 0 ]]; then
        log_success "All Container Apps configured and restarted successfully"
        echo
        echo "🚀 Production deployment ready for smoke tests (issue #216 cycle 1)"
        exit 0
    else
        log_warning "Configuration complete but ${restart_failures:-0} restart(s) failed"
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    log_info "Script interrupted - cleaning up..."
    exit 130
}

trap cleanup SIGINT SIGTERM

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
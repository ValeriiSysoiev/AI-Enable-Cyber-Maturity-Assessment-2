#!/bin/bash

# App Service Production Settings Configuration Script
# Configures Azure App Services with production environment variables and settings
# Reads repository variables and applies settings to Web and API App Services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - read from repository variables (no defaults for security)
WEB_APP_NAME="${APPSVC_WEBAPP_WEB_PROD:-}"
API_APP_NAME="${APPSVC_WEBAPP_API_PROD:-}"
PROD_URL="${PROD_URL:-}"

# Resource group from Azure deployment context
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"

# Logging functions following project patterns
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Validate required environment variables
validate_environment() {
    log_info "Validating environment variables..."
    
    local missing_vars=()
    
    if [[ -z "$WEB_APP_NAME" ]]; then
        missing_vars+=("APPSVC_WEBAPP_WEB_PROD")
    fi
    
    if [[ -z "$API_APP_NAME" ]]; then
        missing_vars+=("APPSVC_WEBAPP_API_PROD")
    fi
    
    if [[ -z "$RESOURCE_GROUP" ]]; then
        missing_vars+=("AZURE_RESOURCE_GROUP")
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required repository variables:"
        printf '  - %s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set the following repository variables in GitHub:"
        echo "  APPSVC_WEBAPP_WEB_PROD=<your-web-app-name>"
        echo "  APPSVC_WEBAPP_API_PROD=<your-api-app-name>"
        echo "  AZURE_RESOURCE_GROUP=<your-resource-group>"
        echo "  PROD_URL=<your-production-url>  # optional"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

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

# Check if App Service exists
verify_app_service() {
    local app_name="$1"
    local service_type="$2"
    
    log_info "Verifying $service_type App Service: $app_name"
    
    if az webapp show --name "$app_name" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
        log_success "$service_type App Service exists: $app_name"
        return 0
    else
        log_warning "$service_type App Service not found: $app_name (will skip configuration)"
        return 1
    fi
}

# Apply setting with guard rails and status reporting
apply_setting() {
    local app_name="$1"
    local setting_name="$2"
    local setting_value="$3"
    local service_type="$4"
    local overwrite="${5:-true}"
    
    log_info "Applying $service_type setting: $setting_name"
    
    # Check if setting already exists (guard rail)
    local current_value
    current_value=$(az webapp config appsettings list \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?name=='$setting_name'].value | [0]" -o tsv 2>/dev/null || echo "")
    
    if [[ -n "$current_value" && "$current_value" != "null" ]]; then
        if [[ "$overwrite" == "false" ]]; then
            log_warning "$service_type $setting_name already set to '$current_value' (skipping)"
            return 0
        else
            log_info "$service_type $setting_name currently set to '$current_value' (will update)"
        fi
    fi
    
    # Apply the setting
    if az webapp config appsettings set \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --settings "$setting_name=$setting_value" \
        --output none 2>/dev/null; then
        log_success "$service_type $setting_name = '$setting_value'"
    else
        log_error "Failed to set $service_type $setting_name"
        return 1
    fi
}

# Configure Web App Service settings
configure_web_app() {
    log_info "=== Configuring Web App Service: $WEB_APP_NAME ==="
    
    if ! verify_app_service "$WEB_APP_NAME" "Web"; then
        log_warning "Skipping Web App configuration - service not found"
        return 0
    fi
    
    # Required Web App settings
    apply_setting "$WEB_APP_NAME" "WEBSITES_PORT" "3000" "Web"
    apply_setting "$WEB_APP_NAME" "PORT" "3000" "Web"
    apply_setting "$WEB_APP_NAME" "NODE_ENV" "production" "Web"
    
    # NEXTAUTH_URL setting (conditional)
    if [[ -n "$PROD_URL" ]]; then
        apply_setting "$WEB_APP_NAME" "NEXTAUTH_URL" "$PROD_URL" "Web"
    else
        log_warning "PROD_URL not set - skipping NEXTAUTH_URL configuration"
    fi
    
    # NEXT_PUBLIC_API_BASE_URL setting
    local api_base_url="https://${API_APP_NAME}.azurewebsites.net"
    apply_setting "$WEB_APP_NAME" "NEXT_PUBLIC_API_BASE_URL" "$api_base_url" "Web"
    
    log_success "Web App configuration complete"
}

# Configure API App Service settings
configure_api_app() {
    log_info "=== Configuring API App Service: $API_APP_NAME ==="
    
    if ! verify_app_service "$API_APP_NAME" "API"; then
        log_warning "Skipping API App configuration - service not found"
        return 0
    fi
    
    # PORT setting (only if not already set - guard rail)
    apply_setting "$API_APP_NAME" "PORT" "8000" "API" "false"
    
    log_success "API App configuration complete"
}

# Enable container logs with filesystem storage and tail hints
enable_container_logs() {
    local app_name="$1"
    local service_type="$2"
    
    log_info "Enabling container logs for $service_type: $app_name"
    
    if az webapp log config \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --docker-container-logging filesystem \
        --output none 2>/dev/null; then
        log_success "$service_type container logs enabled (filesystem)"
        
        # Provide tail hints
        log_info "$service_type log tail hint: az webapp log tail --name $app_name --resource-group $RESOURCE_GROUP"
    else
        log_warning "Failed to enable container logs for $service_type"
        return 1
    fi
}

# Restart App Service
restart_app_service() {
    local app_name="$1"
    local service_type="$2"
    
    log_info "Restarting $service_type App Service: $app_name"
    
    if az webapp restart \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --output none 2>/dev/null; then
        log_success "$service_type App Service restart initiated"
        
        # Wait a moment and check status
        sleep 5
        local status
        status=$(az webapp show \
            --name "$app_name" \
            --resource-group "$RESOURCE_GROUP" \
            --query "state" -o tsv 2>/dev/null || echo "Unknown")
        
        if [[ "$status" == "Running" ]]; then
            log_success "$service_type App Service is running"
        else
            log_warning "$service_type App Service status: $status"
        fi
    else
        log_warning "Failed to restart $service_type App Service"
        return 1
    fi
}

# Generate configuration summary
generate_summary() {
    log_info "=== Configuration Summary ==="
    
    echo
    echo "Applied Settings:"
    echo "================"
    
    echo "Web App Service: $WEB_APP_NAME"
    echo "  - WEBSITES_PORT: 3000"
    echo "  - PORT: 3000"
    echo "  - NODE_ENV: production"
    if [[ -n "$PROD_URL" ]]; then
        echo "  - NEXTAUTH_URL: $PROD_URL"
    else
        echo "  - NEXTAUTH_URL: [SKIPPED - PROD_URL not set]"
    fi
    echo "  - NEXT_PUBLIC_API_BASE_URL: https://${API_APP_NAME}.azurewebsites.net"
    echo "  - Container logs: Enabled (filesystem)"
    echo "  - Status: Restarted"
    
    echo
    echo "API App Service: $API_APP_NAME"
    echo "  - PORT: 8000 (if not already set)"
    echo "  - Container logs: Enabled (filesystem)"
    echo "  - Status: Restarted"
    
    echo
    echo "Log Monitoring Commands:"
    echo "======================="
    echo "Web App logs: az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
    echo "API App logs: az webapp log tail --name $API_APP_NAME --resource-group $RESOURCE_GROUP"
    
    echo
    echo "App Service URLs:"
    echo "================"
    echo "Web App: https://${WEB_APP_NAME}.azurewebsites.net"
    echo "API App: https://${API_APP_NAME}.azurewebsites.net"
    
    if [[ -n "$PROD_URL" ]]; then
        echo "Production URL: $PROD_URL"
    fi
    
    echo
    log_success "Production App Service configuration complete"
}

# Main execution function
main() {
    echo "=== App Service Production Settings Configuration ==="
    echo "Web App: ${WEB_APP_NAME:-'Not set'}"
    echo "API App: ${API_APP_NAME:-'Not set'}"
    echo "Resource Group: ${RESOURCE_GROUP:-'Not set'}"
    echo "Production URL: ${PROD_URL:-'Not set'}"
    echo
    
    # Validation
    validate_environment
    verify_az_auth
    
    echo
    # Configure applications
    configure_web_app
    echo
    configure_api_app
    
    echo
    # Enable logging for both services
    log_info "=== Enabling Container Logs ==="
    if verify_app_service "$WEB_APP_NAME" "Web" >/dev/null 2>&1; then
        enable_container_logs "$WEB_APP_NAME" "Web"
    fi
    
    if verify_app_service "$API_APP_NAME" "API" >/dev/null 2>&1; then
        enable_container_logs "$API_APP_NAME" "API"
    fi
    
    echo
    # Restart both services
    log_info "=== Restarting App Services ==="
    local restart_failures=0
    
    if verify_app_service "$WEB_APP_NAME" "Web" >/dev/null 2>&1; then
        restart_app_service "$WEB_APP_NAME" "Web" || ((restart_failures++))
    fi
    
    if verify_app_service "$API_APP_NAME" "API" >/dev/null 2>&1; then
        restart_app_service "$API_APP_NAME" "API" || ((restart_failures++))
    fi
    
    echo
    # Generate summary
    generate_summary
    
    # Final status
    if [[ $restart_failures -eq 0 ]]; then
        log_success "All App Services configured and restarted successfully"
        exit 0
    else
        log_warning "Configuration complete but $restart_failures restart(s) failed"
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
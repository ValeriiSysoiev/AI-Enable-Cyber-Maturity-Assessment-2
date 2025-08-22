#!/bin/bash

# Production Rollback Script
# Re-deploys previous GHCR image tags to Azure Container Apps

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Configuration from environment variables
ACA_RG_PROD="${ACA_RG_PROD:-}"
ACA_ENV_PROD="${ACA_ENV_PROD:-}"
ACA_APP_API_PROD="${ACA_APP_API_PROD:-}"
ACA_APP_WEB_PROD="${ACA_APP_WEB_PROD:-}"
GHCR_REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-${GHCR_REPO_OWNER:-}}"

# Validate required variables
validate_environment() {
    local missing_vars=()
    
    if [[ -z "$ACA_RG_PROD" ]]; then
        missing_vars+=("ACA_RG_PROD")
    fi
    
    if [[ -z "$ACA_ENV_PROD" ]]; then
        missing_vars+=("ACA_ENV_PROD")
    fi
    
    if [[ -z "$ACA_APP_API_PROD" ]]; then
        missing_vars+=("ACA_APP_API_PROD")
    fi
    
    if [[ -z "$ACA_APP_WEB_PROD" ]]; then
        missing_vars+=("ACA_APP_WEB_PROD")
    fi
    
    if [[ -z "$GHCR_REPO_OWNER" ]]; then
        missing_vars+=("GHCR_REPO_OWNER or GITHUB_REPOSITORY_OWNER")
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        printf '  - %s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set the following environment variables:"
        echo "  export ACA_RG_PROD=<production-resource-group>"
        echo "  export ACA_ENV_PROD=<production-container-apps-environment>"
        echo "  export ACA_APP_API_PROD=<production-api-app-name>"
        echo "  export ACA_APP_WEB_PROD=<production-web-app-name>"
        echo "  export GHCR_REPO_OWNER=<github-repo-owner>"
        echo ""
        exit 1
    fi
}

# Check Azure CLI authentication
check_azure_auth() {
    log_info "Checking Azure CLI authentication..."
    
    if ! az account show >/dev/null 2>&1; then
        log_error "Azure CLI not authenticated. Please run 'az login'"
        exit 1
    fi
    
    local subscription_id
    subscription_id=$(az account show --query id -o tsv)
    log_success "Authenticated to subscription: $subscription_id"
}

# Get current container app revisions
get_current_revisions() {
    log_info "Getting current production container app revisions..."
    
    # Get current API revision
    local current_api_revision
    current_api_revision=$(az containerapp revision list \
        --name "$ACA_APP_API_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --query "[?properties.active].name" \
        --output tsv | head -1 2>/dev/null || echo "")
    
    if [[ -n "$current_api_revision" ]]; then
        log_info "Current API revision: $current_api_revision"
        echo "CURRENT_API_REVISION=$current_api_revision"
    else
        log_warning "Could not determine current API revision"
    fi
    
    # Get current Web revision
    local current_web_revision
    current_web_revision=$(az containerapp revision list \
        --name "$ACA_APP_WEB_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --query "[?properties.active].name" \
        --output tsv | head -1 2>/dev/null || echo "")
    
    if [[ -n "$current_web_revision" ]]; then
        log_info "Current Web revision: $current_web_revision"
        echo "CURRENT_WEB_REVISION=$current_web_revision"
    else
        log_warning "Could not determine current Web revision"
    fi
}

# Get previous GHCR image tags
get_previous_images() {
    log_info "Determining previous GHCR image tags for rollback..."
    
    # For emergency rollback, we'll use the 'latest' tag as the previous version
    # In a production environment, you might want to maintain a specific rollback tag
    
    local api_image="ghcr.io/${GHCR_REPO_OWNER}/aecma-api:latest"
    local web_image="ghcr.io/${GHCR_REPO_OWNER}/aecma-web:latest"
    
    log_info "API rollback image: $api_image"
    log_info "Web rollback image: $web_image"
    
    echo "API_ROLLBACK_IMAGE=$api_image"
    echo "WEB_ROLLBACK_IMAGE=$web_image"
}

# Execute rollback for API container app
rollback_api() {
    local api_image="$1"
    
    log_info "Rolling back API container app to: $api_image"
    
    local rollback_suffix
    rollback_suffix="rollback-$(date +%Y%m%d-%H%M%S)"
    
    if az containerapp update \
        --name "$ACA_APP_API_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --environment "$ACA_ENV_PROD" \
        --image "$api_image" \
        --revision-suffix "$rollback_suffix" \
        >/dev/null 2>&1; then
        
        log_success "API rollback completed successfully"
        return 0
    else
        log_error "API rollback failed"
        return 1
    fi
}

# Execute rollback for Web container app
rollback_web() {
    local web_image="$1"
    
    log_info "Rolling back Web container app to: $web_image"
    
    local rollback_suffix
    rollback_suffix="rollback-$(date +%Y%m%d-%H%M%S)"
    
    if az containerapp update \
        --name "$ACA_APP_WEB_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --environment "$ACA_ENV_PROD" \
        --image "$web_image" \
        --revision-suffix "$rollback_suffix" \
        >/dev/null 2>&1; then
        
        log_success "Web rollback completed successfully"
        return 0
    else
        log_error "Web rollback failed"
        return 1
    fi
}

# Wait for rollback stabilization
wait_for_stabilization() {
    log_info "Waiting for rollback to stabilize..."
    
    local wait_time=60
    log_info "Waiting ${wait_time} seconds for container apps to stabilize..."
    sleep $wait_time
    
    # Check API app status
    local api_status
    api_status=$(az containerapp show \
        --name "$ACA_APP_API_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Unknown")
    
    log_info "API app status: $api_status"
    
    # Check Web app status
    local web_status
    web_status=$(az containerapp show \
        --name "$ACA_APP_WEB_PROD" \
        --resource-group "$ACA_RG_PROD" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Unknown")
    
    log_info "Web app status: $web_status"
    
    if [[ "$api_status" == "Succeeded" && "$web_status" == "Succeeded" ]]; then
        log_success "Rollback stabilization completed"
        return 0
    else
        log_warning "Rollback stabilization may require additional time"
        return 1
    fi
}

# Verify rollback success
verify_rollback() {
    log_info "Verifying rollback success..."
    
    # Compute production URL for verification
    local prod_url
    if [[ -n "${PROD_URL:-}" ]]; then
        prod_url="$PROD_URL"
    else
        prod_url="https://${ACA_APP_WEB_PROD}.${ACA_ENV_PROD}.azurecontainerapps.io"
    fi
    
    log_info "Testing production URL: $prod_url"
    
    # Basic health check
    local health_check_attempts=3
    local attempt=1
    
    while [[ $attempt -le $health_check_attempts ]]; do
        log_info "Health check attempt $attempt/$health_check_attempts..."
        
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$prod_url" 2>/dev/null || echo "000")
        
        if [[ "$response_code" =~ ^[23][0-9][0-9]$ ]]; then
            log_success "Rollback verification passed (HTTP $response_code)"
            return 0
        else
            log_warning "Health check failed (HTTP $response_code), attempt $attempt/$health_check_attempts"
            ((attempt++))
            [[ $attempt -le $health_check_attempts ]] && sleep 10
        fi
    done
    
    log_error "Rollback verification failed after $health_check_attempts attempts"
    return 1
}

# Generate rollback summary
generate_summary() {
    local rollback_status="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo
    echo "=================================="
    echo "Production Rollback Summary"
    echo "=================================="
    echo "Timestamp: $timestamp"
    echo "Status: $rollback_status"
    echo
    echo "Environment:"
    echo "  Resource Group: $ACA_RG_PROD"
    echo "  Container Apps Environment: $ACA_ENV_PROD"
    echo "  API App: $ACA_APP_API_PROD"
    echo "  Web App: $ACA_APP_WEB_PROD"
    echo
    echo "Rollback Images:"
    echo "  API: ghcr.io/${GHCR_REPO_OWNER}/aecma-api:latest"
    echo "  Web: ghcr.io/${GHCR_REPO_OWNER}/aecma-web:latest"
    echo
    
    if [[ "$rollback_status" == "SUCCESS" ]]; then
        echo "✅ ROLLBACK SUCCESSFUL"
        echo
        echo "Next Steps:"
        echo "1. Monitor system health and performance"
        echo "2. Notify stakeholders of rollback completion"
        echo "3. Begin root cause analysis of original issue"
        echo "4. Plan fix-forward strategy"
        echo "5. Update incident documentation"
    else
        echo "❌ ROLLBACK FAILED"
        echo
        echo "Immediate Actions Required:"
        echo "1. Escalate to senior technical staff"
        echo "2. Consider manual intervention"
        echo "3. Activate incident response team"
        echo "4. Communicate status to stakeholders"
        echo "5. Document rollback failure details"
    fi
    
    echo "=================================="
}

# Main execution
main() {
    echo "=== Production Emergency Rollback ==="
    echo
    
    log_warning "EMERGENCY ROLLBACK INITIATED"
    log_warning "This will rollback production to previous GHCR images"
    echo
    
    # Validation
    validate_environment
    check_azure_auth
    
    # Get current state for documentation
    get_current_revisions
    
    # Determine rollback images
    get_previous_images
    
    # Confirmation prompt
    echo
    log_warning "CONFIRMATION REQUIRED"
    echo "This will rollback the following production apps:"
    echo "  - API: $ACA_APP_API_PROD"
    echo "  - Web: $ACA_APP_WEB_PROD"
    echo
    read -p "Proceed with emergency rollback? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
    
    # Execute rollback
    local rollback_success=true
    
    log_info "Starting emergency rollback process..."
    
    # Rollback API
    if ! rollback_api "ghcr.io/${GHCR_REPO_OWNER}/aecma-api:latest"; then
        rollback_success=false
    fi
    
    # Rollback Web
    if ! rollback_web "ghcr.io/${GHCR_REPO_OWNER}/aecma-web:latest"; then
        rollback_success=false
    fi
    
    # Wait for stabilization
    wait_for_stabilization
    
    # Verify rollback
    if ! verify_rollback; then
        rollback_success=false
    fi
    
    # Generate summary
    if [[ "$rollback_success" == "true" ]]; then
        generate_summary "SUCCESS"
        log_success "Emergency rollback completed successfully"
        exit 0
    else
        generate_summary "FAILED"
        log_error "Emergency rollback failed - manual intervention required"
        exit 1
    fi
}

# Usage information
show_usage() {
    echo "Usage: $0"
    echo
    echo "Emergency production rollback script for Azure Container Apps"
    echo
    echo "Required environment variables:"
    echo "  ACA_RG_PROD              # Production resource group"
    echo "  ACA_ENV_PROD             # Production container apps environment"
    echo "  ACA_APP_API_PROD         # Production API app name"
    echo "  ACA_APP_WEB_PROD         # Production web app name"
    echo "  GHCR_REPO_OWNER          # GitHub repository owner"
    echo
    echo "Prerequisites:"
    echo "  - Azure CLI installed and authenticated"
    echo "  - Contributor permissions on production resources"
    echo "  - GHCR images available for rollback"
    echo
    echo "Security notes:"
    echo "  - No secrets are stored in this script"
    echo "  - Uses Azure CLI authentication"
    echo "  - Confirmation required before execution"
}

# Handle arguments
if [[ $# -gt 0 ]]; then
    case "$1" in
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
fi

# Run main function
main "$@"
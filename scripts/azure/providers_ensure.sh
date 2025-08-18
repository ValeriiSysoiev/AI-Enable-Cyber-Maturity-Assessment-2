#!/bin/bash

# Azure Providers Ensure Script
# Ensures resource group exists and registers required Azure providers
# Idempotent and bounded with proper error handling

set -euo pipefail

# Configuration
MAX_WAIT=${MAX_WAIT:-480}  # Maximum wait time in seconds (8 minutes)
REQUIRED_PROVIDERS=(
    "Microsoft.OperationalInsights"
    "Microsoft.Insights"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if Azure CLI is installed and authenticated
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        log_error "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    if ! az account show &> /dev/null; then
        log_error "Azure CLI is not authenticated. Please run 'az login' first."
        exit 1
    fi
}

# Get current subscription info
get_subscription_info() {
    local sub_info
    sub_info=$(az account show --query '{id:id,name:name,tenantId:tenantId}' -o json 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to get subscription information"
        exit 1
    fi
    
    echo "$sub_info"
}

# Print subscription details
print_subscription_info() {
    local sub_info="$1"
    local sub_id sub_name tenant_id
    
    sub_id=$(echo "$sub_info" | jq -r '.id')
    sub_name=$(echo "$sub_info" | jq -r '.name')
    tenant_id=$(echo "$sub_info" | jq -r '.tenantId')
    
    log_info "Subscription ID: $sub_id"
    log_info "Subscription Name: $sub_name"
    log_info "Tenant ID: $tenant_id"
}

# Ensure resource group exists
ensure_resource_group() {
    local rg_name="$1"
    local location="$2"
    
    log_info "Checking resource group: $rg_name"
    
    if az group show --name "$rg_name" &> /dev/null; then
        log_success "Resource group '$rg_name' already exists"
        return 0
    fi
    
    log_info "Creating resource group: $rg_name in $location"
    
    if az group create --name "$rg_name" --location "$location" &> /dev/null; then
        log_success "Resource group '$rg_name' created successfully"
    else
        log_error "Failed to create resource group '$rg_name'"
        log_error "Check if you have Contributor permissions on the subscription"
        exit 1
    fi
}

# Check provider registration status
check_provider_status() {
    local provider="$1"
    local status
    
    status=$(az provider show --namespace "$provider" --query 'registrationState' -o tsv 2>/dev/null)
    echo "$status"
}

# Register a provider
register_provider() {
    local provider="$1"
    
    log_info "Registering provider: $provider"
    
    if az provider register --namespace "$provider" &> /dev/null; then
        log_info "Provider registration initiated: $provider"
        return 0
    else
        log_error "Failed to register provider: $provider"
        return 1
    fi
}

# Wait for provider registration with timeout
wait_for_provider_registration() {
    local provider="$1"
    local start_time end_time elapsed
    
    start_time=$(date +%s)
    end_time=$((start_time + MAX_WAIT))
    
    log_info "Waiting for $provider registration (max ${MAX_WAIT}s)..."
    
    while true; do
        local status
        status=$(check_provider_status "$provider")
        
        case "$status" in
            "Registered")
                log_success "Provider $provider is registered"
                return 0
                ;;
            "Registering")
                elapsed=$(($(date +%s) - start_time))
                if [[ $elapsed -ge $MAX_WAIT ]]; then
                    log_error "Timeout waiting for $provider registration (${MAX_WAIT}s)"
                    return 2
                fi
                log_info "Provider $provider is still registering... (${elapsed}s elapsed)"
                sleep 10
                ;;
            "NotRegistered")
                log_warning "Provider $provider registration failed, retrying..."
                if ! register_provider "$provider"; then
                    return 1
                fi
                sleep 5
                ;;
            *)
                log_error "Unknown provider status: $status"
                return 1
                ;;
        esac
    done
}

# Ensure all required providers are registered
ensure_providers() {
    local failed_providers=()
    local timeout_providers=()
    
    for provider in "${REQUIRED_PROVIDERS[@]}"; do
        local status
        status=$(check_provider_status "$provider")
        
        log_info "Provider $provider status: $status"
        
        case "$status" in
            "Registered")
                log_success "Provider $provider is already registered"
                ;;
            "Registering")
                if ! wait_for_provider_registration "$provider"; then
                    case $? in
                        2) timeout_providers+=("$provider") ;;
                        *) failed_providers+=("$provider") ;;
                    esac
                fi
                ;;
            "NotRegistered")
                if register_provider "$provider"; then
                    if ! wait_for_provider_registration "$provider"; then
                        case $? in
                            2) timeout_providers+=("$provider") ;;
                            *) failed_providers+=("$provider") ;;
                        esac
                    fi
                else
                    failed_providers+=("$provider")
                fi
                ;;
            *)
                log_error "Unknown status '$status' for provider $provider"
                failed_providers+=("$provider")
                ;;
        esac
    done
    
    # Handle failures and timeouts
    if [[ ${#timeout_providers[@]} -gt 0 ]]; then
        log_error "Provider registration timed out for: ${timeout_providers[*]}"
        log_error ""
        log_error "REMEDIATION TIPS:"
        log_error "1. Provider registration can take 10-15 minutes in some regions"
        log_error "2. Check Azure Service Health for any ongoing issues"
        log_error "3. Verify you have Owner or Contributor role on the subscription"
        log_error "4. Re-run this script later or increase MAX_WAIT environment variable"
        log_error "5. Check provider status manually: az provider show --namespace <provider>"
        return 2
    fi
    
    if [[ ${#failed_providers[@]} -gt 0 ]]; then
        log_error "Failed to register providers: ${failed_providers[*]}"
        log_error ""
        log_error "REMEDIATION TIPS:"
        log_error "1. Check if you have sufficient permissions (Owner or Contributor role)"
        log_error "2. Verify subscription is active and not disabled"
        log_error "3. Contact Azure support if the issue persists"
        log_error "4. Check Azure Service Health for provider-specific issues"
        return 1
    fi
    
    log_success "All required providers are registered successfully"
    return 0
}

# Main function
main() {
    local resource_group_name="${AZURE_RESOURCE_GROUP:-}"
    local location="${AZURE_LOCATION:-East US}"
    
    log_info "Azure Providers Ensure Script Starting..."
    log_info "Max wait time: ${MAX_WAIT}s"
    
    # Check prerequisites
    check_azure_cli
    
    # Get and display subscription info
    local sub_info
    sub_info=$(get_subscription_info)
    print_subscription_info "$sub_info"
    
    # Ensure resource group if specified
    if [[ -n "$resource_group_name" ]]; then
        ensure_resource_group "$resource_group_name" "$location"
    else
        log_info "AZURE_RESOURCE_GROUP not set, skipping resource group creation"
    fi
    
    # Ensure providers are registered
    log_info "Ensuring required Azure providers are registered..."
    if ensure_providers; then
        log_success "All operations completed successfully!"
        exit 0
    else
        case $? in
            2)
                log_error "Script exited due to timeout"
                exit 2
                ;;
            *)
                log_error "Script exited due to errors"
                exit 1
                ;;
        esac
    fi
}

# Handle script interruption
trap 'log_error "Script interrupted by user"; exit 130' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
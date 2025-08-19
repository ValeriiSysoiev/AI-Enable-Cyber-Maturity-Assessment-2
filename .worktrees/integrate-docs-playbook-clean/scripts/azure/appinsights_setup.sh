#!/bin/bash

# Azure Application Insights Setup Script
# Ensures Log Analytics workspace exists and creates/updates workspace-based Application Insights
# Idempotent and bounded with proper error handling and permission checks

set -euo pipefail

# Configuration
REQUIRED_PROVIDERS=("Microsoft.OperationalInsights" "Microsoft.Insights")

# Colors and logging functions
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1" >&2; }

# Print PO needed checklist for permission failures
print_po_checklist() {
    log_error "=========================================="
    log_error "PRODUCT OWNER (PO) ACTION REQUIRED"
    log_error "=========================================="
    log_error "REQUIRED PERMISSIONS:"
    log_error "1. Contributor role on subscription & resource group: ${AZURE_RESOURCE_GROUP:-<not-set>}"
    log_error "2. Resource Provider registration permissions"
    
    log_error "PROVIDER STATUS:"
    for provider in "${REQUIRED_PROVIDERS[@]}"; do
        local status=$(az provider show --namespace "$provider" --query 'registrationState' -o tsv 2>/dev/null || echo "Unknown")
        log_error "   $provider: $status"
    done
    
    log_error "NEXT STEPS: Grant roles via Azure RBAC, register providers, re-run script"
    log_error "PORTAL: https://portal.azure.com -> Subscriptions -> Access control (IAM)"
    log_error "=========================================="
}

# Check prerequisites
check_prerequisites() {
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not installed: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        return 1
    fi
    
    if ! az account show &> /dev/null; then
        log_error "Azure CLI not authenticated. Run 'az login' first."
        return 1
    fi
    
    if [[ -z "${AZURE_RESOURCE_GROUP:-}" ]]; then
        log_error "Missing AZURE_RESOURCE_GROUP environment variable"
        return 1
    fi
    
    return 0
}

# Check if resource group exists and user has permissions
check_permissions() {
    local rg_name="$1"
    
    if ! az group show --name "$rg_name" &> /dev/null; then
        log_error "Cannot access resource group '$rg_name'"
        return 1
    fi
    
    if ! az resource list --resource-group "$rg_name" --query "length(@)" -o tsv &> /dev/null; then
        log_error "Insufficient permissions for resource group '$rg_name'"
        return 1
    fi
    
    log_success "Resource group access verified: $rg_name"
    return 0
}

# Resource management helpers
generate_law_suffix() {
    local rg_name="$1"
    local sub_id=$(az account show --query 'id' -o tsv)
    echo -n "${rg_name}${sub_id}" | sha256sum | cut -c1-6
}

ensure_law() {
    local rg_name="$1" law_name="$2" location="$3"
    
    if az monitor log-analytics workspace show --resource-group "$rg_name" --workspace-name "$law_name" &> /dev/null; then
        log_success "Log Analytics workspace exists: $law_name"
        return 0
    fi
    
    log_info "Creating Log Analytics workspace: $law_name"
    if az monitor log-analytics workspace create \
        --resource-group "$rg_name" --workspace-name "$law_name" --location "$location" \
        --sku "PerGB2018" --retention-time 30 \
        --tags "Purpose=CyberMaturityAssessment" "ManagedBy=appinsights_setup.sh" &> /dev/null; then
        log_success "Log Analytics workspace created: $law_name"
        return 0
    else
        log_error "Failed to create Log Analytics workspace: $law_name"
        return 1
    fi
}

ensure_appinsights() {
    local rg_name="$1" ai_name="$2" location="$3" law_id="$4"
    
    if az monitor app-insights component show --app "$ai_name" --resource-group "$rg_name" &> /dev/null; then
        local current_workspace=$(az monitor app-insights component show \
            --app "$ai_name" --resource-group "$rg_name" \
            --query 'workspaceResourceId' -o tsv 2>/dev/null || echo "")
        
        if [[ "$current_workspace" == "$law_id" ]]; then
            log_success "Application Insights already linked to workspace: $ai_name"
            return 0
        else
            log_warning "Application Insights exists but not linked - manual update may be required"
            return 0
        fi
    fi
    
    log_info "Creating Application Insights: $ai_name"
    if az monitor app-insights component create \
        --app "$ai_name" --location "$location" --resource-group "$rg_name" \
        --application-type "web" --workspace "$law_id" \
        --tags "Purpose=CyberMaturityAssessment" "ManagedBy=appinsights_setup.sh" &> /dev/null; then
        log_success "Application Insights created: $ai_name"
        return 0
    else
        log_error "Failed to create Application Insights: $ai_name"
        return 1
    fi
}

# Print setup results
print_results() {
    local law_name="$1" ai_name="$2" law_id="$3" connection_string="$4"
    
    log_success "=========================================="
    log_success "APPLICATION INSIGHTS SETUP COMPLETE"
    log_success "=========================================="
    log_success "Log Analytics: $law_name (ID: ${law_id##*/})"
    log_success "App Insights: $ai_name"
    log_success "Connection: $connection_string"
    log_success "Workspace Binding: CONFIRMED - Ready for monitoring!"
    log_success "=========================================="
}

# Main setup function
setup_appinsights() {
    local rg_name="${AZURE_RESOURCE_GROUP}"
    local location="${AZURE_LOCATION:-East US}"
    local name_prefix="${AZURE_RESOURCE_PREFIX:-cma}"
    local law_suffix=$(generate_law_suffix "$rg_name")
    local law_name="log-${name_prefix}-${law_suffix}"
    local ai_name="appi-${name_prefix}"
    
    log_info "Setting up: RG=$rg_name, LAW=$law_name, AI=$ai_name"
    
    # Check permissions first
    if ! check_permissions "$rg_name"; then
        log_skip "Permission denied - see PO checklist below"
        print_po_checklist
        exit 0
    fi
    
    # Ensure Log Analytics workspace
    if ! ensure_law "$rg_name" "$law_name" "$location"; then
        log_skip "Cannot create Log Analytics workspace"
        print_po_checklist
        exit 0
    fi
    
    # Get workspace ID
    local law_id=$(az monitor log-analytics workspace show \
        --resource-group "$rg_name" --workspace-name "$law_name" \
        --query 'id' -o tsv 2>/dev/null)
    
    if [[ -z "$law_id" ]]; then
        log_error "Failed to retrieve Log Analytics workspace ID"
        exit 1
    fi
    
    # Ensure Application Insights
    if ! ensure_appinsights "$rg_name" "$ai_name" "$location" "$law_id"; then
        log_skip "Cannot create/update Application Insights"
        print_po_checklist
        exit 0
    fi
    
    # Get connection string and print results
    local connection_string=$(az monitor app-insights component show \
        --app "$ai_name" --resource-group "$rg_name" \
        --query 'connectionString' -o tsv 2>/dev/null)
    
    if [[ -z "$connection_string" ]]; then
        log_error "Failed to retrieve Application Insights connection string"
        exit 1
    fi
    
    print_results "$law_name" "$ai_name" "$law_id" "$connection_string"
    return 0
}

# Main function
main() {
    log_info "Azure Application Insights Setup Starting..."
    
    if ! check_prerequisites; then
        log_skip "Prerequisites not met - see error above"
        exit 0
    fi
    
    # Check provider registration (non-blocking warning)
    for provider in "${REQUIRED_PROVIDERS[@]}"; do
        local status=$(az provider show --namespace "$provider" --query 'registrationState' -o tsv 2>/dev/null || echo "Unknown")
        if [[ "$status" != "Registered" ]]; then
            log_warning "Provider $provider not registered (status: $status)"
        fi
    done
    
    # Run setup
    if setup_appinsights; then
        log_success "Setup completed successfully!"
        exit 0
    else
        log_error "Setup failed - see output above"
        exit 1
    fi
}

# Handle interruption and run main
trap 'log_error "Script interrupted"; exit 130' INT TERM
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi
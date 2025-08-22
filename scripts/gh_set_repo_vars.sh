#!/bin/bash

# GitHub Repository Variables Helper Script
# Sets repository variables from .env.staging.vars file using GitHub CLI
# Includes security guards and clear warnings about PAT requirements

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VARS_FILE="${PROJECT_ROOT}/.env.staging.vars"

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Security check for sensitive patterns
check_sensitive_data() {
    local key="$1"
    local value="$2"
    
    # Patterns that should never be committed
    local sensitive_patterns=(
        "password"
        "secret"
        "token"
        "key"
        "credential"
    )
    
    for pattern in "${sensitive_patterns[@]}"; do
        if echo "$key" | grep -qi "$pattern"; then
            log_warning "Variable '$key' contains sensitive pattern '$pattern'"
            log_warning "Ensure this is appropriate for repository variables (not secrets)"
            return 1
        fi
    done
    
    # Check for obvious credentials in value
    if [[ ${#value} -gt 50 && "$value" =~ [A-Za-z0-9+/=]{40,} ]]; then
        log_warning "Variable '$key' value looks like a credential (base64/jwt pattern)"
        return 1
    fi
    
    return 0
}

# Main function
main() {
    log_info "GitHub Repository Variables Setup"
    echo
    
    # Check prerequisites
    if ! command -v gh >/dev/null 2>&1; then
        log_error "GitHub CLI (gh) not found. Install with: brew install gh"
        exit 1
    fi
    
    # Check authentication
    if ! gh auth status >/dev/null 2>&1; then
        log_error "GitHub CLI not authenticated"
        echo
        echo "Required scopes for repository variables:"
        echo "  - repo (for repository access)"
        echo "  - admin:org (for organization variables, if needed)"
        echo
        echo "Authenticate with:"
        echo "  gh auth login --scopes repo,admin:org"
        echo
        exit 1
    fi
    
    # Check if vars file exists
    if [[ ! -f "$VARS_FILE" ]]; then
        log_error "Variables file not found: $VARS_FILE"
        echo
        echo "Create a file with KEY=VALUE pairs:"
        echo "  GHCR_ENABLED=1"
        echo "  STAGING_URL=https://your-staging-url.com"
        echo "  ACA_RG=your-resource-group"
        echo "  # etc..."
        echo
        exit 1
    fi
    
    log_info "Reading variables from: $VARS_FILE"
    
    # Security warning
    echo
    log_warning "SECURITY NOTICE:"
    echo "  - Repository variables are visible to all repository collaborators"
    echo "  - Use GitHub secrets for sensitive data (passwords, tokens, keys)"
    echo "  - This script will NOT echo variable values for security"
    echo "  - Sensitive patterns will be flagged for review"
    echo
    
    # Read and validate variables
    local vars_to_set=()
    local sensitive_count=0
    
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Skip if no value
        [[ -z "$value" ]] && continue
        
        # Security check
        if ! check_sensitive_data "$key" "$value"; then
            ((sensitive_count++))
            log_warning "Consider using GitHub secrets for '$key' instead of variables"
        fi
        
        vars_to_set+=("$key=$value")
        log_info "Queued variable: $key"
        
    done < "$VARS_FILE"
    
    # Check if any variables found
    if [[ ${#vars_to_set[@]} -eq 0 ]]; then
        log_error "No valid variables found in $VARS_FILE"
        exit 1
    fi
    
    # Security confirmation if sensitive data detected
    if [[ $sensitive_count -gt 0 ]]; then
        echo
        log_warning "Found $sensitive_count potentially sensitive variables"
        read -p "Continue with setting repository variables? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Aborted by user"
            exit 0
        fi
    fi
    
    echo
    log_info "Setting ${#vars_to_set[@]} repository variables..."
    
    # Set variables
    local success_count=0
    local error_count=0
    
    for var in "${vars_to_set[@]}"; do
        local key="${var%%=*}"
        local value="${var#*=}"
        
        if gh variable set "$key" --body "$value" >/dev/null 2>&1; then
            log_success "Set variable: $key"
            ((success_count++))
        else
            log_error "Failed to set variable: $key"
            ((error_count++))
        fi
    done
    
    echo
    log_info "Summary:"
    echo "  ✓ Successfully set: $success_count variables"
    if [[ $error_count -gt 0 ]]; then
        echo "  ✗ Failed to set: $error_count variables"
    fi
    
    if [[ $success_count -gt 0 ]]; then
        echo
        log_success "Repository variables updated successfully"
        echo
        echo "Next steps:"
        echo "  1. Verify variables in GitHub repo Settings → Variables"
        echo "  2. Trigger 'Deploy Staging' workflow to test deployment"
        echo "  3. Run verification: ./scripts/verify_live.sh --staging"
    fi
    
    if [[ $error_count -gt 0 ]]; then
        echo
        log_warning "Some variables failed to set. Check:"
        echo "  - GitHub CLI authentication and scopes"
        echo "  - Repository permissions"
        echo "  - Variable name restrictions"
        exit 1
    fi
}

# Usage information
show_usage() {
    echo "Usage: $0"
    echo
    echo "Sets GitHub repository variables from .env.staging.vars file"
    echo
    echo "Required file format (.env.staging.vars):"
    echo "  GHCR_ENABLED=1"
    echo "  STAGING_URL=https://your-app.azurewebsites.net"
    echo "  ACA_RG=rg-staging"
    echo "  ACA_ENV=env-staging"
    echo "  # Comments are ignored"
    echo
    echo "Prerequisites:"
    echo "  - GitHub CLI installed and authenticated"
    echo "  - Repository access permissions"
    echo "  - .env.staging.vars file in project root"
    echo
    echo "Security notes:"
    echo "  - Use GitHub secrets for passwords/tokens/keys"
    echo "  - Repository variables are visible to all collaborators"
    echo "  - Sensitive patterns will trigger warnings"
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
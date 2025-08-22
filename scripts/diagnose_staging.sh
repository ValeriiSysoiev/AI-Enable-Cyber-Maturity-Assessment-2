#!/bin/bash

# Staging Environment Diagnostics Script
# Collects comprehensive staging deployment information for troubleshooting

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
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts/verify"

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Ensure artifacts directory exists
mkdir -p "$ARTIFACTS_DIR"

# Main diagnostics function
main() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    log_info "Starting staging environment diagnostics..."
    
    {
        echo "=================================="
        echo "Staging Environment Diagnostics"
        echo "=================================="
        echo "Timestamp: $timestamp"
        echo ""
        
        # Environment snapshot
        echo "=== Environment Variables ==="
        echo "STAGING_URL: ${STAGING_URL:-'Not set'}"
        echo "ACA_APP_WEB: ${ACA_APP_WEB:-'Not set'}"
        echo "ACA_ENV: ${ACA_ENV:-'Not set'}"
        echo "GHCR_ENABLED: ${GHCR_ENABLED:-'Not set'}"
        echo "AZURE_SUBSCRIPTION_ID: ${AZURE_SUBSCRIPTION_ID:+*REDACTED*}"
        echo "AZURE_CLIENT_ID: ${AZURE_CLIENT_ID:+*REDACTED*}"
        echo "AZURE_TENANT_ID: ${AZURE_TENANT_ID:+*REDACTED*}"
        echo ""
        
        # Computed staging URL
        local computed_url=""
        if [[ -n "$STAGING_URL" ]]; then
            computed_url="$STAGING_URL"
            echo "=== Computed Staging URL ==="
            echo "Using configured STAGING_URL: $computed_url"
        elif [[ -n "$ACA_APP_WEB" && -n "$ACA_ENV" ]]; then
            computed_url="https://${ACA_APP_WEB}.${ACA_ENV}.azurecontainerapps.io"
            echo "=== Computed Staging URL ==="
            echo "Computed from ACA variables: $computed_url"
        else
            echo "=== Computed Staging URL ==="
            echo "ERROR: Cannot compute staging URL - insufficient variables"
        fi
        echo ""
        
        # GitHub Actions information
        echo "=== GitHub Actions ==="
        if command -v gh >/dev/null 2>&1; then
            echo "GitHub CLI available"
            
            # Get last Deploy Staging run
            local last_run_url
            last_run_url=$(gh run list --workflow="Deploy Staging" --limit=1 --json url --jq '.[0].url' 2>/dev/null || echo "Not available")
            echo "Last Deploy Staging run: $last_run_url"
            
            # Get run status
            local run_status
            run_status=$(gh run list --workflow="Deploy Staging" --limit=1 --json status --jq '.[0].status' 2>/dev/null || echo "Unknown")
            echo "Last run status: $run_status"
            
            # Get run conclusion
            local run_conclusion
            run_conclusion=$(gh run list --workflow="Deploy Staging" --limit=1 --json conclusion --jq '.[0].conclusion' 2>/dev/null || echo "Unknown")
            echo "Last run conclusion: $run_conclusion"
        else
            echo "GitHub CLI not available - install with: brew install gh"
        fi
        echo ""
        
        # Curl diagnostics if URL available
        if [[ -n "$computed_url" ]]; then
            echo "=== HTTP Diagnostics ==="
            echo "Testing URL: $computed_url"
            echo ""
            
            echo "--- Response Headers ---"
            curl -s -I --max-time 30 "$computed_url" 2>/dev/null || echo "Connection failed"
            echo ""
            
            echo "--- Response Body (first 500 chars) ---"
            local response_body
            response_body=$(curl -s --max-time 30 "$computed_url" 2>/dev/null || echo "Connection failed")
            echo "$response_body" | head -c 500
            if [[ ${#response_body} -gt 500 ]]; then
                echo "... (truncated)"
            fi
            echo ""
            
            # Test health endpoint
            echo "--- Health Endpoint ---"
            local health_url="${computed_url}/health"
            local health_response
            health_response=$(curl -s --max-time 10 "$health_url" 2>/dev/null || echo "Health endpoint not accessible")
            echo "Health URL: $health_url"
            echo "Health Response: $health_response"
            echo ""
            
            # Test API config endpoint
            echo "--- API Configuration ---"
            local config_url="${computed_url}/api/ops/config"
            local config_response
            config_response=$(curl -s --max-time 10 "$config_url" 2>/dev/null || echo "Config endpoint not accessible")
            echo "Config URL: $config_url"
            echo "Config Response (first 300 chars):"
            echo "$config_response" | head -c 300
            if [[ ${#config_response} -gt 300 ]]; then
                echo "... (truncated)"
            fi
            echo ""
        fi
        
        # Azure CLI diagnostics
        echo "=== Azure CLI Diagnostics ==="
        if command -v az >/dev/null 2>&1; then
            echo "Azure CLI available"
            
            # Check authentication
            local azure_account
            azure_account=$(az account show --query name -o tsv 2>/dev/null || echo "Not authenticated")
            echo "Authenticated account: $azure_account"
            
            if [[ "$azure_account" != "Not authenticated" ]]; then
                local subscription_id
                subscription_id=$(az account show --query id -o tsv 2>/dev/null || echo "Unknown")
                echo "Subscription ID: $subscription_id"
                
                # Check Container Apps if variables are set
                if [[ -n "$ACA_APP_WEB" && -n "${ACA_RG:-}" ]]; then
                    echo ""
                    echo "--- Container App Status ---"
                    local app_status
                    app_status=$(az containerapp show \
                        --name "$ACA_APP_WEB" \
                        --resource-group "${ACA_RG}" \
                        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "App not found or access denied")
                    echo "Web app status: $app_status"
                    
                    if [[ "$app_status" == "Succeeded" ]]; then
                        local app_url
                        app_url=$(az containerapp show \
                            --name "$ACA_APP_WEB" \
                            --resource-group "${ACA_RG}" \
                            --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "URL not available")
                        echo "Web app URL: https://$app_url"
                    fi
                fi
            fi
        else
            echo "Azure CLI not available - install with: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
        fi
        echo ""
        
        # Docker/Container diagnostics
        echo "=== Container Diagnostics ==="
        if command -v docker >/dev/null 2>&1; then
            echo "Docker available"
            
            # Check if any AECMA containers are running locally
            local local_containers
            local_containers=$(docker ps --filter "name=aecma" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No local containers")
            echo "Local AECMA containers: $local_containers"
        else
            echo "Docker not available"
        fi
        echo ""
        
        # Network diagnostics
        echo "=== Network Diagnostics ==="
        if [[ -n "$computed_url" ]]; then
            local hostname
            hostname=$(echo "$computed_url" | sed 's|https\?://||' | cut -d'/' -f1)
            echo "Testing DNS resolution for: $hostname"
            
            local dns_result
            dns_result=$(nslookup "$hostname" 2>/dev/null || echo "DNS resolution failed")
            echo "$dns_result"
        fi
        echo ""
        
        # Troubleshooting suggestions
        echo "=== Troubleshooting Suggestions ==="
        echo "1. Check GitHub Actions workflow status:"
        echo "   - Go to Actions tab in GitHub repository"
        echo "   - Look for 'Deploy Staging' workflow"
        echo "   - Check for any failed steps or error messages"
        echo ""
        echo "2. Verify repository variables are set:"
        echo "   - Go to Settings > Secrets and variables > Actions > Variables"
        echo "   - Ensure STAGING_URL or ACA_* variables are configured"
        echo "   - For App Service: set STAGING_URL, leave ACA_ENV empty"
        echo "   - For Container Apps: set all AZURE_* and ACA_* variables"
        echo ""
        echo "3. Check staging deployment logs:"
        echo "   - Use: gh run view --log (if GitHub CLI is available)"
        echo "   - Look for deployment errors or timeout issues"
        echo ""
        echo "4. Manual verification commands:"
        echo "   - Test health: curl -I $computed_url"
        echo "   - Run staging verify: ./scripts/verify_live.sh --staging"
        echo "   - Check Azure resources: az containerapp show --name \$ACA_APP_WEB --resource-group \$ACA_RG"
        echo ""
        echo "=== End Diagnostics ==="
        
    } | tee "$ARTIFACTS_DIR/staging_diagnose.log"
    
    log_success "Diagnostics complete - saved to: $ARTIFACTS_DIR/staging_diagnose.log"
}

# Run diagnostics
main "$@"
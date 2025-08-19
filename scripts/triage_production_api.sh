#!/bin/bash
# Production API Triage Script
# Systematic approach to diagnose and fix API 503 issues

set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-cybermat-prd"
API_APP_NAME="api-cybermat-prd"
WEB_APP_NAME="web-cybermat-prd"
COSMOS_NAME="cdb-cybermat-prd"
LOG_DIR="logs/triage/$(date +%Y%m%d-%H%M%S)"
MAX_REPAIR_CYCLES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_DIR/triage.log"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_DIR/triage.log"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_DIR/triage.log"
}

# Phase 0: Preflight Checks
phase0_preflight() {
    log "PHASE 0: Running preflight checks..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        error "Azure CLI not installed"
        exit 1
    fi
    
    # Check authentication
    if ! az account show &> /dev/null; then
        error "Not logged into Azure. Run: az login"
        exit 1
    fi
    
    # Check resource group
    if ! az group show -n "$RESOURCE_GROUP" &> /dev/null; then
        error "Resource group $RESOURCE_GROUP not found"
        exit 1
    fi
    
    # Check Microsoft.App provider
    local provider_state=$(az provider show -n Microsoft.App --query "registrationState" -o tsv)
    if [ "$provider_state" != "Registered" ]; then
        warning "Microsoft.App provider not registered. Registering..."
        az provider register -n Microsoft.App --wait
    fi
    
    log "Preflight checks complete"
}

# Phase 1: Diagnostics Collection
phase1_diagnostics() {
    log "PHASE 1: Collecting diagnostics..."
    
    # Get App Service configuration
    log "Fetching App Service configuration..."
    az webapp config show -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
        > "$LOG_DIR/app_config.json" 2>&1 || true
    
    # Get App Service settings
    az webapp config appsettings list -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
        > "$LOG_DIR/app_settings.json" 2>&1 || true
    
    # Get recent logs
    log "Fetching recent logs..."
    az webapp log tail -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
        --timeout 30 > "$LOG_DIR/app_logs.txt" 2>&1 || true
    
    # Test endpoints
    log "Testing API endpoints..."
    local api_url="https://${API_APP_NAME}.azurewebsites.net"
    
    for endpoint in "/" "/health" "/docs"; do
        log "Testing $endpoint..."
        curl -w "\n%{http_code} %{time_total}s\n" -m 10 \
            "$api_url$endpoint" > "$LOG_DIR/probe_${endpoint//\//_}.txt" 2>&1 || true
    done
    
    # Create diagnostic summary
    cat > "$LOG_DIR/diagnostic_summary.md" << EOF
# Diagnostic Summary
Generated: $(date)

## App Service: $API_APP_NAME
- Resource Group: $RESOURCE_GROUP
- URL: $api_url

## Configuration
$(cat "$LOG_DIR/app_config.json" | jq -r '.linuxFxVersion // "N/A"')

## HTTP Probe Results
$(for f in "$LOG_DIR"/probe_*.txt; do echo "### $(basename $f)"; tail -1 "$f"; done)

## Recent Logs
$(tail -20 "$LOG_DIR/app_logs.txt" || echo "No logs captured")
EOF
    
    log "Diagnostics collected in $LOG_DIR"
}

# Phase 2: Repair Attempts
phase2_repair() {
    log "PHASE 2: Starting repair attempts (max $MAX_REPAIR_CYCLES cycles)..."
    
    local cycle=1
    local api_url="https://${API_APP_NAME}.azurewebsites.net"
    
    while [ $cycle -le $MAX_REPAIR_CYCLES ]; do
        log "Repair cycle $cycle/$MAX_REPAIR_CYCLES"
        
        case $cycle in
            1)
                log "Attempting startup command fix..."
                az webapp config set -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
                    --startup-file "cd /home/site/wwwroot && python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000"
                ;;
            2)
                log "Attempting gunicorn configuration..."
                az webapp config set -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
                    --startup-file "cd /home/site/wwwroot && gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.api.main:app --bind 0.0.0.0:8000"
                ;;
            3)
                log "Attempting simple Python HTTP server test..."
                az webapp config set -n "$API_APP_NAME" -g "$RESOURCE_GROUP" \
                    --startup-file "cd /home/site/wwwroot && python -m http.server 8000"
                ;;
        esac
        
        # Restart app
        log "Restarting App Service..."
        az webapp restart -n "$API_APP_NAME" -g "$RESOURCE_GROUP"
        
        # Wait for startup
        sleep 30
        
        # Test health endpoint
        if curl -f -m 10 "$api_url/health" > /dev/null 2>&1; then
            log "✅ Repair successful! API is responding."
            return 0
        else
            warning "Repair cycle $cycle failed"
        fi
        
        ((cycle++))
    done
    
    error "All repair attempts failed"
    return 1
}

# Phase 3: Container Apps Fallback
phase3_aca_fallback() {
    log "PHASE 3: Deploying to Azure Container Apps as fallback..."
    
    local env_name="cae-cybermat-prd"
    local aca_name="api-cybermat-prd-aca"
    
    # Check if environment exists
    if ! az containerapp env show -n "$env_name" -g "$RESOURCE_GROUP" &> /dev/null; then
        log "Creating Container Apps environment..."
        az containerapp env create \
            -n "$env_name" \
            -g "$RESOURCE_GROUP" \
            --location "West Europe"
    fi
    
    # Build container using ACR (if available)
    local acr_name=$(az acr list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    if [ -n "$acr_name" ]; then
        log "Building container in ACR: $acr_name"
        az acr build \
            --registry "$acr_name" \
            --image "api-cybermat:latest" \
            ./app
        
        # Deploy to Container Apps
        log "Deploying to Container Apps..."
        az containerapp create \
            -n "$aca_name" \
            -g "$RESOURCE_GROUP" \
            --environment "$env_name" \
            --image "${acr_name}.azurecr.io/api-cybermat:latest" \
            --target-port 8000 \
            --ingress external \
            --system-assigned \
            --env-vars PORT=8000
    else
        warning "No ACR found. Manual container build required."
        return 1
    fi
    
    # Get ACA URL
    local aca_url=$(az containerapp show -n "$aca_name" -g "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" -o tsv)
    
    log "Container App deployed: https://$aca_url"
    
    # Test health
    if curl -f -m 10 "https://$aca_url/health" > /dev/null 2>&1; then
        log "✅ Container Apps deployment successful!"
        return 0
    else
        error "Container Apps deployment failed"
        return 1
    fi
}

# Phase 4: Update Frontend
phase4_update_frontend() {
    log "PHASE 4: Updating frontend configuration..."
    
    local new_api_url="$1"
    
    az webapp config appsettings set \
        -n "$WEB_APP_NAME" \
        -g "$RESOURCE_GROUP" \
        --settings "NEXT_PUBLIC_API_BASE_URL=$new_api_url"
    
    az webapp restart -n "$WEB_APP_NAME" -g "$RESOURCE_GROUP"
    
    log "Frontend updated to use: $new_api_url"
}

# Phase 5: Generate Report
phase5_report() {
    log "PHASE 5: Generating final report..."
    
    cat > "$LOG_DIR/triage_report.md" << EOF
# Production API Triage Report
Generated: $(date)

## Execution Summary
- Start Time: $(head -1 "$LOG_DIR/triage.log" | cut -d' ' -f1-2)
- End Time: $(date +'%Y-%m-%d %H:%M:%S')
- Log Directory: $LOG_DIR

## Phase Results
$(grep "PHASE" "$LOG_DIR/triage.log")

## Recommendations
1. Review diagnostic logs in $LOG_DIR
2. If App Service continues to fail, use Container Apps deployment
3. Monitor health endpoints continuously
4. Implement automated failover for future incidents

## Support Bundle Location
$LOG_DIR/

## Next Steps
- [ ] Open Azure support ticket if needed
- [ ] Implement monitoring alerts
- [ ] Document lessons learned
- [ ] Update runbooks
EOF
    
    log "Report generated: $LOG_DIR/triage_report.md"
}

# Main execution
main() {
    log "Starting Production API Triage..."
    
    # Run phases
    phase0_preflight
    phase1_diagnostics
    
    if phase2_repair; then
        log "✅ App Service repaired successfully!"
        phase5_report
        exit 0
    fi
    
    warning "App Service repair failed, attempting Container Apps fallback..."
    
    if phase3_aca_fallback; then
        local aca_url=$(az containerapp show -n "api-cybermat-prd-aca" -g "$RESOURCE_GROUP" \
            --query "properties.configuration.ingress.fqdn" -o tsv)
        phase4_update_frontend "https://$aca_url"
        log "✅ Container Apps fallback successful!"
    else
        error "Both App Service and Container Apps deployment failed"
        error "Manual intervention required. Support bundle: $LOG_DIR"
    fi
    
    phase5_report
}

# Run main function
main "$@"
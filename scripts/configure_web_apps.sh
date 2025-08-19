#!/bin/bash

# Web Frontend Repair - Azure App Service Configuration Script
# This script configures both staging and production Azure Web Apps

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../logs/agents/configurator.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if Azure CLI is available and logged in
check_az_cli() {
    if ! command -v az &> /dev/null; then
        log "ERROR: Azure CLI is not installed"
        exit 1
    fi
    
    if ! az account show &> /dev/null; then
        log "ERROR: Not logged into Azure CLI. Please run 'az login' first"
        exit 1
    fi
    
    log "Azure CLI is available and authenticated"
}

# Configure staging environment
configure_staging() {
    log "=== CONFIGURING STAGING ENVIRONMENT ==="
    
    # Set Node.js runtime
    log "Setting Node.js runtime for staging..."
    az webapp config set \
        -g rg-cybermat-stg \
        -n web-cybermat-stg \
        --linux-fx-version "NODE|20-lts" \
        2>&1 | tee -a "$LOG_FILE"
    
    # Configure app settings
    log "Setting app settings for staging..."
    az webapp config appsettings set \
        -g rg-cybermat-stg \
        -n web-cybermat-stg \
        --settings \
            "PORT=8080" \
            "WEBSITES_PORT=8080" \
            "NODE_ENV=production" \
            "NEXT_TELEMETRY_DISABLED=1" \
            "WEBSITE_NODE_DEFAULT_VERSION=~20" \
            "SCM_DO_BUILD_DURING_DEPLOYMENT=false" \
            "NEXT_PUBLIC_API_BASE_URL=https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io" \
        2>&1 | tee -a "$LOG_FILE"
    
    # Set startup file
    log "Setting startup file for staging..."
    az webapp config set \
        -g rg-cybermat-stg \
        -n web-cybermat-stg \
        --startup-file "node server.js" \
        2>&1 | tee -a "$LOG_FILE"
    
    log "Staging environment configuration completed"
}

# Configure production environment
configure_production() {
    log "=== CONFIGURING PRODUCTION ENVIRONMENT ==="
    
    # Set Node.js runtime
    log "Setting Node.js runtime for production..."
    az webapp config set \
        -g rg-cybermat-prd \
        -n web-cybermat-prd \
        --linux-fx-version "NODE|20-lts" \
        2>&1 | tee -a "$LOG_FILE"
    
    # Configure app settings
    log "Setting app settings for production..."
    az webapp config appsettings set \
        -g rg-cybermat-prd \
        -n web-cybermat-prd \
        --settings \
            "PORT=8080" \
            "WEBSITES_PORT=8080" \
            "NODE_ENV=production" \
            "NEXT_TELEMETRY_DISABLED=1" \
            "WEBSITE_NODE_DEFAULT_VERSION=~20" \
            "SCM_DO_BUILD_DURING_DEPLOYMENT=false" \
            "NEXT_PUBLIC_API_BASE_URL=https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io" \
        2>&1 | tee -a "$LOG_FILE"
    
    # Set startup file
    log "Setting startup file for production..."
    az webapp config set \
        -g rg-cybermat-prd \
        -n web-cybermat-prd \
        --startup-file "node server.js" \
        2>&1 | tee -a "$LOG_FILE"
    
    log "Production environment configuration completed"
}

# Verify configurations
verify_configurations() {
    log "=== VERIFYING CONFIGURATIONS ==="
    
    # Verify staging
    log "Verifying staging configuration..."
    log "Runtime and startup settings for staging:"
    az webapp config show \
        -g rg-cybermat-stg \
        -n web-cybermat-stg \
        --query "{linuxFxVersion:linuxFxVersion,nodeVersion:nodeVersion,appCommandLine:appCommandLine}" \
        2>&1 | tee -a "$LOG_FILE"
    
    log "App settings for staging:"
    az webapp config appsettings list \
        -g rg-cybermat-stg \
        -n web-cybermat-stg \
        --query "[?name=='PORT' || name=='WEBSITES_PORT' || name=='NODE_ENV' || name=='NEXT_PUBLIC_API_BASE_URL' || name=='NEXT_TELEMETRY_DISABLED' || name=='WEBSITE_NODE_DEFAULT_VERSION' || name=='SCM_DO_BUILD_DURING_DEPLOYMENT'].{name:name, value:value}" \
        2>&1 | tee -a "$LOG_FILE"
    
    # Verify production
    log "Verifying production configuration..."
    log "Runtime and startup settings for production:"
    az webapp config show \
        -g rg-cybermat-prd \
        -n web-cybermat-prd \
        --query "{linuxFxVersion:linuxFxVersion,nodeVersion:nodeVersion,appCommandLine:appCommandLine}" \
        2>&1 | tee -a "$LOG_FILE"
    
    log "App settings for production:"
    az webapp config appsettings list \
        -g rg-cybermat-prd \
        -n web-cybermat-prd \
        --query "[?name=='PORT' || name=='WEBSITES_PORT' || name=='NODE_ENV' || name=='NEXT_PUBLIC_API_BASE_URL' || name=='NEXT_TELEMETRY_DISABLED' || name=='WEBSITE_NODE_DEFAULT_VERSION' || name=='SCM_DO_BUILD_DURING_DEPLOYMENT'].{name:name, value:value}" \
        2>&1 | tee -a "$LOG_FILE"
}

# Main execution
main() {
    log "Starting Web Frontend Repair Configuration"
    
    check_az_cli
    configure_staging
    configure_production
    verify_configurations
    
    log "=== CONFIGURATION COMPLETED SUCCESSFULLY ==="
    log "All Azure Web App configurations have been applied"
    log "Check the log file for detailed output: $LOG_FILE"
}

# Run the main function
main "$@"
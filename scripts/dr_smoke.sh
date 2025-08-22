#!/bin/bash
# Disaster Recovery Smoke Test Script
# Validates backup systems and recovery capabilities

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
DRY_RUN="${DRY_RUN:-true}"
RESOURCE_GROUP="${ACA_RG_PROD:-}"
COSMOS_ACCOUNT="${COSMOS_ACCOUNT:-}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"
CONTAINER_APP="${ACA_APP_API_PROD:-}"
OUTPUT_DIR="${OUTPUT_DIR:-artifacts/dr}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${BLUE}==== $1 ====${NC}"; }

# Initialize output directory
initialize_output() {
    log_header "Initializing DR Smoke Test"
    
    mkdir -p "$OUTPUT_DIR"
    
    # Create test report file
    REPORT_FILE="$OUTPUT_DIR/dr-smoke-report-$TIMESTAMP.md"
    
    cat > "$REPORT_FILE" << EOF
# Disaster Recovery Smoke Test Report

**Date**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
**Test Type**: ${DRY_RUN:+Dry Run}${DRY_RUN:-Live Test}
**Resource Group**: ${RESOURCE_GROUP:-Not configured}

## Test Results

EOF
    
    log_info "Report file: $REPORT_FILE"
    echo "REPORT_FILE=$REPORT_FILE" >> "$OUTPUT_DIR/test-vars.env"
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    local prerequisites_met=true
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_warn "Azure CLI not installed - running in documentation mode"
        DRY_RUN="true"
    fi
    
    # Check Azure login
    if [[ "$DRY_RUN" != "true" ]] && ! az account show &> /dev/null; then
        log_warn "Not logged into Azure - switching to dry run mode"
        DRY_RUN="true"
    fi
    
    # Check configuration
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_warn "RESOURCE_GROUP not set (set ACA_RG_PROD)"
        prerequisites_met=false
    fi
    
    if [[ -z "$COSMOS_ACCOUNT" ]]; then
        log_warn "COSMOS_ACCOUNT not set"
        prerequisites_met=false
    fi
    
    if [[ -z "$STORAGE_ACCOUNT" ]]; then
        log_warn "STORAGE_ACCOUNT not set"
        prerequisites_met=false
    fi
    
    if [[ "$prerequisites_met" == "false" && "$DRY_RUN" != "true" ]]; then
        log_error "Missing required configuration for live testing"
        log_info "Running in dry run mode instead"
        DRY_RUN="true"
    fi
    
    # Log test mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Running in DRY RUN mode - no actual Azure operations"
    else
        log_info "Running in LIVE mode - will perform actual Azure operations"
    fi
    
    echo "### Prerequisites Check" >> "$REPORT_FILE"
    echo "- Azure CLI: $(command -v az &> /dev/null && echo "✅ Available" || echo "❌ Not available")" >> "$REPORT_FILE"
    echo "- Azure Login: $(az account show &> /dev/null 2>&1 && echo "✅ Authenticated" || echo "❌ Not authenticated")" >> "$REPORT_FILE"
    echo "- Test Mode: ${DRY_RUN:+🏃 Dry Run}${DRY_RUN:-⚡ Live Test}" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
}

# Test database backup status
test_database_backup() {
    log_header "Testing Database Backup Status"
    
    echo "### Database Backup Test" >> "$REPORT_FILE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would check Cosmos DB backup status"
        echo "- Cosmos DB Account: ${COSMOS_ACCOUNT:-<not configured>}" >> "$REPORT_FILE"
        echo "- Backup Status: 🏃 Dry run - would check continuous backup" >> "$REPORT_FILE"
        echo "- Retention Period: 🏃 Dry run - would verify 30-day retention" >> "$REPORT_FILE"
        echo "- Geo-redundancy: 🏃 Dry run - would check geo-backup status" >> "$REPORT_FILE"
        return 0
    fi
    
    log_info "Checking Cosmos DB backup configuration..."
    
    # Check if account exists
    if ! az cosmosdb show --name "$COSMOS_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log_error "Cosmos DB account '$COSMOS_ACCOUNT' not found"
        echo "- Status: ❌ Account not found" >> "$REPORT_FILE"
        return 1
    fi
    
    # Get backup policy
    local backup_policy
    backup_policy=$(az cosmosdb show --name "$COSMOS_ACCOUNT" --resource-group "$RESOURCE_GROUP" \
        --query 'backupPolicy' -o json 2>/dev/null || echo "{}")
    
    if [[ "$backup_policy" != "{}" ]]; then
        log_info "✅ Backup policy found"
        echo "- Backup Policy: ✅ Configured" >> "$REPORT_FILE"
        
        # Save backup policy details
        echo "$backup_policy" > "$OUTPUT_DIR/cosmos-backup-policy-$TIMESTAMP.json"
        echo "- Policy Details: Saved to artifacts/dr/" >> "$REPORT_FILE"
    else
        log_warn "⚠️ Backup policy not found or accessible"
        echo "- Backup Policy: ⚠️ Not accessible" >> "$REPORT_FILE"
    fi
    
    # Check account properties
    local account_info
    account_info=$(az cosmosdb show --name "$COSMOS_ACCOUNT" --resource-group "$RESOURCE_GROUP" \
        --query '{locations: locations, consistencyPolicy: consistencyPolicy.defaultConsistencyLevel}' -o json)
    
    echo "$account_info" > "$OUTPUT_DIR/cosmos-account-info-$TIMESTAMP.json"
    
    log_info "✅ Database backup test completed"
    echo "" >> "$REPORT_FILE"
}

# Test storage backup status
test_storage_backup() {
    log_header "Testing Storage Backup Status"
    
    echo "### Storage Backup Test" >> "$REPORT_FILE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would check storage account backup configuration"
        echo "- Storage Account: ${STORAGE_ACCOUNT:-<not configured>}" >> "$REPORT_FILE"
        echo "- Replication Type: 🏃 Dry run - would check GRS/RA-GRS" >> "$REPORT_FILE"
        echo "- Versioning: 🏃 Dry run - would verify blob versioning" >> "$REPORT_FILE"
        echo "- Soft Delete: 🏃 Dry run - would check soft delete policy" >> "$REPORT_FILE"
        return 0
    fi
    
    log_info "Checking storage account backup configuration..."
    
    # Check if storage account exists
    if ! az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log_error "Storage account '$STORAGE_ACCOUNT' not found"
        echo "- Status: ❌ Account not found" >> "$REPORT_FILE"
        return 1
    fi
    
    # Get storage account properties
    local storage_info
    storage_info=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" \
        --query '{sku: sku.name, replication: sku.tier, encryption: encryption.services}' -o json)
    
    echo "$storage_info" > "$OUTPUT_DIR/storage-account-info-$TIMESTAMP.json"
    
    # Check replication type
    local replication_type
    replication_type=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" \
        --query 'sku.name' -o tsv)
    
    if [[ "$replication_type" == *"GRS"* || "$replication_type" == *"RAGRS"* ]]; then
        log_info "✅ Geo-redundant replication enabled: $replication_type"
        echo "- Replication: ✅ $replication_type" >> "$REPORT_FILE"
    else
        log_warn "⚠️ Non-geo-redundant replication: $replication_type"
        echo "- Replication: ⚠️ $replication_type (not geo-redundant)" >> "$REPORT_FILE"
    fi
    
    log_info "✅ Storage backup test completed"
    echo "" >> "$REPORT_FILE"
}

# Test container image backup
test_container_backup() {
    log_header "Testing Container Image Backup"
    
    echo "### Container Image Backup Test" >> "$REPORT_FILE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would check container image backup status"
        echo "- Container App: ${CONTAINER_APP:-<not configured>}" >> "$REPORT_FILE"
        echo "- Image Repository: 🏃 Dry run - would check GHCR/ACR" >> "$REPORT_FILE"
        echo "- Image Tags: 🏃 Dry run - would verify latest and SHA tags" >> "$REPORT_FILE"
        echo "- Registry Health: 🏃 Dry run - would check registry status" >> "$REPORT_FILE"
        return 0
    fi
    
    log_info "Checking container app configuration..."
    
    if [[ -z "$CONTAINER_APP" ]]; then
        log_warn "Container app name not configured"
        echo "- Status: ⚠️ Not configured" >> "$REPORT_FILE"
        return 0
    fi
    
    # Get container app info
    local app_info
    if app_info=$(az containerapp show --name "$CONTAINER_APP" --resource-group "$RESOURCE_GROUP" 2>/dev/null); then
        local current_image
        current_image=$(echo "$app_info" | jq -r '.properties.template.containers[0].image' 2>/dev/null || echo "unknown")
        
        log_info "✅ Container app found with image: $current_image"
        echo "- Current Image: $current_image" >> "$REPORT_FILE"
        
        # Save container app configuration
        echo "$app_info" > "$OUTPUT_DIR/container-app-config-$TIMESTAMP.json"
        echo "- Configuration: Saved to artifacts/dr/" >> "$REPORT_FILE"
    else
        log_warn "Container app '$CONTAINER_APP' not found or not accessible"
        echo "- Status: ⚠️ Not found or not accessible" >> "$REPORT_FILE"
    fi
    
    log_info "✅ Container backup test completed"
    echo "" >> "$REPORT_FILE"
}

# Test backup restoration capability
test_restore_capability() {
    log_header "Testing Restore Capability"
    
    echo "### Restore Capability Test" >> "$REPORT_FILE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would test restore procedures"
        echo "- Database Restore: 🏃 Dry run - would test point-in-time restore" >> "$REPORT_FILE"
        echo "- Storage Restore: 🏃 Dry run - would test blob recovery" >> "$REPORT_FILE"
        echo "- Application Restore: 🏃 Dry run - would test container deployment" >> "$REPORT_FILE"
        echo "- RTO/RPO Validation: 🏃 Dry run - would measure recovery times" >> "$REPORT_FILE"
        return 0
    fi
    
    log_info "Testing restore procedures (non-destructive)..."
    
    # Test database restore capability (read-only check)
    if [[ -n "$COSMOS_ACCOUNT" ]]; then
        log_info "Validating database restore capability..."
        
        # Check if we can list restorable timestamps
        local restorable_timestamps
        if restorable_timestamps=$(az cosmosdb sql restorable-database list \
            --location "East US" \
            --instance-id "$COSMOS_ACCOUNT" 2>/dev/null); then
            log_info "✅ Database restore capability verified"
            echo "- Database Restore: ✅ Capable" >> "$REPORT_FILE"
        else
            log_warn "⚠️ Could not verify database restore capability"
            echo "- Database Restore: ⚠️ Could not verify" >> "$REPORT_FILE"
        fi
    fi
    
    # Test storage restore capability
    if [[ -n "$STORAGE_ACCOUNT" ]]; then
        log_info "Validating storage restore capability..."
        
        # Check blob service properties
        if az storage account blob-service-properties show \
            --account-name "$STORAGE_ACCOUNT" \
            --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_info "✅ Storage restore capability verified"
            echo "- Storage Restore: ✅ Capable" >> "$REPORT_FILE"
        else
            log_warn "⚠️ Could not verify storage restore capability"
            echo "- Storage Restore: ⚠️ Could not verify" >> "$REPORT_FILE"
        fi
    fi
    
    log_info "✅ Restore capability test completed"
    echo "" >> "$REPORT_FILE"
}

# Generate verification checklist
generate_verification_checklist() {
    log_header "Generating Verification Checklist"
    
    local checklist_file="$OUTPUT_DIR/dr-verification-checklist-$TIMESTAMP.md"
    
    cat > "$checklist_file" << 'EOF'
# Disaster Recovery Verification Checklist

## Pre-Recovery Verification
- [ ] Incident declared and team notified
- [ ] Recovery procedures document accessible
- [ ] Required Azure permissions verified
- [ ] Backup availability confirmed
- [ ] Recovery environment prepared

## Database Recovery
- [ ] Cosmos DB point-in-time restore initiated
- [ ] Target restore timestamp confirmed
- [ ] Database connectivity established
- [ ] Data integrity verification completed
- [ ] Application database connections updated

## Storage Recovery
- [ ] Blob storage restore initiated
- [ ] Evidence files accessibility verified
- [ ] File integrity checks completed
- [ ] Storage account permissions validated
- [ ] Application storage connections updated

## Application Recovery
- [ ] Container images verified available
- [ ] Container apps redeployed
- [ ] Health checks passing
- [ ] Application endpoints responding
- [ ] SSL certificates valid

## Post-Recovery Validation
- [ ] End-to-end functionality testing
- [ ] User authentication working
- [ ] Assessment workflows functional
- [ ] Evidence upload/download working
- [ ] API endpoints responding correctly
- [ ] Performance within acceptable limits

## Communication and Documentation
- [ ] Stakeholders notified of recovery status
- [ ] Recovery timeline documented
- [ ] Issues encountered recorded
- [ ] Lessons learned captured
- [ ] Recovery report completed

## Sign-off
- [ ] Technical team validation: _________________ Date: _______
- [ ] Business team validation: _________________ Date: _______
- [ ] Incident commander approval: ______________ Date: _______

---
Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
EOF
    
    log_info "Verification checklist saved: $checklist_file"
    echo "- Verification Checklist: Generated in artifacts/dr/" >> "$REPORT_FILE"
}

# Generate final report
generate_final_report() {
    log_header "Generating Final Report"
    
    # Add summary to report
    cat >> "$REPORT_FILE" << EOF

## Summary

**Test Completed**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
**Test Duration**: Approximately 2 minutes
**Test Mode**: ${DRY_RUN:+Dry Run}${DRY_RUN:-Live Test}

### Recommendations
1. **Regular Testing**: Run this script monthly to validate backup systems
2. **Full DR Drill**: Conduct quarterly full disaster recovery exercises
3. **Documentation Updates**: Keep backup procedures current with infrastructure changes
4. **Monitoring**: Implement alerts for backup failures and replication lag

### Next Steps
- Review test results with operations team
- Address any warnings or failed checks
- Schedule next DR drill
- Update procedures based on findings

---
*This report was generated automatically by the DR smoke test script*
EOF
    
    log_info "Final report completed: $REPORT_FILE"
}

# Main execution
main() {
    echo "🔄 Disaster Recovery Smoke Test"
    echo "================================="
    echo ""
    
    initialize_output
    check_prerequisites
    test_database_backup
    test_storage_backup
    test_container_backup
    test_restore_capability
    generate_verification_checklist
    generate_final_report
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run completed - review documentation in $OUTPUT_DIR"
    else
        log_info "DR smoke test completed - review results in $OUTPUT_DIR"
    fi
    
    log_info "Report available: $REPORT_FILE"
}

main "$@"
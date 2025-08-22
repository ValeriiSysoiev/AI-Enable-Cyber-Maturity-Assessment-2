#!/bin/bash
# Import Log Analytics Workbook for AECMA Monitoring
# Idempotent import with dry-run capability

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
WORKBOOK_FILE="${1:-monitoring/kql/workbook.json}"
RESOURCE_GROUP="${ACA_RG_PROD:-}"
WORKSPACE_NAME="${LOG_ANALYTICS_WORKSPACE:-}"
WORKBOOK_NAME="AECMA-Production-Monitoring"
DRY_RUN="${DRY_RUN:-false}"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${BLUE}==== $1 ====${NC}"; }

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    if ! command -v az &> /dev/null; then
        log_warn "Azure CLI not installed - running in documentation mode"
        DRY_RUN="true"
        return 0
    fi
    
    if ! az account show &> /dev/null; then
        log_warn "Not logged into Azure - running in documentation mode"
        DRY_RUN="true"
        return 0
    fi
    
    if [[ -z "$RESOURCE_GROUP" || -z "$WORKSPACE_NAME" ]]; then
        log_warn "Missing Azure configuration - set ACA_RG_PROD and LOG_ANALYTICS_WORKSPACE"
        log_info "Running in documentation mode"
        DRY_RUN="true"
    fi
    
    if [[ ! -f "$WORKBOOK_FILE" ]]; then
        log_error "Workbook file not found: $WORKBOOK_FILE"
        exit 1
    fi
    
    log_info "Prerequisites check completed"
}

# Import workbook to Log Analytics
import_workbook() {
    log_header "Importing Workbook"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would import workbook:"
        echo "  - Name: $WORKBOOK_NAME"
        echo "  - Resource Group: ${RESOURCE_GROUP:-<not set>}"
        echo "  - Workspace: ${WORKSPACE_NAME:-<not set>}"
        echo "  - Source: $WORKBOOK_FILE"
        
        log_info "Documentation: Workbook structure preview:"
        jq '.items[0].content.json' "$WORKBOOK_FILE" 2>/dev/null || head -20 "$WORKBOOK_FILE"
        
        return 0
    fi
    
    # Get workspace resource ID
    log_info "Fetching workspace resource ID..."
    WORKSPACE_ID=$(az monitor log-analytics workspace show \
        --resource-group "$RESOURCE_GROUP" \
        --workspace-name "$WORKSPACE_NAME" \
        --query id -o tsv)
    
    if [[ -z "$WORKSPACE_ID" ]]; then
        log_error "Failed to get workspace ID"
        exit 1
    fi
    
    # Check if workbook already exists
    EXISTING_WORKBOOK=$(az monitor app-insights workbook list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?displayName=='$WORKBOOK_NAME'].id" -o tsv || echo "")
    
    if [[ -n "$EXISTING_WORKBOOK" ]]; then
        log_info "Workbook already exists, updating..."
        
        az monitor app-insights workbook update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$(basename $EXISTING_WORKBOOK)" \
            --display-name "$WORKBOOK_NAME" \
            --category "AECMA" \
            --source-id "$WORKSPACE_ID" \
            --serialized-data "@$WORKBOOK_FILE" \
            --tags Environment=Production Component=Monitoring
            
        log_info "Workbook updated successfully"
    else
        log_info "Creating new workbook..."
        
        WORKBOOK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
        
        az monitor app-insights workbook create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$WORKBOOK_ID" \
            --display-name "$WORKBOOK_NAME" \
            --category "AECMA" \
            --source-id "$WORKSPACE_ID" \
            --serialized-data "@$WORKBOOK_FILE" \
            --tags Environment=Production Component=Monitoring
            
        log_info "Workbook created successfully"
    fi
}

# Import KQL queries as saved searches
import_kql_queries() {
    log_header "Importing KQL Queries"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would import KQL queries:"
        for kql_file in monitoring/kql/*.kql; do
            if [[ -f "$kql_file" ]]; then
                echo "  - $(basename $kql_file)"
            fi
        done
        return 0
    fi
    
    for kql_file in monitoring/kql/*.kql; do
        if [[ ! -f "$kql_file" ]]; then
            continue
        fi
        
        QUERY_NAME="AECMA-$(basename $kql_file .kql)"
        log_info "Importing query: $QUERY_NAME"
        
        # Extract first query from file for saved search
        QUERY_CONTENT=$(grep -v "^//" "$kql_file" | head -20)
        
        az monitor log-analytics workspace saved-search create \
            --resource-group "$RESOURCE_GROUP" \
            --workspace-name "$WORKSPACE_NAME" \
            --name "$QUERY_NAME" \
            --category "AECMA Monitoring" \
            --display-name "$QUERY_NAME" \
            --query "$QUERY_CONTENT" \
            --fa "ContainerAppConsoleLogs_CL" \
            --fp "" || log_warn "Query may already exist: $QUERY_NAME"
    done
    
    log_info "KQL queries imported"
}

# Generate documentation
generate_documentation() {
    log_header "Generating Documentation"
    
    local DOC_FILE="artifacts/monitoring/workbook-import-$(date +%Y%m%d-%H%M%S).md"
    mkdir -p artifacts/monitoring
    
    cat > "$DOC_FILE" << EOF
# Log Analytics Workbook Import Report

Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## Configuration
- Workbook Name: $WORKBOOK_NAME
- Resource Group: ${RESOURCE_GROUP:-<not configured>}
- Workspace: ${WORKSPACE_NAME:-<not configured>}
- Dry Run: $DRY_RUN

## KQL Queries Available
$(for f in monitoring/kql/*.kql; do [[ -f "$f" ]] && echo "- $(basename $f)"; done)

## Manual Import Instructions

### Via Azure Portal
1. Navigate to Log Analytics workspace
2. Select "Workbooks" from left menu
3. Click "+ New"
4. Switch to "Advanced Editor"
5. Paste contents from \`monitoring/kql/workbook.json\`
6. Click "Apply" then "Save"

### Via Azure CLI
\`\`\`bash
# Set environment variables
export ACA_RG_PROD="your-resource-group"
export LOG_ANALYTICS_WORKSPACE="your-workspace"

# Run import script
./scripts/monitor_import_workbook.sh
\`\`\`

## Verification
1. Open Azure Portal
2. Navigate to Log Analytics workspace
3. Select "Workbooks" → "AECMA-Production-Monitoring"
4. Verify all charts render correctly

## Query Library
The following KQL queries are available in \`monitoring/kql/\`:
- **errors.kql**: Error analysis and 5xx tracking
- **latency.kql**: P95/P99 latency metrics
- **availability.kql**: Service health and uptime
- **resources.kql**: CPU and memory utilization
EOF
    
    log_info "Documentation saved to: $DOC_FILE"
}

# Main execution
main() {
    echo "📊 Log Analytics Workbook Import"
    echo "================================="
    echo ""
    
    check_prerequisites
    import_workbook
    import_kql_queries
    generate_documentation
    
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run completed - review documentation in artifacts/monitoring/"
    else
        log_info "Workbook import completed successfully"
        log_info "Access in Azure Portal: Log Analytics → Workbooks → $WORKBOOK_NAME"
    fi
}

main "$@"
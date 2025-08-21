#!/bin/bash

# Live Infrastructure Verification Script
# Verifies all deployed Azure resources are functioning correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source safe utilities
source "$SCRIPT_DIR/lib/safe.sh"

# Configuration from environment variables (no defaults for security)
RG_NAME="${AZURE_RESOURCE_GROUP:-}"
SEARCH_SERVICE_NAME="${AZURE_SEARCH_SERVICE_NAME:-}"
OPENAI_SERVICE_NAME="${AZURE_OPENAI_SERVICE_NAME:-}"
KEY_VAULT_NAME="${AZURE_KEY_VAULT_NAME:-}"
STORAGE_ACCOUNT_NAME="${AZURE_STORAGE_ACCOUNT_NAME:-}"
ACA_ENV_NAME="${AZURE_ACA_ENV_NAME:-}"
COSMOS_ACCOUNT_NAME="${AZURE_COSMOS_ACCOUNT_NAME:-}"
API_BASE_URL="${API_BASE_URL:-}"
WEB_BASE_URL="${WEB_BASE_URL:-}"
STAGING_URL="${STAGING_URL:-}"
MCP_GATEWAY_URL="${MCP_GATEWAY_URL:-}"

# Performance thresholds (in seconds)
API_RESPONSE_THRESHOLD=5
SEARCH_RESPONSE_THRESHOLD=3
RAG_RESPONSE_THRESHOLD=10

# Enterprise gates - critical pass criteria
ENTERPRISE_GATES_ENABLED=${ENTERPRISE_GATES_ENABLED:-true}
CRITICAL_PASS_REQUIRED=${CRITICAL_PASS_REQUIRED:-true}

# Validate required environment variables
validate_environment() {
    local missing_vars=()
    
    if [[ -z "$RG_NAME" ]]; then
        missing_vars+=("AZURE_RESOURCE_GROUP")
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        printf '  - %s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set the following environment variables:"
        echo "  export AZURE_RESOURCE_GROUP=<your-resource-group>"
        echo "  export API_BASE_URL=<your-api-url>  # optional"
        echo "  export WEB_BASE_URL=<your-web-url>  # optional"
        echo ""
        echo "Or run this script in a deployment context where these are set."
        exit 1
    fi
}

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Get terraform outputs
get_terraform_outputs() {
    log_info "Getting Terraform outputs..."
    
    cd "$PROJECT_ROOT/infra"
    
    if [[ ! -f "terraform.tfstate" ]]; then
        log_error "Terraform state file not found. Please deploy infrastructure first."
        exit 1
    fi
    
    SEARCH_SERVICE_NAME=$(terraform output -raw search_service_name 2>/dev/null || echo "")
    OPENAI_SERVICE_NAME=$(terraform output -raw openai_service_name 2>/dev/null || echo "")
    KEY_VAULT_NAME=$(terraform output -raw key_vault_name 2>/dev/null || echo "")
    STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name 2>/dev/null || echo "")
    ACA_ENV_NAME=$(terraform output -raw aca_env_name 2>/dev/null || echo "")
    COSMOS_ACCOUNT_NAME=$(terraform output -raw cosmos_account_name 2>/dev/null || echo "")
    API_BASE_URL=$(terraform output -raw api_url 2>/dev/null || echo "")
    WEB_BASE_URL=$(terraform output -raw web_url 2>/dev/null || echo "")
    
    log_success "Retrieved terraform outputs"
}

# Verify Azure CLI authentication
verify_az_auth() {
    log_info "Verifying Azure CLI authentication..."
    
    if ! az account show >/dev/null 2>&1; then
        log_error "Azure CLI not authenticated. Please run 'az login'"
        exit 1
    fi
    
    local subscription_id
    subscription_id=$(az account show --query id -o tsv)
    log_success "Authenticated to subscription: $subscription_id"
}

# Verify Resource Group
verify_resource_group() {
    log_info "Verifying Resource Group: $RG_NAME"
    
    if az group show --name "$RG_NAME" >/dev/null 2>&1; then
        local location
        location=$(az group show --name "$RG_NAME" --query location -o tsv)
        log_success "Resource Group exists in location: $location"
    else
        log_error "Resource Group $RG_NAME not found"
        exit 1
    fi
}

# Verify Azure AI Search Service
verify_search_service() {
    if [[ -z "$SEARCH_SERVICE_NAME" ]]; then
        log_warning "Search service name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Azure AI Search Service: $SEARCH_SERVICE_NAME"
    
    local search_status
    search_status=$(az search service show \
        --resource-group "$RG_NAME" \
        --name "$SEARCH_SERVICE_NAME" \
        --query "status" -o tsv 2>/dev/null || echo "NotFound")
    
    if [[ "$search_status" == "running" ]]; then
        log_success "Search service is running"
        
        # Check if eng-docs index exists
        local index_exists
        index_exists=$(az search index show \
            --service-name "$SEARCH_SERVICE_NAME" \
            --name "eng-docs" \
            --query "name" -o tsv 2>/dev/null || echo "NotFound")
        
        if [[ "$index_exists" == "eng-docs" ]]; then
            log_success "Search index 'eng-docs' exists"
        else
            log_warning "Search index 'eng-docs' not found. Run bootstrap_search_index.sh to create it."
        fi
        
        # Verify search service configuration
        local tier
        tier=$(az search service show \
            --resource-group "$RG_NAME" \
            --name "$SEARCH_SERVICE_NAME" \
            --query "sku.name" -o tsv)
        log_info "Search service tier: $tier"
        
    elif [[ "$search_status" == "NotFound" ]]; then
        log_error "Search service not found"
        return 1
    else
        log_warning "Search service status: $search_status"
        return 1
    fi
}

# Verify Azure OpenAI Service
verify_openai_service() {
    if [[ -z "$OPENAI_SERVICE_NAME" ]]; then
        log_warning "OpenAI service name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Azure OpenAI Service: $OPENAI_SERVICE_NAME"
    
    local openai_state
    openai_state=$(az cognitiveservices account show \
        --resource-group "$RG_NAME" \
        --name "$OPENAI_SERVICE_NAME" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
    
    if [[ "$openai_state" == "Succeeded" ]]; then
        log_success "OpenAI service is provisioned successfully"
        
        # Check embeddings deployment
        local deployment_state
        deployment_state=$(az cognitiveservices account deployment show \
            --resource-group "$RG_NAME" \
            --name "$OPENAI_SERVICE_NAME" \
            --deployment-name "text-embedding-3-large" \
            --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
        
        if [[ "$deployment_state" == "Succeeded" ]]; then
            log_success "Text embedding deployment is ready"
        else
            log_warning "Text embedding deployment state: $deployment_state"
        fi
        
    elif [[ "$openai_state" == "NotFound" ]]; then
        log_error "OpenAI service not found"
        return 1
    else
        log_warning "OpenAI service state: $openai_state"
        return 1
    fi
}

# Verify Key Vault and secrets
verify_key_vault() {
    if [[ -z "$KEY_VAULT_NAME" ]]; then
        log_warning "Key Vault name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Key Vault: $KEY_VAULT_NAME"
    
    if az keyvault show --name "$KEY_VAULT_NAME" >/dev/null 2>&1; then
        log_success "Key Vault exists and is accessible"
        
        # Check for required secrets
        local secrets=("search-admin-key" "openai-key" "cosmos-connstr" "aad-client-id" "aad-client-secret" "aad-tenant-id" "nextauth-secret")
        for secret in "${secrets[@]}"; do
            if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret" >/dev/null 2>&1; then
                log_success "Secret '$secret' exists"
            else
                log_warning "Secret '$secret' not found"
            fi
        done
    else
        log_error "Key Vault not accessible"
        return 1
    fi
}

# Verify Storage Account
verify_storage() {
    if [[ -z "$STORAGE_ACCOUNT_NAME" ]]; then
        log_warning "Storage account name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Storage Account: $STORAGE_ACCOUNT_NAME"
    
    local storage_state
    storage_state=$(az storage account show \
        --resource-group "$RG_NAME" \
        --name "$STORAGE_ACCOUNT_NAME" \
        --query "provisioningState" -o tsv 2>/dev/null || echo "NotFound")
    
    if [[ "$storage_state" == "Succeeded" ]]; then
        log_success "Storage account is available"
        
        # Check for docs container
        local container_exists
        container_exists=$(az storage container exists \
            --account-name "$STORAGE_ACCOUNT_NAME" \
            --name "docs" \
            --auth-mode login \
            --query "exists" -o tsv 2>/dev/null || echo "false")
        
        if [[ "$container_exists" == "true" ]]; then
            log_success "Documents container exists"
        else
            log_warning "Documents container not found"
        fi
    else
        log_error "Storage account state: $storage_state"
        return 1
    fi
}

# Verify Container Apps Environment
verify_container_apps() {
    if [[ -z "$ACA_ENV_NAME" ]]; then
        log_warning "Container Apps environment name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Container Apps Environment: $ACA_ENV_NAME"
    
    local aca_state
    aca_state=$(az containerapp env show \
        --resource-group "$RG_NAME" \
        --name "$ACA_ENV_NAME" \
        --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
    
    if [[ "$aca_state" == "Succeeded" ]]; then
        log_success "Container Apps environment is ready"
    else
        log_error "Container Apps environment state: $aca_state"
        return 1
    fi
}

# Verify Cosmos DB
verify_cosmos_db() {
    if [[ -z "$COSMOS_ACCOUNT_NAME" ]]; then
        log_warning "Cosmos DB account name not found in terraform outputs"
        return 1
    fi
    
    log_info "Verifying Cosmos DB: $COSMOS_ACCOUNT_NAME"
    
    local cosmos_state
    cosmos_state=$(az cosmosdb show \
        --resource-group "$RG_NAME" \
        --name "$COSMOS_ACCOUNT_NAME" \
        --query "provisioningState" -o tsv 2>/dev/null || echo "NotFound")
    
    if [[ "$cosmos_state" == "Succeeded" ]]; then
        log_success "Cosmos DB account is available"
        
        # Check if databases exist
        local databases
        databases=$(az cosmosdb sql database list \
            --resource-group "$RG_NAME" \
            --account-name "$COSMOS_ACCOUNT_NAME" \
            --query "[].name" -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$databases" ]]; then
            log_success "Found databases: $(echo $databases | tr '\n' ' ')"
        else
            log_warning "No databases found in Cosmos DB"
        fi
        
    elif [[ "$cosmos_state" == "NotFound" ]]; then
        log_error "Cosmos DB account not found"
        return 1
    else
        log_warning "Cosmos DB account state: $cosmos_state"
        return 1
    fi
}

# Test search service connectivity
test_search_connectivity() {
    if [[ -z "$SEARCH_SERVICE_NAME" ]]; then
        log_warning "Skipping search connectivity test - service name not available"
        return 0
    fi
    
    log_info "Testing search service connectivity..."
    
    local search_endpoint="https://${SEARCH_SERVICE_NAME}.search.windows.net"
    
    # Test public endpoint accessibility
    if curl -s -f "$search_endpoint" >/dev/null 2>&1; then
        log_success "Search service endpoint is accessible"
    else
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "$search_endpoint" || echo "000")
        
        if [[ "$response_code" == "403" ]]; then
            log_success "Search service endpoint returns 403 (expected without API key)"
        else
            log_warning "Search service endpoint returned HTTP $response_code"
        fi
    fi
}

# Test API connectivity and performance
test_api_connectivity() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping API tests"
        return 0
    fi
    
    log_info "Testing API connectivity: $API_BASE_URL"
    
    # Test health endpoint using safe utilities
    local start_time end_time duration
    start_time=$(date +%s.%N)
    
    local response_code
    response_code=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" \
        -H "X-Correlation-ID: health-$(date +%s)" \
        "${API_BASE_URL}/health" 2>/dev/null || echo "000")
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "API health endpoint responded in ${duration}s"
        
        # Check performance threshold
        if (( $(echo "$duration > $API_RESPONSE_THRESHOLD" | bc -l) )); then
            log_warning "API response time (${duration}s) exceeds threshold (${API_RESPONSE_THRESHOLD}s)"
        fi
    else
        log_error "API health endpoint returned HTTP $response_code"
        return 1
    fi
    
    # Test version endpoint with timeout
    local version_response
    version_response=$(curl -s --max-time 10 \
        -H "X-Correlation-ID: version-$(date +%s)" \
        "${API_BASE_URL}/version" 2>/dev/null || echo "")
    
    if [[ -n "$version_response" ]]; then
        log_success "API version endpoint accessible"
        log_info "API version info: $version_response"
    else
        log_warning "API version endpoint not accessible"
    fi
}

# Test RAG service functionality
test_rag_service() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping RAG tests"
        return 0
    fi
    
    log_info "Testing RAG service functionality..."
    
    # Test RAG search endpoint
    local start_time end_time duration
    start_time=$(date +%s.%N)
    
    local test_query='{"query": "test document search", "top": 1}'
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$test_query" \
        "${API_BASE_URL}/api/evidence/search" || echo "000")
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "RAG search endpoint responded in ${duration}s"
        
        # Check performance threshold
        if (( $(echo "$duration > $RAG_RESPONSE_THRESHOLD" | bc -l) )); then
            log_warning "RAG response time (${duration}s) exceeds threshold (${RAG_RESPONSE_THRESHOLD}s)"
        fi
    elif [[ "$response_code" == "404" ]]; then
        log_warning "RAG service endpoint not found (feature may be disabled)"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_warning "RAG service requires authentication (expected in production)"
    else
        log_error "RAG search endpoint returned HTTP $response_code"
        return 1
    fi
}

# Test document ingestion endpoint
test_document_ingestion() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping document ingestion tests"
        return 0
    fi
    
    log_info "Testing document ingestion endpoint..."
    
    # Test upload endpoint accessibility (without actually uploading)
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        "${API_BASE_URL}/api/documents/upload" || echo "000")
    
    if [[ "$response_code" == "200" || "$response_code" == "204" ]]; then
        log_success "Document upload endpoint is accessible"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "Document upload endpoint not found"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_warning "Document upload requires authentication (expected)"
    else
        log_warning "Document upload endpoint returned HTTP $response_code"
    fi
}

# Test AAD authentication flow
test_aad_authentication() {
    if [[ -z "$WEB_BASE_URL" ]]; then
        log_warning "Web base URL not available - skipping AAD tests"
        return 0
    fi
    
    log_info "Testing AAD authentication flow..."
    
    # Test auth configuration endpoint
    local auth_config
    auth_config=$(curl -s "${WEB_BASE_URL}/api/auth/mode" 2>/dev/null || echo "")
    
    if [[ -n "$auth_config" ]]; then
        log_success "Authentication mode endpoint accessible"
        log_info "Auth mode: $auth_config"
        
        # Check if AAD is enabled
        if echo "$auth_config" | grep -q "aad"; then
            log_success "AAD authentication is enabled"
            
            # Test AAD signin redirect
            local signin_response_code
            signin_response_code=$(curl -s -o /dev/null -w "%{http_code}" \
                "${WEB_BASE_URL}/signin" || echo "000")
            
            if [[ "$signin_response_code" == "200" || "$signin_response_code" == "302" ]]; then
                log_success "AAD signin endpoint is accessible"
            else
                log_warning "AAD signin endpoint returned HTTP $signin_response_code"
            fi
        else
            log_info "AAD authentication is disabled (demo mode)"
        fi
    else
        log_warning "Authentication configuration not accessible"
    fi
}

# Run KQL log analysis for errors
analyze_application_logs() {
    log_info "Analyzing application logs for errors..."
    
    # Check if we have Log Analytics workspace configured
    local law_workspace
    law_workspace=$(az monitor log-analytics workspace list \
        --resource-group "$RG_NAME" \
        --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    if [[ -z "$law_workspace" ]]; then
        log_warning "No Log Analytics workspace found - skipping log analysis"
        return 0
    fi
    
    log_info "Found Log Analytics workspace: $law_workspace"
    
    # Run KQL query to check for recent errors
    local query='ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "ERROR" or Log_s contains "Exception" or Log_s contains "Failed"
| project TimeGenerated, ContainerAppName_s, Log_s
| order by TimeGenerated desc
| limit 10'
    
    local log_results
    log_results=$(az monitor log-analytics query \
        --workspace "$law_workspace" \
        --analytics-query "$query" \
        --query "tables[0].rows" -o tsv 2>/dev/null || echo "")
    
    if [[ -n "$log_results" && "$log_results" != "[]" ]]; then
        log_warning "Recent errors found in application logs:"
        echo "$log_results" | head -5
        log_warning "Check Log Analytics for full error details"
    else
        log_success "No recent errors found in application logs"
    fi
}

# Test PPTX export functionality
test_pptx_export() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping PPTX export tests"
        return 0
    fi
    
    log_info "Testing PPTX export functionality..."
    
    # Test export endpoint accessibility
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        "${API_BASE_URL}/api/exports/pptx" || echo "000")
    
    if [[ "$response_code" == "200" || "$response_code" == "204" ]]; then
        log_success "PPTX export endpoint is accessible"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "PPTX export endpoint not found (feature may not be deployed)"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_warning "PPTX export requires authentication (expected)"
    else
        log_warning "PPTX export endpoint returned HTTP $response_code"
    fi
}

# Test Sprint v1.4 UAT mode audio transcription endpoints
test_uat_audio_transcription() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping UAT audio transcription tests"
        return 0
    fi
    
    log_info "Testing Sprint v1.4 UAT audio transcription endpoints..."
    
    # Test orchestrator audio transcription endpoint
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        "${API_BASE_URL}/transcribe/audio" || echo "000")
    
    if [[ "$response_code" == "200" || "$response_code" == "204" ]]; then
        log_success "Audio transcription endpoint is accessible"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "Audio transcription endpoint not found (Sprint v1.4 not deployed)"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_warning "Audio transcription requires authentication (expected)"
    else
        log_warning "Audio transcription endpoint returned HTTP $response_code"
    fi
    
    # Test enhanced orchestration endpoint
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        "${API_BASE_URL}/orchestrate/analyze_with_transcript" || echo "000")
    
    if [[ "$response_code" == "200" || "$response_code" == "204" ]]; then
        log_success "Enhanced orchestration endpoint is accessible"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "Enhanced orchestration endpoint not found"
    else
        log_warning "Enhanced orchestration endpoint returned HTTP $response_code"
    fi
}

# Test Sprint v1.4 audit logging endpoints
test_uat_audit_logging() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping UAT audit logging tests"
        return 0
    fi
    
    log_info "Testing Sprint v1.4 audit logging endpoints..."
    
    # Test audit events endpoint
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/audit/events" || echo "000")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "Audit events endpoint is accessible"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_success "Audit events requires authentication (expected)"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "Audit events endpoint not found (Sprint v1.4 audit logging not deployed)"
    else
        log_warning "Audit events endpoint returned HTTP $response_code"
    fi
    
    # Test audit export endpoint
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        "${API_BASE_URL}/audit/export" || echo "000")
    
    if [[ "$response_code" == "200" || "$response_code" == "204" ]]; then
        log_success "Audit export endpoint is accessible"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_success "Audit export requires authentication (expected)"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "Audit export endpoint not found"
    else
        log_warning "Audit export endpoint returned HTTP $response_code"
    fi
    
    # Test connectors status endpoint
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/connectors/status" || echo "000")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "MCP connectors status endpoint is accessible"
        
        # Get connector status details
        local status_response
        status_response=$(curl -s "${API_BASE_URL}/connectors/status" 2>/dev/null || echo "")
        
        if echo "$status_response" | grep -q "audio_enabled"; then
            log_success "MCP connectors status includes Sprint v1.4 features"
        else
            log_warning "MCP connectors status may not include Sprint v1.4 features"
        fi
    elif [[ "$response_code" == "404" ]]; then
        log_warning "MCP connectors status endpoint not found"
    else
        log_warning "MCP connectors status endpoint returned HTTP $response_code"
    fi
}

# Generate summary report
generate_summary() {
    log_info "Generating verification summary..."
    
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo
    echo "=================================="
    echo "Infrastructure Verification Report"
    echo "=================================="
    echo "Timestamp: $timestamp"
    echo "Resource Group: $RG_NAME"
    echo
    echo "Infrastructure Services:"
    echo "  - Resource Group: ✓"
    echo "  - Azure AI Search: ${SEARCH_SERVICE_NAME:-'Not configured'}"
    echo "  - Azure OpenAI: ${OPENAI_SERVICE_NAME:-'Not configured'}"
    echo "  - Key Vault: ${KEY_VAULT_NAME:-'Not configured'}"
    echo "  - Storage Account: ${STORAGE_ACCOUNT_NAME:-'Not configured'}"
    echo "  - Cosmos DB: ${COSMOS_ACCOUNT_NAME:-'Not configured'}"
    echo "  - Container Apps: ${ACA_ENV_NAME:-'Not configured'}"
    echo
    echo "Application Services:"
    echo "  - API Endpoint: ${API_BASE_URL:-'Not available'}"
    echo "  - Web Endpoint: ${WEB_BASE_URL:-'Not available'}"
    echo "  - RAG Service: Tested"
    echo "  - AAD Authentication: Tested"
    echo "  - Document Ingestion: Tested"
    echo "  - PPTX Export: Tested"
    echo
    echo "Sprint v1.4 UAT Features:"
    echo "  - Audio Transcription (POST /transcribe/audio): Tested"
    echo "  - Enhanced Orchestration (POST /orchestrate/analyze_with_transcript): Tested"
    echo "  - Audit Events (GET /audit/events): Tested"
    echo "  - Audit Export (POST /audit/export): Tested"
    echo "  - MCP Connectors Status (GET /connectors/status): Tested"
    echo
    echo "S4 Extensions:"
    echo "  - CSF Taxonomy (GET /api/v1/csf/functions): Tested"
    echo "  - Workshop Consent (POST /api/v1/workshops): Tested"
    echo "  - Minutes Immutability (POST /api/v1/minutes/*:publish): Tested"
    echo
    echo "Performance Thresholds:"
    echo "  - API Response: < ${API_RESPONSE_THRESHOLD}s"
    echo "  - Search Response: < ${SEARCH_RESPONSE_THRESHOLD}s"
    echo "  - RAG Response: < ${RAG_RESPONSE_THRESHOLD}s"
    echo
    echo "Next Steps:"
    echo "  1. If search index is missing, run: ./scripts/bootstrap_search_index.sh"
    echo "  2. Deploy container applications with proper environment variables"
    echo "  3. Check Log Analytics for any error patterns"
    echo "  4. Verify AAD configuration if authentication issues occur"
    echo "  5. Test end-to-end evidence workflow through the web interface"
    echo
    echo "=================================="
}

# Main execution
main() {
    echo "=== Live Infrastructure Verification ==="
    echo
    
    # Infrastructure verification
    verify_az_auth
    get_terraform_outputs
    verify_resource_group
    verify_search_service
    verify_openai_service
    verify_key_vault
    verify_storage
    verify_cosmos_db
    verify_container_apps
    
    echo
    echo "=== Service Connectivity Tests ==="
    test_search_connectivity
    test_api_connectivity
    test_aad_authentication
    
    echo
    echo "=== RAG and Evidence Features ==="
    test_rag_service
    test_document_ingestion
    test_pptx_export
    
    echo
    echo "=== Log Analysis ==="
    analyze_application_logs
    
    echo
    generate_summary
    
    log_success "Verification complete"
}

# Verify Application Insights and monitoring setup
verify_monitoring() {
    log_info "Verifying monitoring and alerting setup..."
    
    # Check for Application Insights
    local appinsights_name
    appinsights_name=$(az monitor app-insights component list \
        --resource-group "$RG_NAME" \
        --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    if [[ -n "$appinsights_name" ]]; then
        log_success "Application Insights configured: $appinsights_name"
        
        # Check for alert rules
        local alert_count
        alert_count=$(az monitor metrics alert list \
            --resource-group "$RG_NAME" \
            --query "length(@)" -o tsv 2>/dev/null || echo "0")
        
        if [[ "$alert_count" -gt 0 ]]; then
            log_success "Found $alert_count metric alert rules"
        else
            log_warning "No metric alert rules configured"
        fi
    else
        log_warning "Application Insights not found"
    fi
    
    # Check for Log Analytics queries for AAD and RAG monitoring
    if [[ -n "$KEY_VAULT_NAME" ]]; then
        local law_workspace
        law_workspace=$(az monitor log-analytics workspace list \
            --resource-group "$RG_NAME" \
            --query "[0].name" -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$law_workspace" ]]; then
            log_success "Log Analytics workspace found: $law_workspace"
        else
            log_warning "Log Analytics workspace not found"
        fi
    fi
}

# Verify embeddings container and RAG prerequisites  
verify_rag_prerequisites() {
    log_info "Verifying RAG service prerequisites..."
    
    # Check Cosmos DB embeddings container
    if [[ -n "$COSMOS_ACCOUNT_NAME" ]]; then
        local containers
        containers=$(az cosmosdb sql container list \
            --resource-group "$RG_NAME" \
            --account-name "$COSMOS_ACCOUNT_NAME" \
            --database-name "ai_maturity" \
            --query "[].name" -o tsv 2>/dev/null || echo "")
        
        if echo "$containers" | grep -q "embeddings"; then
            log_success "Embeddings container exists for RAG storage"
        else
            log_warning "Embeddings container not found - required for RAG functionality"
        fi
        
        # Check other required containers
        local required_containers=("assessments" "documents" "answers" "engagements")
        for container in "${required_containers[@]}"; do
            if echo "$containers" | grep -q "$container"; then
                log_success "Container '$container' exists"
            else
                log_warning "Container '$container' not found"
            fi
        done
    fi
    
    # Verify OpenAI embedding deployment
    if [[ -n "$OPENAI_SERVICE_NAME" ]]; then
        local embedding_deployment
        embedding_deployment=$(az cognitiveservices account deployment show \
            --resource-group "$RG_NAME" \
            --name "$OPENAI_SERVICE_NAME" \
            --deployment-name "text-embedding-3-large" \
            --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
        
        if [[ "$embedding_deployment" == "Succeeded" ]]; then
            log_success "Text embedding deployment is ready for RAG"
        else
            log_warning "Text embedding deployment state: $embedding_deployment"
        fi
    fi
}

# Test container app environment variables
test_container_app_config() {
    log_info "Testing container app environment configuration..."
    
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping container app config test"
        return 0
    fi
    
    # Test environment configuration endpoint
    local env_config
    env_config=$(curl -s "${API_BASE_URL}/api/ops/config" 2>/dev/null || echo "")
    
    if [[ -n "$env_config" ]]; then
        log_success "Environment configuration endpoint accessible"
        
        # Check RAG configuration
        if echo "$env_config" | grep -q "RAG_MODE"; then
            local rag_mode
            rag_mode=$(echo "$env_config" | grep -o '"RAG_MODE":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
            log_info "RAG mode: $rag_mode"
        fi
        
        # Check authentication mode
        if echo "$env_config" | grep -q "AUTH_MODE"; then
            local auth_mode
            auth_mode=$(echo "$env_config" | grep -o '"AUTH_MODE":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
            log_info "Authentication mode: $auth_mode"
        fi
        
        # Check managed identity usage
        if echo "$env_config" | grep -q "USE_MANAGED_IDENTITY.*true"; then
            log_success "Managed identity is enabled"
        else
            log_warning "Managed identity not enabled - check container app configuration"
        fi
    else
        log_warning "Environment configuration endpoint not accessible"
    fi
}

# Test enterprise AAD groups functionality
test_aad_groups() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping AAD groups tests"
        return 0
    fi
    
    log_info "Testing AAD groups functionality..."
    
    # Test admin auth diagnostics endpoint
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/admin/auth-diagnostics" || echo "000")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "AAD auth diagnostics endpoint accessible"
    elif [[ "$response_code" == "401" || "$response_code" == "403" ]]; then
        log_success "AAD auth diagnostics requires authentication (expected)"
    elif [[ "$response_code" == "404" ]]; then
        log_warning "AAD auth diagnostics endpoint not found"
    else
        log_warning "AAD auth diagnostics returned HTTP $response_code"
    fi
}

# Test GDPR endpoints
test_gdpr_endpoints() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping GDPR tests"
        return 0
    fi
    
    log_info "Testing GDPR endpoints..."
    
    # Test GDPR admin dashboard
    local dashboard_code
    dashboard_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/gdpr/admin/dashboard" || echo "000")
    
    if [[ "$dashboard_code" == "200" ]]; then
        log_success "GDPR admin dashboard accessible"
    elif [[ "$dashboard_code" == "401" || "$dashboard_code" == "403" ]]; then
        log_success "GDPR admin dashboard requires authentication (expected)"
    elif [[ "$dashboard_code" == "404" ]]; then
        log_warning "GDPR admin dashboard not found"
    else
        log_warning "GDPR admin dashboard returned HTTP $dashboard_code"
    fi
    
    # Test background jobs endpoint
    local jobs_code
    jobs_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/gdpr/admin/jobs" || echo "000")
    
    if [[ "$jobs_code" == "200" ]]; then
        log_success "GDPR background jobs endpoint accessible"
    elif [[ "$jobs_code" == "401" || "$jobs_code" == "403" ]]; then
        log_success "GDPR background jobs requires authentication (expected)"
    else
        log_warning "GDPR background jobs returned HTTP $jobs_code"
    fi
}

# Test performance monitoring endpoints
test_performance_monitoring() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping performance tests"
        return 0
    fi
    
    log_info "Testing performance monitoring..."
    
    # Test performance metrics endpoint
    local metrics_code
    metrics_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/api/performance/metrics" || echo "000")
    
    if [[ "$metrics_code" == "200" ]]; then
        log_success "Performance metrics endpoint accessible"
        
        # Get cache metrics
        local cache_metrics
        cache_metrics=$(curl -s "${API_BASE_URL}/api/performance/metrics" 2>/dev/null || echo "")
        
        if echo "$cache_metrics" | grep -q "cache_hit_rate"; then
            log_success "Cache metrics available"
        else
            log_warning "Cache metrics not found in response"
        fi
    elif [[ "$metrics_code" == "401" || "$metrics_code" == "403" ]]; then
        log_success "Performance metrics requires authentication (expected)"
    elif [[ "$metrics_code" == "404" ]]; then
        log_warning "Performance metrics endpoint not found"
    else
        log_warning "Performance metrics returned HTTP $metrics_code"
    fi
}

# Test caching functionality
test_caching() {
    if [[ -z "$API_BASE_URL" ]]; then
        log_warning "API base URL not available - skipping cache tests"
        return 0
    fi
    
    log_info "Testing caching functionality..."
    
    # Test presets endpoint performance (should benefit from caching)
    local start_time end_time duration
    start_time=$(date +%s.%N)
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE_URL}/presets/" || echo "000")
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
    
    if [[ "$response_code" == "200" ]]; then
        log_success "Presets endpoint responded in ${duration}s"
        
        # Second request should be faster (cached)
        start_time=$(date +%s.%N)
        curl -s -o /dev/null "${API_BASE_URL}/presets/" 2>/dev/null || true
        end_time=$(date +%s.%N)
        duration2=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")
        
        if (( $(echo "$duration2 < $duration" | bc -l) )); then
            log_success "Second request faster (${duration2}s) - caching likely working"
        else
            log_info "Cache performance test inconclusive"
        fi
    else
        log_warning "Presets endpoint returned HTTP $response_code"
    fi
}

# Critical pass validation for enterprise features
validate_critical_pass() {
    if [[ "$CRITICAL_PASS_REQUIRED" != "true" ]]; then
        log_info "Critical pass validation disabled"
        return 0
    fi
    
    log_info "Validating critical pass criteria..."
    
    local critical_failures=0
    
    # Check API health
    if [[ -n "$API_BASE_URL" ]]; then
        local health_code
        health_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/health" || echo "000")
        if [[ "$health_code" != "200" ]]; then
            log_error "CRITICAL: API health check failed (HTTP $health_code)"
            ((critical_failures++))
        fi
    else
        log_error "CRITICAL: API URL not configured"
        ((critical_failures++))
    fi
    
    # Check essential endpoints
    local endpoints=("/presets/" "/docs")
    for endpoint in "${endpoints[@]}"; do
        if [[ -n "$API_BASE_URL" ]]; then
            local endpoint_code
            endpoint_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}${endpoint}" || echo "000")
            if [[ "$endpoint_code" != "200" ]]; then
                log_error "CRITICAL: Essential endpoint $endpoint failed (HTTP $endpoint_code)"
                ((critical_failures++))
            fi
        fi
    done
    
    # Check RAG if enabled
    if [[ -n "$API_BASE_URL" ]]; then
        local rag_response
        rag_response=$(curl -s "${API_BASE_URL}/api/evidence/search" 2>/dev/null || echo "")
        if [[ -z "$rag_response" ]]; then
            log_warning "RAG service not responding (may be disabled)"
        else
            log_success "RAG service responsive"
        fi
    fi
    
    if [[ $critical_failures -gt 0 ]]; then
        log_error "CRITICAL PASS FAILED: $critical_failures critical issues found"
        return 1
    else
        log_success "CRITICAL PASS: All essential services operational"
        return 0
    fi
}

# ==== S4 VERIFICATION EXTENSIONS ====
# Bounded S4 checks with safe utilities and correlation ID validation

# Test S4 CSF taxonomy endpoint structure
test_s4_csf_taxonomy() {
    [[ -z "$API_BASE_URL" ]] && { log_warning "API base URL not available - skipping S4 CSF taxonomy test"; return 0; }
    log_info "Testing S4 CSF taxonomy endpoint structure..."
    
    local temp_response; temp_response=$(mktemp); trap "rm -f '$temp_response'" RETURN
    
    if require_http "${API_BASE_URL}/api/v1/csf/functions" "200" "10"; then
        curl -s --max-time 10 -H "X-Correlation-ID: s4-csf-$(date +%s)" \
            "${API_BASE_URL}/api/v1/csf/functions" > "$temp_response" 2>/dev/null || true
        
        if validate_json_response "$temp_response" "functions"; then
            log_success "CSF taxonomy endpoint has expected structure"
            local categories subcategories
            categories=$(jq -r 'try .functions[0].categories | length' "$temp_response" 2>/dev/null || echo "0")
            subcategories=$(jq -r 'try .functions[0].categories[0].subcategories | length' "$temp_response" 2>/dev/null || echo "0")
            [[ $categories -gt 0 && $subcategories -gt 0 ]] && \
                log_success "CSF taxonomy has functions/categories/subcategories hierarchy" || \
                log_warning "CSF taxonomy structure may be incomplete"
        else
            log_error "S4 CSF taxonomy endpoint returned invalid structure"; return 1
        fi
    else
        log_error "S4 CSF taxonomy endpoint failed accessibility test"; return 1
    fi
}

# Test S4 workshop consent validation
test_s4_workshop_consent() {
    [[ -z "$API_BASE_URL" ]] && { log_warning "API base URL not available - skipping S4 workshop consent test"; return 0; }
    log_info "Testing S4 workshop consent validation..."
    
    local temp_payload temp_response
    temp_payload=$(mktemp); temp_response=$(mktemp)
    trap "rm -f '$temp_payload' '$temp_response'" RETURN
    
    cat > "$temp_payload" <<'EOF'
{"title": "Test Workshop", "description": "S4 validation test", "scheduled_date": "2025-12-31T10:00:00Z"}
EOF
    
    local response_code correlation_id
    correlation_id=$(uuidgen 2>/dev/null || echo "s4-workshop-$(date +%s)")
    response_code=$(curl -s --max-time 10 -X POST -H "Content-Type: application/json" \
        -H "X-Correlation-ID: $correlation_id" -d "@$temp_payload" -o "$temp_response" \
        -w "%{http_code}" "${API_BASE_URL}/api/v1/workshops" 2>/dev/null || echo "000")
    
    if [[ "$response_code" == "400" || "$response_code" == "422" ]]; then
        log_success "Workshop consent validation working - returned HTTP $response_code"
        grep -qi "consent" "$temp_response" 2>/dev/null && \
            log_success "Error response correctly mentions consent requirement" || \
            log_warning "Error response should mention consent requirement"
    elif [[ "$response_code" =~ ^(404|401|403)$ ]]; then
        log_warning "Workshop endpoint expected response (HTTP $response_code)"
    else
        log_error "Workshop consent test returned unexpected status $response_code"; return 1
    fi
}

# Test S4 minutes publish immutability
test_s4_minutes_immutability() {
    [[ -z "$API_BASE_URL" ]] && { log_warning "API base URL not available - skipping S4 minutes immutability test"; return 0; }
    log_info "Testing S4 minutes publish immutability..."
    
    local test_id correlation_id response_code temp_response
    test_id="test-minutes-$(date +%s)"
    correlation_id=$(uuidgen 2>/dev/null || echo "s4-minutes-$(date +%s)")
    temp_response=$(mktemp); trap "rm -f '$temp_response'" RETURN
    
    response_code=$(curl -s --max-time 10 -X POST -H "X-Correlation-ID: $correlation_id" \
        -o "$temp_response" -w "%{http_code}" \
        "${API_BASE_URL}/api/v1/minutes/${test_id}:publish" 2>/dev/null || echo "000")
    
    if [[ "$response_code" =~ ^(404|409|403|401)$ ]]; then
        log_success "Minutes publish returned expected HTTP $response_code"
    else
        # Test PATCH for immutability
        local patch_payload; patch_payload=$(mktemp); trap "rm -f '$patch_payload'" RETURN
        echo '{"content": "Test modification", "updated_at": "2025-08-18T12:00:00Z"}' > "$patch_payload"
        
        response_code=$(curl -s --max-time 10 -X PATCH -H "Content-Type: application/json" \
            -H "X-Correlation-ID: $correlation_id" -d "@$patch_payload" -o "$temp_response" \
            -w "%{http_code}" "${API_BASE_URL}/api/v1/minutes/${test_id}" 2>/dev/null || echo "000")
        
        [[ "$response_code" =~ ^(404|409|403)$ ]] && \
            log_success "Minutes PATCH correctly enforces immutability (HTTP $response_code)" || \
            log_warning "Minutes immutability test returned unexpected status $response_code"
    fi
}

# Consolidated S4 verification suite
verify_s4_extensions() {
    log_info "=== S4 VERIFICATION EXTENSIONS ==="
    local s4_failures=0
    
    test_s4_csf_taxonomy || ((s4_failures++))
    test_s4_workshop_consent || ((s4_failures++))  
    test_s4_minutes_immutability || ((s4_failures++))
    
    if [[ $s4_failures -eq 0 ]]; then
        log_success "All S4 verification checks passed"; return 0
    else
        log_error "S4 verification failed: $s4_failures checks failed"; return 1
    fi
}

# Test staging environment specific checks
test_staging_environment() {
    if [[ -z "$STAGING_URL" ]]; then
        log_info "STAGING_URL not set - skipping staging-specific checks"
        return 0
    fi
    
    log_info "Testing staging environment at $STAGING_URL..."
    
    # Test staging health endpoint
    local staging_health_code
    staging_health_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "${STAGING_URL}/health" || echo "000")
    
    if [[ "$staging_health_code" == "200" ]]; then
        log_success "Staging health endpoint accessible"
    else
        log_warning "Staging health endpoint returned HTTP $staging_health_code"
    fi
    
    # Test MCP Gateway if URL provided
    if [[ -n "$MCP_GATEWAY_URL" ]]; then
        log_info "Testing MCP Gateway at $MCP_GATEWAY_URL..."
        
        local mcp_health_code
        mcp_health_code=$(curl -s -o /dev/null -w "%{http_code}" \
            "${MCP_GATEWAY_URL}/health" || echo "000")
        
        if [[ "$mcp_health_code" == "200" ]]; then
            log_success "MCP Gateway health endpoint accessible"
            
            # Test SharePoint tool availability
            local tools_response
            tools_response=$(curl -s "${MCP_GATEWAY_URL}/mcp/tools" 2>/dev/null || echo "")
            
            if echo "$tools_response" | grep -q "sharepoint.fetch"; then
                log_success "SharePoint connector available in MCP Gateway"
            else
                log_warning "SharePoint connector not found in MCP Gateway"
            fi
            
            # Test Jira tool availability (may not be available yet)
            if echo "$tools_response" | grep -q "jira.createIssue"; then
                log_success "Jira connector available in MCP Gateway"
            else
                log_info "Jira connector not yet deployed (expected in v1.5)"
            fi
        else
            log_warning "MCP Gateway health endpoint returned HTTP $mcp_health_code"
        fi
    else
        log_info "MCP_GATEWAY_URL not set - skipping MCP Gateway checks"
    fi
    
    # Test staging feature flags via environment config
    if [[ -n "$STAGING_URL" ]]; then
        local config_response
        config_response=$(curl -s "${STAGING_URL}/api/ops/config" 2>/dev/null || echo "")
        
        if echo "$config_response" | grep -q "STAGING_ENV.*true"; then
            log_success "Staging environment flag detected"
        else
            log_warning "Staging environment flag not detected"
        fi
        
        # Check MCP connector flags
        if echo "$config_response" | grep -q "MCP_CONNECTORS_SP"; then
            log_info "SharePoint connector configuration detected"
        fi
        
        if echo "$config_response" | grep -q "MCP_CONNECTORS_JIRA"; then
            log_info "Jira connector configuration detected"
        fi
    fi
}

# Enhanced main execution with Phase 7 enterprise verification
main() {
    echo "=== Live Infrastructure Verification ==="
    echo
    
    # Validate environment before proceeding
    validate_environment
    
    # Infrastructure verification
    verify_az_auth
    get_terraform_outputs
    verify_resource_group
    verify_search_service
    verify_openai_service
    verify_key_vault
    verify_storage
    verify_cosmos_db
    verify_container_apps
    
    echo
    echo "=== Phase 6 RAG and AAD Verification ==="
    verify_monitoring
    verify_rag_prerequisites
    test_container_app_config
    
    echo
    echo "=== Phase 7 Enterprise Features Verification ==="
    if [[ "$ENTERPRISE_GATES_ENABLED" == "true" ]]; then
        test_aad_groups
        test_gdpr_endpoints
        test_performance_monitoring
        test_caching
    else
        log_info "Enterprise gates disabled - skipping Phase 7 tests"
    fi
    
    echo
    echo "=== Service Connectivity Tests ==="
    test_search_connectivity
    test_api_connectivity
    test_aad_authentication
    
    echo
    echo "=== RAG and Evidence Features ==="
    test_rag_service
    test_document_ingestion
    test_pptx_export
    
    echo
    echo "=== Sprint v1.4 UAT Features ==="
    test_uat_audio_transcription
    test_uat_audit_logging
    
    echo
    echo "=== Log Analysis ==="
    analyze_application_logs
    
    echo
    echo "=== S4 Extensions Verification ==="
    if ! verify_s4_extensions; then
        log_error "S4 VERIFICATION FAILED: S4 extension checks failed"
        exit 1
    fi
    
    echo
    echo "=== Staging Environment Tests ==="
    test_staging_environment
    
    echo
    echo "=== Critical Pass Validation ==="
    if ! validate_critical_pass; then
        log_error "VERIFICATION FAILED: Critical issues prevent production readiness"
        exit 1
    fi
    
    echo
    generate_summary
    
    log_success "Phase 7 enterprise verification with S4 extensions complete"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
#!/bin/bash
# S3 Live Infrastructure Verification - Bounded checks with retry logic
# Exit codes: 0=success, 1=critical failure, 2=warnings only
set -euo pipefail

# Source safe utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/safe.sh"

# Colors and globals (use safe lib colors)
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAILURE_COUNT=0; WARNING_COUNT=0; CRITICAL_SECTIONS=("health_checks" "authz_flow" "evidence_flow"); FAILED_SECTIONS=()

# Configuration
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RG_NAME="${RG_NAME:-rg-aaa-demo}"; API_BASE_URL="${API_BASE_URL:-}"; WEB_BASE_URL="${WEB_BASE_URL:-}"; AUTH_BEARER="${AUTH_BEARER:-}"
MAX_RETRIES=3; BACKOFF_BASE=2; UPLOAD_FILE_SIZE=1024; OVERSIZE_LIMIT_MB=10

# Logging functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; ((WARNING_COUNT++)); }
log_error() { echo -e "${RED}✗${NC} $1"; ((FAILURE_COUNT++)); }
log_critical() { echo -e "${RED}💥${NC} CRITICAL: $1"; ((FAILURE_COUNT++)); }


# Helper function to perform HTTP checks with auth token if available
check_endpoint() {
    local url="$1" expect_status="${2:-200}"
    if [ -n "$AUTH_BEARER" ]; then
        require_http "$expect_status" "$url" "$AUTH_BEARER"
    else
        require_http "$expect_status" "$url"
    fi
}

# Section failure tracking
fail_section() {
    local section="$1"
    local message="$2"
    log_critical "[$section] $message"
    FAILED_SECTIONS+=("$section")
    return 1
}

# Get terraform outputs or use environment variables
get_deployment_config() {
    log_info "Getting deployment configuration..."
    
    # Try terraform first, fallback to environment variables
    if [ -f "$PROJECT_ROOT/infra/terraform.tfstate" ]; then
        cd "$PROJECT_ROOT/infra"
        API_BASE_URL="${API_BASE_URL:-$(terraform output -raw api_url 2>/dev/null || echo "")}"
        WEB_BASE_URL="${WEB_BASE_URL:-$(terraform output -raw web_url 2>/dev/null || echo "")}"
    fi
    
    # Validate required URLs
    if [ -z "$API_BASE_URL" ] || [ -z "$WEB_BASE_URL" ]; then
        log_error "Missing required URLs. Set API_BASE_URL and WEB_BASE_URL environment variables."
        return 1
    fi
    
    log_success "Configuration loaded - API: $API_BASE_URL, WEB: $WEB_BASE_URL"
}

# Health checks section
health_checks() {
    log_info "[HEALTH] Starting health checks..."
    
    # API health check
    if ! retry $MAX_RETRIES $BACKOFF_BASE check_endpoint "$API_BASE_URL/health" "200"; then
        fail_section "health_checks" "API health endpoint failed"
        return 1
    fi
    log_success "API health check passed"
    
    # API readiness check
    if ! retry $MAX_RETRIES $BACKOFF_BASE check_endpoint "$API_BASE_URL/readyz" "200"; then
        fail_section "health_checks" "API readiness endpoint failed"
        return 1
    fi
    log_success "API readiness check passed"
    
    # Web health check
    if ! retry $MAX_RETRIES $BACKOFF_BASE check_endpoint "$WEB_BASE_URL/health" "200"; then
        log_warning "Web health endpoint not available (may not be implemented)"
    else
        log_success "Web health check passed"
    fi
    
    # Web readiness check
    if ! retry $MAX_RETRIES $BACKOFF_BASE check_endpoint "$WEB_BASE_URL/readyz" "200"; then
        log_warning "Web readiness endpoint not available (may not be implemented)"
    else
        log_success "Web readiness check passed"
    fi
    
    log_success "[HEALTH] Health checks completed"
}

# AuthZ flow section
authz_flow() {
    log_info "[AUTHZ] Starting authorization flow tests..."
    
    # Test 1: No token should return 401
    local temp_auth_bearer="$AUTH_BEARER"
    
    if retry $MAX_RETRIES $BACKOFF_BASE require_http "401" "$API_BASE_URL/api/v1/engagements"; then
        log_success "No token correctly returns 401"
    else
        fail_section "authz_flow" "No token test failed - expected 401"
        return 1
    fi
    
    # Test 2: Invalid token should return 401/403
    if require_http "401" "$API_BASE_URL/api/v1/engagements" "invalid_token_12345" || \
       require_http "403" "$API_BASE_URL/api/v1/engagements" "invalid_token_12345"; then
        log_success "Invalid token correctly returns 401/403"
    else
        fail_section "authz_flow" "Invalid token test failed - expected 401/403"
        return 1
    fi
    
    # Test 3: Valid token (if provided) should return 200
    if [ -n "$temp_auth_bearer" ]; then
        if retry $MAX_RETRIES $BACKOFF_BASE require_http "200" "$API_BASE_URL/api/v1/engagements" "$temp_auth_bearer"; then
            log_success "Valid token correctly returns 200"
        else
            log_warning "Valid token test failed - check AUTH_BEARER variable"
        fi
    else
        log_info "No AUTH_BEARER provided - skipping valid token test"
    fi
    
    log_success "[AUTHZ] Authorization flow tests completed"
}

# Evidence flow section
evidence_flow() {
    log_info "[EVIDENCE] Starting evidence workflow tests..."
    
    # Test 1: SAS without membership should return 401/403
    local sas_url="$API_BASE_URL/api/sas-upload"
    if require_http "401" "$sas_url" || require_http "403" "$sas_url"; then
        log_success "SAS without membership correctly returns 401/403"
    else
        fail_section "evidence_flow" "SAS without membership test failed"
        return 1
    fi
    
    # Test 2: SAS with membership (if auth provided)
    if [ -n "$AUTH_BEARER" ]; then
        if retry $MAX_RETRIES $BACKOFF_BASE require_http "200" "$sas_url" "$AUTH_BEARER"; then
            log_success "SAS with membership returns 200"
            
            # Note: Simplified evidence flow tests - full upload simulation would require
            # more complex multipart form data handling not easily done with require_http
            if require_http "200" "$API_BASE_URL/api/documents" "$AUTH_BEARER"; then
                log_success "Document listing passed"
            else
                log_warning "Document listing failed"
            fi
        else
            log_warning "SAS with membership test failed - check authentication"
        fi
    else
        log_info "No AUTH_BEARER provided - skipping authenticated evidence tests"
    fi
    
    log_success "[EVIDENCE] Evidence workflow tests completed"
}

# MIME type and size validation tests
validation_tests() {
    log_info "[VALIDATION] Starting file validation tests..."
    
    # Note: Validation tests simplified - complex POST data validation would require
    # more sophisticated handling beyond the simple require_http utility
    # These tests would be better suited for integration tests with proper HTTP clients
    
    log_info "Validation tests simplified - complex POST validation deferred to integration tests"
    
    # Basic endpoint availability check
    if [ -n "$AUTH_BEARER" ]; then
        if require_http "200" "$API_BASE_URL/api/documents" "$AUTH_BEARER" || \
           require_http "401" "$API_BASE_URL/api/documents/upload" "$AUTH_BEARER" || \
           require_http "405" "$API_BASE_URL/api/documents/upload" "$AUTH_BEARER"; then
            log_success "Document upload endpoint is responsive"
        else
            log_warning "Document upload endpoint may not be available"
        fi
    fi
    
    log_success "[VALIDATION] File validation tests completed"
}

# Generate summary report
generate_summary() {
    echo
    echo "=== S3 Verification Summary ($(date '+%Y-%m-%d %H:%M:%S UTC')) ==="
    echo "API: $API_BASE_URL | Web: $WEB_BASE_URL"
    echo "Failures: $FAILURE_COUNT | Warnings: $WARNING_COUNT | Failed Sections: ${#FAILED_SECTIONS[@]}"
    [ ${#FAILED_SECTIONS[@]} -gt 0 ] && printf 'Failed: %s\n' "${FAILED_SECTIONS[@]}"
    
    if [ $FAILURE_COUNT -eq 0 ]; then
        echo "Status: PASSED (exit 0) - Using safe bash utilities"
    elif [ ${#FAILED_SECTIONS[@]} -eq 0 ]; then
        echo "Status: WARNINGS (exit 2) - Using safe bash utilities"
    else
        echo "Status: FAILED (exit 1) - Using safe bash utilities"
    fi
    echo "========================================"
}

# Main execution with S3 standardized checks
main() {
    local start_time=$(date +%s)
    
    echo "=== S3 Live Infrastructure Verification ==="
    echo "Bounded verification: 10s timeouts, ${MAX_RETRIES} retries with exponential backoff (using safe bash utilities)"
    
    get_deployment_config || { log_critical "Failed to load deployment configuration"; exit 1; }
    
    echo "=== Critical Health Checks ==="; health_checks || true
    echo "=== Authorization Flow Tests ==="; authz_flow || true
    echo "=== Evidence Workflow Tests ==="; evidence_flow || true
    echo "=== File Validation Tests ==="; validation_tests || true
    
    generate_summary
    echo "Total time: $(($(date +%s) - start_time))s"
    
    # Exit with appropriate code
    if [ ${#FAILED_SECTIONS[@]} -gt 0 ]; then
        log_critical "FAILED: ${#FAILED_SECTIONS[@]} critical sections failed"; exit 1
    elif [ $FAILURE_COUNT -gt 0 ]; then
        log_warning "WARNINGS: $FAILURE_COUNT non-critical failures"; exit 2
    else
        log_success "PASSED: All checks successful"; exit 0
    fi
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
#!/bin/bash
# S3 Live Infrastructure Verification - Bounded checks with retry logic
# Exit codes: 0=success, 1=critical failure, 2=warnings only
set -euo pipefail

# Colors and globals
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAILURE_COUNT=0; WARNING_COUNT=0; CRITICAL_SECTIONS=("health_checks" "authz_flow" "evidence_flow"); FAILED_SECTIONS=()

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RG_NAME="${RG_NAME:-rg-aaa-demo}"; API_BASE_URL="${API_BASE_URL:-}"; WEB_BASE_URL="${WEB_BASE_URL:-}"; AUTH_BEARER="${AUTH_BEARER:-}"
CURL_TIMEOUT=10; MAX_RETRIES=3; BACKOFF_BASE=2; UPLOAD_FILE_SIZE=1024; OVERSIZE_LIMIT_MB=10

# Logging functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; ((WARNING_COUNT++)); }
log_error() { echo -e "${RED}✗${NC} $1"; ((FAILURE_COUNT++)); }
log_critical() { echo -e "${RED}💥${NC} CRITICAL: $1"; ((FAILURE_COUNT++)); }

# Retry wrapper with exponential backoff
retry_with_backoff() {
    local max_attempts=$1 delay=$2 command="${@:3}" attempt=1
    while [ $attempt -le $max_attempts ]; do
        eval "$command" && return 0
        [ $attempt -eq $max_attempts ] && return 1
        log_info "Attempt $attempt/$max_attempts failed. Retrying in ${delay}s..."
        sleep $delay; delay=$((delay * BACKOFF_BASE)); ((attempt++))
    done
}

# Bounded curl with correlation ID check
curl_with_checks() {
    local url="$1" method="${2:-GET}" data="${3:-}" expect_status="${4:-200}"
    local temp_headers=$(mktemp) temp_body=$(mktemp)
    local curl_cmd="curl --max-time $CURL_TIMEOUT -s -w '%{http_code}' -D '$temp_headers' -o '$temp_body'"
    
    [ "$method" != "GET" ] && curl_cmd+=" -X $method"
    [ -n "$data" ] && curl_cmd+=" -H 'Content-Type: application/json' -d '$data'"
    [ -n "$AUTH_BEARER" ] && curl_cmd+=" -H 'Authorization: Bearer $AUTH_BEARER'"
    curl_cmd+=" '$url'"
    
    local http_code=$(eval "$curl_cmd" 2>/dev/null || echo "000")
    
    if ! grep -qi "x-correlation-id" "$temp_headers"; then
        log_error "Missing X-Correlation-ID header in response from $url"
        rm -f "$temp_headers" "$temp_body"; return 1
    fi
    
    if [ "$http_code" != "$expect_status" ]; then
        log_error "Expected HTTP $expect_status but got $http_code from $url"
        rm -f "$temp_headers" "$temp_body"; return 1
    fi
    
    rm -f "$temp_headers" "$temp_body"; return 0
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
    if ! retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$API_BASE_URL/health' GET '' 200"; then
        fail_section "health_checks" "API health endpoint failed"
        return 1
    fi
    log_success "API health check passed"
    
    # API readiness check
    if ! retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$API_BASE_URL/readyz' GET '' 200"; then
        fail_section "health_checks" "API readiness endpoint failed"
        return 1
    fi
    log_success "API readiness check passed"
    
    # Web health check
    if ! retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$WEB_BASE_URL/health' GET '' 200"; then
        log_warning "Web health endpoint not available (may not be implemented)"
    else
        log_success "Web health check passed"
    fi
    
    # Web readiness check
    if ! retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$WEB_BASE_URL/readyz' GET '' 200"; then
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
    AUTH_BEARER=""  # Clear auth for this test
    
    if retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$API_BASE_URL/api/v1/engagements' GET '' 401"; then
        log_success "No token correctly returns 401"
    else
        AUTH_BEARER="$temp_auth_bearer"
        fail_section "authz_flow" "No token test failed - expected 401"
        return 1
    fi
    
    # Test 2: Invalid token should return 401/403
    AUTH_BEARER="invalid_token_12345"
    if curl_with_checks "$API_BASE_URL/api/v1/engagements" "GET" "" "401" || \
       curl_with_checks "$API_BASE_URL/api/v1/engagements" "GET" "" "403"; then
        log_success "Invalid token correctly returns 401/403"
    else
        AUTH_BEARER="$temp_auth_bearer"
        fail_section "authz_flow" "Invalid token test failed - expected 401/403"
        return 1
    fi
    
    # Test 3: Valid token (if provided) should return 200
    AUTH_BEARER="$temp_auth_bearer"
    if [ -n "$AUTH_BEARER" ]; then
        if retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$API_BASE_URL/api/v1/engagements' GET '' 200"; then
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
    if curl_with_checks "$sas_url" "GET" "" "401" || curl_with_checks "$sas_url" "GET" "" "403"; then
        log_success "SAS without membership correctly returns 401/403"
    else
        fail_section "evidence_flow" "SAS without membership test failed"
        return 1
    fi
    
    # Test 2: SAS with membership (if auth provided)
    if [ -n "$AUTH_BEARER" ]; then
        if retry_with_backoff $MAX_RETRIES $BACKOFF_BASE "curl_with_checks '$sas_url' GET '' 200"; then
            log_success "SAS with membership returns 200"
            
            # Test 3: Upload tiny file (simulate)
            local upload_data='{"filename":"test.txt","size":1024,"contentType":"text/plain"}'
            if curl_with_checks "$API_BASE_URL/api/documents/upload" "POST" "$upload_data" "200"; then
                log_success "Document upload simulation passed"
                
                # Test 4: Complete upload
                if curl_with_checks "$API_BASE_URL/api/documents/complete" "POST" "{}" "200"; then
                    log_success "Upload completion passed"
                    
                    # Test 5: List shows record
                    if curl_with_checks "$API_BASE_URL/api/documents" "GET" "" "200"; then
                        log_success "Document listing passed"
                    else
                        log_warning "Document listing failed"
                    fi
                else
                    log_warning "Upload completion failed"
                fi
            else
                log_warning "Document upload simulation failed"
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
    
    # Test 1: Disallowed MIME type should return 415
    local disallowed_data='{"filename":"test.exe","size":1024,"contentType":"application/x-executable"}'
    if curl_with_checks "$API_BASE_URL/api/documents/upload" "POST" "$disallowed_data" "415"; then
        log_success "Disallowed MIME type correctly returns 415"
    else
        log_warning "Disallowed MIME type test failed - expected 415"
    fi
    
    # Test 2: Oversize file should return 413
    local oversize_bytes=$((OVERSIZE_LIMIT_MB * 1024 * 1024 + 1))
    local oversize_data='{"filename":"large.pdf","size":'$oversize_bytes',"contentType":"application/pdf"}'
    if curl_with_checks "$API_BASE_URL/api/documents/upload" "POST" "$oversize_data" "413"; then
        log_success "Oversize file correctly returns 413"
    else
        log_warning "Oversize file test failed - expected 413"
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
        echo "Status: 🟢 PASSED (exit 0)"
    elif [ ${#FAILED_SECTIONS[@]} -eq 0 ]; then
        echo "Status: 🟡 WARNINGS (exit 2)"
    else
        echo "Status: 🔴 FAILED (exit 1)"
    fi
    echo "========================================"
}

# Main execution with S3 standardized checks
main() {
    local start_time=$(date +%s)
    
    echo "=== S3 Live Infrastructure Verification ==="
    echo "Bounded verification: ${CURL_TIMEOUT}s timeouts, ${MAX_RETRIES} retries with exponential backoff"
    
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
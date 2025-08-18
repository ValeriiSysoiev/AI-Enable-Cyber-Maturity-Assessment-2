#!/usr/bin/env bash

# Sprint S1 Live Verification Script
# Tests all Sprint S1 acceptance criteria against deployed environment

set -e

# Compatible with bash 3.2+

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
VERIFY_LOG="logs/verify-s1-$(date +%Y%m%d-%H%M%S).log"
RESULTS_FILE="logs/verify-s1-results-$(date +%Y%m%d-%H%M%S).json"

# Ensure logs directory exists
mkdir -p logs

# Logging function
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$VERIFY_LOG"
}

# Test result tracking (compatible with older bash)
test_results=""
total_tests=0
passed_tests=0
failed_tests=0

# Function to add test result
add_test_result() {
    local test_name="$1"
    local result="$2"
    if [[ -z "$test_results" ]]; then
        test_results="$test_name:$result"
    else
        test_results="$test_results|$test_name:$result"
    fi
}

# Test execution function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    total_tests=$((total_tests + 1))
    log "${BLUE}[TEST $total_tests] $test_name${NC}"
    
    if eval "$test_command" | grep -q "$expected_pattern"; then
        log "${GREEN}✅ PASS: $test_name${NC}"
        add_test_result "$test_name" "PASS"
        passed_tests=$((passed_tests + 1))
        return 0
    else
        log "${RED}❌ FAIL: $test_name${NC}"
        add_test_result "$test_name" "FAIL"
        failed_tests=$((failed_tests + 1))
        return 1
    fi
}

# HTTP test function
http_test() {
    local test_name="$1"
    local url="$2"
    local expected_status="$3"
    local expected_content="$4"
    
    total_tests=$((total_tests + 1))
    log "${BLUE}[TEST $total_tests] $test_name${NC}"
    
    local response
    local status_code
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\n000")
    status_code=$(echo "$response" | tail -1)
    content=$(echo "$response" | sed '$d')
    
    if [[ "$status_code" == "$expected_status" ]] && [[ -z "$expected_content" || "$content" =~ $expected_content ]]; then
        log "${GREEN}✅ PASS: $test_name (Status: $status_code)${NC}"
        add_test_result "$test_name" "PASS"
        passed_tests=$((passed_tests + 1))
        return 0
    else
        log "${RED}❌ FAIL: $test_name (Status: $status_code, Expected: $expected_status)${NC}"
        add_test_result "$test_name" "FAIL"
        failed_tests=$((failed_tests + 1))
        return 1
    fi
}

# Generate correlation ID for test session
CORRELATION_ID=$(uuidgen 2>/dev/null || openssl rand -hex 16 2>/dev/null || echo "test-$(date +%s)")

log "${YELLOW}🚀 Starting Sprint S1 Live Verification${NC}"
log "Web Base URL: $WEB_BASE_URL"
log "API Base URL: $API_BASE_URL"
log "Correlation ID: $CORRELATION_ID"
log "Results will be saved to: $RESULTS_FILE"

# ============================================================================
# PHASE 1: Health & Readiness Endpoints
# ============================================================================

log "${YELLOW}📊 Phase 1: Health & Readiness Endpoints${NC}"

http_test "Web Health Check" "$WEB_BASE_URL/health" "200" "\"status\":\"ok\""
http_test "Web Readiness Check" "$WEB_BASE_URL/readyz" "200" "\"status\":\"ready\""
http_test "API Health Check" "$API_BASE_URL/health" "200" "\"status\":\"ok\""
http_test "API Readiness Check" "$API_BASE_URL/readyz" "200" "\"status\":\"ready\""

# ============================================================================
# PHASE 2: Authentication & Route Guards
# ============================================================================

log "${YELLOW}🔐 Phase 2: Authentication & Route Guards${NC}"

# Test unauthenticated access redirects
http_test "Unauthenticated /engagements redirects" "$WEB_BASE_URL/engagements" "302|307" ""

# Test signin page accessibility
http_test "Signin page accessible" "$WEB_BASE_URL/signin" "200" "Sign in to AI Maturity Assessment"

# Test 403 page accessibility  
http_test "403 page accessible" "$WEB_BASE_URL/403" "200" "403 - Access Forbidden"

# ============================================================================
# PHASE 3: API Authentication & RBAC
# ============================================================================

log "${YELLOW}🛡️ Phase 3: API Authentication & RBAC${NC}"

# Test API endpoints require authentication
http_test "API requires auth header" "$API_BASE_URL/engagements" "401|403" ""

# Test API health with correlation ID
http_test "API correlation ID support" "$API_BASE_URL/health" "200" "\"correlation_id\""

# ============================================================================
# PHASE 4: Structured Logging & Correlation IDs
# ============================================================================

log "${YELLOW}📝 Phase 4: Structured Logging & Correlation IDs${NC}"

# Test correlation ID propagation
test_correlation_id() {
    local response
    response=$(curl -s -H "X-Correlation-ID: $CORRELATION_ID" "$API_BASE_URL/health")
    if echo "$response" | grep -q "$CORRELATION_ID"; then
        return 0
    else
        return 1
    fi
}

if test_correlation_id; then
    log "${GREEN}✅ PASS: Correlation ID propagation${NC}"
    add_test_result "Correlation ID propagation" "PASS"
    passed_tests=$((passed_tests + 1))
else
    log "${RED}❌ FAIL: Correlation ID propagation${NC}"
    add_test_result "Correlation ID propagation" "FAIL"
    failed_tests=$((failed_tests + 1))
fi
total_tests=$((total_tests + 1))

# ============================================================================
# PHASE 5: Frontend Integration Tests
# ============================================================================

log "${YELLOW}🌐 Phase 5: Frontend Integration${NC}"

# Test main pages render correctly
http_test "Dashboard page loads" "$WEB_BASE_URL/" "200" "AI Maturity Tool"
http_test "Navigation present" "$WEB_BASE_URL/" "200" "nav|navigation"

# Test static assets
http_test "CSS assets load" "$WEB_BASE_URL/_next/static/css" "200|404" ""

# ============================================================================
# Results Summary
# ============================================================================

log "${YELLOW}📋 Verification Complete - Generating Report${NC}"

# Calculate success rate
success_rate=$(( (passed_tests * 100) / total_tests ))

# Generate JSON results
cat > "$RESULTS_FILE" << EOF
{
  "verification_session": {
    "correlation_id": "$CORRELATION_ID",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "web_base_url": "$WEB_BASE_URL",
    "api_base_url": "$API_BASE_URL",
    "sprint": "S1",
    "version": "1.0.0"
  },
  "summary": {
    "total_tests": $total_tests,
    "passed_tests": $passed_tests,
    "failed_tests": $failed_tests,
    "success_rate": $success_rate,
    "status": "$([[ $failed_tests -eq 0 ]] && echo "PASS" || echo "FAIL")"
  },
  "test_results": {
EOF

# Add test results to JSON
if [[ -n "$test_results" ]]; then
    first=true
    IFS='|' read -ra TEST_ARRAY <<< "$test_results"
    for test_entry in "${TEST_ARRAY[@]}"; do
        test_name="${test_entry%%:*}"
        test_result="${test_entry##*:}"
        if [[ "$first" == true ]]; then
            first=false
        else
            echo "," >> "$RESULTS_FILE"
        fi
        echo "    \"$test_name\": \"$test_result\"" >> "$RESULTS_FILE"
    done
fi

cat >> "$RESULTS_FILE" << EOF
  }
}
EOF

# Display summary
log ""
log "${YELLOW}📊 VERIFICATION SUMMARY${NC}"
log "════════════════════════════════════════"
log "Total Tests: $total_tests"
log "Passed: ${GREEN}$passed_tests${NC}"
log "Failed: ${RED}$failed_tests${NC}"
log "Success Rate: ${BLUE}$success_rate%${NC}"
log ""

if [[ $failed_tests -eq 0 ]]; then
    log "${GREEN}🎉 Sprint S1 Verification: PASSED${NC}"
    log "All acceptance criteria verified successfully!"
    exit 0
else
    log "${RED}💥 Sprint S1 Verification: FAILED${NC}"
    log "Review failed tests above and check logs: $VERIFY_LOG"
    exit 1
fi
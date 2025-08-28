#!/bin/bash
# Production Health Check Script
# Validates all critical endpoints and services are operational

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io}"
WEB_BASE_URL="${WEB_BASE_URL:-https://web-cybermat-prd.azurewebsites.net}"
TIMEOUT=10
FAILURES=0

echo -e "${BLUE}=== Production Health Check ===${NC}"
echo "API: $API_BASE_URL"
echo "Web: $WEB_BASE_URL"
echo ""

# Function to check endpoint
check_endpoint() {
    local url=$1
    local expected_status=$2
    local description=$3
    
    echo -n "Checking $description... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" || echo "000")
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $status)${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL (Expected $expected_status, got $status)${NC}"
        ((FAILURES++))
        return 1
    fi
}

# Function to check endpoint with headers
check_endpoint_with_headers() {
    local url=$1
    local expected_status=$2
    local description=$3
    local headers=$4
    
    echo -n "Checking $description... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT \
             -H "X-User-Email: health@check.local" \
             -H "X-Engagement-ID: health-check" \
             $headers \
             "$url" || echo "000")
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $status)${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL (Expected $expected_status, got $status)${NC}"
        ((FAILURES++))
        return 1
    fi
}

# Function to check response time
check_response_time() {
    local url=$1
    local max_time=$2
    local description=$3
    
    echo -n "Checking $description response time... "
    
    response_time=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout $TIMEOUT "$url" || echo "999")
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d'.' -f1)
    
    if (( $(echo "$response_time < $max_time" | bc -l) )); then
        echo -e "${GREEN}✓ OK (${response_time_ms}ms)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ SLOW (${response_time_ms}ms, max ${max_time}s)${NC}"
        return 0
    fi
}

echo -e "${BLUE}--- API Health Checks ---${NC}"
check_endpoint "$API_BASE_URL/api/health" "200" "API Health"
check_endpoint "$API_BASE_URL/api/version" "200" "API Version"
check_endpoint "$API_BASE_URL/api/features" "200" "Feature Flags"
check_response_time "$API_BASE_URL/api/health" "2" "API Health"

echo ""
echo -e "${BLUE}--- API Endpoints ---${NC}"
check_endpoint "$API_BASE_URL/api/presets" "200" "Presets List"
check_endpoint "$API_BASE_URL/api/presets/cscm-v3" "200" "CSCM-V3 Preset"
check_endpoint "$API_BASE_URL/api/presets/cyber-for-ai" "200" "Cyber-for-AI Preset"
check_endpoint_with_headers "$API_BASE_URL/api/engagements" "200" "Engagements List" ""
check_endpoint_with_headers "$API_BASE_URL/api/admin/status" "200" "Admin Status" ""

echo ""
echo -e "${BLUE}--- Web Application ---${NC}"
check_endpoint "$WEB_BASE_URL" "200" "Web Home Page"
check_endpoint "$WEB_BASE_URL/api/admin/status" "200" "Web Admin Status Proxy"
check_response_time "$WEB_BASE_URL" "3" "Web Home Page"

echo ""
echo -e "${BLUE}--- Security Headers ---${NC}"
echo -n "Checking security headers... "
headers=$(curl -s -I "$WEB_BASE_URL" | grep -E "(Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options)" | wc -l)
if [ "$headers" -ge 1 ]; then
    echo -e "${GREEN}✓ Security headers present${NC}"
else
    echo -e "${YELLOW}⚠ Some security headers missing${NC}"
fi

echo ""
echo -e "${BLUE}--- API Version Check ---${NC}"
echo -n "Fetching deployed version... "
version_info=$(curl -s "$API_BASE_URL/api/version" 2>/dev/null | jq -r '.git_sha' 2>/dev/null || echo "unknown")
if [ "$version_info" != "unknown" ] && [ "$version_info" != "null" ]; then
    echo -e "${GREEN}✓ Version: $version_info${NC}"
else
    echo -e "${YELLOW}⚠ Unable to determine version${NC}"
fi

# Check RAG status
echo ""
echo -e "${BLUE}--- RAG Service Status ---${NC}"
echo -n "Checking RAG operational status... "
rag_status=$(curl -s "$API_BASE_URL/api/version" 2>/dev/null | jq -r '.rag_status.operational' 2>/dev/null || echo "unknown")
if [ "$rag_status" = "true" ]; then
    echo -e "${GREEN}✓ RAG Operational${NC}"
elif [ "$rag_status" = "false" ]; then
    echo -e "${YELLOW}⚠ RAG Not Operational${NC}"
else
    echo -e "${YELLOW}⚠ RAG Status Unknown${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}=== Health Check Summary ===${NC}"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILURES health checks failed${NC}"
    exit 1
fi
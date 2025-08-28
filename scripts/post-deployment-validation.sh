#!/bin/bash
# Post-deployment validation script for Azure Container Apps
# Runs comprehensive smoke tests and validates deployment success

set -e

# Configuration
API_URL="${API_BASE_URL:-https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io}"
WEB_URL="${WEB_BASE_URL:-https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io}"
TIMEOUT=${TIMEOUT:-60}
MAX_RETRIES=${MAX_RETRIES:-5}
RETRY_DELAY=${RETRY_DELAY:-30}

echo "🚀 Post-Deployment Validation Starting"
echo "API URL: $API_URL"
echo "Web URL: $WEB_URL"
echo "Timeout: ${TIMEOUT}s"
echo "Max Retries: $MAX_RETRIES"
echo "======================================"

# Function to wait for deployment to be ready
wait_for_deployment() {
    local url=$1
    local max_attempts=$2
    local delay=$3
    
    echo "⏳ Waiting for deployment at $url to be ready..."
    
    for i in $(seq 1 $max_attempts); do
        echo "   Attempt $i/$max_attempts..."
        
        if curl -f -s --max-time 10 "$url/health" > /dev/null 2>&1; then
            echo "✅ Deployment is responding"
            return 0
        fi
        
        if [ $i -lt $max_attempts ]; then
            echo "   Deployment not ready, waiting ${delay}s..."
            sleep $delay
        fi
    done
    
    echo "❌ Deployment failed to become ready after $max_attempts attempts"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    local api_url=$1
    
    echo "🧪 Running API smoke tests..."
    
    # Check if smoke test script exists
    if [ ! -f "scripts/smoke-test.py" ]; then
        echo "⚠️ Smoke test script not found, running basic validation..."
        
        # Basic curl-based validation
        echo "   Testing health endpoint..."
        if ! curl -f -s --max-time 10 "$api_url/health"; then
            echo "❌ Health endpoint test failed"
            return 1
        fi
        
        echo "   Testing OpenAPI schema..."
        local endpoint_count=$(curl -s --max-time 10 "$api_url/openapi.json" | python3 -c "import json,sys; data=json.load(sys.stdin); print(len(data.get('paths', {})))" 2>/dev/null || echo "0")
        
        if [ "$endpoint_count" -lt 10 ]; then
            echo "❌ Insufficient endpoints loaded: $endpoint_count (expected >10)"
            return 1
        else
            echo "✅ API has $endpoint_count endpoints loaded"
        fi
        
        return 0
    fi
    
    # Run comprehensive smoke tests
    python3 scripts/smoke-test.py --url "$api_url" --timeout $TIMEOUT --output smoke-test-results.json
    
    return $?
}

# Function to validate specific business endpoints
validate_business_endpoints() {
    local api_url=$1
    
    echo "🎯 Validating critical business endpoints..."
    
    local critical_endpoints=(
        "/api/features"
        "/api/engagements"
        "/api/domain-assessments"
        "/openapi.json"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${critical_endpoints[@]}"; do
        echo "   Testing $endpoint..."
        if curl -f -s --max-time 10 "$api_url$endpoint" > /dev/null; then
            echo "     ✅ $endpoint responding"
        else
            echo "     ❌ $endpoint failed"
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [ ${#failed_endpoints[@]} -gt 0 ]; then
        echo "❌ Critical endpoints failed: ${failed_endpoints[*]}"
        return 1
    fi
    
    echo "✅ All critical endpoints validated"
    return 0
}

# Function to check for deployment rollback
check_deployment_status() {
    echo "🔍 Checking deployment status..."
    
    # Get endpoint count from OpenAPI
    local endpoint_count=$(curl -s --max-time 10 "$API_URL/openapi.json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    paths = data.get('paths', {})
    business_paths = [p for p in paths if p.startswith('/api/') and p not in ['/', '/health', '/version']]
    print(f'{len(paths)},{len(business_paths)}')
except:
    print('0,0')
" 2>/dev/null || echo "0,0")
    
    local total=$(echo $endpoint_count | cut -d',' -f1)
    local business=$(echo $endpoint_count | cut -d',' -f2)
    
    echo "   Total endpoints: $total"
    echo "   Business endpoints: $business"
    
    if [ "$total" -lt 10 ]; then
        echo "⚠️ WARNING: Deployment may have failed - only $total endpoints available"
        echo "   This suggests routes failed to load properly"
        return 1
    fi
    
    if [ "$business" -lt 5 ]; then
        echo "⚠️ WARNING: Limited business functionality - only $business business endpoints"
        return 1
    fi
    
    echo "✅ Deployment appears successful with $total endpoints"
    return 0
}

# Main validation flow
main() {
    local exit_code=0
    
    # Wait for deployment to be ready
    if ! wait_for_deployment "$API_URL" $MAX_RETRIES $RETRY_DELAY; then
        echo "❌ VALIDATION FAILED: Deployment not responding"
        exit 1
    fi
    
    # Check deployment status
    if ! check_deployment_status; then
        echo "⚠️ Deployment status check failed"
        exit_code=1
    fi
    
    # Validate critical endpoints
    if ! validate_business_endpoints "$API_URL"; then
        echo "❌ VALIDATION FAILED: Critical endpoints not working"
        exit_code=1
    fi
    
    # Run comprehensive smoke tests
    if ! run_smoke_tests "$API_URL"; then
        echo "❌ VALIDATION FAILED: Smoke tests failed"
        exit_code=1
    fi
    
    # Final status
    if [ $exit_code -eq 0 ]; then
        echo "======================================"
        echo "🎉 POST-DEPLOYMENT VALIDATION PASSED"
        echo "   API is healthy and all endpoints are working"
        echo "   Deployment was successful"
        echo "======================================"
    else
        echo "======================================"
        echo "💥 POST-DEPLOYMENT VALIDATION FAILED"
        echo "   Deployment may have issues"
        echo "   Manual investigation required"
        echo "======================================"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"
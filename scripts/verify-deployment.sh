#!/bin/bash

# Deployment Verification Script
# Verifies that deployment was successful and all services are healthy

set -e

EXPECTED_SHA="${1:-$(git rev-parse HEAD)}"
PROD_URL="${2:-https://aecma-prod.azurewebsites.net}"
STAGING_URL="${3:-https://aecma-staging.azurewebsites.net}"

echo "🔍 DEPLOYMENT VERIFICATION"
echo "=========================="
echo "Expected SHA: $EXPECTED_SHA"
echo "Production URL: $PROD_URL"
echo "Staging URL: $STAGING_URL"
echo ""

# Function to check endpoint
check_endpoint() {
    local url=$1
    local endpoint=$2
    local description=$3
    
    echo "Checking $description..."
    
    if response=$(curl -s --max-time 10 "$url$endpoint" 2>/dev/null); then
        if [ -n "$response" ]; then
            echo "✅ $description: OK"
            if [[ "$endpoint" == "/api/version" ]]; then
                if echo "$response" | grep -q "$EXPECTED_SHA"; then
                    echo "✅ Version matches expected SHA: $EXPECTED_SHA"
                else
                    echo "⚠️  Version mismatch - Expected: $EXPECTED_SHA"
                    echo "   Response: $response"
                fi
            fi
            return 0
        else
            echo "❌ $description: Empty response"
            return 1
        fi
    else
        echo "❌ $description: Connection failed"
        return 1
    fi
}

# Function to verify environment
verify_environment() {
    local env_name=$1
    local base_url=$2
    
    echo ""
    echo "🌐 Verifying $env_name Environment"
    echo "================================"
    
    local health_ok=0
    local version_ok=0
    local auth_ok=0
    
    # Check health endpoint
    if check_endpoint "$base_url" "/health" "$env_name Health"; then
        health_ok=1
    fi
    
    # Check version endpoint
    if check_endpoint "$base_url" "/api/version" "$env_name Version"; then
        version_ok=1
    fi
    
    # Check auth mode endpoint
    if check_endpoint "$base_url" "/api/auth/mode" "$env_name Auth Mode"; then
        auth_ok=1
    fi
    
    # Summary for this environment
    local total=$((health_ok + version_ok + auth_ok))
    echo ""
    echo "📊 $env_name Summary: $total/3 endpoints healthy"
    
    if [ $total -eq 3 ]; then
        echo "✅ $env_name: All systems operational"
        return 0
    else
        echo "⚠️  $env_name: Some issues detected"
        return 1
    fi
}

# Main verification
echo "🚀 Starting deployment verification..."
echo ""

prod_ok=0
staging_ok=0

# Verify production
if verify_environment "Production" "$PROD_URL"; then
    prod_ok=1
fi

# Verify staging
if verify_environment "Staging" "$STAGING_URL"; then
    staging_ok=1
fi

# Final summary
echo ""
echo "🏁 FINAL DEPLOYMENT STATUS"
echo "=========================="

if [ $prod_ok -eq 1 ] && [ $staging_ok -eq 1 ]; then
    echo "✅ DEPLOYMENT SUCCESSFUL"
    echo "   - Production: ✅ Healthy"
    echo "   - Staging: ✅ Healthy"
    echo "   - Version: $EXPECTED_SHA"
    exit 0
elif [ $prod_ok -eq 1 ]; then
    echo "⚠️  DEPLOYMENT PARTIAL"
    echo "   - Production: ✅ Healthy"
    echo "   - Staging: ❌ Issues detected"
    echo "   - Version: $EXPECTED_SHA"
    exit 1
else
    echo "❌ DEPLOYMENT FAILED"
    echo "   - Production: ❌ Issues detected"
    echo "   - Staging: $([ $staging_ok -eq 1 ] && echo '✅ Healthy' || echo '❌ Issues detected')"
    echo "   - Version: $EXPECTED_SHA"
    exit 2
fi

#!/bin/bash
# Version Synchronization Verification Script
# This script ensures production version matches the expected commit SHA

set -euo pipefail

# Configuration
PROD_URL="${1:-https://web-cybermat-prd.azurewebsites.net}"
EXPECTED_SHA="${2:-$(git rev-parse HEAD)}"
MAX_RETRIES=10
RETRY_DELAY=30

echo "🔍 VERSION SYNCHRONIZATION VERIFICATION"
echo "======================================="
echo "Production URL: $PROD_URL"
echo "Expected SHA: ${EXPECTED_SHA:0:8}"
echo ""

# Function to check version
check_version() {
    local current_sha
    current_sha=$(curl -s "$PROD_URL/api/version" | jq -r '.sha // "unknown"' 2>/dev/null || echo "unknown")
    echo "$current_sha"
}

# Function to check debug info
check_debug_info() {
    curl -s "$PROD_URL/api/version" | jq '.debug // {}' 2>/dev/null || echo "{}"
}

echo "🔄 Checking production version..."
for i in $(seq 1 $MAX_RETRIES); do
    echo "Attempt $i/$MAX_RETRIES..."
    
    current_sha=$(check_version)
    
    if [ "$current_sha" = "$EXPECTED_SHA" ]; then
        echo "✅ SUCCESS: Production version matches expected SHA"
        echo "   Expected: ${EXPECTED_SHA:0:8}"
        echo "   Actual:   ${current_sha:0:8}"
        echo ""
        echo "🔍 Environment Variable Status:"
        check_debug_info | jq .
        exit 0
    elif [ "$current_sha" = "unknown" ]; then
        echo "⚠️  Version API returned 'unknown' - checking debug info..."
        check_debug_info | jq .
    else
        echo "⏳ Version mismatch (expected: ${EXPECTED_SHA:0:8}, got: ${current_sha:0:8})"
    fi
    
    if [ $i -lt $MAX_RETRIES ]; then
        echo "   Waiting ${RETRY_DELAY}s before retry..."
        sleep $RETRY_DELAY
    fi
done

echo ""
echo "❌ FAILED: Production version did not sync after $MAX_RETRIES attempts"
echo "Expected: ${EXPECTED_SHA:0:8}"
echo "Actual:   $(check_version | cut -c1-8)"
echo ""
echo "🔍 Debug Information:"
check_debug_info | jq .
echo ""
echo "🔧 Troubleshooting Steps:"
echo "1. Check if environment variables are set correctly"
echo "2. Verify the Docker image was built with correct build args"
echo "3. Ensure the app service restarted after environment variable changes"
echo "4. Check application logs for any errors"

exit 1

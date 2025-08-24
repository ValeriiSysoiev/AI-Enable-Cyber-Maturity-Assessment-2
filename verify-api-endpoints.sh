#!/bin/bash

# Script to verify API endpoints in production
# Usage: ./verify-api-endpoints.sh [BASE_URL]

BASE_URL=${1:-"https://web-cybermat-prd.azurewebsites.net"}

echo "Testing API endpoints on: $BASE_URL"
echo "=================================="

echo -n "Testing /api/health: "
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health")
if [ "$HEALTH_STATUS" = "200" ]; then
    echo "✅ PASS (HTTP $HEALTH_STATUS)"
    echo "Response: $(curl -s "$BASE_URL/api/health" | jq -r '.status + " at " + .timestamp')"
else
    echo "❌ FAIL (HTTP $HEALTH_STATUS)"
fi

echo -n "Testing /api/version: "
VERSION_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/version")
if [ "$VERSION_STATUS" = "200" ]; then
    echo "✅ PASS (HTTP $VERSION_STATUS)"
    echo "Response: $(curl -s "$BASE_URL/api/version" | jq -r '.sha')"
else
    echo "❌ FAIL (HTTP $VERSION_STATUS)"
fi

echo "=================================="
if [ "$HEALTH_STATUS" = "200" ] && [ "$VERSION_STATUS" = "200" ]; then
    echo "🎉 All API endpoints are working correctly!"
    exit 0
else
    echo "💥 Some API endpoints are failing. Check deployment."
    exit 1
fi
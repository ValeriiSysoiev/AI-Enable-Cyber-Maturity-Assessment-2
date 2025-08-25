#!/bin/bash

# Deployment Monitoring Script
# Monitors all deployment workflows and provides comprehensive status

set -e

echo "🔍 DEPLOYMENT MONITORING DASHBOARD"
echo "=================================="
echo "Timestamp: $(date)"
echo ""

# Function to get workflow status with emoji
get_status_emoji() {
    case $1 in
        "completed") echo "✅" ;;
        "in_progress") echo "🔄" ;;
        "queued") echo "⏳" ;;
        "failure") echo "❌" ;;
        "cancelled") echo "🚫" ;;
        *) echo "❓" ;;
    esac
}

# Function to check workflow runs
check_workflow() {
    local workflow_name=$1
    local workflow_file=$2
    
    echo "📋 $workflow_name"
    echo "$(printf '%.0s-' {1..50})"
    
    if ! gh run list --workflow="$workflow_file" --limit 5 --json status,conclusion,createdAt,headSha,event 2>/dev/null | jq -r '.[] | "\(.status) \(.conclusion // "running") \(.createdAt) \(.headSha[0:8]) \(.event)"' | while read -r status conclusion created_at sha event; do
        emoji=$(get_status_emoji "$conclusion")
        if [ "$conclusion" = "null" ] || [ "$conclusion" = "running" ]; then
            emoji=$(get_status_emoji "$status")
        fi
        
        # Format timestamp
        formatted_time=$(date -d "$created_at" "+%H:%M %m/%d" 2>/dev/null || echo "$created_at")
        
        printf "%s %s %s %s (%s)\n" "$emoji" "$sha" "$formatted_time" "$event" "$status"
    done; then
        echo ""
    else
        echo "❌ Failed to fetch workflow data"
        echo ""
    fi
}

# Check current commit
current_sha=$(git rev-parse HEAD | cut -c1-8)
echo "🏷️  Current Commit: $current_sha"
echo ""

# Check all deployment workflows
check_workflow "Primary Deployment (GHCR)" "deploy.yml"
check_workflow "Staging Deployment" "deploy_staging.yml"  
check_workflow "Production Release" "release.yml"

# Check production status
echo "🌐 PRODUCTION STATUS"
echo "$(printf '%.0s-' {1..50})"

prod_url="https://aecma-prod.azurewebsites.net"

# Health check
if curl -s --max-time 5 "$prod_url/health" > /dev/null 2>&1; then
    echo "✅ Health endpoint: OK"
else
    echo "❌ Health endpoint: FAILED"
fi

# Version check
if version_response=$(curl -s --max-time 5 "$prod_url/api/version" 2>/dev/null); then
    if [ -n "$version_response" ]; then
        prod_sha=$(echo "$version_response" | jq -r '.sha // .commit_sha // "unknown"' 2>/dev/null || echo "unknown")
        if [ "$prod_sha" = "$current_sha" ]; then
            echo "✅ Version: $prod_sha (matches current)"
        else
            echo "⚠️  Version: $prod_sha (expected: $current_sha)"
        fi
    else
        echo "❌ Version endpoint: Empty response"
    fi
else
    echo "❌ Version endpoint: FAILED"
fi

# Auth mode check
if auth_response=$(curl -s --max-time 5 "$prod_url/api/auth/mode" 2>/dev/null); then
    if [ -n "$auth_response" ]; then
        auth_mode=$(echo "$auth_response" | jq -r '.mode // "unknown"' 2>/dev/null || echo "unknown")
        echo "✅ Auth mode: $auth_mode"
    else
        echo "❌ Auth mode endpoint: Empty response"
    fi
else
    echo "❌ Auth mode endpoint: FAILED"
fi

echo ""

# Check staging status
echo "🧪 STAGING STATUS"
echo "$(printf '%.0s-' {1..50})"

staging_url="https://aecma-staging.azurewebsites.net"

# Health check
if curl -s --max-time 5 "$staging_url/health" > /dev/null 2>&1; then
    echo "✅ Health endpoint: OK"
else
    echo "❌ Health endpoint: FAILED"
fi

# Version check
if version_response=$(curl -s --max-time 5 "$staging_url/api/version" 2>/dev/null); then
    if [ -n "$version_response" ]; then
        staging_sha=$(echo "$version_response" | jq -r '.sha // .commit_sha // "unknown"' 2>/dev/null || echo "unknown")
        if [ "$staging_sha" = "$current_sha" ]; then
            echo "✅ Version: $staging_sha (matches current)"
        else
            echo "⚠️  Version: $staging_sha (expected: $current_sha)"
        fi
    else
        echo "❌ Version endpoint: Empty response"
    fi
else
    echo "❌ Version endpoint: FAILED"
fi

echo ""

# Check container registry
echo "📦 CONTAINER REGISTRY STATUS"
echo "$(printf '%.0s-' {1..50})"

# Check if current commit image exists in GHCR
if docker manifest inspect "ghcr.io/valeriisysoiev/aecma-web:$current_sha" > /dev/null 2>&1; then
    echo "✅ GHCR image: ghcr.io/valeriisysoiev/aecma-web:$current_sha"
else
    echo "❌ GHCR image: Not found for $current_sha"
fi

# Check latest tag
if docker manifest inspect "ghcr.io/valeriisysoiev/aecma-web:latest" > /dev/null 2>&1; then
    echo "✅ GHCR latest: Available"
else
    echo "❌ GHCR latest: Not found"
fi

echo ""

# Summary and recommendations
echo "📊 DEPLOYMENT SUMMARY"
echo "$(printf '%.0s-' {1..50})"

# Count recent failures
recent_failures=$(gh run list --limit 10 --json status,conclusion 2>/dev/null | jq '[.[] | select(.conclusion == "failure")] | length' 2>/dev/null || echo "0")

if [ "$recent_failures" -eq 0 ]; then
    echo "✅ No recent deployment failures"
elif [ "$recent_failures" -lt 3 ]; then
    echo "⚠️  $recent_failures recent deployment failures"
else
    echo "❌ $recent_failures recent deployment failures - investigate immediately"
fi

echo ""
echo "🔧 QUICK ACTIONS"
echo "$(printf '%.0s-' {1..50})"
echo "• Trigger deployment: gh workflow run .github/workflows/deploy.yml"
echo "• Check logs: gh run list --limit 5"
echo "• Verify deployment: ./scripts/verify-deployment.sh"
echo "• View in browser: open https://github.com/$(gh repo view --json owner,name -q '.owner.login + \"/\" + .name')/actions"

echo ""
echo "Last updated: $(date)"

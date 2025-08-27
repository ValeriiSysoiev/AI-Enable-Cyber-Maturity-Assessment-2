#!/bin/bash
# Deployment Monitoring Script
# Monitors GitHub Actions deployment and provides real-time status updates

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get run ID from argument or find latest
RUN_ID="${1:-}"
if [ -z "$RUN_ID" ]; then
    echo "Finding latest deployment run..."
    RUN_ID=$(gh run list --workflow="Deploy to Production" --limit 1 --json databaseId -q '.[0].databaseId')
fi

if [ -z "$RUN_ID" ]; then
    echo -e "${RED}No deployment runs found${NC}"
    exit 1
fi

echo -e "${BLUE}=== Monitoring Deployment Run #$RUN_ID ===${NC}"
echo ""

# Function to format duration
format_duration() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local remaining_seconds=$((seconds % 60))
    echo "${minutes}m ${remaining_seconds}s"
}

# Function to check deployment status
check_status() {
    local status_json=$(gh run view $RUN_ID --json status,conclusion,jobs 2>/dev/null || echo "{}")
    
    if [ "$status_json" = "{}" ]; then
        echo -e "${RED}Failed to get deployment status${NC}"
        return 1
    fi
    
    local status=$(echo $status_json | jq -r '.status')
    local conclusion=$(echo $status_json | jq -r '.conclusion')
    
    # Get current step
    local current_step=$(echo $status_json | jq -r '.jobs[0].steps[] | select(.status == "in_progress") | .name' | head -1)
    
    # Count completed steps
    local completed_count=$(echo $status_json | jq -r '[.jobs[0].steps[] | select(.status == "completed")] | length')
    local total_steps=$(echo $status_json | jq -r '.jobs[0].steps | length')
    
    # Calculate progress
    local progress=$((completed_count * 100 / total_steps))
    
    echo -e "${CYAN}Status:${NC} $status"
    echo -e "${CYAN}Progress:${NC} $completed_count/$total_steps steps (${progress}%)"
    
    if [ -n "$current_step" ]; then
        echo -e "${CYAN}Current Step:${NC} $current_step"
    fi
    
    if [ "$status" = "completed" ]; then
        if [ "$conclusion" = "success" ]; then
            echo -e "${GREEN}✅ Deployment Successful!${NC}"
            return 0
        else
            echo -e "${RED}❌ Deployment Failed: $conclusion${NC}"
            return 1
        fi
    fi
    
    return 2  # Still running
}

# Function to show step details
show_steps() {
    echo ""
    echo -e "${BLUE}Step Status:${NC}"
    gh run view $RUN_ID --json jobs | jq -r '.jobs[0].steps[] | 
        if .status == "completed" then
            if .conclusion == "success" then
                "✅ " + .name
            else
                "❌ " + .name
            end
        elif .status == "in_progress" then
            "🔄 " + .name + " (running)"
        else
            "⏳ " + .name + " (pending)"
        end'
}

# Main monitoring loop
START_TIME=$(date +%s)
LAST_STATUS=""

while true; do
    clear
    echo -e "${BLUE}=== Deployment Monitor ===${NC}"
    echo -e "${CYAN}Run ID:${NC} $RUN_ID"
    echo -e "${CYAN}URL:${NC} https://github.com/ValeriiSysoiev/AI-Enable-Cyber-Maturity-Assessment-2/actions/runs/$RUN_ID"
    
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    echo -e "${CYAN}Elapsed:${NC} $(format_duration $ELAPSED)"
    echo ""
    
    check_status
    STATUS_CODE=$?
    
    if [ $STATUS_CODE -eq 0 ]; then
        # Success
        show_steps
        echo ""
        echo -e "${GREEN}=== Deployment Complete ===${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Run health check: ./scripts/health-check-prod.sh"
        echo "2. View application: https://web-cybermat-prd.azurewebsites.net"
        echo "3. Check API: https://api-cybermat-prd.azurewebsites.net/api/health"
        exit 0
    elif [ $STATUS_CODE -eq 1 ]; then
        # Failed
        show_steps
        echo ""
        echo -e "${RED}=== Deployment Failed ===${NC}"
        echo ""
        echo "To view logs:"
        echo "gh run view $RUN_ID --log"
        exit 1
    else
        # Still running
        show_steps
        echo ""
        echo -e "${YELLOW}Deployment in progress...${NC}"
        echo "Press Ctrl+C to stop monitoring"
    fi
    
    sleep 10
done
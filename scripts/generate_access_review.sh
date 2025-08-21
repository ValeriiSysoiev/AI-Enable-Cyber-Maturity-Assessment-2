#!/bin/bash
# Generate Access Review Report for Compliance

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
OUTPUT_DIR="${OUTPUT_DIR:-./access-reviews}"
ENGAGEMENT_ID="${1:-}"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Create output directory
mkdir -p "$OUTPUT_DIR"

generate_review_report() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local report_file="$OUTPUT_DIR/access-review-$timestamp.json"
    
    log_info "Generating access review report..."
    
    # API endpoint for export
    local api_endpoint="$API_BASE_URL/admin/access-reviews/export"
    if [[ -n "$ENGAGEMENT_ID" ]]; then
        api_endpoint="$api_endpoint?engagement_id=$ENGAGEMENT_ID"
    fi
    
    # Generate JSON report
    if curl -s -f "$api_endpoint" > "$report_file" 2>/dev/null; then
        log_info "Access review report generated: $report_file"
        
        # Also generate CSV version
        local csv_file="$OUTPUT_DIR/access-review-$timestamp.csv"
        curl -s -f "$api_endpoint&format=csv" | jq -r '.data' > "$csv_file" 2>/dev/null || true
        
        if [[ -f "$csv_file" ]] && [[ -s "$csv_file" ]]; then
            log_info "CSV report generated: $csv_file"
        fi
        
        # Generate summary
        generate_summary "$report_file"
        
    else
        log_warn "Failed to generate access review report"
        log_warn "Ensure API is running at $API_BASE_URL"
        return 1
    fi
}

generate_summary() {
    local report_file="$1"
    local summary_file="${report_file%.json}_summary.txt"
    
    log_info "Generating access review summary..."
    
    {
        echo "ACCESS REVIEW SUMMARY"
        echo "===================="
        echo "Generated: $(date -u)"
        echo ""
        
        if command -v jq >/dev/null 2>&1; then
            echo "Review Period:"
            jq -r '.review_period | "Start: \(.start)\nEnd: \(.end)"' "$report_file" 2>/dev/null || echo "N/A"
            echo ""
            
            echo "Engagements Summary:"
            local total_engagements=$(jq '.engagements | length' "$report_file" 2>/dev/null || echo "0")
            echo "Total Engagements: $total_engagements"
            
            if [[ "$total_engagements" -gt 0 ]]; then
                echo ""
                echo "Engagement Details:"
                jq -r '.engagements[] | "- \(.engagement_id): \(.client_name) (\(.members | length) members)"' "$report_file" 2>/dev/null || echo "N/A"
                
                echo ""
                echo "Member Statistics:"
                local total_members=$(jq '[.engagements[].members | length] | add' "$report_file" 2>/dev/null || echo "0")
                echo "Total Active Members: $total_members"
            fi
        else
            echo "jq not available - raw report in $report_file"
        fi
        
        echo ""
        echo "Action Items:"
        echo "- Review member access for each engagement"
        echo "- Verify roles and permissions are appropriate" 
        echo "- Remove inactive or unnecessary access"
        echo "- Update next review schedule"
        
    } > "$summary_file"
    
    log_info "Summary generated: $summary_file"
    cat "$summary_file"
}

# Main execution
main() {
    echo "🔍 Access Review Generator"
    echo "========================="
    
    if [[ -n "$ENGAGEMENT_ID" ]]; then
        echo "Scope: Engagement $ENGAGEMENT_ID"
    else
        echo "Scope: All engagements"
    fi
    echo ""
    
    generate_review_report
    
    echo ""
    log_info "Access review generation complete"
    log_info "Reports saved to: $OUTPUT_DIR"
}

main "$@"
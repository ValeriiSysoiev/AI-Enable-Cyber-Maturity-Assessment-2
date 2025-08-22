#!/bin/bash

# Go-Live Pre-flight Check Script
# Validates all requirements for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts/verify"

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Check results tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Log check result
log_check() {
    local status="$1"
    local message="$2"
    
    case "$status" in
        "PASS")
            log_success "$message"
            ((CHECKS_PASSED++))
            ;;
        "FAIL")
            log_error "$message"
            ((CHECKS_FAILED++))
            ;;
        "WARN")
            log_warning "$message"
            ((CHECKS_WARNING++))
            ;;
    esac
}

# Check CI/CD pipeline status
check_ci_status() {
    log_info "Checking CI/CD pipeline status..."
    
    if command -v gh >/dev/null 2>&1; then
        # Check latest workflow runs
        local latest_run_status
        latest_run_status=$(gh run list --limit 1 --json status --jq '.[0].status' 2>/dev/null || echo "unknown")
        
        if [[ "$latest_run_status" == "completed" ]]; then
            local latest_run_conclusion
            latest_run_conclusion=$(gh run list --limit 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null || echo "unknown")
            
            if [[ "$latest_run_conclusion" == "success" ]]; then
                log_check "PASS" "Latest CI/CD run successful"
            else
                log_check "FAIL" "Latest CI/CD run failed: $latest_run_conclusion"
            fi
        else
            log_check "WARN" "CI/CD pipeline status: $latest_run_status"
        fi
    else
        log_check "WARN" "GitHub CLI not available - cannot check CI status"
    fi
}

# Check staging verification
check_staging_verification() {
    log_info "Checking staging environment verification..."
    
    if [[ -x "./scripts/verify_live.sh" ]]; then
        # Run staging verification
        if ./scripts/verify_live.sh --staging >/dev/null 2>&1; then
            log_check "PASS" "Staging verification passed"
        else
            log_check "FAIL" "Staging verification failed"
        fi
    else
        log_check "FAIL" "Verification script not found or not executable"
    fi
}

# Check access review export
check_access_review() {
    log_info "Checking access review export availability..."
    
    # Look for recent access review exports
    local export_found=false
    
    # Check common locations
    local export_locations=(
        "./artifacts/access-review"
        "./exports/access-review"
        "./reports/access-review"
    )
    
    for location in "${export_locations[@]}"; do
        if [[ -d "$location" ]]; then
            local recent_exports
            recent_exports=$(find "$location" -type f -name "*.json" -o -name "*.csv" -o -name "*.xlsx" -mtime -7 2>/dev/null | wc -l)
            
            if [[ $recent_exports -gt 0 ]]; then
                export_found=true
                log_check "PASS" "Access review export found ($recent_exports files in $location)"
                break
            fi
        fi
    done
    
    if [[ "$export_found" != "true" ]]; then
        log_check "WARN" "No recent access review export found"
    fi
}

# Check incident drill completion
check_incident_drill() {
    log_info "Checking incident drill completion..."
    
    if [[ -x "./scripts/drill_incident.sh" ]]; then
        # Check if incident drill can be executed
        if ./scripts/drill_incident.sh general --dry-run >/dev/null 2>&1; then
            log_check "PASS" "Incident drill script operational"
        else
            log_check "WARN" "Incident drill script issues detected"
        fi
    else
        log_check "WARN" "Incident drill script not found"
    fi
    
    # Check for recent drill artifacts
    if [[ -d "./artifacts/verify" ]]; then
        local drill_logs
        drill_logs=$(find "./artifacts/verify" -name "*incident*" -o -name "*drill*" -mtime -30 2>/dev/null | wc -l)
        
        if [[ $drill_logs -gt 0 ]]; then
            log_check "PASS" "Recent incident drill artifacts found"
        else
            log_check "WARN" "No recent incident drill artifacts found"
        fi
    fi
}

# Check production environment variables
check_production_config() {
    log_info "Checking production environment configuration..."
    
    # Check if production variables are documented
    if [[ -f "./docs/prod-env.md" ]]; then
        log_check "PASS" "Production environment documentation found"
    else
        log_check "FAIL" "Production environment documentation missing"
    fi
    
    # Check if production workflow exists
    if [[ -f "./.github/workflows/deploy_production.yml" ]]; then
        log_check "PASS" "Production deployment workflow found"
    else
        log_check "WARN" "Production deployment workflow not found"
    fi
    
    # Check if production verification is available
    if grep -q "\-\-prod" "./scripts/verify_live.sh" 2>/dev/null; then
        log_check "PASS" "Production verification mode available"
    else
        log_check "FAIL" "Production verification mode not available"
    fi
}

# Check monitoring and alerting
check_monitoring() {
    log_info "Checking monitoring and alerting setup..."
    
    # Check for monitoring documentation
    if [[ -f "./docs/monitoring-alerts.md" ]]; then
        log_check "PASS" "Monitoring documentation found"
    else
        log_check "WARN" "Monitoring documentation not found"
    fi
    
    # Check for health check endpoints in application code
    if grep -r "health" "./app" >/dev/null 2>&1 || grep -r "health" "./web" >/dev/null 2>&1; then
        log_check "PASS" "Health check endpoints present in application"
    else
        log_check "WARN" "Health check endpoints not clearly defined"
    fi
}

# Check security requirements
check_security() {
    log_info "Checking security requirements..."
    
    # Check for security scan artifacts
    if [[ -d "./artifacts/verify" ]]; then
        local security_logs
        security_logs=$(find "./artifacts/verify" -name "*security*" -o -name "*scan*" -mtime -7 2>/dev/null | wc -l)
        
        if [[ $security_logs -gt 0 ]]; then
            log_check "PASS" "Recent security scan artifacts found"
        else
            log_check "WARN" "No recent security scan artifacts found"
        fi
    fi
    
    # Check for GDPR/compliance documentation
    if grep -r "GDPR\|gdpr" "./docs" >/dev/null 2>&1 || grep -r "compliance" "./docs" >/dev/null 2>&1; then
        log_check "PASS" "Compliance documentation present"
    else
        log_check "WARN" "Limited compliance documentation found"
    fi
}

# Check rollback capability
check_rollback() {
    log_info "Checking rollback capability..."
    
    if [[ -x "./scripts/rollback_to_previous.sh" ]]; then
        log_check "PASS" "Rollback script available"
    else
        log_check "FAIL" "Rollback script not found or not executable"
    fi
    
    # Check if rollback procedures are documented
    if grep -r "rollback\|Rollback" "./docs" >/dev/null 2>&1; then
        log_check "PASS" "Rollback procedures documented"
    else
        log_check "WARN" "Rollback procedures not clearly documented"
    fi
}

# Generate summary report
generate_summary() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo
    echo "=================================="
    echo "Go-Live Pre-flight Check Summary"
    echo "=================================="
    echo "Timestamp: $timestamp"
    echo
    echo "Check Results:"
    echo "  ✅ Passed: $CHECKS_PASSED"
    echo "  ⚠️  Warnings: $CHECKS_WARNING"
    echo "  ❌ Failed: $CHECKS_FAILED"
    echo
    
    local total_checks=$((CHECKS_PASSED + CHECKS_WARNING + CHECKS_FAILED))
    local pass_rate=0
    if [[ $total_checks -gt 0 ]]; then
        pass_rate=$(( (CHECKS_PASSED * 100) / total_checks ))
    fi
    
    echo "Pass Rate: ${pass_rate}%"
    echo
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        if [[ $CHECKS_WARNING -eq 0 ]]; then
            log_success "GO-LIVE READY: All checks passed"
            echo "🚀 System ready for production deployment"
        else
            log_warning "GO-LIVE CONDITIONAL: $CHECKS_WARNING warnings to review"
            echo "⚠️  Review warnings before proceeding with production deployment"
        fi
    else
        log_error "GO-LIVE BLOCKED: $CHECKS_FAILED critical issues"
        echo "❌ Resolve failed checks before production deployment"
        echo
        echo "Required Actions:"
        echo "1. Address all failed checks"
        echo "2. Re-run go-live check"
        echo "3. Obtain stakeholder approval"
        echo "4. Proceed with deployment only after all checks pass"
    fi
    
    echo
    echo "Next Steps:"
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo "1. Review and address any warnings"
        echo "2. Obtain final stakeholder approvals"
        echo "3. Execute production deployment"
        echo "4. Run post-deployment verification"
    else
        echo "1. Fix all failed checks"
        echo "2. Re-run this script: ./scripts/go_live_check.sh"
        echo "3. Ensure staging environment is stable"
        echo "4. Contact technical lead for guidance"
    fi
    
    echo "=================================="
}

# Save artifacts
save_artifacts() {
    mkdir -p "$ARTIFACTS_DIR"
    
    {
        echo "Go-Live Pre-flight Check Results"
        echo "Generated: $(date)"
        echo ""
        echo "Passed: $CHECKS_PASSED"
        echo "Warnings: $CHECKS_WARNING"
        echo "Failed: $CHECKS_FAILED"
        echo ""
        echo "Overall Status: $(if [[ $CHECKS_FAILED -eq 0 ]]; then echo "READY"; else echo "BLOCKED"; fi)"
    } > "$ARTIFACTS_DIR/go_live_check.log"
    
    log_info "Results saved to: $ARTIFACTS_DIR/go_live_check.log"
}

# Main execution
main() {
    echo "=== Go-Live Pre-flight Check ==="
    echo
    
    check_ci_status
    check_staging_verification
    check_access_review
    check_incident_drill
    check_production_config
    check_monitoring
    check_security
    check_rollback
    
    generate_summary
    save_artifacts
    
    # Exit with error code if any checks failed
    if [[ $CHECKS_FAILED -gt 0 ]]; then
        exit 1
    elif [[ $CHECKS_WARNING -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# Run main function
main "$@"
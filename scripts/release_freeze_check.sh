#!/bin/bash

# Release Freeze Check Script
# Validates all release gates and generates go/no-go decision report
# Usage: ./scripts/release_freeze_check.sh [--verbose] [--environment staging|production]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERBOSE=false
ENVIRONMENT="staging"
REPORT_FILE="$PROJECT_ROOT/artifacts/release-freeze-report.md"

# Gate status tracking
GATE_RESULTS=()
TOTAL_GATES=0
PASSED_GATES=0
FAILED_GATES=0

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --verbose              Enable verbose output"
    echo "  --environment ENV      Target environment (staging|production)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Check staging environment"
    echo "  $0 --environment production           # Check production readiness"
    echo "  $0 --verbose --environment staging    # Verbose staging check"
}

# Logging functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

verbose_log() {
    if [[ "$VERBOSE" == "true" ]]; then
        log_info "$1"
    fi
}

# Gate result tracking
record_gate_result() {
    local gate_name="$1"
    local status="$2"
    local details="$3"
    
    TOTAL_GATES=$((TOTAL_GATES + 1))
    
    if [[ "$status" == "PASS" ]]; then
        PASSED_GATES=$((PASSED_GATES + 1))
        log_success "Gate: $gate_name"
    else
        FAILED_GATES=$((FAILED_GATES + 1))
        log_error "Gate: $gate_name - $details"
    fi
    
    GATE_RESULTS+=("$gate_name|$status|$details")
    
    verbose_log "Recorded gate result: $gate_name = $status"
}

# Initialize report
initialize_report() {
    mkdir -p "$(dirname "$REPORT_FILE")"
    
    cat > "$REPORT_FILE" << EOF
# Release Freeze Check Report

**Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')  
**Environment:** $ENVIRONMENT  
**Project:** AI-Enable Cyber Maturity Assessment v2  
**Commit:** $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")  

---

## Executive Summary

EOF
}

# Quality Gates
check_ci_status() {
    log_info "Checking CI/CD pipeline status..."
    
    local ci_status="unknown"
    local details=""
    
    # Check GitHub Actions status if available
    if command -v gh >/dev/null 2>&1; then
        verbose_log "Checking GitHub Actions workflow status..."
        
        local workflow_status
        workflow_status=$(gh run list --limit 1 --json status,conclusion 2>/dev/null || echo "[]")
        
        if [[ "$workflow_status" != "[]" ]]; then
            local last_status
            last_status=$(echo "$workflow_status" | jq -r '.[0].status' 2>/dev/null || echo "unknown")
            local last_conclusion
            last_conclusion=$(echo "$workflow_status" | jq -r '.[0].conclusion' 2>/dev/null || echo "unknown")
            
            if [[ "$last_status" == "completed" && "$last_conclusion" == "success" ]]; then
                ci_status="PASS"
                details="Latest workflow completed successfully"
            else
                ci_status="FAIL"
                details="Latest workflow status: $last_status, conclusion: $last_conclusion"
            fi
        else
            ci_status="WARN"
            details="No recent workflow runs found"
        fi
    else
        ci_status="WARN"
        details="GitHub CLI not available - manual verification required"
    fi
    
    record_gate_result "CI/CD Pipeline" "$ci_status" "$details"
}

check_test_coverage() {
    log_info "Checking test coverage..."
    
    local coverage_status="WARN"
    local details="Test coverage check requires manual verification"
    
    # Look for coverage reports
    if [[ -f "$PROJECT_ROOT/coverage/lcov.info" ]]; then
        verbose_log "Found coverage report at coverage/lcov.info"
        coverage_status="PASS"
        details="Coverage report found - manual review required"
    elif [[ -f "$PROJECT_ROOT/.coverage" ]]; then
        verbose_log "Found Python coverage report"
        coverage_status="PASS"
        details="Python coverage report found - manual review required"
    elif [[ -d "$PROJECT_ROOT/htmlcov" ]]; then
        verbose_log "Found HTML coverage report"
        coverage_status="PASS"
        details="HTML coverage report found - manual review required"
    fi
    
    record_gate_result "Test Coverage" "$coverage_status" "$details"
}

check_security_scan() {
    log_info "Checking security scan results..."
    
    local security_status="PASS"
    local details=""
    local issues_found=0
    
    # Run security scan if script exists
    if [[ -x "$PROJECT_ROOT/scripts/security_scan.sh" ]]; then
        verbose_log "Running security scan..."
        
        if "$PROJECT_ROOT/scripts/security_scan.sh" >/tmp/security_scan.log 2>&1; then
            security_status="PASS"
            details="Security scan completed successfully"
        else
            security_status="FAIL"
            details="Security scan found issues - see /tmp/security_scan.log"
            issues_found=1
        fi
    else
        security_status="WARN"
        details="Security scan script not found - manual verification required"
    fi
    
    record_gate_result "Security Scan" "$security_status" "$details"
}

check_dependency_vulnerabilities() {
    log_info "Checking dependency vulnerabilities..."
    
    local vuln_status="PASS"
    local details=""
    
    # Check npm vulnerabilities if package.json exists
    if [[ -f "$PROJECT_ROOT/package.json" ]] && command -v npm >/dev/null 2>&1; then
        verbose_log "Checking npm vulnerabilities..."
        
        if npm audit --audit-level high >/tmp/npm_audit.log 2>&1; then
            vuln_status="PASS"
            details="No high/critical npm vulnerabilities found"
        else
            vuln_status="FAIL"
            details="High/critical npm vulnerabilities found - see /tmp/npm_audit.log"
        fi
    elif [[ -f "$PROJECT_ROOT/requirements.txt" ]] && command -v pip >/dev/null 2>&1; then
        verbose_log "Checking Python package vulnerabilities..."
        
        if command -v safety >/dev/null 2>&1; then
            if safety check >/tmp/safety_check.log 2>&1; then
                vuln_status="PASS"
                details="No known Python package vulnerabilities"
            else
                vuln_status="FAIL"
                details="Python package vulnerabilities found - see /tmp/safety_check.log"
            fi
        else
            vuln_status="WARN"
            details="Safety tool not installed - manual verification required"
        fi
    else
        vuln_status="WARN"
        details="No package files found or package managers unavailable"
    fi
    
    record_gate_result "Dependency Vulnerabilities" "$vuln_status" "$details"
}

# Operational Gates
check_environment_health() {
    log_info "Checking environment health..."
    
    local health_status="PASS"
    local details=""
    
    # Run live verification if script exists
    if [[ -x "$PROJECT_ROOT/scripts/verify_live.sh" ]]; then
        verbose_log "Running environment health check..."
        
        local verify_args=""
        if [[ "$ENVIRONMENT" == "staging" ]]; then
            verify_args="--staging"
        fi
        
        if "$PROJECT_ROOT/scripts/verify_live.sh" $verify_args >/tmp/health_check.log 2>&1; then
            health_status="PASS"
            details="Environment health check passed"
        else
            health_status="FAIL"
            details="Environment health check failed - see /tmp/health_check.log"
        fi
    else
        health_status="WARN"
        details="Health check script not found - manual verification required"
    fi
    
    record_gate_result "Environment Health" "$health_status" "$details"
}

check_access_review() {
    log_info "Checking access review status..."
    
    local access_status="WARN"
    local details="Access review requires manual verification"
    
    # Check if access review script exists and run it
    if [[ -x "$PROJECT_ROOT/scripts/access_reviews.sh" ]]; then
        verbose_log "Running access review check..."
        
        if "$PROJECT_ROOT/scripts/access_reviews.sh" --dry-run >/tmp/access_review.log 2>&1; then
            access_status="PASS"
            details="Access review checks passed"
        else
            access_status="WARN"
            details="Access review checks incomplete - manual verification required"
        fi
    fi
    
    record_gate_result "Access Review" "$access_status" "$details"
}

check_incident_drill() {
    log_info "Checking incident response drill status..."
    
    local drill_status="WARN"
    local details="Incident drill requires manual verification"
    
    # Check if incident drill script exists
    if [[ -x "$PROJECT_ROOT/scripts/drill_incident.sh" ]]; then
        verbose_log "Running incident drill validation..."
        
        if "$PROJECT_ROOT/scripts/drill_incident.sh" general --dry-run >/tmp/incident_drill.log 2>&1; then
            drill_status="PASS"
            details="Incident response drill validation passed"
        else
            drill_status="WARN"
            details="Incident drill validation incomplete"
        fi
    fi
    
    record_gate_result "Incident Response Drill" "$drill_status" "$details"
}

# Documentation and Configuration Gates
check_release_documentation() {
    log_info "Checking release documentation..."
    
    local docs_status="PASS"
    local details=""
    local missing_docs=()
    
    # Check for required documentation
    local required_docs=(
        "README.md"
        "CHANGELOG.md"
        "docs/release-freeze.md"
        "docs/deployment.md"
    )
    
    for doc in "${required_docs[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$doc" ]]; then
            missing_docs+=("$doc")
        fi
    done
    
    if [[ ${#missing_docs[@]} -eq 0 ]]; then
        docs_status="PASS"
        details="All required documentation present"
    else
        docs_status="FAIL"
        details="Missing documentation: ${missing_docs[*]}"
    fi
    
    record_gate_result "Release Documentation" "$docs_status" "$details"
}

check_configuration_validation() {
    log_info "Checking configuration validation..."
    
    local config_status="PASS"
    local details=""
    
    # Check environment configuration files
    local env_configs=()
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        env_configs=("env/staging.example" ".env.staging")
    else
        env_configs=("env/production.example" ".env.production")
    fi
    
    local missing_configs=()
    for config in "${env_configs[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$config" ]]; then
            missing_configs+=("$config")
        fi
    done
    
    if [[ ${#missing_configs[@]} -eq 0 ]]; then
        config_status="PASS"
        details="Configuration files present"
    else
        config_status="WARN"
        details="Missing configuration files: ${missing_configs[*]}"
    fi
    
    record_gate_result "Configuration Validation" "$config_status" "$details"
}

# Generate comprehensive report
generate_report() {
    log_info "Generating release freeze report..."
    
    # Calculate pass rate
    local pass_rate=0
    if [[ $TOTAL_GATES -gt 0 ]]; then
        pass_rate=$(( (PASSED_GATES * 100) / TOTAL_GATES ))
    fi
    
    # Determine overall status
    local overall_status="NO-GO"
    local recommendation=""
    
    if [[ $FAILED_GATES -eq 0 ]]; then
        if [[ $pass_rate -ge 90 ]]; then
            overall_status="GO"
            recommendation="✅ **RECOMMENDATION: APPROVED FOR RELEASE**"
        else
            overall_status="CONDITIONAL GO"
            recommendation="⚠️ **RECOMMENDATION: CONDITIONAL APPROVAL - Address warnings before release**"
        fi
    else
        overall_status="NO-GO"
        recommendation="🔴 **RECOMMENDATION: RELEASE BLOCKED - Critical issues must be resolved**"
    fi
    
    # Append summary to report
    cat >> "$REPORT_FILE" << EOF
**Overall Status:** $overall_status  
**Pass Rate:** $pass_rate% ($PASSED_GATES/$TOTAL_GATES gates passed)  
**Failed Gates:** $FAILED_GATES  

$recommendation

---

## Gate Results Summary

| Gate | Status | Details |
|------|--------|---------|
EOF
    
    # Add gate results to report
    for result in "${GATE_RESULTS[@]}"; do
        IFS='|' read -r gate_name status details <<< "$result"
        local status_icon="❌"
        if [[ "$status" == "PASS" ]]; then
            status_icon="✅"
        elif [[ "$status" == "WARN" ]]; then
            status_icon="⚠️"
        fi
        
        echo "| $gate_name | $status_icon $status | $details |" >> "$REPORT_FILE"
    done
    
    # Add detailed sections
    cat >> "$REPORT_FILE" << EOF

---

## Detailed Results

### Quality Gates
EOF
    
    # Add quality gate details
    for result in "${GATE_RESULTS[@]}"; do
        IFS='|' read -r gate_name status details <<< "$result"
        if [[ "$gate_name" =~ (CI/CD|Test|Security|Dependency) ]]; then
            cat >> "$REPORT_FILE" << EOF

#### $gate_name
**Status:** $status  
**Details:** $details  
EOF
        fi
    done
    
    cat >> "$REPORT_FILE" << EOF

### Operational Gates
EOF
    
    # Add operational gate details
    for result in "${GATE_RESULTS[@]}"; do
        IFS='|' read -r gate_name status details <<< "$result"
        if [[ "$gate_name" =~ (Environment|Access|Incident) ]]; then
            cat >> "$REPORT_FILE" << EOF

#### $gate_name
**Status:** $status  
**Details:** $details  
EOF
        fi
    done
    
    cat >> "$REPORT_FILE" << EOF

### Documentation and Configuration Gates
EOF
    
    # Add documentation gate details
    for result in "${GATE_RESULTS[@]}"; do
        IFS='|' read -r gate_name status details <<< "$result"
        if [[ "$gate_name" =~ (Documentation|Configuration) ]]; then
            cat >> "$REPORT_FILE" << EOF

#### $gate_name
**Status:** $status  
**Details:** $details  
EOF
        fi
    done
    
    # Add next steps
    cat >> "$REPORT_FILE" << EOF

---

## Next Steps

EOF
    
    if [[ "$overall_status" == "GO" ]]; then
        cat >> "$REPORT_FILE" << EOF
### Ready for Release ✅
- [ ] Final stakeholder sign-offs
- [ ] Schedule deployment window
- [ ] Prepare monitoring and support teams
- [ ] Execute deployment plan
EOF
    elif [[ "$overall_status" == "CONDITIONAL GO" ]]; then
        cat >> "$REPORT_FILE" << EOF
### Conditional Release Approval ⚠️
- [ ] Address warning conditions identified above
- [ ] Re-run release freeze check
- [ ] Obtain final stakeholder approval
- [ ] Proceed with deployment if conditions met
EOF
    else
        cat >> "$REPORT_FILE" << EOF
### Release Blocked 🔴
- [ ] Resolve all failed gate conditions
- [ ] Re-run affected tests and validations
- [ ] Schedule new go/no-go decision meeting
- [ ] Consider release timeline impact
EOF
    fi
    
    cat >> "$REPORT_FILE" << EOF

---

**Report Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')  
**Environment:** $ENVIRONMENT  
**Total Gates Checked:** $TOTAL_GATES  
**Overall Recommendation:** $overall_status  
EOF
}

# Main execution
main() {
    echo "=== Release Freeze Check ==="
    echo "Environment: $ENVIRONMENT"
    echo "Verbose: $VERBOSE"
    echo
    
    # Initialize report
    initialize_report
    
    # Run all gate checks
    log_info "Running quality gates..."
    check_ci_status
    check_test_coverage
    check_security_scan
    check_dependency_vulnerabilities
    
    echo
    log_info "Running operational gates..."
    check_environment_health
    check_access_review
    check_incident_drill
    
    echo
    log_info "Running documentation and configuration gates..."
    check_release_documentation
    check_configuration_validation
    
    echo
    
    # Generate final report
    generate_report
    
    # Display summary
    echo "=== Release Freeze Check Summary ==="
    echo "Total Gates: $TOTAL_GATES"
    echo "Passed: $PASSED_GATES"
    echo "Failed: $FAILED_GATES"
    echo "Pass Rate: $(( (PASSED_GATES * 100) / TOTAL_GATES ))%"
    echo
    echo "Report saved to: $REPORT_FILE"
    
    # Exit with appropriate code
    if [[ $FAILED_GATES -gt 0 ]]; then
        log_error "Release freeze check failed - $FAILED_GATES critical gates failed"
        exit 1
    elif [[ $(( (PASSED_GATES * 100) / TOTAL_GATES )) -lt 90 ]]; then
        log_warning "Release freeze check completed with warnings"
        exit 2
    else
        log_success "Release freeze check passed - ready for deployment"
        exit 0
    fi
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi
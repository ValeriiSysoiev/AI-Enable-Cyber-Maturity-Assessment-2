#!/bin/bash
# Security scanning script for local and CI use

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if docs-only change
check_docs_only() {
    local changed_files
    changed_files=$(git diff --name-only HEAD~1 2>/dev/null || git diff --name-only main 2>/dev/null || echo "")
    
    if [[ -z "$changed_files" ]]; then
        return 1
    fi
    
    for file in $changed_files; do
        if [[ ! "$file" =~ \.(md|txt)$ ]] && [[ ! "$file" =~ ^docs/ ]]; then
            return 1
        fi
    done
    
    log_info "Docs-only changes detected - fast pass enabled"
    return 0
}

# Secret scanning
run_secret_scan() {
    log_info "Running secret scan..."
    
    if command -v trufflehog >/dev/null 2>&1; then
        trufflehog filesystem . --only-verified --json 2>/dev/null | \
            jq -r 'select(.SourceMetadata.Data.Filesystem.file != null) | .SourceMetadata.Data.Filesystem.file' | \
            sort -u > /tmp/secrets_found.txt || true
        
        if [[ -s /tmp/secrets_found.txt ]]; then
            log_error "Secrets detected in:"
            cat /tmp/secrets_found.txt
            return 1
        fi
        log_info "✅ No secrets detected"
    else
        log_warn "TruffleHog not installed - skipping secret scan"
    fi
}

# Dependency vulnerability scan
run_sca_scan() {
    log_info "Running dependency vulnerability scan..."
    
    if command -v trivy >/dev/null 2>&1; then
        trivy fs . --severity HIGH,CRITICAL --exit-code 1 2>/dev/null || {
            log_error "High/Critical vulnerabilities found"
            return 1
        }
        log_info "✅ No high/critical vulnerabilities"
    else
        log_warn "Trivy not installed - skipping SCA scan"
    fi
}

# IaC security scan
run_iac_scan() {
    log_info "Running IaC security scan..."
    
    if command -v checkov >/dev/null 2>&1; then
        checkov -d . --framework terraform,dockerfile,kubernetes \
            --quiet --compact --skip-check CKV_DOCKER_2,CKV_DOCKER_3 || {
            log_error "IaC security issues found"
            return 1
        }
        log_info "✅ IaC security checks passed"
    else
        log_warn "Checkov not installed - skipping IaC scan"
    fi
}

# Main execution
main() {
    echo "🔒 Security Gates Check"
    echo "======================="
    
    # Check for docs-only changes
    if check_docs_only; then
        log_info "Fast-pass granted for documentation changes"
        exit 0
    fi
    
    local failed=0
    
    run_secret_scan || ((failed++))
    run_sca_scan || ((failed++))
    run_iac_scan || ((failed++))
    
    echo ""
    if [[ $failed -gt 0 ]]; then
        log_error "Security gates failed: $failed check(s) did not pass"
        exit 1
    else
        log_info "🎉 All security gates passed!"
    fi
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
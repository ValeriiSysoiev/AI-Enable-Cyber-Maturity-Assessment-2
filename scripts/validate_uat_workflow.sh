#!/bin/bash

# UAT Explorer GitHub Actions Workflow Validation Script
# Validates the setup and configuration of the UAT Explorer workflow

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
WORKFLOW_FILE="$PROJECT_ROOT/.github/workflows/uat-explorer.yml"

# Functions
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Validation functions
validate_workflow_file() {
    log_info "Validating UAT Explorer workflow file..."
    
    if [[ ! -f "$WORKFLOW_FILE" ]]; then
        log_error "UAT Explorer workflow file not found: $WORKFLOW_FILE"
        return 1
    fi
    
    log_success "Workflow file exists"
    
    # Validate YAML syntax
    if command -v yq >/dev/null 2>&1; then
        if yq eval '.' "$WORKFLOW_FILE" >/dev/null 2>&1; then
            log_success "Workflow YAML syntax is valid"
        else
            log_error "Workflow YAML syntax is invalid"
            return 1
        fi
    else
        log_warning "yq not installed - skipping YAML syntax validation"
    fi
    
    # Check required sections
    local required_sections=("on" "permissions" "env" "jobs")
    for section in "${required_sections[@]}"; do
        if grep -q "^${section}:" "$WORKFLOW_FILE"; then
            log_success "Required section '$section' found"
        else
            log_error "Required section '$section' missing"
            return 1
        fi
    done
    
    return 0
}

validate_web_dependencies() {
    log_info "Validating web application dependencies..."
    
    local web_dir="$PROJECT_ROOT/web"
    
    if [[ ! -f "$web_dir/package.json" ]]; then
        log_error "Web package.json not found"
        return 1
    fi
    
    log_success "Web package.json found"
    
    # Check for required dependencies
    local required_deps=("@playwright/test" "@octokit/rest")
    for dep in "${required_deps[@]}"; do
        if jq -e ".devDependencies.\"$dep\" // .dependencies.\"$dep\"" "$web_dir/package.json" >/dev/null 2>&1; then
            log_success "Required dependency '$dep' found"
        else
            log_error "Required dependency '$dep' missing"
            return 1
        fi
    done
    
    # Check for UAT test scripts
    local required_scripts=("test:e2e:uat" "test:e2e:uat:demo" "test:e2e:uat:production" "test:e2e:uat:validate")
    for script in "${required_scripts[@]}"; do
        if jq -e ".scripts.\"$script\"" "$web_dir/package.json" >/dev/null 2>&1; then
            log_success "Required script '$script' found"
        else
            log_error "Required script '$script' missing"
            return 1
        fi
    done
    
    return 0
}

validate_uat_explorer_files() {
    log_info "Validating UAT Explorer files..."
    
    local web_dir="$PROJECT_ROOT/web"
    local required_files=(
        "e2e/tests/uat-explorer.spec.ts"
        "e2e/reporters/uat-reporter.ts"
        "e2e/utils/github-issue-manager.ts"
        "e2e/UAT_EXPLORER.md"
        "scripts/validate-uat-setup.js"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$web_dir/$file" ]]; then
            log_success "UAT file '$file' exists"
        else
            log_error "UAT file '$file' missing"
            return 1
        fi
    done
    
    return 0
}

validate_playwright_config() {
    log_info "Validating Playwright configuration..."
    
    local web_dir="$PROJECT_ROOT/web"
    local config_file="$web_dir/playwright.config.ts"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Playwright config not found: $config_file"
        return 1
    fi
    
    log_success "Playwright config exists"
    
    # Check for UAT project configuration
    if grep -q "uat-explorer" "$config_file"; then
        log_success "UAT Explorer project configured in Playwright"
    else
        log_warning "UAT Explorer project not found in Playwright config"
    fi
    
    return 0
}

validate_environment_variables() {
    log_info "Validating required environment variables..."
    
    # Check for variables used in workflow
    local workflow_vars=(
        "STAGING_URL"
        "PRODUCTION_URL"
        "AZURE_SUBSCRIPTION_ID"
        "AZURE_TENANT_ID"
        "AZURE_CLIENT_ID"
    )
    
    log_info "Checking GitHub repository variables (these should be set in repository settings):"
    for var in "${workflow_vars[@]}"; do
        log_info "  - $var (set in GitHub repository variables)"
    done
    
    # Check local environment for testing
    local local_vars=(
        "WEB_BASE_URL"
        "DEMO_E2E"
        "UAT_HEADLESS"
    )
    
    log_info "Local testing environment variables:"
    for var in "${local_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_success "  - $var is set locally"
        else
            log_info "  - $var not set (optional for testing)"
        fi
    done
    
    return 0
}

validate_github_integration() {
    log_info "Validating GitHub integration setup..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        log_error "Not in a git repository"
        return 1
    fi
    
    log_success "Git repository detected"
    
    # Check for remote origin
    if git remote -v | grep -q origin; then
        local origin_url
        origin_url=$(git remote get-url origin 2>/dev/null || echo "")
        log_success "Git remote origin configured: $origin_url"
    else
        log_warning "Git remote origin not configured"
    fi
    
    # Check workflow permissions
    if grep -q "issues: write" "$WORKFLOW_FILE"; then
        log_success "GitHub issues permission configured"
    else
        log_error "GitHub issues permission missing"
        return 1
    fi
    
    return 0
}

validate_artifact_directories() {
    log_info "Validating artifact directories..."
    
    local web_dir="$PROJECT_ROOT/web"
    local artifacts_dir="$web_dir/artifacts"
    
    # Check if artifacts directory structure can be created
    if mkdir -p "$artifacts_dir/uat" 2>/dev/null; then
        log_success "Artifacts directory structure created"
        
        # Test write permissions
        if touch "$artifacts_dir/uat/test-file" 2>/dev/null; then
            rm -f "$artifacts_dir/uat/test-file"
            log_success "Artifacts directory writable"
        else
            log_error "Artifacts directory not writable"
            return 1
        fi
    else
        log_error "Cannot create artifacts directory structure"
        return 1
    fi
    
    return 0
}

run_uat_setup_validation() {
    log_info "Running UAT setup validation..."
    
    local web_dir="$PROJECT_ROOT/web"
    
    if [[ -f "$web_dir/scripts/validate-uat-setup.js" ]]; then
        cd "$web_dir"
        if node scripts/validate-uat-setup.js; then
            log_success "UAT setup validation passed"
            return 0
        else
            log_error "UAT setup validation failed"
            return 1
        fi
    else
        log_warning "UAT setup validation script not found"
        return 0
    fi
}

test_github_issue_integration() {
    log_info "Testing GitHub issue manager integration..."
    
    local web_dir="$PROJECT_ROOT/web"
    
    if [[ -f "$web_dir/e2e/utils/test-github-integration.js" ]]; then
        cd "$web_dir"
        if node e2e/utils/test-github-integration.js; then
            log_success "GitHub issue integration test passed"
        else
            log_warning "GitHub issue integration test failed (may be expected without GitHub token)"
        fi
    else
        log_warning "GitHub issue integration test not found"
    fi
}

generate_validation_report() {
    log_info "Generating validation report..."
    
    local report_file="$PROJECT_ROOT/artifacts/uat-workflow-validation.md"
    mkdir -p "$(dirname "$report_file")"
    
    cat > "$report_file" <<EOF
# UAT Explorer Workflow Validation Report

**Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')
**Script:** $(basename "$0")

## Validation Results

### ✓ Completed Checks

- GitHub Actions workflow file syntax and structure
- Web application dependencies and scripts
- UAT Explorer test files and configuration
- Playwright configuration
- Environment variable requirements
- GitHub repository integration
- Artifact directory permissions

### Configuration Requirements

#### Repository Variables (Set in GitHub Settings)

- \`STAGING_URL\`: URL for staging environment testing
- \`PRODUCTION_URL\`: URL for production environment testing  
- \`AZURE_SUBSCRIPTION_ID\`: Azure subscription for authentication
- \`AZURE_TENANT_ID\`: Azure tenant for authentication
- \`AZURE_CLIENT_ID\`: Azure client ID for authentication
- \`UAT_GITHUB_ASSIGNEES\`: Comma-separated list of GitHub users for issue assignment

#### Repository Secrets

- \`GITHUB_TOKEN\`: Automatically provided by GitHub Actions (requires issues: write permission)

#### Optional Environment Variables

- \`DEMO_E2E=1\`: Force demo mode for local testing
- \`UAT_HEADLESS=true\`: Run in headless mode
- \`WEB_BASE_URL\`: Override target URL for testing

### Usage Instructions

#### Manual Workflow Trigger

1. Go to GitHub Actions → UAT Explorer
2. Click "Run workflow"
3. Select environment (staging/production)
4. Choose test mode (demo/aad)
5. Enable/disable GitHub issue creation

#### Local Testing

\`\`\`bash
# Test UAT setup
cd web
npm run test:e2e:uat:validate

# Run UAT Explorer locally  
WEB_BASE_URL=http://localhost:3000 DEMO_E2E=1 npm run test:e2e:uat

# Test GitHub integration
npm run test:e2e:uat:github
\`\`\`

### Next Steps

1. Set required repository variables in GitHub Settings → Secrets and variables → Actions
2. Test workflow with manual trigger against staging environment
3. Review generated artifacts and GitHub issues
4. Configure monitoring alerts based on workflow results
5. Schedule regular UAT runs or rely on nightly automation

EOF

    log_success "Validation report generated: $report_file"
}

# Main execution
main() {
    echo "=== UAT Explorer Workflow Validation ==="
    echo
    
    local validation_failed=false
    
    # Run validation checks
    validate_workflow_file || validation_failed=true
    echo
    
    validate_web_dependencies || validation_failed=true
    echo
    
    validate_uat_explorer_files || validation_failed=true
    echo
    
    validate_playwright_config || validation_failed=true
    echo
    
    validate_environment_variables || validation_failed=true
    echo
    
    validate_github_integration || validation_failed=true
    echo
    
    validate_artifact_directories || validation_failed=true
    echo
    
    run_uat_setup_validation || validation_failed=true
    echo
    
    test_github_issue_integration
    echo
    
    generate_validation_report
    echo
    
    if [[ "$validation_failed" == "true" ]]; then
        log_error "UAT Explorer workflow validation failed"
        echo
        echo "Please fix the issues above before using the UAT Explorer workflow."
        echo "See the generated validation report for detailed instructions."
        exit 1
    else
        log_success "UAT Explorer workflow validation passed"
        echo
        echo "The UAT Explorer workflow is ready to use!"
        echo "Check the validation report for configuration instructions."
        exit 0
    fi
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
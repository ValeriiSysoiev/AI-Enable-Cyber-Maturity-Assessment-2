#!/bin/bash

# Validate Staging Deployment Workflow Configuration
# This script validates that all required components are configured correctly

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
declare -A validation_results
validation_count=0
passed_count=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✅ PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠️ WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[❌ FAIL]${NC} $1"
}

log_check() {
    echo -e "${BLUE}[🔍 CHECK]${NC} $1"
}

record_result() {
    local check_name="$1"
    local status="$2"
    local message="$3"
    
    validation_results["$check_name"]="$status:$message"
    ((validation_count++))
    
    if [[ "$status" == "PASS" ]]; then
        ((passed_count++))
        log_success "$message"
    elif [[ "$status" == "WARN" ]]; then
        log_warning "$message"
    else
        log_error "$message"
    fi
}

check_workflow_file() {
    log_check "Checking workflow file existence and syntax"
    
    local workflow_file=".github/workflows/deploy_staging.yml"
    
    if [[ ! -f "$workflow_file" ]]; then
        record_result "workflow_file" "FAIL" "Workflow file not found: $workflow_file"
        return
    fi
    
    # Check YAML syntax
    if command -v yq &> /dev/null; then
        if yq eval '.' "$workflow_file" >/dev/null 2>&1; then\n            record_result \"workflow_file\" \"PASS\" \"Workflow file exists and has valid YAML syntax\"\n        else\n            record_result \"workflow_file\" \"FAIL\" \"Workflow file has invalid YAML syntax\"\n            return\n        fi\n    else\n        record_result \"workflow_file\" \"WARN\" \"Workflow file exists (unable to validate YAML syntax - yq not installed)\"\n    fi\n    \n    # Check required workflow components\n    local required_jobs=(\"validate-prerequisites\" \"build-images\" \"deploy-staging\" \"verify-deployment\")\n    \n    for job in \"${required_jobs[@]}\"; do\n        if grep -q \"$job:\" \"$workflow_file\"; then\n            record_result \"job_$job\" \"PASS\" \"Required job '$job' found in workflow\"\n        else\n            record_result \"job_$job\" \"FAIL\" \"Required job '$job' missing from workflow\"\n        fi\n    done\n}\n\ncheck_github_cli() {\n    log_check \"Checking GitHub CLI authentication\"\n    \n    if ! command -v gh &> /dev/null; then\n        record_result \"github_cli\" \"FAIL\" \"GitHub CLI not installed\"\n        return\n    fi\n    \n    if gh auth status &> /dev/null; then\n        local user=$(gh api user --jq '.login' 2>/dev/null || echo \"unknown\")\n        record_result \"github_cli\" \"PASS\" \"GitHub CLI authenticated as: $user\"\n    else\n        record_result \"github_cli\" \"FAIL\" \"GitHub CLI not authenticated - run 'gh auth login'\"\n    fi\n}\n\ncheck_github_environments() {\n    log_check \"Checking GitHub Environments configuration\"\n    \n    if ! gh auth status &> /dev/null; then\n        record_result \"environments\" \"FAIL\" \"Cannot check environments - GitHub CLI not authenticated\"\n        return\n    fi\n    \n    # Get repository info\n    local repo_info\n    if repo_info=$(gh repo view --json owner,name 2>/dev/null); then\n        local owner=$(echo \"$repo_info\" | jq -r '.owner.login')\n        local name=$(echo \"$repo_info\" | jq -r '.name')\n        record_result \"repo_info\" \"PASS\" \"Repository detected: $owner/$name\"\n    else\n        record_result \"repo_info\" \"FAIL\" \"Not in a GitHub repository or unable to detect repository\"\n        return\n    fi\n    \n    # Required environments\n    local required_envs=(\"staging-validation\" \"staging-build\" \"staging\" \"staging-verification\")\n    \n    for env in \"${required_envs[@]}\"; do\n        if gh api \"/repos/$owner/$name/environments/$env\" &> /dev/null; then\n            record_result \"env_$env\" \"PASS\" \"Environment '$env' exists\"\n        else\n            record_result \"env_$env\" \"FAIL\" \"Environment '$env' not configured\"\n        fi\n    done\n}\n\ncheck_environment_variables() {\n    log_check \"Checking staging environment variables\"\n    \n    if ! gh auth status &> /dev/null; then\n        record_result \"env_vars\" \"FAIL\" \"Cannot check environment variables - GitHub CLI not authenticated\"\n        return\n    fi\n    \n    local repo_info\n    if repo_info=$(gh repo view --json owner,name 2>/dev/null); then\n        local owner=$(echo \"$repo_info\" | jq -r '.owner.login')\n        local name=$(echo \"$repo_info\" | jq -r '.name')\n    else\n        record_result \"env_vars\" \"FAIL\" \"Cannot determine repository for environment variable check\"\n        return\n    fi\n    \n    # Required environment variables for staging environment\n    local required_vars=(\n        \"AZURE_CLIENT_ID\"\n        \"AZURE_TENANT_ID\"\n        \"AZURE_SUBSCRIPTION_ID\"\n        \"ACA_RG\"\n        \"ACA_ENV\"\n        \"ACA_APP_API\"\n        \"ACA_APP_WEB\"\n        \"ACA_APP_MCP\"\n        \"STAGING_URL\"\n    )\n    \n    local missing_vars=()\n    \n    for var in \"${required_vars[@]}\"; do\n        # Try to get the variable (this will fail if it doesn't exist)\n        if gh api \"/repos/$owner/$name/environments/staging/variables/$var\" &> /dev/null; then\n            record_result \"var_$var\" \"PASS\" \"Environment variable '$var' is configured\"\n        else\n            missing_vars+=(\"$var\")\n            record_result \"var_$var\" \"FAIL\" \"Environment variable '$var' not configured\"\n        fi\n    done\n    \n    if [[ ${#missing_vars[@]} -eq 0 ]]; then\n        record_result \"all_env_vars\" \"PASS\" \"All required environment variables are configured\"\n    else\n        record_result \"all_env_vars\" \"FAIL\" \"Missing ${#missing_vars[@]} required environment variables\"\n    fi\n}\n\ncheck_azure_cli() {\n    log_check \"Checking Azure CLI authentication and resources\"\n    \n    if ! command -v az &> /dev/null; then\n        record_result \"azure_cli\" \"FAIL\" \"Azure CLI not installed\"\n        return\n    fi\n    \n    if az account show &> /dev/null; then\n        local subscription=$(az account show --query name -o tsv 2>/dev/null || echo \"unknown\")\n        record_result \"azure_auth\" \"PASS\" \"Azure CLI authenticated - Subscription: $subscription\"\n    else\n        record_result \"azure_auth\" \"FAIL\" \"Azure CLI not authenticated - run 'az login'\"\n        return\n    fi\n    \n    # Check if staging resource group exists (if we can determine the name)\n    local staging_rg=\"rg-aecma-staging\"\n    \n    if az group show --name \"$staging_rg\" &> /dev/null; then\n        record_result \"staging_rg\" \"PASS\" \"Staging resource group '$staging_rg' exists\"\n        \n        # Check Container Apps Environment\n        local aca_env=\"cae-aecma-staging\"\n        if az containerapp env show --name \"$aca_env\" --resource-group \"$staging_rg\" &> /dev/null; then\n            record_result \"aca_env\" \"PASS\" \"Container Apps Environment '$aca_env' exists\"\n        else\n            record_result \"aca_env\" \"FAIL\" \"Container Apps Environment '$aca_env' not found\"\n        fi\n        \n        # Check Container Apps\n        local apps=(\"api-staging\" \"web-staging\" \"mcp-staging\")\n        for app in \"${apps[@]}\"; do\n            if az containerapp show --name \"$app\" --resource-group \"$staging_rg\" &> /dev/null; then\n                record_result \"app_$app\" \"PASS\" \"Container App '$app' exists\"\n            else\n                record_result \"app_$app\" \"FAIL\" \"Container App '$app' not found\"\n            fi\n        done\n    else\n        record_result \"staging_rg\" \"FAIL\" \"Staging resource group '$staging_rg' not found\"\n    fi\n}\n\ncheck_docker_config() {\n    log_check \"Checking Docker and container registry configuration\"\n    \n    if ! command -v docker &> /dev/null; then\n        record_result \"docker\" \"WARN\" \"Docker not installed (not required for GitHub Actions, but useful for local testing)\"\n    else\n        if docker --version &> /dev/null; then\n            local docker_version=$(docker --version | cut -d' ' -f3 | tr -d ',')\n            record_result \"docker\" \"PASS\" \"Docker installed: $docker_version\"\n        else\n            record_result \"docker\" \"FAIL\" \"Docker installed but not working properly\"\n        fi\n    fi\n    \n    # Check if we can access GitHub Container Registry (requires GitHub CLI)\n    if gh auth status &> /dev/null; then\n        local username=$(gh api user --jq '.login' 2>/dev/null || echo \"unknown\")\n        record_result \"ghcr_access\" \"PASS\" \"GHCR access configured for user: $username\"\n    else\n        record_result \"ghcr_access\" \"WARN\" \"Cannot verify GHCR access - GitHub CLI not authenticated\"\n    fi\n}\n\ncheck_required_scripts() {\n    log_check \"Checking required scripts and dependencies\"\n    \n    local required_scripts=(\n        \"scripts/verify_live.sh\"\n        \"scripts/test_abac_staging.sh\"\n        \"scripts/test_mcp_tools.sh\"\n    )\n    \n    for script in \"${required_scripts[@]}\"; do\n        if [[ -f \"$script\" ]]; then\n            if [[ -x \"$script\" ]]; then\n                record_result \"script_$(basename \"$script\")\" \"PASS\" \"Script '$script' exists and is executable\"\n            else\n                record_result \"script_$(basename \"$script\")\" \"WARN\" \"Script '$script' exists but is not executable\"\n            fi\n        else\n            record_result \"script_$(basename \"$script\")\" \"WARN\" \"Script '$script' not found (deployment will skip related tests)\"\n        fi\n    done\n    \n    # Check requirements.txt\n    if [[ -f \"requirements.txt\" ]]; then\n        record_result \"requirements\" \"PASS\" \"requirements.txt found\"\n    else\n        record_result \"requirements\" \"WARN\" \"requirements.txt not found (may cause verification failures)\"\n    fi\n}\n\ngenerate_report() {\n    echo\n    echo \"📊 Validation Report\"\n    echo \"==================\"\n    echo\n    \n    local fail_count=$((validation_count - passed_count))\n    local pass_percentage=$((passed_count * 100 / validation_count))\n    \n    echo \"Total Checks: $validation_count\"\n    echo \"Passed: $passed_count\"\n    echo \"Failed/Warnings: $fail_count\"\n    echo \"Success Rate: $pass_percentage%\"\n    echo\n    \n    # Categorize results\n    local critical_failures=()\n    local warnings=()\n    \n    for check in \"${!validation_results[@]}\"; do\n        local status=\"${validation_results[$check]%%:*}\"\n        local message=\"${validation_results[$check]#*:}\"\n        \n        if [[ \"$status\" == \"FAIL\" ]]; then\n            critical_failures+=(\"$check: $message\")\n        elif [[ \"$status\" == \"WARN\" ]]; then\n            warnings+=(\"$check: $message\")\n        fi\n    done\n    \n    if [[ ${#critical_failures[@]} -gt 0 ]]; then\n        echo \"🚨 Critical Issues (Must Fix):\"\n        printf '  ❌ %s\\n' \"${critical_failures[@]}\"\n        echo\n    fi\n    \n    if [[ ${#warnings[@]} -gt 0 ]]; then\n        echo \"⚠️  Warnings (Recommended to Fix):\"\n        printf '  ⚠️  %s\\n' \"${warnings[@]}\"\n        echo\n    fi\n    \n    # Provide next steps\n    if [[ ${#critical_failures[@]} -eq 0 ]]; then\n        log_success \"🎉 All critical checks passed! Staging deployment pipeline is ready.\"\n        echo\n        echo \"Next Steps:\"\n        echo \"1. Push a commit to main branch to test the deployment\"\n        echo \"2. Monitor the GitHub Actions workflow execution\"\n        echo \"3. Verify the staging environment after deployment\"\n    else\n        log_error \"❌ Critical issues found. Please address them before deploying.\"\n        echo\n        echo \"Quick Fixes:\"\n        echo \"1. Run: ./scripts/setup_staging_environments.sh (to configure GitHub environments)\"\n        echo \"2. Ensure Azure resources are created and accessible\"\n        echo \"3. Verify GitHub CLI and Azure CLI authentication\"\n    fi\n    \n    echo\n    echo \"📚 Documentation:\"\n    echo \"- Staging Environment: docs/staging-env.md\"\n    echo \"- GitHub Environments: docs/github-environments.md\"\n    echo \"- Setup Script: scripts/setup_staging_environments.sh\"\n}\n\n# Main execution\nmain() {\n    echo \"🔍 Staging Deployment Pipeline Validation\"\n    echo \"===========================================\"\n    echo\n    \n    check_workflow_file\n    check_github_cli\n    check_github_environments\n    check_environment_variables\n    check_azure_cli\n    check_docker_config\n    check_required_scripts\n    \n    generate_report\n}\n\n# Check if script is being sourced or executed\nif [[ \"${BASH_SOURCE[0]}\" == \"${0}\" ]]; then\n    main \"$@\"\nfi"}]
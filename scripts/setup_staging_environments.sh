#!/bin/bash

# Setup GitHub Environments for Staging Deployment Pipeline
# This script helps configure the required GitHub environments and Azure OIDC integration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER=""
REPO_NAME=""
AZURE_SUBSCRIPTION_ID=""
AZURE_TENANT_ID=""
STAGING_RG="rg-aecma-staging"
SP_NAME="GitHub-Actions-Staging"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    local missing_tools=()
    
    if ! command -v az &> /dev/null; then
        missing_tools+=("azure-cli")
    fi
    
    if ! command -v gh &> /dev/null; then
        missing_tools+=("github-cli")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "Missing required tools:"
        printf '  - %s\n' "${missing_tools[@]}"
        exit 1
    fi
    
    # Check Azure CLI login
    if ! az account show &> /dev/null; then
        log_error "Please login to Azure CLI: az login"
        exit 1
    fi
    
    # Check GitHub CLI authentication
    if ! gh auth status &> /dev/null; then
        log_error "Please authenticate with GitHub CLI: gh auth login"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

get_user_input() {
    log_info "Gathering configuration..."
    
    # Get repository information
    if [[ -z "$REPO_OWNER" ]]; then
        read -p "GitHub repository owner: " REPO_OWNER
    fi
    
    if [[ -z "$REPO_NAME" ]]; then
        read -p "GitHub repository name: " REPO_NAME
    fi
    
    # Get Azure information
    if [[ -z "$AZURE_SUBSCRIPTION_ID" ]]; then
        AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
        read -p "Azure Subscription ID [$AZURE_SUBSCRIPTION_ID]: " input
        AZURE_SUBSCRIPTION_ID=${input:-$AZURE_SUBSCRIPTION_ID}
    fi
    
    if [[ -z "$AZURE_TENANT_ID" ]]; then
        AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)\n        read -p \"Azure Tenant ID [$AZURE_TENANT_ID]: \" input\n        AZURE_TENANT_ID=${input:-$AZURE_TENANT_ID}\n    fi\n    \n    read -p \"Staging Resource Group [$STAGING_RG]: \" input\n    STAGING_RG=${input:-$STAGING_RG}\n    \n    read -p \"Service Principal Name [$SP_NAME]: \" input\n    SP_NAME=${input:-$SP_NAME}\n    \n    log_success \"Configuration gathered\"\n}\n\ncreate_service_principal() {\n    log_info \"Creating Azure Service Principal...\"\n    \n    # Check if service principal already exists\n    SP_APP_ID=$(az ad sp list --display-name \"$SP_NAME\" --query \"[0].appId\" -o tsv 2>/dev/null || echo \"\")\n    \n    if [[ -n \"$SP_APP_ID\" ]]; then\n        log_warning \"Service Principal '$SP_NAME' already exists with App ID: $SP_APP_ID\"\n        read -p \"Do you want to use the existing service principal? (y/n): \" -n 1 -r\n        echo\n        if [[ ! $REPLY =~ ^[Yy]$ ]]; then\n            log_error \"Please use a different service principal name\"\n            exit 1\n        fi\n    else\n        # Create new service principal\n        log_info \"Creating new service principal: $SP_NAME\"\n        SP_RESULT=$(az ad sp create-for-rbac \\\n            --name \"$SP_NAME\" \\\n            --role \"Contributor\" \\\n            --scopes \"/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$STAGING_RG\" \\\n            --json-auth)\n        \n        SP_APP_ID=$(echo \"$SP_RESULT\" | jq -r '.clientId')\n        log_success \"Service Principal created with App ID: $SP_APP_ID\"\n    fi\n    \n    # Store for later use\n    echo \"$SP_APP_ID\" > .sp_app_id.tmp\n}\n\nconfigure_federated_credential() {\n    log_info \"Configuring OIDC Federated Identity Credential...\"\n    \n    SP_APP_ID=$(cat .sp_app_id.tmp)\n    \n    # Create federated credential for staging environment\n    FEDERATED_CRED_JSON=$(\ncat <<EOF\n{\n  \"name\": \"GitHub-Actions-Staging\",\n  \"issuer\": \"https://token.actions.githubusercontent.com\",\n  \"subject\": \"repo:$REPO_OWNER/$REPO_NAME:environment:staging\",\n  \"description\": \"GitHub Actions OIDC for staging environment\",\n  \"audiences\": [\"api://AzureADTokenExchange\"]\n}\nEOF\n    )\n    \n    # Check if federated credential already exists\n    EXISTING_CRED=$(az ad app federated-credential list --id \"$SP_APP_ID\" \\\n        --query \"[?subject=='repo:$REPO_OWNER/$REPO_NAME:environment:staging'].name\" -o tsv 2>/dev/null || echo \"\")\n    \n    if [[ -n \"$EXISTING_CRED\" ]]; then\n        log_warning \"Federated credential already exists: $EXISTING_CRED\"\n    else\n        echo \"$FEDERATED_CRED_JSON\" | az ad app federated-credential create \\\n            --id \"$SP_APP_ID\" \\\n            --parameters @-\n        log_success \"Federated credential created for staging environment\"\n    fi\n}\n\nassign_azure_roles() {\n    log_info \"Assigning required Azure roles...\"\n    \n    SP_APP_ID=$(cat .sp_app_id.tmp)\n    \n    # Required roles for Container Apps deployment\n    local roles=(\n        \"Container Apps Contributor\"\n        \"AcrPull\"\n        \"AcrPush\"\n        \"Key Vault Secrets User\"\n    )\n    \n    for role in \"${roles[@]}\"; do\n        log_info \"Assigning role: $role\"\n        \n        # Check if role assignment already exists\n        EXISTING_ASSIGNMENT=$(az role assignment list \\\n            --assignee \"$SP_APP_ID\" \\\n            --role \"$role\" \\\n            --scope \"/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$STAGING_RG\" \\\n            --query \"[0].roleDefinitionName\" -o tsv 2>/dev/null || echo \"\")\n        \n        if [[ -n \"$EXISTING_ASSIGNMENT\" ]]; then\n            log_warning \"Role '$role' already assigned\"\n        else\n            az role assignment create \\\n                --assignee \"$SP_APP_ID\" \\\n                --role \"$role\" \\\n                --scope \"/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$STAGING_RG\"\n            log_success \"Assigned role: $role\"\n        fi\n    done\n}\n\nsetup_github_environments() {\n    log_info \"Setting up GitHub Environments...\"\n    \n    SP_APP_ID=$(cat .sp_app_id.tmp)\n    \n    # GitHub Environments to create\n    local environments=(\n        \"staging-validation\"\n        \"staging-build\"\n        \"staging\"\n        \"staging-verification\"\n    )\n    \n    for env in \"${environments[@]}\"; do\n        log_info \"Creating environment: $env\"\n        \n        # Create environment (this will not fail if it already exists)\n        gh api \\\n            --method PUT \\\n            \"/repos/$REPO_OWNER/$REPO_NAME/environments/$env\" \\\n            --silent || log_warning \"Environment '$env' might already exist\"\n        \n        log_success \"Environment '$env' configured\"\n    done\n    \n    # Configure staging environment with protection rules\n    log_info \"Configuring protection rules for staging environment...\"\n    \n    # Get current user for reviewer (in real scenario, this would be a team)\n    CURRENT_USER=$(gh api user --jq '.login')\n    \n    gh api \\\n        --method PUT \\\n        \"/repos/$REPO_OWNER/$REPO_NAME/environments/staging\" \\\n        --field \"wait_timer=0\" \\\n        --field \"prevent_self_review=false\" \\\n        --field \"reviewers[][type]=User\" \\\n        --field \"reviewers[][id]=$(gh api user --jq '.id')\" || {\n            log_warning \"Could not set protection rules - you may need to configure them manually\"\n        }\n    \n    log_success \"GitHub Environments configured\"\n}\n\nset_environment_variables() {\n    log_info \"Setting GitHub Environment Variables...\"\n    \n    SP_APP_ID=$(cat .sp_app_id.tmp)\n    \n    # Environment variables for staging environment\n    local env_vars=(\n        \"AZURE_CLIENT_ID=$SP_APP_ID\"\n        \"AZURE_TENANT_ID=$AZURE_TENANT_ID\"\n        \"AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID\"\n        \"ACA_RG=rg-aecma-staging\"\n        \"ACA_ENV=cae-aecma-staging\"\n        \"ACA_APP_API=api-staging\"\n        \"ACA_APP_WEB=web-staging\"\n        \"ACA_APP_MCP=mcp-staging\"\n        \"STAGING_URL=https://web-staging.eastus.azurecontainerapps.io\"\n    )\n    \n    for var in \"${env_vars[@]}\"; do\n        local name=\"${var%%=*}\"\n        local value=\"${var#*=}\"\n        \n        log_info \"Setting environment variable: $name\"\n        \n        gh api \\\n            --method PUT \\\n            \"/repos/$REPO_OWNER/$REPO_NAME/environments/staging/variables/$name\" \\\n            --field \"name=$name\" \\\n            --field \"value=$value\" \\\n            --silent && log_success \"Set $name\" || log_warning \"Failed to set $name\"\n    done\n}\n\ngenerate_summary() {\n    log_info \"Generating setup summary...\"\n    \n    SP_APP_ID=$(cat .sp_app_id.tmp)\n    \n    cat > staging_setup_summary.md << EOF\n# Staging Environment Setup Summary\n\n## Configuration Completed\n\n### Azure Resources\n- **Service Principal**: $SP_NAME\n- **App ID**: $SP_APP_ID\n- **Subscription**: $AZURE_SUBSCRIPTION_ID\n- **Resource Group**: $STAGING_RG\n- **OIDC Configured**: ✅ Yes\n\n### GitHub Environments\n- **staging-validation**: ✅ Created\n- **staging-build**: ✅ Created\n- **staging**: ✅ Created (with protection rules)\n- **staging-verification**: ✅ Created\n\n### Environment Variables Set\n- AZURE_CLIENT_ID: $SP_APP_ID\n- AZURE_TENANT_ID: $AZURE_TENANT_ID\n- AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID\n- ACA_RG: $STAGING_RG\n- ACA_ENV: cae-aecma-staging\n- ACA_APP_API: api-staging\n- ACA_APP_WEB: web-staging\n- ACA_APP_MCP: mcp-staging\n- STAGING_URL: https://web-staging.eastus.azurecontainerapps.io\n\n## Next Steps\n\n1. **Update Staging URL**: \n   - Replace the placeholder staging URL with your actual Container Apps URL\n   - Go to: https://github.com/$REPO_OWNER/$REPO_NAME/settings/environments/staging\n\n2. **Configure Protection Rules**:\n   - Add your Platform Engineering Team as reviewers\n   - Configure any additional protection rules as needed\n\n3. **Test Deployment Pipeline**:\n   - Push a commit to main branch\n   - Monitor the deployment workflow\n   - Verify all stages complete successfully\n\n4. **Validate OIDC Authentication**:\n   - Check that no secrets are required for Azure authentication\n   - Verify service principal has appropriate permissions\n\n## Manual Configuration Required\n\n### Container Apps Environment\nEnsure these Azure resources exist:\n- Resource Group: $STAGING_RG\n- Container Apps Environment: cae-aecma-staging\n- Container Apps: api-staging, web-staging, mcp-staging\n\n### GitHub Settings\n1. Go to: https://github.com/$REPO_OWNER/$REPO_NAME/settings/environments\n2. Configure staging environment reviewers\n3. Update STAGING_URL variable with actual URL\n\n## Troubleshooting\n\n- **OIDC Errors**: Check federated credential subject matches exactly\n- **Permission Errors**: Verify service principal role assignments\n- **Environment Issues**: Ensure Azure resources exist before deployment\n\n## Support\n- Documentation: docs/github-environments.md\n- Azure Setup: docs/staging-env.md\nEOF\n\n    log_success \"Setup summary saved to: staging_setup_summary.md\"\n}\n\ncleanup() {\n    # Remove temporary files\n    rm -f .sp_app_id.tmp\n}\n\n# Main execution\nmain() {\n    echo \"🚀 GitHub Environments Setup for Staging Deployment Pipeline\"\n    echo \"=============================================================\"\n    \n    check_prerequisites\n    get_user_input\n    create_service_principal\n    configure_federated_credential\n    assign_azure_roles\n    setup_github_environments\n    set_environment_variables\n    generate_summary\n    \n    log_success \"✅ Staging environment setup completed!\"\n    log_info \"📋 Review staging_setup_summary.md for next steps\"\n    log_info \"🔗 GitHub Environments: https://github.com/$REPO_OWNER/$REPO_NAME/settings/environments\"\n    \n    cleanup\n}\n\n# Handle script interruption\ntrap cleanup EXIT\n\n# Check if script is being sourced or executed\nif [[ \"${BASH_SOURCE[0]}\" == \"${0}\" ]]; then\n    main \"$@\"\nfi"}]
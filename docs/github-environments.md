# GitHub Environments Configuration

## Overview

This document describes the GitHub Environments setup required for the staging deployment pipeline with protection rules and OIDC authentication.

## Required Environments

### 1. staging-validation
**Purpose**: Pre-deployment validation and security checks
**Protection Rules**: None (automated validation)
**Required Variables**: None
**Secrets**: 
- `GITHUB_TOKEN` (automatically provided)

### 2. staging-build
**Purpose**: Container image building and registry operations
**Protection Rules**: None (automated process)
**Required Variables**: None
**Secrets**:
- `GITHUB_TOKEN` (automatically provided for GHCR access)

### 3. staging
**Purpose**: Main staging deployment environment
**Protection Rules**: 
- Required reviewers: 1 (Platform Engineering Team)
- Wait timer: 0 minutes
- Restrict pushes to protected branches: true

**Required Variables**:
```
AZURE_CLIENT_ID          # Service principal client ID for OIDC
AZURE_TENANT_ID          # Azure AD tenant ID  
AZURE_SUBSCRIPTION_ID    # Azure subscription ID
ACA_RG                   # Azure resource group (e.g., rg-aecma-staging)
ACA_ENV                  # Container Apps environment (e.g., cae-aecma-staging)
ACA_APP_API              # API container app name (e.g., api-staging)
ACA_APP_WEB              # Web container app name (e.g., web-staging)
ACA_APP_MCP              # MCP Gateway container app name (e.g., mcp-staging)
STAGING_URL              # Main staging URL (e.g., https://web-staging.region.azurecontainerapps.io)
```

**Secrets**: None (uses OIDC)

### 4. staging-verification
**Purpose**: Post-deployment verification and testing
**Protection Rules**: None (automated verification)
**Required Variables**: None
**Secrets**: None

## OIDC Configuration

### Azure Service Principal Setup

1. **Create Service Principal**:
   ```bash
   az ad sp create-for-rbac \
     --name "GitHub-Actions-Staging" \
     --role "Contributor" \
     --scopes "/subscriptions/{subscription-id}/resourceGroups/rg-aecma-staging" \
     --json-auth
   ```

2. **Configure Federated Identity Credential**:
   ```bash
   az ad app federated-credential create \
     --id {client-id} \
     --parameters '{
       "name": "GitHub-Actions-Staging",
       "issuer": "https://token.actions.githubusercontent.com",
       "subject": "repo:{owner}/{repo}:environment:staging",
       "description": "GitHub Actions OIDC for staging environment",
       "audiences": ["api://AzureADTokenExchange"]
     }'
   ```

3. **Assign Required Roles**:
   ```bash
   # Container Apps Contributor
   az role assignment create \
     --assignee {client-id} \
     --role "Container Apps Contributor" \
     --scope "/subscriptions/{subscription-id}/resourceGroups/rg-aecma-staging"
   
   # ACR Pull & Push
   az role assignment create \
     --assignee {client-id} \
     --role "AcrPull" \
     --scope "/subscriptions/{subscription-id}/resourceGroups/rg-aecma-staging"
   
   az role assignment create \
     --assignee {client-id} \
     --role "AcrPush" \
     --scope "/subscriptions/{subscription-id}/resourceGroups/rg-aecma-staging"
   ```

### GitHub Repository Configuration

1. **Set Environment Variables** (in GitHub repository settings > Environments > staging):
   ```
   AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789012
   AZURE_TENANT_ID=87654321-4321-4321-4321-210987654321
   AZURE_SUBSCRIPTION_ID=11111111-2222-3333-4444-555555555555
   ACA_RG=rg-aecma-staging
   ACA_ENV=cae-aecma-staging
   ACA_APP_API=api-staging
   ACA_APP_WEB=web-staging
   ACA_APP_MCP=mcp-staging
   STAGING_URL=https://web-staging.eastus.azurecontainerapps.io
   ```

2. **Configure Protection Rules**:
   - Go to Settings > Environments > staging
   - Enable "Required reviewers" and add Platform Engineering Team
   - Enable "Restrict pushes to protected branches"
   - Leave "Wait timer" at 0 minutes for staging

## Deployment Pipeline Flow

### 1. Pre-deployment Validation (staging-validation)
- ✅ Check CI status for current commit
- ✅ Run security vulnerability scan
- ✅ Validate deployment prerequisites
- ❌ Block deployment if CI failed (unless force_deploy=true)

### 2. Build Phase (staging-build)
- ✅ Build container images for API, Web, and MCP Gateway
- ✅ Push images to GitHub Container Registry
- ✅ Tag images with staging-{sha} and staging-latest
- ✅ Cache Docker layers for faster builds

### 3. Deployment Phase (staging)
- ⏸️ **MANUAL APPROVAL REQUIRED** (Platform Engineering Team)
- ✅ Authenticate to Azure using OIDC (no secrets)
- ✅ Validate Azure resources exist
- ✅ Deploy to Azure Container Apps
- ✅ Wait for deployment stabilization
- ✅ Capture deployment URLs and metadata

### 4. Verification Phase (staging-verification)
- ✅ Run comprehensive health checks
- ✅ Execute staging verification script
- ✅ Test ABAC authorization enforcement
- ✅ Validate MCP tools integration
- ✅ Generate deployment report

## Graceful Degradation

The pipeline includes graceful handling for missing components:

### Missing Secrets/Variables
```yaml
# Example: Skip verification if script not found
if [[ -f "scripts/test_abac_staging.sh" ]]; then
  ./scripts/test_abac_staging.sh
else
  echo "⚠️ ABAC test script not found - skipping ABAC tests"
fi
```

### CI Failures
```yaml
# Allow force deployment even if CI fails
if [[ "${{ inputs.force_deploy }}" == "true" ]]; then
  echo "⚠️ Force deployment requested - skipping CI checks"
  echo "deployment_allowed=true" >> $GITHUB_OUTPUT
fi
```

### Environment Variables
```yaml
# Validate required variables with clear error messages
if [[ -z "${{ vars.ACA_RG }}" ]]; then
  echo "❌ Missing required staging environment variables"
  echo "Please configure these variables in GitHub repository settings."
  echo "Refer to docs/staging-env.md for configuration details."
  exit 1
fi
```

## Manual Deployment Options

### Force Deployment
```bash
# Trigger deployment even if CI checks fail
gh workflow run deploy_staging.yml -f force_deploy=true
```

### Skip Verification
```bash
# Skip post-deployment verification (for emergency deployments)
gh workflow run deploy_staging.yml -f skip_verification=true
```

### Combined Options
```bash
# Force deployment and skip verification
gh workflow run deploy_staging.yml \
  -f force_deploy=true \
  -f skip_verification=true
```

## Monitoring and Alerts

### Deployment Status
- ✅ GitHub Actions status badges
- ✅ Deployment reports in GitHub Step Summary
- ✅ Artifact retention for 30 days

### Health Monitoring
- ✅ Automated health checks post-deployment
- ✅ Application-level health endpoints
- ✅ Azure Container Apps built-in monitoring

### Notification Channels
- ✅ GitHub Actions notifications
- ✅ Azure Monitor integration (optional)
- ✅ Slack/Teams webhook (optional)

## Troubleshooting

### Common Issues

**OIDC Authentication Fails**
```bash
# Verify federated credential configuration
az ad app federated-credential list --id {client-id}

# Check service principal permissions
az role assignment list --assignee {client-id}
```

**Container Apps Deployment Fails**
```bash
# Check container app logs
az containerapp logs show \
  --name api-staging \
  --resource-group rg-aecma-staging \
  --tail 50

# Verify environment exists
az containerapp env show \
  --name cae-aecma-staging \
  --resource-group rg-aecma-staging
```

**Build Failures**
```bash
# Check GitHub Container Registry permissions
echo $GITHUB_TOKEN | docker login ghcr.io -u username --password-stdin

# Verify Dockerfile syntax
docker build --no-cache ./app
```

## Security Considerations

### OIDC Benefits
- ✅ No long-lived secrets in GitHub
- ✅ Short-lived tokens (1 hour max)
- ✅ Scoped to specific environment
- ✅ Audit trail in Azure AD

### Least Privilege Access
- ✅ Service principal limited to staging resource group
- ✅ Container Apps Contributor role (not Owner)
- ✅ ACR Pull/Push permissions only

### Environment Protection
- ✅ Manual approval required for staging deployment
- ✅ Restricted to protected branches
- ✅ Review required by Platform Engineering Team

## Support Contacts

- **Infrastructure Issues**: Platform Engineering Team
- **OIDC/Authentication**: Azure Identity Team
- **GitHub Actions**: DevOps Team
- **Emergency Deployments**: On-call rotation
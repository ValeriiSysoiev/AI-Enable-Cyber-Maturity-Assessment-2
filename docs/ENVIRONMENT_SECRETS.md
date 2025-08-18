# Environment Secrets Documentation

This document lists all required GitHub repository secrets and environment variables needed for CI/CD deployment workflows.

## Core Azure OIDC Authentication

Required for secure, passwordless authentication to Azure using OpenID Connect.

### Required Secrets
- **`AZURE_CLIENT_ID`** - Azure App Registration client ID for OIDC authentication
- **`AZURE_TENANT_ID`** - Azure Active Directory tenant ID  
- **`AZURE_SUBSCRIPTION_ID`** - Target Azure subscription ID

### Setup Instructions
1. Create Azure App Registration with federated credentials
2. Configure GitHub repository secrets with the above values
3. Assign necessary Azure RBAC permissions to the service principal

## Production Deployment Secrets

Used by `.github/workflows/release.yml` workflow for production deployments.

### Required Secrets
- **`AZURE_CONTAINER_REGISTRY`** - Production ACR name (without .azurecr.io suffix)
- **`AZURE_RESOURCE_GROUP`** - Production resource group name
- **`API_CONTAINER_APP`** - Production API container app name
- **`WEB_CONTAINER_APP`** - Production web container app name

### Optional Secrets
- **`PRODUCTION_AUTH_BEARER`** - Authentication token for production verification tests

## Staging Deployment Secrets

Used by `.github/workflows/deploy_staging.yml` workflow for staging deployments.

### Required Secrets
- **`AZURE_CONTAINER_REGISTRY_STAGING`** - Staging ACR name (without .azurecr.io suffix)
- **`AZURE_RESOURCE_GROUP_STAGING`** - Staging resource group name
- **`API_CONTAINER_APP_STAGING`** - Staging API container app name
- **`WEB_CONTAINER_APP_STAGING`** - Staging web container app name

### Optional Secrets
- **`STAGING_AUTH_BEARER`** - Authentication token for staging verification tests

## Legacy Authentication (Deprecated)

These secrets are used by older workflows but should be migrated to OIDC authentication.

### Deprecated Secrets
- **`AZURE_CREDENTIALS`** - JSON object with clientId, clientSecret, subscriptionId, tenantId
- **`ACR_LOGIN_SERVER`** - Container registry login server
- **`ACR_USERNAME`** - Container registry username
- **`ACR_PASSWORD`** - Container registry password

## Environment Variable Patterns

### Container Registry Names
- Production: `myapp-prod-acr`
- Staging: `myapp-staging-acr`

### Resource Group Names
- Production: `rg-myapp-prod`
- Staging: `rg-myapp-staging`

### Container App Names
- Production API: `ca-myapp-api-prod`
- Production Web: `ca-myapp-web-prod`
- Staging API: `ca-myapp-api-staging`
- Staging Web: `ca-myapp-web-staging`

## Workflow Permissions

Each deployment workflow requires these Azure RBAC permissions for the service principal:

### Required Azure Roles
- **`AcrPush`** - Push images to Container Registry
- **`Contributor`** - Deploy and manage Container Apps
- **`Reader`** - Read resource group and container app status

### Resource Scope
- Container Registry: ACR resource level
- Container Apps: Resource group level
- Resource Group: Resource group level

## Verification Script Environment Variables

The `scripts/verify_live.sh` script accepts these environment variables:

### Required Variables
- **`WEB_BASE_URL`** - Full HTTPS URL to web application (e.g., https://myapp-web.azurecontainerapps.io)
- **`API_BASE_URL`** - Full HTTPS URL to API application (e.g., https://myapp-api.azurecontainerapps.io)

### Optional Variables
- **`AUTH_BEARER`** - Bearer token for authenticated API requests
- **`DEPLOYMENT_VERIFICATION`** - Set to `true` to enable deployment-specific checks
- **`GITHUB_SHA`** - Git commit SHA for deployment tracking
- **`DEPLOYMENT_ENVIRONMENT`** - Environment name (staging, production)

## Security Best Practices

### Secret Management
1. **Principle of Least Privilege** - Grant minimal required permissions
2. **Environment Separation** - Use separate secrets for staging and production
3. **Regular Rotation** - Rotate service principal credentials periodically
4. **Audit Access** - Monitor secret access and usage

### OIDC Benefits
- **No Long-lived Secrets** - Temporary tokens instead of stored credentials
- **Enhanced Security** - Federated authentication with Azure AD
- **Automatic Rotation** - Tokens are short-lived and auto-renewed
- **Audit Trail** - Better tracking of authentication events

### Repository Settings
- **Required Status Checks** - Enforce successful deployment verification
- **Branch Protection** - Prevent direct pushes to main branch
- **Secret Scanning** - Enable GitHub secret scanning alerts
- **Dependency Updates** - Keep workflow actions updated

## Troubleshooting

### Common Issues

#### OIDC Authentication Failures
- Verify federated credentials are configured for correct repository
- Check AZURE_CLIENT_ID matches the App Registration
- Ensure service principal has required RBAC permissions

#### Container Registry Access Denied
- Verify ACR name is correct (without .azurecr.io suffix)
- Check service principal has AcrPush role on registry
- Confirm registry exists in specified resource group

#### Container App Deployment Failures
- Verify container app names are correct
- Check service principal has Contributor role on resource group
- Ensure container apps environment is running

#### Verification Script Failures
- Check WEB_BASE_URL and API_BASE_URL are accessible
- Verify AUTH_BEARER token is valid if using authentication
- Review verification script logs for specific error details

### Debug Commands

```bash
# Test Azure CLI authentication
az account show

# Verify container registry access
az acr login --name myapp-prod-acr

# Check container app status
az containerapp show --name ca-myapp-api-prod --resource-group rg-myapp-prod

# Test application endpoints
curl -f https://myapp-api.azurecontainerapps.io/health
curl -f https://myapp-web.azurecontainerapps.io
```

## Migration Guide

### From Service Principal to OIDC

1. **Create App Registration**
   ```bash
   az ad app create --display-name "MyApp-GitHub-OIDC"
   ```

2. **Configure Federated Credentials**
   - Subject: `repo:organization/repository:environment:production`
   - Issuer: `https://token.actions.githubusercontent.com`

3. **Update GitHub Secrets**
   - Remove: `AZURE_CREDENTIALS`
   - Add: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`

4. **Update Workflow Files**
   - Replace `azure/login@v1` with `azure/login@v2`
   - Remove `creds` parameter, add OIDC parameters

5. **Test Deployment**
   - Run workflow and verify OIDC authentication works
   - Remove old service principal if successful

For questions or issues, please refer to the Azure OIDC documentation or create a GitHub issue.
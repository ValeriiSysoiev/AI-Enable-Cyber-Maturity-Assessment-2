# Staging Environment Deployment Guide

## Quick Redeploy (TL;DR)

1. Set repo variable `STAGING_URL` (App Service URL) or ACA vars for Container Apps Environment
2. Run **Deploy Staging** workflow from GitHub Actions tab
3. Verify: `./scripts/verify_live.sh --staging` 
4. Local gates: `--mcp --uat --governance` for comprehensive testing
5. Logs live in `artifacts/verify/staging_verify.log`
6. Troubleshooting: See sections below or check workflow run logs

## Overview
This guide covers two deployment paths for staging environment:
1. **App Service Only** - Simple deployment without Azure Container Apps
2. **Azure Container Apps** - Full infrastructure deployment with ACA

## Option 1: App Service Only Path (No Azure Context Required)

### Prerequisites
- GitHub repository with Actions enabled
- App Service or any HTTP-accessible hosting

### Setup Steps

1. **Configure Staging URL**
   ```bash
   # In GitHub repository settings → Secrets and variables → Actions → Variables
   STAGING_URL = https://your-app.azurewebsites.net
   ```

2. **Run Deployment Workflow**
   ```bash
   gh workflow run deploy_staging.yml
   ```
   - GHCR images will be built and pushed
   - ACA deployment will be skipped (no Azure variables)
   - Health check runs against STAGING_URL

3. **Verify Deployment Locally**
   ```bash
   export STAGING_URL=https://your-app.azurewebsites.net
   ./scripts/verify_live.sh --staging
   ```

### Expected Output
```
ℹ Staging mode with STAGING_URL - Azure context optional
ℹ Testing staging environment deployment...
ℹ Using configured STAGING_URL: https://your-app.azurewebsites.net
✓ Health check passed (200 OK)
✓ Staging verification complete
```

## Option 2: App Service Deploy

For automated App Service deployment with GHCR images:

### Variables Required
- `APPSVC_RG` - Resource group containing App Services
- `APPSVC_WEBAPP_WEB` - Web App Service name  
- `APPSVC_WEBAPP_API` - API App Service name

### Steps
1. Set repo variables: `APPSVC_RG`, `APPSVC_WEBAPP_WEB`, `APPSVC_WEBAPP_API`
2. Run **Deploy Staging** workflow 
3. `./scripts/verify_live.sh --staging`

## Option 3: Azure Container Apps Path

### Prerequisites
- Azure subscription with OIDC configured
- Container Apps environment deployed

### Setup Steps

1. **Configure Azure Variables**
   ```bash
   # In GitHub repository settings → Variables
   AZURE_SUBSCRIPTION_ID = your-subscription-id
   AZURE_TENANT_ID = your-tenant-id
   AZURE_CLIENT_ID = your-client-id
   ACA_RG = your-resource-group
   ACA_ENV = your-aca-environment
   ACA_APP_API = your-api-app-name
   ACA_APP_WEB = your-web-app-name
   ```

2. **Run Full Deployment**
   ```bash
   gh workflow run deploy_staging.yml
   ```
   - GHCR images built and pushed
   - ACA deployment executed
   - URL computed from ACA configuration

3. **Verify with Azure Context**
   ```bash
   export AZURE_RESOURCE_GROUP=your-resource-group
   export ACA_APP_WEB=your-web-app-name
   export ACA_ENV=your-aca-environment
   ./scripts/verify_live.sh --staging
   ```

## Deployment Workflow Behavior

The staging workflow intelligently handles both scenarios:

| Variables Set | Behavior |
|--------------|----------|
| `STAGING_URL` only | Build images, skip ACA, verify URL |
| Azure/ACA variables | Build images, deploy to ACA, compute URL |
| Both | Build images, deploy to ACA, use STAGING_URL for verification |
| Neither | Build images only, skip deployment |

## Troubleshooting

### Common Issues

1. **"No staging URL available"**
   - Set `STAGING_URL` variable in repository
   - OR provide `ACA_APP_WEB` + `ACA_ENV` variables

2. **"Health check failed after 5 attempts"**
   - Verify the URL is accessible
   - Check if application needs more startup time
   - Review application logs for errors

3. **"GHCR push unauthorized"**
   - Ensure repository has packages write permission
   - Check GitHub token has required scopes

### Verification Artifacts

Logs are saved to `artifacts/verify/staging_verify.log` when running with `--staging` flag.

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Verify Staging
  env:
    STAGING_URL: ${{ vars.STAGING_URL }}
  run: |
    ./scripts/verify_live.sh --staging
```

### Local Testing
```bash
# Test without deploying
export STAGING_URL=http://localhost:3000
./scripts/verify_live.sh --staging
```

## Migration Path

To migrate from App Service to ACA:
1. Keep `STAGING_URL` variable set
2. Add Azure/ACA variables
3. Workflow will start deploying to ACA
4. Remove `STAGING_URL` when ready to use computed URL

## Security Notes

- Never commit URLs with credentials
- Use repository variables for sensitive configuration
- Enable branch protection for production deployments
- Review workflow logs for exposed secrets

---

For more details, see:
- [Deploy Staging Workflow](.github/workflows/deploy_staging.yml)
- [Verification Script](scripts/verify_live.sh)
- [Production Deployment Guide](docs/prod-env.md)
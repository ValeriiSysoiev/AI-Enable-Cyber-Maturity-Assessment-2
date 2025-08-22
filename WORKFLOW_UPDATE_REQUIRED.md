# Workflow Update Required

## Summary
The following changes to `.github/workflows/deploy_staging.yml` are required but cannot be pushed via OAuth due to scope limitations.

## Required Changes

### 1. Add Environment Variables Mapping
Add this section after the `on:` block and before `permissions:`:

```yaml
env:
  GHCR_ENABLED: ${{ vars.GHCR_ENABLED }}
  AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
  AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ACA_RG: ${{ vars.ACA_RG }}
  ACA_ENV: ${{ vars.ACA_ENV }}
  ACA_APP_API: ${{ vars.ACA_APP_API }}
  ACA_APP_WEB: ${{ vars.ACA_APP_WEB }}
  STAGING_URL: ${{ vars.STAGING_URL }}
```

### 2. Update Environment Block
In the `deploy_azure_aca` job, ensure the environment block is:

```yaml
environment:
  name: staging
```

## Implementation Notes
- Environment variables enable conditional deployment based on configuration
- The `environment` block auto-creates GitHub staging environment
- Conditional deployment allows App Service and Container Apps scenarios

## Manual Application Required
These changes must be applied manually due to GitHub OAuth workflow scope restrictions.
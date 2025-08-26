# Deployment Version Troubleshooting Guide

## Issue: Production Version Not Updating

### Problem Description
After deployment, the `/api/version` endpoint returns an old commit SHA instead of the latest deployed version.

### Root Cause
Next.js environment variables need to be available at both **build time** and **runtime**:
- **Build time**: Variables baked into the application during `npm run build`
- **Runtime**: Variables available when the container starts

### Solution Priority Order

#### 1. Runtime Environment Variables (Preferred)
Set these in Azure App Service:
```bash
NEXT_PUBLIC_BUILD_SHA=<commit-sha>  # Accessible at runtime
GITHUB_SHA=<commit-sha>             # Build-time fallback
BUILD_SHA=<commit-sha>              # Build-time fallback
```

#### 2. Docker Build Arguments
Ensure Docker build includes:
```dockerfile
ARG GITHUB_SHA=""
ARG BUILD_SHA=""
ENV GITHUB_SHA=$GITHUB_SHA
ENV BUILD_SHA=$BUILD_SHA
```

### Verification Steps

#### 1. Check Environment Variables
```bash
az webapp config appsettings list --name "web-app-name" --resource-group "rg-name" \
  --query "[?contains(name, 'SHA')]"
```

#### 2. Test Version Endpoint
```bash
curl -s https://your-app.azurewebsites.net/api/version | jq .
```

#### 3. Use Verification Script
```bash
./scripts/verify-version-sync.sh https://your-app.azurewebsites.net expected-sha
```

### Prevention Measures

#### 1. Automated Environment Variable Setting
The `release.yml` workflow automatically sets all required environment variables after deployment.

#### 2. Version Verification
The `deploy.yml` workflow includes automatic version verification using `verify-version-sync.sh`.

#### 3. Debug Information
The `/api/version` endpoint includes debug information showing which environment variables are set.

### Troubleshooting Checklist

- [ ] Environment variables are set in Azure App Service
- [ ] App Service has been restarted after environment variable changes
- [ ] Docker image was built with correct build arguments
- [ ] Version API endpoint is accessible
- [ ] No hardcoded fallback values are masking the issue

### Manual Fix Commands

If the issue occurs, run these commands:

```bash
# Set environment variables
az webapp config appsettings set \
  --name "web-app-name" \
  --resource-group "rg-name" \
  --settings \
    GITHUB_SHA=<commit-sha> \
    BUILD_SHA=<commit-sha> \
    NEXT_PUBLIC_BUILD_SHA=<commit-sha>

# Restart the app
az webapp restart --name "web-app-name" --resource-group "rg-name"

# Verify after 2-3 minutes
./scripts/verify-version-sync.sh https://your-app.azurewebsites.net <commit-sha>
```

### Related Files
- `web/app/api/version/route.ts` - Version API endpoint
- `.github/workflows/release.yml` - Deployment workflow with env var setting
- `scripts/verify-version-sync.sh` - Verification script
- `web/Dockerfile` - Docker build configuration

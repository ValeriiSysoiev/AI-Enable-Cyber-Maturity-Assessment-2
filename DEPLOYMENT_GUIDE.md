# 🚀 Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the AI-Enable Cyber Maturity Assessment application to production and staging environments.

## 🏗️ Deployment Architecture

### Workflows

1. **`deploy.yml`** - Primary deployment workflow (GHCR + fallback)
2. **`deploy_staging.yml`** - Staging environment deployment
3. **`release.yml`** - Production deployment via Azure Container Registry

### Container Registries

- **GitHub Container Registry (GHCR)**: `ghcr.io/valeriisysoiev/aecma-web`
- **Azure Container Registry (ACR)**: `{AZURE_CONTAINER_REGISTRY}.azurecr.io`

## 🔧 Prerequisites

### Required GitHub Secrets

For **full production deployment**, configure these secrets in GitHub repository settings:

```
AZURE_CREDENTIALS          # JSON with Azure service principal
AZURE_CONTAINER_REGISTRY    # ACR name (without .azurecr.io)
AZURE_RESOURCE_GROUP        # Azure resource group name
API_CONTAINER_APP          # API container app name
WEB_CONTAINER_APP          # Web container app name
```

### Azure Credentials Format

```json
{
  "clientId": "your-client-id",
  "clientSecret": "your-client-secret",
  "subscriptionId": "your-subscription-id",
  "tenantId": "your-tenant-id"
}
```

## 🚀 Deployment Methods

### Method 1: Automatic Deployment (Recommended)

**Triggers automatically on push to main branch:**

```bash
git push origin main
```

**What happens:**
1. ✅ Code is built into Docker image
2. ✅ Image pushed to GHCR (always works)
3. ✅ If Azure secrets configured → Production deployment
4. ❌ If Azure secrets missing → Fallback mode (image ready, deployment pending)

### Method 2: Manual Deployment

**Trigger specific workflows manually:**

```bash
# Primary deployment (GHCR + fallback/production)
gh workflow run .github/workflows/deploy.yml

# Staging deployment
gh workflow run .github/workflows/deploy_staging.yml

# Production deployment (requires Azure secrets)
gh workflow run .github/workflows/release.yml
```

### Method 3: Emergency Deployment

**If workflows fail, use direct Docker commands:**

```bash
# Build and push to GHCR
docker build --build-arg GITHUB_SHA=$(git rev-parse HEAD) \
             --build-arg BUILD_SHA=$(git rev-parse HEAD) \
             -t ghcr.io/valeriisysoiev/aecma-web:$(git rev-parse HEAD) ./web

docker push ghcr.io/valeriisysoiev/aecma-web:$(git rev-parse HEAD)
```

## 🔍 Verification

### Automated Verification

Use the provided script:

```bash
./scripts/verify-deployment.sh [expected-sha] [prod-url] [staging-url]
```

### Manual Verification

Check these endpoints:

```bash
# Production
curl https://aecma-prod.azurewebsites.net/health
curl https://aecma-prod.azurewebsites.net/api/version
curl https://aecma-prod.azurewebsites.net/api/auth/mode

# Staging
curl https://aecma-staging.azurewebsites.net/health
curl https://aecma-staging.azurewebsites.net/api/version
curl https://aecma-staging.azurewebsites.net/api/auth/mode
```

**Expected responses:**
- `/health`: `200 OK`
- `/api/version`: `{"sha": "current-commit-sha", ...}`
- `/api/auth/mode`: `{"mode": "aad|demo", "enabled": true, ...}`

## 🛠️ Troubleshooting

### Common Issues

#### 1. "repository name must be lowercase"
**Cause:** Docker registry requires lowercase names
**Fix:** ✅ Already fixed with `REPO_OWNER_LOWER` environment variable

#### 2. "405 Method Not Allowed" on `/api/auth/signin`
**Cause:** NextAuth has no providers configured
**Fix:** ✅ Already fixed with fallback demo provider

#### 3. "Hardcoded session data"
**Cause:** Session API returning static data
**Fix:** ✅ Already fixed with dynamic cookie checking

#### 4. "Version mismatch"
**Cause:** Docker build missing `GITHUB_SHA` argument
**Fix:** ✅ Already fixed in all workflows

#### 5. "Azure credentials not configured"
**Cause:** Missing Azure secrets
**Fix:** Configure secrets or use GHCR fallback mode

### Deployment Status Interpretation

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ All workflows pass | Full deployment successful | None |
| ⚠️ Build passes, Release fails | Image built, Azure deployment failed | Configure Azure secrets |
| ❌ Build fails | Code/workflow issues | Fix code issues |

### Recovery Procedures

#### If Production is Down

1. **Check workflow status:**
   ```bash
   gh run list --workflow="release.yml" --limit 5
   ```

2. **Verify image availability:**
   ```bash
   docker pull ghcr.io/valeriisysoiev/aecma-web:latest
   ```

3. **Manual deployment trigger:**
   ```bash
   gh workflow run .github/workflows/release.yml
   ```

4. **Emergency rollback:**
   ```bash
   # Use previous working SHA
   gh workflow run .github/workflows/release.yml --ref previous-working-commit
   ```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Version endpoint updated with build args
- [ ] Auth configuration tested

### During Deployment
- [ ] Monitor workflow progress
- [ ] Check build logs for errors
- [ ] Verify image push success

### Post-Deployment
- [ ] Run verification script
- [ ] Check all endpoints respond
- [ ] Verify version matches expected SHA
- [ ] Test authentication flows
- [ ] Monitor application logs

## 🔄 Continuous Improvement

### Monitoring

Set up monitoring for:
- Deployment success/failure rates
- Application health endpoints
- Version consistency across environments

### Automation Enhancements

Future improvements:
- Automated rollback on health check failures
- Blue-green deployment strategy
- Canary releases
- Integration with monitoring systems

## 📞 Support

If deployment issues persist:
1. Check GitHub Actions logs
2. Verify all secrets are configured
3. Run verification script for detailed diagnostics
4. Check Azure Container Apps logs (if using Azure)

---

**Last Updated:** $(date)
**Version:** 1.0.0

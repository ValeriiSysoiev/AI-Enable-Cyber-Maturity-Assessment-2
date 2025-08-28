# Deployments

## Overview

All deployments use GitHub Actions as the canonical CI/CD pipeline. The system deploys to Azure Container Apps with Docker images stored in Azure Container Registry (ACR).

## Deployment Workflows

### Primary Workflow: `deploy-container-apps.yml`

**Location**: `.github/workflows/deploy-container-apps.yml`

**Triggers**:
- Push to `main` branch (automatic)
- Manual workflow dispatch (for production releases)

**Deployment Targets**:
- API: `api-cybermat-prd-aca`
- Web: `web-cybermat-prd-aca`

## Deployment Process

### 1. Build Phase
```yaml
# Docker image build
docker build -t $ACR_NAME.azurecr.io/[service]:${{ github.sha }}
```

### 2. Registry Push
```yaml
# Push to ACR
az acr login --name $ACR_NAME
docker push $ACR_NAME.azurecr.io/[service]:${{ github.sha }}
```

### 3. Container App Update
```yaml
# Update Container App with new image
az containerapp update \
  --name [container-app-name] \
  --image $ACR_NAME.azurecr.io/[service]:${{ github.sha }}
```

### 4. Verification
```yaml
# Health check
curl https://[service-url]/health

# Version verification (SHA proof)
curl https://api-cybermat-prd-aca.../version
# Should return: {"sha": "abc123...", "timestamp": "..."}
```

## SHA-Based Versioning

Every deployment is tagged with the Git commit SHA:

1. **Image Tag**: `service:${{ github.sha }}`
2. **Environment Variable**: `BUILD_SHA=${{ github.sha }}`
3. **Verification Endpoint**: `/api/version` returns current SHA

This enables:
- Exact version tracking
- Rollback to specific versions
- Audit trail of deployments

## Deployment Commands

### View Deployment History
```bash
# List recent workflow runs
gh run list --workflow=deploy-container-apps.yml --limit=10

# View specific run details
gh run view [run-id]

# Check deployment logs
gh run view [run-id] --log
```

### Trigger Manual Deployment
```bash
# Deploy all services
gh workflow run deploy-container-apps.yml

# Deploy specific service
gh workflow run deploy-container-apps.yml -f deploy_target=api
gh workflow run deploy-container-apps.yml -f deploy_target=web
```

### Monitor Deployment
```bash
# Watch deployment progress
gh run watch

# Check Container App status
az containerapp show --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd --query properties.provisioningState

# View Container App logs
az containerapp logs show --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd --follow
```

## Deployment Stages

### 1. Development
- Local development with Docker Compose
- Hot reload enabled
- Mock services available

### 2. Staging (Auto-deploy)
- Triggered on push to `main`
- Runs integration tests
- Deploys to staging environment
- Smoke tests execute

### 3. Production (Manual)
- Requires manual workflow dispatch
- UAT gate must pass
- Deployment with specific SHA tag
- Post-deployment verification

## Rollback Procedures

### Quick Rollback
```bash
# Find previous successful deployment SHA
gh run list --workflow=deploy-container-apps.yml --status=success

# Deploy previous version
az containerapp update \
  --name api-cybermat-prd-aca \
  --image webcybermatprdacr.azurecr.io/api-cybermat:[previous-sha]
```

### Full Rollback Process
1. Identify last known good SHA
2. Update Container App to previous image
3. Verify health endpoints
4. Check application logs
5. Confirm with UAT smoke test

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing locally
- [ ] PR approved and merged
- [ ] No critical security alerts
- [ ] Release notes prepared

### During Deployment
- [ ] Monitor GitHub Actions progress
- [ ] Watch Container App metrics
- [ ] Check for error logs

### Post-Deployment
- [ ] Health endpoints return 200
- [ ] Version endpoint shows correct SHA
- [ ] UAT smoke tests pass
- [ ] No error spike in monitoring

## Troubleshooting Deployments

### Failed Container App Update
```bash
# Check Container App status
az containerapp show --name [app-name] --resource-group rg-cybermat-prd

# View recent revisions
az containerapp revision list --name [app-name] --resource-group rg-cybermat-prd

# Activate specific revision
az containerapp revision activate --name [app-name] --revision [revision-name]
```

### Image Pull Errors
```bash
# Verify ACR credentials
az acr credential show --name webcybermatprdacr

# Check image exists
az acr repository show-tags --name webcybermatprdacr --repository [service]

# Re-configure Container App registry
az containerapp registry set --name [app-name] \
  --server webcybermatprdacr.azurecr.io \
  --username [username] --password [password]
```

### Health Check Failures
```bash
# Direct health check
curl -v https://[service-url]/health

# Check Container App logs
az containerapp logs show --name [app-name] --resource-group rg-cybermat-prd

# Restart Container App
az containerapp revision restart --name [app-name] --revision [active-revision]
```

## Deployment Metrics

Key metrics to monitor:
- Deployment duration: < 10 minutes
- Health check success rate: > 99%
- Post-deployment error rate: < 1%
- Rollback frequency: < 5% of deployments

## Security Considerations

- All images scanned for vulnerabilities
- Secrets stored in Azure Key Vault
- Deployment requires GitHub Actions approval
- Audit logs for all deployment activities
- Network isolation for Container Apps
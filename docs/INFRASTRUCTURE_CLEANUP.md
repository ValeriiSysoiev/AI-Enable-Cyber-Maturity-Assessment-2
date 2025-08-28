# Infrastructure Cleanup - August 28, 2025

## Summary
Completed full migration to Azure Container Apps for both API and Web services. All Azure App Service resources have been deleted. The entire application now runs on Container Apps for consistency and better scalability.

## Migration Details

### Infrastructure Changes
- **Old Infrastructure (Deleted)**: Azure App Service
  - API: `api-cybermat-prd.azurewebsites.net` (deleted August 27)
  - Web: `web-cybermat-prd.azurewebsites.net` (deleted August 28)
  
- **Current Infrastructure**: Azure Container Apps
  - API: `api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - Web: `web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - Resource Group: `rg-cybermat-prd`

## Files Cleaned Up

### 1. Removed Files
- **Deployment Archives**:
  - `api-source.zip`
  - `test-minimal.zip`
  - `web-deploy.zip`
  - Various deployment logs and status files

- **Duplicate Startup Scripts**:
  - `app/minimal_app.py` (removed, keeping `simple_start.py`)

- **Legacy Workflows**:
  - `.github/workflows/deploy-production.yml` → `.github/workflows/deploy-production.yml.deprecated`

- **Environment Files**:
  - `.env.staging`
  - `web/.env.production.local`

### 2. Updated Files

#### Scripts Updated to Use Container Apps:
- `scripts/setup-azure-secrets.sh`
  - Changed API references from App Service to Container Apps
  - Updated URLs to use Container Apps endpoint

- `scripts/configure_prod_container_apps.sh`
  - Updated API URLs to Container Apps endpoint
  - Fixed health check URLs
  - Corrected container app names

#### Web Proxy Routes Updated:
All proxy routes now point to Container Apps API:
- `web/app/api/proxy/[...path]/route.ts`
- `web/app/api/proxy/engagements/route.ts`
- `web/app/api/proxy/assessments/route.ts`
- `web/app/api/engagements/route.ts`
- `web/lib/assessments.ts`

#### Environment Configuration:
- `.env.production` - Consolidated with Container Apps URLs
- `.env.production.example` - Updated with correct Container Apps endpoints

### 3. Active Deployment Workflows
- `.github/workflows/deploy-container-apps.yml` - Primary deployment workflow
- Uses Azure Container Registry (ACR) for Docker images
- Deploys to Container Apps infrastructure

## Current Architecture

```
Production Environment (100% Container Apps):
├── API Container App
│   ├── Name: api-cybermat-prd-aca
│   ├── URL: api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io
│   ├── Runtime: Python 3.11
│   ├── Framework: FastAPI
│   ├── Startup: simple_start.py
│   └── Image: webcybermatprdacr.azurecr.io/api-cybermat:latest
│
├── Web Container App
│   ├── Name: web-cybermat-prd-aca
│   ├── URL: web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io
│   ├── Runtime: Node.js 20 (Alpine)
│   ├── Framework: Next.js 14.2.31 (Standalone)
│   ├── Proxies API requests to Container Apps API
│   └── Image: webcybermatprdacr.azurecr.io/web-cybermat-prd:latest
│
└── Shared Resources
    ├── Container Apps Environment: cae-cybermat-prd
    ├── ACR: webcybermatprdacr.azurecr.io
    ├── Cosmos DB: For data storage
    ├── Azure Storage: For file storage
    ├── Service Bus: For async processing
    └── Resource Group: rg-cybermat-prd
```

## Verification Commands

```bash
# Check API health
curl https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/health

# Check Web health
curl https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/api/health

# View Container App logs
az containerapp logs show --name api-cybermat-prd-aca --resource-group rg-cybermat-prd
az containerapp logs show --name web-cybermat-prd-aca --resource-group rg-cybermat-prd

# Check current deployments
az containerapp revision list --name api-cybermat-prd-aca --resource-group rg-cybermat-prd
az containerapp revision list --name web-cybermat-prd-aca --resource-group rg-cybermat-prd

# View Container Apps status
az containerapp list --resource-group rg-cybermat-prd -o table
```

## Important Notes

1. **Complete Migration**: Both API and Web now run on Container Apps - no App Service dependencies remain
2. **URLs Changed**: 
   - Old Web: `web-cybermat-prd.azurewebsites.net` → New: `web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
   - Old API: `api-cybermat-prd.azurewebsites.net` → New: `api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
3. **Deployment**: Use the updated `deploy-container-apps.yml` workflow for both services
4. **Secrets**: Managed through GitHub Actions secrets and environment variables in Container Apps
5. **Docker Images**: Both services use Docker images stored in ACR

## Next Steps

1. Monitor the Container Apps deployment for stability
2. Consider migrating Web app to Container Apps for consistency
3. Update any external documentation or client configurations with new API URL
4. Clean up any remaining Azure resources not in use

## Rollback Plan

If issues arise with Container Apps:
1. The infrastructure can be recreated using Terraform configurations in `/infra`
2. Docker images are stored in ACR and can be redeployed
3. All configuration is documented in `.env.production`

---
*Last Updated: August 28, 2025*
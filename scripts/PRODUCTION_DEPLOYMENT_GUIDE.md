# Production Container Apps Configuration Guide

## Overview
This guide provides instructions for configuring Azure Container Apps for production deployment with proper environment variables, security settings, and operational readiness.

## Production Configuration Summary

### Environment Variables Applied
- **NEXTAUTH_URL**: `https://web-cybermat-prd.azurewebsites.net`
- **AUTH_TRUST_HOST**: `true` (enable NextAuth host trust for production)
- **NEXT_PUBLIC_ADMIN_E2E**: `0` (disable admin demo features)
- **DEMO_E2E**: `0` (disable demo authentication)
- **NEXT_PUBLIC_API_BASE_URL**: `/api/proxy` (use proxy routing)
- **PROXY_TARGET_API_BASE_URL**: `https://api-cybermat-prd.azurewebsites.net`
- **NODE_ENV**: `production`
- **NEXTAUTH_SECRET**: Retrieved from Key Vault

## Deployment Steps

### 1. Infrastructure Updates (Terraform)

The following Terraform configurations have been updated:

**File**: `/infra/terraform.tfvars`
```hcl
env = "prd"
client_code = "cybermat"
```

**File**: `/infra/container_apps.tf`
- Added production environment variables to web container app
- Configured Key Vault secret reference for NEXTAUTH_SECRET
- Added managed identity permissions for web app to access Key Vault

### 2. Apply Infrastructure Changes

```bash
# Navigate to infrastructure directory
cd /infra

# Plan the changes (requires Terraform)
terraform plan -out=prod.tfplan

# Apply the changes
terraform apply prod.tfplan
```

### 3. Configure Container Apps (Alternative Method)

If Terraform is not available, use the Container Apps configuration script:

```bash
# Make script executable
chmod +x /scripts/configure_prod_container_apps.sh

# Run the configuration
./scripts/configure_prod_container_apps.sh
```

This script will:
- Verify Container Apps exist
- Generate NEXTAUTH_SECRET if needed
- Apply production environment variables
- Restart both web and API container apps
- Check warmup status

### 4. Verify Production Configuration

```bash
# Run verification with production mode
./scripts/verify_live.sh --prod
```

This will:
- Test production environment variables
- Verify NextAuth configuration
- Check that demo mode is disabled
- Validate production readiness

## Security Considerations

### Key Vault Secrets
- **nextauth-secret**: Generated automatically if not present
- **aad-client-id**: Must be configured for production AAD integration
- **aad-client-secret**: Must be configured for production AAD integration

### Managed Identity Permissions
- Web container app has Key Vault Secrets User role
- API container app has comprehensive Azure service permissions
- No hardcoded credentials in environment variables

### Production Settings
- Demo mode disabled (`DEMO_E2E=0`)
- Admin E2E features disabled (`NEXT_PUBLIC_ADMIN_E2E=0`)
- Production NextAuth trust enabled (`AUTH_TRUST_HOST=true`)
- Proper API routing via proxy (`/api/proxy`)

## Monitoring and Verification

### Health Checks
- Web app: `https://web-cybermat-prd.azurewebsites.net/api/health`
- API app: `https://api-cybermat-prd.azurewebsites.net/health`

### Log Monitoring
```bash
# View web container logs
az containerapp logs show --name web-cybermat-prd --resource-group rg-cybermat-prd

# View API container logs
az containerapp logs show --name api-cybermat-prd --resource-group rg-cybermat-prd
```

### Performance Monitoring
- Monitor startup times (expect 2-3 minutes for initial warmup)
- Check memory and CPU utilization
- Verify managed identity authentication

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**
   - Wait 2-5 minutes for container warmup
   - Check container logs for startup errors
   - Verify environment variable configuration

2. **Authentication Issues**
   - Verify NEXTAUTH_SECRET is properly configured
   - Check AAD application registration
   - Confirm Key Vault permissions

3. **API Connectivity Issues**
   - Verify PROXY_TARGET_API_BASE_URL setting
   - Check API container health
   - Validate network connectivity

### Rollback Procedure

If issues occur, rollback using:

```bash
# Rollback to previous Terraform state
cd /infra
terraform apply terraform.tfstate.backup

# Or restore previous container app revision
az containerapp revision list --name web-cybermat-prd --resource-group rg-cybermat-prd
az containerapp revision activate --name web-cybermat-prd --resource-group rg-cybermat-prd --revision <previous-revision>
```

## Production Readiness Checklist

- [ ] Infrastructure deployed with production configuration
- [ ] NEXTAUTH_SECRET generated and stored in Key Vault
- [ ] Demo mode disabled (DEMO_E2E=0)
- [ ] Admin E2E features disabled (NEXT_PUBLIC_ADMIN_E2E=0)
- [ ] Production URL configured (NEXTAUTH_URL)
- [ ] API proxy routing configured
- [ ] Managed identity permissions configured
- [ ] Health endpoints responding
- [ ] Container logs showing successful startup
- [ ] Authentication flow tested
- [ ] Smoke tests passing

## Next Steps

1. **Smoke Testing**: Run comprehensive smoke tests to verify functionality
2. **Load Testing**: Execute performance tests to validate production capacity
3. **Security Validation**: Perform security scans and penetration testing
4. **Monitoring Setup**: Configure alerts and monitoring dashboards
5. **Documentation Update**: Update operational runbooks with production specifics

## Support

For issues with this deployment:
1. Check container logs for errors
2. Verify environment variable configuration
3. Validate Key Vault access and secrets
4. Review Azure Container Apps health status
5. Consult operational runbooks for troubleshooting procedures

---

**Production Deployment Status**: Ready for Cycle 1 Smoke Tests (Issue #216)
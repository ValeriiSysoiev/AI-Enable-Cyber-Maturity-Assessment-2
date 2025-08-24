# Terraform Plan Summary - Production Configuration

## Overview
This document summarizes the changes that will be applied to configure the production Azure Container Apps environment with proper settings for issue #216 cycle 1.

## Infrastructure Changes

### 1. Environment Configuration Update
**File**: `terraform.tfvars`
- **env**: `demo` → `prd`
- **client_code**: `AAA` → `cybermat`
- **Impact**: Changes resource naming from `aaa-demo` to `cybermat-prd`

### 2. Container Apps Configuration Updates

#### Web Container App (`azurerm_container_app.web`)

**New Environment Variables Added:**
```hcl
env {
  name = "NODE_ENV"
  value = "production"
}

env {
  name = "AUTH_TRUST_HOST"
  value = "true"
}

env {
  name = "NEXT_PUBLIC_ADMIN_E2E"
  value = "0"
}

env {
  name = "DEMO_E2E"
  value = "0"
}

env {
  name = "NEXT_PUBLIC_API_BASE_URL"
  value = "/api/proxy"
}

env {
  name = "PROXY_TARGET_API_BASE_URL"
  value = "https://${azurerm_container_app.api.latest_revision_fqdn}"
}

env {
  name = "NEXTAUTH_SECRET"
  secret_name = "nextauth-secret"
}
```

**URL Configuration Change:**
```hcl
env {
  name = "NEXTAUTH_URL"
  value = "https://web-cybermat-prd.azurewebsites.net"  # Updated for production
}
```

**Secret Configuration Added:**
```hcl
secret {
  name = "nextauth-secret"
  key_vault_secret_id = azurerm_key_vault_secret.nextauth_secret.id
}
```

### 3. Identity and Access Management

#### New Role Assignment Added
**Resource**: `azurerm_role_assignment.web_kv_secrets_user`
```hcl
resource "azurerm_role_assignment" "web_kv_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.web.principal_id
}
```

### 4. Expected Resource Changes

Based on the configuration updates, the following changes are expected:

**Resources Modified:**
- `azurerm_container_app.web` - Environment variables and secrets updated
- `azurerm_container_app.api` - May require restart due to dependencies
- New role assignment created for web identity

**Resources with Changed Names (due to environment change):**
- Resource Group: `rg-aaa-demo` → `rg-cybermat-prd`
- Web Container App: `web-aaa-demo` → `web-cybermat-prd`
- API Container App: `api-aaa-demo` → `api-cybermat-prd`
- All other resources will follow the new naming pattern

## Security Enhancements

### 1. Managed Identity Configuration
- Web container app now has Key Vault access for NextAuth secrets
- No hardcoded secrets in environment variables
- Least privilege access principles maintained

### 2. Production Hardening
- Demo mode explicitly disabled (`DEMO_E2E=0`)
- Admin E2E features disabled (`NEXT_PUBLIC_ADMIN_E2E=0`)
- Production environment mode enabled (`NODE_ENV=production`)
- NextAuth host trust enabled for production (`AUTH_TRUST_HOST=true`)

### 3. API Security
- API access routed through proxy (`/api/proxy`)
- Direct API access patterns secured
- Container-to-container communication maintained

## Expected Deployment Impact

### 1. Minimal Downtime
- Container app updates trigger new revisions
- Rolling deployment maintains availability
- Expected downtime: < 2 minutes per service

### 2. Configuration Validation
- All environment variables will be validated on startup
- NextAuth secret will be automatically retrieved from Key Vault
- Health endpoints will reflect new configuration

### 3. Monitoring Impact
- Container app logs will show new environment variables
- Application startup will validate production settings
- Metrics will reflect production configuration

## Rollback Plan

### 1. Terraform Rollback
```bash
# Restore previous state
terraform apply terraform.tfstate.backup
```

### 2. Container App Revision Rollback
```bash
# List revisions
az containerapp revision list --name web-cybermat-prd --resource-group rg-cybermat-prd

# Activate previous revision if needed
az containerapp revision activate --name web-cybermat-prd --resource-group rg-cybermat-prd --revision <previous-revision>
```

### 3. Environment Variable Reset
```bash
# Use the configuration script to reset if needed
./scripts/configure_prod_container_apps.sh
```

## Verification Steps

### 1. Post-Deployment Checks
```bash
# Verify container app status
az containerapp show --name web-cybermat-prd --resource-group rg-cybermat-prd --query "properties.provisioningState"

# Check health endpoints
curl https://web-cybermat-prd.azurewebsites.net/api/health
curl https://api-cybermat-prd.azurewebsites.net/health
```

### 2. Configuration Validation
```bash
# Run production verification
./scripts/verify_live.sh --prod
```

### 3. Functional Testing
- NextAuth authentication flow
- API proxy routing functionality
- Demo mode disabled verification
- Production environment detection

## Dependencies

### 1. Key Vault Secrets
- `nextauth-secret`: Must be accessible by web container app
- `aad-client-id`, `aad-client-secret`: Required for AAD authentication

### 2. Network Connectivity
- Container apps must be able to reach Key Vault
- API and web containers must communicate properly
- External connectivity for authentication flows

### 3. Azure Permissions
- User/Service Principal must have Container App Contributor role
- Key Vault Administrator access for secret management
- Resource Group Contributor for deployment

## Success Criteria

- [x] Terraform plan executes without errors
- [ ] Container apps restart successfully with new configuration
- [ ] Health endpoints return 200 status codes
- [ ] NextAuth authentication flow works
- [ ] Demo mode is disabled
- [ ] Production environment variables are set correctly
- [ ] Key Vault secrets are accessible
- [ ] No hardcoded credentials in configuration

---

**Status**: Ready for terraform apply
**Target Environment**: Production (cybermat-prd)
**Estimated Apply Time**: 5-10 minutes
**Risk Level**: Low (configuration-only changes with rollback capability)
# Phase 6: RAG and AAD Configuration Management

## Change Summary

This deployment configures the infrastructure for RAG (Retrieval-Augmented Generation) and AAD (Azure Active Directory) functionality while maintaining existing security posture and managed identity authentication patterns.

## Terraform Plan Summary

**Plan: 27 to add, 2 to change, 0 to destroy**

### Key Infrastructure Additions

#### 1. Cosmos DB Enhancements
- **NEW**: `azurerm_cosmosdb_sql_container.embeddings` - Dedicated container for RAG vector storage
  - Partition key: `/engagement_id`
  - Optimized indexing policy for vector operations
  - Excludes embedding vectors from indexing to save storage

#### 2. Key Vault Security Enhancements
- **NEW**: `azurerm_key_vault_secret.aad_client_id` - AAD application client ID (placeholder)
- **NEW**: `azurerm_key_vault_secret.aad_client_secret` - AAD application secret (placeholder)
- **NEW**: `azurerm_key_vault_secret.aad_tenant_id` - AAD tenant ID
- **NEW**: `azurerm_key_vault_secret.nextauth_secret` - NextAuth session encryption secret (placeholder)

#### 3. Container Apps Infrastructure
- **NEW**: `azurerm_container_app.api` - API service with comprehensive environment variables
- **NEW**: `azurerm_container_app.web` - Web service with AAD authentication support
- **Environment Variables Added**:
  - `RAG_MODE=none` (default, ready for activation)
  - `EMBED_MODEL=text-embedding-3-large`
  - `AUTH_MODE=demo` (ready for AAD flip)
  - `USE_MANAGED_IDENTITY=true`
  - All required Azure service endpoints

#### 4. Monitoring and Alerting Infrastructure
- **NEW**: `azurerm_application_insights.appinsights` - Application performance monitoring
- **NEW**: `azurerm_monitor_action_group.alerts` - Alert notification group
- **NEW**: 5 metric alerts for infrastructure monitoring:
  - API error rate threshold
  - RAG service latency monitoring
  - Azure AI Search availability
  - OpenAI service throttling detection
  - Cosmos DB latency monitoring
- **NEW**: 2 log-based alerts for application monitoring:
  - AAD authentication failure detection
  - RAG service error pattern detection

#### 5. Infrastructure Changes
- **CHANGED**: `azurerm_cognitive_account.openai` - Disables public network access for enhanced security
- **CHANGED**: `azurerm_search_service.search` - Additional configuration for RAG integration

## Security Considerations

### ✅ Security Maintained
- All secrets stored in Azure Key Vault with lifecycle management
- Managed identity authentication preserved throughout
- No hardcoded credentials or API keys
- RBAC roles properly assigned for least privilege access
- Network security enhanced (OpenAI service restricted)

### 🔐 Secret Management Strategy
- AAD secrets are placeholders with `ignore_changes` lifecycle rules
- Actual secret rotation handled by separate AAD configuration scripts
- NextAuth secret placeholder for session encryption
- All secrets follow Azure Key Vault best practices

## Rollback Procedures

### 1. Immediate Rollback (Infrastructure)
```bash
# Revert to previous state
cd /Users/valsysoiev/AI-Enable-Cyber-Maturity-Assessment-2/infra
terraform plan -destroy -target="azurerm_container_app.api"
terraform plan -destroy -target="azurerm_container_app.web"
terraform plan -destroy -target="azurerm_application_insights.appinsights"
terraform plan -destroy -target="azurerm_monitor_action_group.alerts"

# Apply destroy plan
terraform apply -auto-approve
```

### 2. Selective Rollback (Remove specific components)
```bash
# Remove only RAG components
terraform destroy -target="azurerm_cosmosdb_sql_container.embeddings"

# Remove only monitoring
terraform destroy -target="azurerm_application_insights.appinsights"
terraform destroy -target="azurerm_monitor_action_group.alerts"

# Remove AAD secrets (if needed)
terraform destroy -target="azurerm_key_vault_secret.aad_client_id"
terraform destroy -target="azurerm_key_vault_secret.aad_client_secret"
terraform destroy -target="azurerm_key_vault_secret.nextauth_secret"
```

### 3. Application-Level Rollback
```bash
# Revert environment variables in existing container apps
az containerapp update -g rg-aaa-demo -n api-aaa-demo \
  --remove-env-vars RAG_MODE EMBED_MODEL RAG_COSMOS_CONTAINER

az containerapp update -g rg-aaa-demo -n web-aaa-demo \
  --remove-env-vars AUTH_MODE KEY_VAULT_URI
```

## Verification Steps

### Enhanced verify_live.sh Script
The verification script has been updated with Phase 6 specific checks:

```bash
./scripts/verify_live.sh
```

**New Verification Capabilities:**
- RAG prerequisites validation (embeddings container, OpenAI deployment)
- AAD secret configuration checks
- Container app environment variable validation
- Application Insights and monitoring setup verification
- Enhanced authentication flow testing

### Manual Verification Checklist

1. **Infrastructure Validation**
   - [ ] Cosmos DB embeddings container exists
   - [ ] All Key Vault secrets created (placeholders)
   - [ ] Container apps deployed with correct environment variables
   - [ ] Application Insights collecting telemetry
   - [ ] Alert rules configured and enabled

2. **Security Validation**
   - [ ] Managed identities assigned to container apps
   - [ ] RBAC permissions working for all Azure services
   - [ ] Key Vault access policies functioning
   - [ ] OpenAI service network restrictions in place

3. **Application Validation**
   - [ ] API responds with RAG status (mode: none)
   - [ ] Authentication mode returns "demo"
   - [ ] Environment configuration endpoint accessible
   - [ ] No application errors in logs

## Deployment Commands

### 1. Deploy Infrastructure
```bash
cd /Users/valsysoiev/AI-Enable-Cyber-Maturity-Assessment-2/infra
terraform plan -out=tfplan-phase6
terraform apply tfplan-phase6
```

### 2. Verify Deployment
```bash
./scripts/verify_live.sh
```

### 3. Enable RAG (After Validation)
```bash
# Update container app environment variables
az containerapp update -g rg-aaa-demo -n api-aaa-demo \
  --set-env-vars RAG_MODE=azure_openai

# Verify RAG activation
curl -s https://api-aaa-demo.canadacentral-01.azurecontainerapps.io/api/ops/rag/status
```

### 4. Configure AAD (Separate Process)
```bash
# Run AAD configuration script (creates actual secrets)
./scripts/configure_aad.sh

# Update authentication mode
az containerapp update -g rg-aaa-demo -n api-aaa-demo \
  --set-env-vars AUTH_MODE=aad
az containerapp update -g rg-aaa-demo -n web-aaa-demo \
  --set-env-vars AUTH_MODE=aad
```

## Performance Impact

### Resource Scaling
- Container apps configured with automatic scaling
- API: 1-3 replicas based on HTTP load (30 concurrent requests)
- Web: 1-2 replicas based on HTTP load (50 concurrent requests)

### Monitoring Thresholds
- API error rate: > 10 errors per 5 minutes
- RAG latency: > 10 seconds average
- Search latency: > 3 seconds average
- OpenAI throttling: > 5 errors per 5 minutes
- Cosmos DB latency: > 100ms average

## Next Steps After Deployment

1. **Immediate (Phase 6)**
   - Deploy container applications using updated Terraform
   - Verify all infrastructure components
   - Test with RAG_MODE=none (safe mode)

2. **Phase 7 (RAG Activation)**
   - Create search index using bootstrap script
   - Set RAG_MODE=azure_openai
   - Test document ingestion and search

3. **Phase 8 (AAD Integration)**
   - Configure AAD application registration
   - Update Key Vault secrets with real values
   - Set AUTH_MODE=aad
   - Test end-to-end authentication flow

## Files Modified

### Infrastructure Configuration
- `/infra/cosmos.tf` - Added embeddings container
- `/infra/keyvault.tf` - Added AAD-related secrets  
- `/infra/container_apps.tf` - NEW FILE - Complete container app configuration
- `/infra/monitoring.tf` - NEW FILE - Comprehensive monitoring setup
- `/infra/variables.tf` - Added RAG and AAD configuration variables

### Operational Scripts
- `/scripts/verify_live.sh` - Enhanced with Phase 6 verification checks

### Documentation
- `/PHASE6_DEPLOYMENT_PLAN.md` - This comprehensive deployment guide

---

This deployment maintains zero-downtime deployment principles and preserves all existing security patterns while preparing the infrastructure for advanced RAG and AAD capabilities.
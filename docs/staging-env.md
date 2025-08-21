# Staging Environment Specification

## Overview

The staging environment provides a production-like testing environment for the AI-Enabled Cyber Maturity Assessment platform, implementing the same architecture with engagement isolation, ABAC authorization, and comprehensive audit trails.

## Architecture Mapping

### Production → Staging Component Alignment

| Component | Production | Staging | Notes |
|-----------|------------|---------|-------|
| **Web App** | `web-prod` | `web-staging` | Next.js with SSR route guards |
| **API Service** | `api-prod` | `api-staging` | FastAPI with ABAC enforcement |
| **MCP Gateway** | `mcp-prod` | `mcp-staging` | Model Context Protocol tools |
| **Container Environment** | `prod-env` | `staging-env` | Azure Container Apps |
| **Resource Group** | `rg-prod` | `rg-staging` | Isolated Azure resources |

## Required GitHub Variables

### OIDC Authentication
```
AZURE_CLIENT_ID          # Service principal for staging OIDC
AZURE_TENANT_ID          # Azure AD tenant ID  
AZURE_SUBSCRIPTION_ID    # Staging subscription ID
```

### Container Registry
```
GHCR_ENABLED=1           # Enable GitHub Container Registry
GHCR_TOKEN               # GitHub token with packages:write
```

### Azure Container Apps
```
ACA_RG                   # Resource group name (e.g., rg-aecma-staging)
ACA_ENV                  # Container environment (e.g., cae-aecma-staging)
ACA_APP_API              # API app name (e.g., api-staging)
ACA_APP_WEB              # Web app name (e.g., web-staging)
ACA_APP_MCP              # MCP Gateway app name (e.g., mcp-staging)
```

### Service URLs
```
STAGING_URL              # Main web app URL (e.g., https://web-staging.region.azurecontainerapps.io)
API_BASE_URL             # API service URL (e.g., https://api-staging.region.azurecontainerapps.io)  
MCP_GATEWAY_URL          # MCP Gateway URL (e.g., https://mcp-staging.region.azurecontainerapps.io)
```

## Health Check Endpoints

### Web Application
- **URL**: `${STAGING_URL}/api/health`
- **Method**: GET
- **Expected**: 200 OK with uptime and version

### API Service  
- **URL**: `${API_BASE_URL}/health`
- **Method**: GET
- **Expected**: 200 OK with service status

### MCP Gateway
- **URL**: `${MCP_GATEWAY_URL}/health`
- **Method**: GET
- **Expected**: 200 OK with tool availability

## Security Framework Implementation

### ABAC Authorization
- **Engagement Isolation**: Users restricted to assigned engagement resources
- **Resource Scoping**: Audit bundles, MCP tools, downloads scoped by engagement_id
- **JWT Claims**: Role-based permissions with engagement context
- **Admin Override**: System admin bypass with audit logging

### Audit Trails
- **Correlation IDs**: Request tracing across all services
- **Structured Logging**: JSON format with standardized fields
- **Immutable Events**: Tamper-proof audit event storage
- **Compliance**: SOC 2 and GDPR audit trail requirements

### Data Isolation
- **Test Data**: Staging-specific datasets with anonymized PII
- **Database Separation**: Isolated Cosmos DB containers for staging
- **Storage Isolation**: Separate Azure Storage accounts and containers
- **AI Service Isolation**: Dedicated OpenAI and Search service instances

## Environment Configuration

### Feature Flags
```
STAGING_ENV=true         # Enable staging-specific behaviors
MCP_ENABLED=true         # Enable Model Context Protocol tools
MCP_CONNECTORS_SP=false  # Disable SharePoint in staging (optional)
MCP_CONNECTORS_JIRA=false # Disable Jira in staging (optional)
UAT_MODE=true            # Enable UAT-specific validation
```

### Performance Settings
```
API_RESPONSE_THRESHOLD=5000    # 5s timeout for staging
SEARCH_RESPONSE_THRESHOLD=3000 # 3s search timeout
RAG_RESPONSE_THRESHOLD=10000   # 10s RAG processing
```

### Monitoring
```
LOG_LEVEL=DEBUG          # Verbose logging for staging
ENABLE_METRICS=true      # Performance metrics collection
AUDIT_VERBOSE=true       # Detailed audit logging
```

## Deployment Verification

### Automated Health Checks
```bash
# Verify staging deployment
./scripts/verify_live.sh --staging

# Check all health endpoints
curl -f $STAGING_URL/api/health
curl -f $API_BASE_URL/health  
curl -f $MCP_GATEWAY_URL/health
```

### Feature Validation
```bash
# Test ABAC enforcement
./scripts/test_abac_staging.sh

# Validate MCP tools
./scripts/test_mcp_tools.sh --staging

# UAT governance checks
./scripts/verify_live.sh --governance --staging
```

## Security Considerations

### Network Security
- **HTTPS Only**: All staging endpoints require TLS
- **Private Endpoints**: Database and storage use private endpoints
- **Network Isolation**: Virtual network integration for Container Apps
- **WAF Protection**: Web Application Firewall for external endpoints

### Identity & Access
- **Managed Identity**: No hardcoded credentials in staging
- **RBAC**: Role-based access control at Azure resource level
- **Key Vault**: Secure secret management with audit logging
- **OIDC**: OpenID Connect for secure CI/CD authentication

### Data Protection
- **PII Anonymization**: Test data with sensitive information scrubbed
- **Encryption**: Data encrypted at rest and in transit
- **Backup Isolation**: Staging backups separate from production
- **Retention Policies**: Automated cleanup of staging data

## Troubleshooting

### Common Issues

**Container App Startup Failures**
```bash
# Check container logs
az containerapp logs show -n $ACA_APP_API -g $ACA_RG --tail 50

# Verify environment variables
az containerapp show -n $ACA_APP_API -g $ACA_RG --query properties.configuration.activeRevisionsMode
```

**Health Check Failures**
```bash
# Test connectivity
curl -v $STAGING_URL/api/health
nslookup $(echo $STAGING_URL | sed 's/https:\/\///')

# Check DNS resolution
dig +short $(echo $STAGING_URL | sed 's/https:\/\///')
```

**Authentication Issues**
```bash
# Verify managed identity
az identity list -g $ACA_RG
az role assignment list --assignee $(az identity show -n staging-identity -g $ACA_RG --query principalId -o tsv)
```

### Support Contacts
- **Infrastructure**: Platform Engineering Team
- **Security**: Security Architecture Team  
- **Compliance**: Legal and Compliance Team
- **Emergency**: On-call rotation via incident management system
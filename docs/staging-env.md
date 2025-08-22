# Staging Environment Setup Guide

## Overview

This guide explains how to configure and deploy the staging environment using GitHub Actions with either Azure App Service or Azure Container Apps.

## Repository Variables Configuration

Navigate to **Settings → Secrets and variables → Actions → Variables** in your GitHub repository and configure the following variables:

### Required Variables (All Scenarios)

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `GHCR_ENABLED` | Enable GitHub Container Registry builds | `1` |

### Scenario A: App Service Staging Only

For existing App Service deployments, set only the staging URL:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `STAGING_URL` | Direct URL to your App Service staging slot | `https://myapp-staging.azurewebsites.net` |

**Important**: Leave `ACA_ENV` empty to skip Container Apps deployment.

### Scenario B: Container Apps Staging

For full Azure Container Apps deployment:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `87654321-4321-4321-4321-210987654321` |
| `AZURE_CLIENT_ID` | Service principal client ID | `abcdef12-3456-7890-abcd-ef1234567890` |
| `ACA_RG` | Resource group name | `rg-aecma-staging` |
| `ACA_ENV` | Container Apps environment name | `env-aecma-staging` |
| `ACA_APP_API` | API container app name | `app-aecma-api-staging` |
| `ACA_APP_WEB` | Web container app name | `app-aecma-web-staging` |
| `STAGING_URL` | (Optional) Override computed URL | `https://custom-staging.domain.com` |

## Deployment Paths

### Path A: App Service Only

1. **Configure Variables**:
   - Set `GHCR_ENABLED=1`
   - Set `STAGING_URL` to your App Service staging slot URL
   - Leave `ACA_ENV` empty or unset

2. **Workflow Behavior**:
   - ✅ GHCR build/push runs (Docker images built and pushed)
   - ❌ Azure Container Apps deploy step skips (due to missing `ACA_ENV`)
   - ✅ GitHub staging environment auto-creates

3. **Verification**:
   ```bash
   ./scripts/verify_live.sh --staging
   ```

### Path B: Container Apps Full Deploy

1. **Configure Variables**:
   - Set all `AZURE_*` variables with proper service principal credentials
   - Set all `ACA_*` variables with your Container Apps resource names
   - Optionally set `STAGING_URL` to override computed URL

2. **Workflow Behavior**:
   - ✅ GHCR build/push runs
   - ✅ Azure Container Apps deploy runs (updates container images)
   - ✅ GitHub staging environment auto-creates with computed URL

3. **Verification**:
   ```bash
   ./scripts/verify_live.sh --staging
   ```

## Environment Auto-Creation

The workflow includes an `environment` block that automatically creates a GitHub environment named "staging" when the workflow runs:

```yaml
environment:
  name: staging
```

This enables:
- Environment-specific protection rules
- Deployment approvals (if configured)
- Environment-specific secrets and variables
- Deployment history tracking

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
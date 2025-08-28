# Configuration

## Overview

Environment configuration for the AI-Enabled Cyber Maturity Assessment platform. This document lists configuration keys only - actual secret values are stored in Azure Key Vault and GitHub Secrets.

## Environment Variables

### Web Application (Container Apps)

| Variable | Description | Location | Example |
|----------|-------------|----------|---------|
| `NODE_ENV` | Environment mode | Container App | `production` |
| `AUTH_MODE` | Authentication type | Container App | `aad` |
| `NEXTAUTH_URL` | NextAuth callback URL | Container App | `https://web-cybermat-prd-aca...` |
| `NEXTAUTH_SECRET` | Session encryption key | GitHub Secret | `{generated}` |
| `PROXY_TARGET_API_BASE_URL` | Backend API URL | Container App | `https://api-cybermat-prd-aca...` |
| `API_BASE_URL` | API base URL | Container App | `https://api-cybermat-prd-aca...` |
| `NEXT_PUBLIC_API_BASE_URL` | Client-side API path | Container App | `/api/proxy` |
| `AZURE_AD_TENANT_ID` | AAD tenant ID | GitHub Secret | `{guid}` |
| `AZURE_AD_CLIENT_ID` | AAD application ID | GitHub Secret | `{guid}` |
| `AZURE_AD_CLIENT_SECRET` | AAD client secret | GitHub Secret | `{secret}` |
| `AUTH_TRUST_HOST` | Trust host header | Container App | `true` |
| `ADMIN_EMAILS` | Admin user emails | GitHub Secret | `admin1@org.com,admin2@org.com` |
| `ENVIRONMENT` | Deployment environment | Container App | `production` |
| `BUILD_SHA` | Git commit SHA | Container App | `{auto-set}` |

### API Application (Container Apps)

| Variable | Description | Location | Example |
|----------|-------------|----------|---------|
| `AUTH_MODE` | Authentication type | Container App | `aad` |
| `AZURE_AD_TENANT_ID` | AAD tenant ID | GitHub Secret | `{guid}` |
| `AZURE_AD_CLIENT_ID` | AAD application ID | GitHub Secret | `{guid}` |
| `AZURE_AD_CLIENT_SECRET` | AAD client secret | GitHub Secret | `{secret}` |
| `ADMIN_EMAILS` | Admin user emails | GitHub Secret | `admin1@org.com,admin2@org.com` |
| `DATA_BACKEND` | Data storage type | Container App | `cosmos` |
| `COSMOS_DB_ENDPOINT` | Cosmos DB endpoint | GitHub Secret | `https://{account}.documents.azure.com` |
| `COSMOS_DB_KEY` | Cosmos DB key | GitHub Secret | `{key}` |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection | GitHub Secret | `{connection-string}` |
| `AZURE_SERVICE_BUS_CONNECTION_STRING` | Service Bus connection | GitHub Secret | `{connection-string}` |
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint | GitHub Secret | `https://{resource}.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | OpenAI API key | GitHub Secret | `{key}` |
| `AZURE_SEARCH_ENDPOINT` | AI Search endpoint | GitHub Secret | `https://{service}.search.windows.net` |
| `AZURE_SEARCH_KEY` | AI Search key | GitHub Secret | `{key}` |
| `ENVIRONMENT` | Deployment environment | Container App | `production` |
| `LOG_LEVEL` | Logging verbosity | Container App | `info` |
| `BUILD_SHA` | Git commit SHA | Container App | `{auto-set}` |

## GitHub Actions Configuration

### Repository Secrets

Configure in: **Settings → Secrets and variables → Actions → Secrets**

| Secret | Description | Used By |
|--------|-------------|---------|
| `AZURE_CREDENTIALS` | Service principal JSON | Deployment workflows |
| `AZURE_AD_TENANT_ID` | AAD tenant | Both apps |
| `AZURE_AD_CLIENT_ID` | AAD app ID | Both apps |
| `AZURE_AD_CLIENT_SECRET` | AAD secret | Both apps |
| `NEXTAUTH_SECRET` | Session key | Web app |
| `ADMIN_EMAILS` | Admin users | Both apps |
| `COSMOS_DB_ENDPOINT` | Database URL | API |
| `COSMOS_DB_KEY` | Database key | API |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection | API |
| `AZURE_SERVICE_BUS_CONNECTION_STRING` | Service bus | API |
| `AZURE_OPENAI_ENDPOINT` | AI endpoint | API |
| `AZURE_OPENAI_API_KEY` | AI key | API |
| `AZURE_SEARCH_ENDPOINT` | Search URL | API |
| `AZURE_SEARCH_KEY` | Search key | API |

### Repository Variables

Configure in: **Settings → Secrets and variables → Actions → Variables**

| Variable | Description | Value |
|----------|-------------|-------|
| `AZURE_RESOURCE_GROUP` | Resource group name | `rg-cybermat-prd` |
| `API_CONTAINER_APP` | API app name | `api-cybermat-prd-aca` |
| `WEB_CONTAINER_APP` | Web app name | `web-cybermat-prd-aca` |
| `ACR_NAME` | Container registry | `webcybermatprdacr` |

## Container Apps Configuration

### API Container App Settings

```bash
# View current configuration
az containerapp show --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query properties.configuration.secrets

# Update environment variables
az containerapp update --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --set-env-vars KEY=value
```

### Web Container App Settings

```bash
# View current configuration
az containerapp show --name web-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query properties.configuration.secrets

# Update environment variables
az containerapp update --name web-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --set-env-vars KEY=value
```

## Local Development Configuration

### `.env.local` (Web)
```env
NODE_ENV=development
AUTH_MODE=demo
NEXT_PUBLIC_API_BASE_URL=/api/proxy
PROXY_TARGET_API_BASE_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=development-secret-change-in-production
```

### `.env` (API)
```env
AUTH_MODE=demo
DATA_BACKEND=local
ENVIRONMENT=development
LOG_LEVEL=debug
```

## Configuration Validation

### Health Check Endpoints

Both applications expose health endpoints that validate configuration:

```bash
# API health (includes config validation)
curl https://api-cybermat-prd-aca.../health

# Web health
curl https://web-cybermat-prd-aca.../api/health
```

### Version Endpoint

Confirms BUILD_SHA is properly set:

```bash
curl https://api-cybermat-prd-aca.../version
# Returns: {"sha": "abc123...", "timestamp": "2025-08-28T..."}
```

## Configuration Best Practices

1. **Never commit secrets** - Use environment variables and secret stores
2. **Validate on startup** - Applications should fail fast on missing config
3. **Use defaults wisely** - Production should require explicit configuration
4. **Document all keys** - Keep this document updated with new variables
5. **Rotate secrets regularly** - Quarterly rotation for all secrets
6. **Audit access** - Log all secret access and configuration changes

## Troubleshooting Configuration

### Missing Environment Variables

**Symptom**: Application fails to start or returns 500 errors

**Check**:
```bash
# List Container App environment variables
az containerapp show --name [app-name] \
  --resource-group rg-cybermat-prd \
  --query properties.template.containers[0].env
```

### Invalid Azure AD Configuration

**Symptom**: Authentication fails with "invalid_client" error

**Check**:
- Verify AZURE_AD_CLIENT_ID matches app registration
- Confirm NEXTAUTH_URL matches redirect URI in app registration
- Ensure AZURE_AD_CLIENT_SECRET is not expired

### Database Connection Issues

**Symptom**: API returns "Service Unavailable" errors

**Check**:
- Verify COSMOS_DB_ENDPOINT is correct
- Confirm COSMOS_DB_KEY is valid
- Check network connectivity to Cosmos DB

## Security Notes

- All production secrets must be stored in Azure Key Vault
- Use managed identities where possible instead of keys
- Enable audit logging for all configuration changes
- Implement secret scanning in CI/CD pipeline
- Never log configuration values, only keys
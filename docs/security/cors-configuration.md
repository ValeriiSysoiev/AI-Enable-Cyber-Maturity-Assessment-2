# CORS Configuration Guide

## Overview

Cross-Origin Resource Sharing (CORS) configuration is critical for the security of the AI Maturity Assessment platform. This guide documents the proper configuration for different environments.

## Security Requirements

### Production Environment

1. **NO WILDCARD ORIGINS**: Never use `*` in production
2. **HTTPS ONLY**: All production origins must use HTTPS
3. **EXPLICIT CONFIGURATION**: Origins must be explicitly set via `API_ALLOWED_ORIGINS`
4. **NO LOCALHOST**: Never include localhost/127.0.0.1 in production

### Staging Environment

1. Similar to production but may include staging-specific domains
2. Should still use HTTPS for all origins
3. May include test domains but not localhost

### Development Environment

1. Can include localhost origins for local development
2. HTTP is acceptable for local origins
3. Should still avoid wildcard if possible

## Configuration

### Environment Variable

Set the `API_ALLOWED_ORIGINS` environment variable with comma-separated origins:

```bash
# Production
API_ALLOWED_ORIGINS=https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io,https://web-cybermat-prd.azurecontainerapps.io

# Staging
API_ALLOWED_ORIGINS=https://web-cybermat-stg-aca.icystone-69c102b0.westeurope.azurecontainerapps.io,https://web-cybermat-stg.azurecontainerapps.io

# Development
API_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000
```

### Azure Configuration

For Azure Container Apps or App Service:

```bash
# Set via Azure CLI
az webapp config appsettings set \
  --name api-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --settings API_ALLOWED_ORIGINS="https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io"

# Or via Portal
# Navigate to Configuration > Application settings
# Add new setting: API_ALLOWED_ORIGINS
```

### Docker Configuration

In `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - API_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## Configuration Helper

Use the provided configuration helper script:

```bash
# Run from the app directory
python scripts/configure_cors.py
```

This will:
- Detect your current environment
- Recommend appropriate origins
- Validate your current configuration
- Generate the correct environment variable

## Security Features

### Automatic Protection

The application includes several automatic security features:

1. **Production Validation**: The API will fail to start if CORS is misconfigured in production
2. **Wildcard Detection**: If wildcard is detected, credentials are automatically disabled
3. **Logging**: All CORS configuration is logged at startup for audit purposes

### Error Messages

If misconfigured, you'll see:

```
CRITICAL: No CORS origins configured for production! Set API_ALLOWED_ORIGINS environment variable.
```

or

```
CRITICAL: Wildcard CORS origin (*) is not allowed in production!
```

## Testing CORS

### Manual Testing

Test CORS configuration with curl:

```bash
# Preflight request
curl -X OPTIONS https://api-cybermat-prd.azurecontainerapps.io/health \
  -H "Origin: https://web-cybermat-prd.azurecontainerapps.io" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-User-Email" \
  -v

# Should see:
# Access-Control-Allow-Origin: https://web-cybermat-prd.azurecontainerapps.io
# Access-Control-Allow-Credentials: true
```

### Automated Testing

Run the CORS security tests:

```bash
cd app
python -m pytest tests/test_cors_security.py -v
```

## Common Issues

### Issue: CORS errors in browser console

**Solution**: Ensure the frontend domain is in `API_ALLOWED_ORIGINS`

### Issue: API fails to start in production

**Solution**: Set `API_ALLOWED_ORIGINS` with proper HTTPS origins

### Issue: Credentials not working

**Solution**: Check that wildcard isn't being used with credentials

## Best Practices

1. **Regular Review**: Review CORS configuration quarterly
2. **Minimal Origins**: Only include necessary origins
3. **Remove Old Origins**: Clean up unused domains
4. **Document Changes**: Log all CORS configuration changes
5. **Test Thoroughly**: Test after any domain changes

## Security Checklist

- [ ] No wildcard (*) in production
- [ ] All production origins use HTTPS
- [ ] API_ALLOWED_ORIGINS is set in production
- [ ] No localhost in production configuration
- [ ] Credentials only enabled for specific origins
- [ ] Configuration is logged at startup
- [ ] Regular security audits performed

## Migration from Wildcard

If currently using wildcard origins:

1. Identify all legitimate frontend domains
2. Set `API_ALLOWED_ORIGINS` with those domains
3. Deploy and test thoroughly
4. Monitor for any CORS errors
5. Add missing origins if needed (after verification)

## Contact

For CORS configuration assistance, contact the DevOps team or security team.
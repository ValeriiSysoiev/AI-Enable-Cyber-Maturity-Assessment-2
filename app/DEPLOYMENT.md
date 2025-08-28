# Production Deployment Guide

This guide explains how to deploy the full FastAPI application to Azure App Service.

## Quick Start

The application now supports graceful startup with automatic fallback:

1. **Primary**: Full FastAPI application with all endpoints
2. **Fallback**: Minimal health check server if dependencies fail

## Startup Scripts

### For Production (Azure App Service)
```bash
# Use the production startup script (recommended)
python start_production.py
```

### For Development/Testing
```bash
# Direct FastAPI startup
python simple_start.py

# Or with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Available Endpoints

After successful deployment, these endpoints will be available:

### Core Health & Status
- `GET /api/health` - Basic health check
- `GET /health` - Alternative health endpoint
- `GET /api/version` - Version info with git SHA
- `GET /api/features` - Feature flags status
- `GET /api/admin/status` - Comprehensive system status

### Business Logic
- `GET /api/presets` - List assessment presets
- `POST /api/assessments` - Create new assessments
- `GET /api/assessments/{id}` - Get assessment details
- `GET /api/engagements` - List engagements
- `GET /api/performance/metrics` - Performance monitoring

## Environment Variables

### Required
- `PORT` - Server port (default: 8000)

### Optional Configuration
- `CI_MODE=1` - Use minimal server for CI/testing
- `GRACEFUL_STARTUP=1` - Enable graceful dependency handling (default: enabled)
- `DISABLE_ML=1` - Disable ML/AI features
- `LOG_LEVEL=INFO` - Logging level

### Azure Services (optional)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_SEARCH_ENDPOINT` - Azure AI Search endpoint
- `AAD_TENANT_ID` - Azure AD tenant for authentication

## Deployment Strategy

### Phase 1: Health Check (Current)
- Minimal health API working at `/api/health`
- Returns 200 OK with basic system info

### Phase 2: Full API (This Update)
- All FastAPI endpoints enabled
- Graceful degradation if services unavailable
- Comprehensive monitoring and status endpoints

### Phase 3: Production Hardening (Future)
- Full authentication and authorization
- Complete Azure service integration
- Performance optimization

## Testing

Test the deployment locally:

```bash
# Start the server
cd /app
python start_production.py

# In another terminal, test endpoints
python test_endpoints.py
```

Expected successful test output:
```
Testing Health Check: http://localhost:8000/api/health
  ✓ Status: 200
  ✓ Valid JSON response
  ✓ Status: healthy

Testing Version Info: http://localhost:8000/api/version
  ✓ Status: 200
  ✓ Valid JSON response
  ✓ Git SHA: abc123def456

...

Test Summary
============
Passed: 8/8
All tests passed! ✓
```

## Troubleshooting

### If Full App Fails to Start
The system will automatically fall back to minimal health server. Check logs:

```bash
# Check Azure App Service logs
az webapp log tail --name your-app-name --resource-group your-rg
```

Common issues:
1. **Missing dependencies**: Install requirements.txt
2. **Database connection**: Check connection strings
3. **Azure service config**: Verify environment variables

### Force Minimal Mode
```bash
export CI_MODE=1
python start_production.py
```

## Production URL
After deployment, test the production endpoints:
- https://api-cybermat-prd.azurewebsites.net/api/health
- https://api-cybermat-prd.azurewebsites.net/api/version
- https://api-cybermat-prd.azurewebsites.net/api/admin/status

## Monitoring

Use the admin status endpoint for monitoring:
```bash
curl https://api-cybermat-prd.azurewebsites.net/api/admin/status
```

This provides:
- Overall health status
- Individual service status
- System metrics
- Configuration summary
- Error details
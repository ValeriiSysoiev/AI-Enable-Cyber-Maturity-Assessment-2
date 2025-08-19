# App Service Production Diagnostic Bundle

**Date**: Mon 19 Aug 2025 22:42:00 MDT  
**App Service**: api-cybermat-prd  
**Resource Group**: rg-cybermat-prd  
**Subscription**: Azure subscription 1  

## Issue Summary
- **Primary Symptom**: HTTP 503 Service Unavailable on all endpoints
- **Duration**: Persistent issue following code deployment switch from container to runtime
- **Impact**: API completely non-functional, blocking web application backend

## HTTP Probe Results

### All Endpoints Return HTTP/2 503
- `/health`: 40+ second timeout → HTTP 503
- `/`: Immediate HTTP 503  
- `/docs`: 1+ second timeout → HTTP 503

**Key Headers Observed**:
```
HTTP/2 503 
date: Tue, 19 Aug 2025 04:41:13 GMT
set-cookie: ARRAffinity=7d84ad198c6f807fbfa2076d1e286d2bb239ec2b3ab1f48a5008aac89bd50ca3
set-cookie: ARRAffinitySameSite=7d84ad198c6f807fbfa2076d1e286d2bb239ec2b3ab1f48a5008aac89bd50ca3
```

## App Service Configuration Snapshot

### Runtime Configuration
- **State**: Running
- **Runtime**: PYTHON|3.11 ✅
- **Startup Command**: `python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **HTTP Logging**: Enabled

### Environment Variables
- **PORT**: 8000 ✅
- **WEBSITES_PORT**: 8000 ✅  
- **SCM_DO_BUILD_DURING_DEPLOYMENT**: true ✅
- **WEBSITE_RUN_FROM_PACKAGE**: 0 (source deployment)

## Issue Characteristics

### Primary Indicators
1. **Long timeouts** on /health (40+ seconds) suggest process startup issues
2. **Immediate 503s** on other endpoints suggest routing/process issues  
3. **ARRAffinity cookies** indicate load balancer is functioning
4. **HTTP/2 response** confirms front-end infrastructure working

### Root Cause Hypothesis
- **Python process not starting** despite correct configuration
- **Module import/dependency issues** preventing uvicorn startup
- **Port binding failures** (though PORT settings appear correct)
- **Working directory issues** affecting module resolution

## Diagnostic Attempts Made
1. ✅ Enhanced logging enabled (application + web server)
2. ✅ Service restart performed
3. ✅ 30-second log tail attempted (no output captured)
4. ✅ HTTP probes from multiple endpoints

## Next Steps for Investigation
1. **Safe repair cycles** with startup command variants
2. **Module path resolution** fixes
3. **Package deployment** mode testing
4. **Container Apps fallback** if App Service path exhausted

## Files in Bundle
- `http-probe-health.txt` - /health endpoint HTTP response headers
- `http-probe-root.txt` - / endpoint HTTP response headers  
- `http-probe-docs.txt` - /docs endpoint HTTP response headers
- `README.md` - This diagnostic summary

## Support Ticket Information
- **Resource ID**: `/subscriptions/10233675-d493-4a97-9c81-4001e353a7bb/resourceGroups/rg-cybermat-prd/providers/Microsoft.Web/sites/api-cybermat-prd`
- **Error Pattern**: Persistent HTTP 503 on Python FastAPI application
- **Configuration Verified**: Runtime, ports, startup command, logging all correct
- **Timeline**: Issue persists after multiple restart cycles and configuration verification
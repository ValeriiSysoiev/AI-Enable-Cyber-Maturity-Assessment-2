# Azure Container Apps Performance Optimization - Terraform Plan Summary

## Overview
This document outlines the infrastructure changes required to optimize Azure Container Apps for production performance. The changes address identified bottlenecks in CPU allocation, memory constraints, scaling behavior, and monitoring.

## Performance Issues Identified
- **Insufficient Resources**: Both API and Web containers allocated only 0.25 CPU and 0.5Gi memory
- **Low Scaling Limits**: API max replicas = 3, Web max replicas = 2 
- **Aggressive Scaling Thresholds**: 30 concurrent requests for API, 50 for Web
- **Missing Health Checks**: No startup/readiness probes causing slow deployments
- **Import/Configuration Errors**: Application startup failures due to configuration issues

## Resource Changes Summary

### 1. Container Apps Performance Optimization

#### API Container App (`azurerm_container_app.api`)
**Resource Scaling:**
- **CPU Allocation**: `0.25` → `0.75` cores (3x improvement)
- **Memory Allocation**: `0.5Gi` → `1.5Gi` (3x improvement) 
- **Minimum Replicas**: `1` → `2` (availability improvement)
- **Maximum Replicas**: `3` → `10` (scaling capacity increase)
- **HTTP Scaling Threshold**: `30` → `50` concurrent requests

**Performance Environment Variables Added:**
```hcl
env {
  name  = "UVICORN_WORKERS"
  value = "2"  # Multiple workers for concurrent processing
}

env {
  name  = "PYTHONUNBUFFERED"
  value = "1"  # Faster log output
}

env {
  name  = "STARTUP_TIMEOUT"
  value = "120"  # Extended startup time
}
```

**Health Probes Added:**
```hcl
startup_probe {
  transport               = "HTTP"
  port                   = 8000
  path                   = "/health"
  interval_seconds       = 10
  timeout_seconds        = 5
  failure_threshold      = 6  # Allow 60 seconds for startup
  success_threshold      = 1
}

liveness_probe {
  transport               = "HTTP"
  port                   = 8000
  path                   = "/health"
  interval_seconds       = 30
  timeout_seconds        = 10
  failure_threshold      = 3
  success_threshold      = 1
}

readiness_probe {
  transport               = "HTTP"
  port                   = 8000
  path                   = "/health"
  interval_seconds       = 10
  timeout_seconds        = 5
  failure_threshold      = 3
  success_threshold      = 1
}
```

#### Web Container App (`azurerm_container_app.web`)
**Resource Scaling:**
- **CPU Allocation**: `0.25` → `0.5` cores (2x improvement)
- **Memory Allocation**: `0.5Gi` → `1Gi` (2x improvement)
- **Minimum Replicas**: `1` → `2` (availability improvement)
- **Maximum Replicas**: `2` → `8` (web traffic spike handling)
- **HTTP Scaling Threshold**: `50` → `75` concurrent requests

**Next.js Optimization Variables Added:**
```hcl
env {
  name  = "NODE_ENV"
  value = "production"
}

env {
  name  = "NEXT_TELEMETRY_DISABLED"
  value = "1"  # Disable telemetry for faster startup
}

env {
  name  = "PORT"
  value = "3000"
}
```

**Health Probes Added:**
```hcl
startup_probe {
  transport               = "HTTP"
  port                   = 3000
  path                   = "/health"
  interval_seconds       = 10
  timeout_seconds        = 5
  failure_threshold      = 12  # Allow 120 seconds for Next.js startup
  success_threshold      = 1
}
```

### 2. Enhanced Performance Monitoring (`monitoring.tf`)

**New Performance Alerts Added:**
- **Container CPU Utilization**: Alert when CPU usage >70%
- **Container Memory Utilization**: Alert when memory usage >80%
- **Web Response Time**: Alert when response time >3s
- **Container Scaling Activity**: Informational alerts for scaling events
- **Container Startup Failures**: Critical alerts for startup issues

**Updated Alert Thresholds (`variables.tf`):**
- **API Error Threshold**: `10` → `15` (reduced false positives)
- **RAG Latency Threshold**: `10s` → `8s` (tighter performance)
- **Search Latency Threshold**: `3s` → `2s` (improved search performance)
- **OpenAI Error Threshold**: `5` → `8` (better tolerance)
- **Cosmos Latency Threshold**: `100ms` → `150ms` (concurrent operations)

### 3. Enhanced Verification (`verify_live.sh`)

**Performance Testing Additions:**
- **Container Performance Tests**: Verify replica counts and resource allocation
- **Startup Performance Tests**: Measure container startup times
- **Concurrent Request Tests**: Validate concurrent processing capability
- **Updated Performance Thresholds**:
  - API Response: `5s` → `3s`
  - Search Response: `3s` → `2s`
  - RAG Response: `10s` → `8s`
  - Container Startup: `120s` threshold
  - HTTP Response: `2s` threshold

### 4. Expected Resource Changes

**Resources to be Modified:**
- `azurerm_container_app.api` - CPU, memory, scaling, health probes
- `azurerm_container_app.web` - CPU, memory, scaling, health probes
- `azurerm_monitor_metric_alert.*` - New performance alerts (5 new resources)
- `azurerm_monitor_scheduled_query_rules_alert_v2.container_startup_failures` - New critical alert

## Expected Performance Improvements

### 1. Resource Utilization
- **API Service**: 3x CPU and memory increase supports:
  - Better RAG processing performance
  - Improved concurrent request handling
  - Faster response times under load
- **Web Service**: 2x CPU and memory increase supports:
  - Faster Next.js SSR performance
  - Better caching and asset handling
  - Improved user experience

### 2. Scaling Behavior
- **Higher Minimum Replicas**: Eliminates cold start delays
- **Increased Maximum Replicas**: Handles traffic spikes more effectively
- **Optimized Scaling Thresholds**: More intelligent auto-scaling

### 3. Startup Performance
- **Health Probes**: Faster deployment and more reliable service detection
- **Startup Optimization**: Environment variables for faster initialization
- **Better Resource Allocation**: Reduces startup timeout issues

### 4. Monitoring & Alerting
- **Proactive Monitoring**: Earlier detection of performance issues
- **Reduced False Positives**: Optimized thresholds for production workloads
- **Comprehensive Coverage**: CPU, memory, response times, and startup failures

## Deployment Impact Assessment

### 1. Resource Cost Impact
- **API Containers**: ~3x resource cost increase per replica
- **Web Containers**: ~2x resource cost increase per replica  
- **Scaling**: Higher minimum replicas = ~2x base cost
- **Overall**: Estimated 2-3x infrastructure cost increase for significant performance gains

### 2. Deployment Strategy
- **Rolling Update**: Changes will trigger new container revisions
- **Zero Downtime**: Health probes ensure traffic only routes to healthy instances
- **Gradual Scaling**: Auto-scaling will adjust to actual load patterns
- **Monitoring**: Enhanced alerts will detect any performance regressions

### 3. Expected Downtime
- **Per Container App**: < 2 minutes during revision switch
- **Total Deployment**: 5-10 minutes for all changes
- **Health Check Verification**: Additional 2-3 minutes

## Rollback Procedures

### 1. Immediate Rollback (Container Revision)
```bash
# List current revisions
az containerapp revision list --name api-${client_code}-${env} --resource-group rg-${client_code}-${env}

# Activate previous revision if needed
az containerapp revision activate --name api-${client_code}-${env} --resource-group rg-${client_code}-${env} --revision <previous-revision-name>
```

### 2. Terraform State Rollback
```bash
# Restore previous Terraform state
cd /infra
terraform apply terraform.tfstate.backup

# Or selective resource replacement
terraform apply -replace="azurerm_container_app.api" -replace="azurerm_container_app.web"
```

### 3. Configuration Rollback
```bash
# Reset performance optimizations
git checkout HEAD~1 -- infra/container_apps.tf infra/variables.tf infra/monitoring.tf
terraform apply
```

## Verification Steps

### 1. Pre-Deployment Verification
```bash
# Validate Terraform plan
cd /infra
terraform plan -out=performance-optimization.tfplan

# Verify no syntax errors
terraform validate
```

### 2. Post-Deployment Checks
```bash
# Run enhanced verification script
./scripts/verify_live.sh --prod

# Check container app status
az containerapp show --name api-${client_code}-${env} --resource-group rg-${client_code}-${env} --query "properties.provisioningState"

# Verify health endpoints with performance thresholds
curl -w "@curl-format.txt" https://api-${client_code}-${env}.azurecontainerapps.io/health
```

### 3. Performance Testing
```bash
# Run load tests to validate improvements
cd /e2e/load
./run-tests.sh stress

# Monitor scaling behavior
watch az containerapp show --name api-${client_code}-${env} --resource-group rg-${client_code}-${env} --query "properties.template.scale"
```

### 4. Monitoring Validation
- Verify new alerts are created and active
- Check Application Insights for performance metrics
- Confirm Log Analytics is receiving enhanced telemetry

## Dependencies and Prerequisites

### 1. Infrastructure Requirements
- **Azure CLI**: Version 2.50+ with containerapp extension
- **Terraform**: Version 1.5+ with azurerm provider 3.70+
- **Container Apps Environment**: Must be in "Succeeded" state
- **Log Analytics Workspace**: Required for new monitoring features

### 2. Application Requirements
- **Health Endpoints**: `/health` must be implemented in both API and Web apps
- **Container Images**: Must support the new environment variables
- **Startup Scripts**: Should handle the extended timeout configurations

### 3. Access Requirements
- **Azure RBAC**: Container App Contributor role
- **Monitoring**: Monitor Contributor role for alert creation
- **Resource Group**: Contributor access to modify resources

## Success Criteria Checklist

- [ ] **Terraform Plan**: Executes without errors showing expected changes
- [ ] **Container Apps**: Both API and Web apps restart successfully
- [ ] **Health Checks**: All health endpoints return 200 within new thresholds
- [ ] **Performance**: Response times meet or exceed new targets
- [ ] **Scaling**: Auto-scaling triggers appropriately under load
- [ ] **Monitoring**: All new alerts are active and properly configured
- [ ] **Resource Utilization**: CPU and memory allocation is effective
- [ ] **Startup Time**: Container startup completes within 120s threshold
- [ ] **Concurrent Handling**: Multiple requests processed efficiently
- [ ] **Rollback**: Rollback procedures validated and documented

## Files Modified

1. **`/infra/container_apps.tf`** - Container resource and scaling optimization
2. **`/infra/variables.tf`** - Performance monitoring thresholds  
3. **`/infra/monitoring.tf`** - Enhanced performance alerts
4. **`/scripts/verify_live.sh`** - Performance testing and verification
5. **`/scripts/terraform_plan_summary.md`** - This planning document

---

**Status**: Ready for Review and Deployment  
**Target Environment**: Production Azure Container Apps  
**Estimated Apply Time**: 10-15 minutes  
**Risk Level**: Medium (resource changes with comprehensive rollback)  
**Performance Impact**: Significant improvement expected  
**Cost Impact**: 2-3x infrastructure cost increase
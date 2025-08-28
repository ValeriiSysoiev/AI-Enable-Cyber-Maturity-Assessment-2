# Operations Guide

## Health Monitoring

### Health Check Endpoints

Monitor application health using these endpoints:

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `https://api-cybermat-prd-aca.../health` | `{"status": "healthy"}` |
| Web | `https://web-cybermat-prd-aca.../api/health` | `{"status": "ok"}` |
| Version | `https://api-cybermat-prd-aca.../version` | `{"sha": "...", "timestamp": "..."}` |

### Quick Health Check

```bash
# Check all services
for endpoint in \
  "https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/health" \
  "https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/api/health"
do
  echo "Checking $endpoint"
  curl -s -o /dev/null -w "%{http_code}\n" $endpoint
done
```

## Logging & Diagnostics

### View Application Logs

**Container Apps Logs**:
```bash
# API logs
az containerapp logs show \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --follow

# Web logs
az containerapp logs show \
  --name web-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --follow
```

**Log Analytics Queries**:
```kusto
// Recent errors
ContainerAppConsoleLogs
| where TimeGenerated > ago(1h)
| where Log contains "ERROR"
| project TimeGenerated, ContainerAppName, Log
| order by TimeGenerated desc

// Request performance
ContainerAppSystemLogs
| where TimeGenerated > ago(1h)
| where EventName == "HttpRequest"
| summarize avg(DurationMs), percentile(DurationMs, 95) by bin(TimeGenerated, 5m)
```

### Application Insights

**Key Metrics**:
- Request rate
- Response time
- Failure rate
- Dependency calls

**Common Queries**:
```kusto
// Failed requests
requests
| where success == false
| where timestamp > ago(1h)
| project timestamp, name, resultCode, duration

// Slow requests (> 3s)
requests
| where duration > 3000
| where timestamp > ago(1h)
| project timestamp, name, duration
```

## Common Production Issues

### 503 Service Unavailable

**Symptoms**: API returns 503 errors

**Verify**:
1. Container App status
2. Health probe status
3. Resource limits
4. Database connectivity

**Commands**:
```bash
# Check Container App status
az containerapp show --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query properties.provisioningState

# Check active revision
az containerapp revision list --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query "[?properties.active].name"
```

### Authentication Failures

**Symptoms**: Users cannot sign in

**Verify**:
1. Azure AD app registration
2. Environment variables
3. Certificate expiration
4. Token validation

**Commands**:
```bash
# Check auth configuration
az containerapp show --name web-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query "properties.template.containers[0].env[?name=='AUTH_MODE']"
```

### Performance Degradation

**Symptoms**: Slow response times

**Verify**:
1. Container App scaling
2. Database throttling
3. Memory/CPU usage
4. Network latency

**Commands**:
```bash
# Check scaling rules
az containerapp show --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query properties.template.scale

# View metrics
az monitor metrics list \
  --resource /subscriptions/.../resourceGroups/rg-cybermat-prd/providers/Microsoft.App/containerApps/api-cybermat-prd-aca \
  --metric "Requests" --interval PT1M
```

### Database Connection Issues

**Symptoms**: "Service temporarily unavailable" errors

**Verify**:
1. Cosmos DB status
2. Connection string validity
3. Firewall rules
4. Throughput limits

**Commands**:
```bash
# Check Cosmos DB status
az cosmosdb show --name [cosmos-account] \
  --resource-group rg-cybermat-prd \
  --query "provisioningState"

# View current throughput
az cosmosdb sql database throughput show \
  --account-name [cosmos-account] \
  --name [database-name] \
  --resource-group rg-cybermat-prd
```

## Maintenance Procedures

### Restart Container App

```bash
# Get active revision
REVISION=$(az containerapp revision list \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query "[?properties.active].name" -o tsv)

# Restart revision
az containerapp revision restart \
  --name api-cybermat-prd-aca \
  --revision $REVISION \
  --resource-group rg-cybermat-prd
```

### Scale Container App

```bash
# Scale up
az containerapp update \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --min-replicas 2 \
  --max-replicas 10

# Scale down
az containerapp update \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --min-replicas 1 \
  --max-replicas 5
```

### Update Environment Variables

```bash
# Update single variable
az containerapp update \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --set-env-vars LOG_LEVEL=debug

# Remove variable
az containerapp update \
  --name api-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --remove-env-vars LOG_LEVEL
```

## Monitoring Dashboard

### Key Performance Indicators

Monitor these KPIs:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | > 99.9% | < 99.5% |
| Response Time (P95) | < 2s | > 3s |
| Error Rate | < 1% | > 5% |
| CPU Usage | < 70% | > 85% |
| Memory Usage | < 80% | > 90% |

### Alert Rules

Configure alerts for:

1. **High Error Rate**: > 5% errors in 5 minutes
2. **Slow Response**: P95 > 3s for 10 minutes
3. **Service Down**: Health check fails 3 times
4. **Resource Exhaustion**: CPU/Memory > 90%
5. **Database Throttling**: Cosmos DB throttled requests

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Service Down | 15 minutes | Complete outage |
| P2 | Major Degradation | 1 hour | Auth failures |
| P3 | Minor Issue | 4 hours | Slow queries |
| P4 | Low Impact | Next business day | UI glitches |

### Response Process

1. **Detect**: Alert triggered or reported
2. **Assess**: Determine severity and impact
3. **Notify**: Inform stakeholders
4. **Mitigate**: Apply immediate fix
5. **Resolve**: Implement permanent solution
6. **Review**: Post-incident analysis

### Rollback Procedure

If issues persist after deployment:

```bash
# Find previous working version
gh run list --workflow=deploy-container-apps.yml --status=success

# Deploy previous version
az containerapp update \
  --name [app-name] \
  --resource-group rg-cybermat-prd \
  --image webcybermatprdacr.azurecr.io/[service]:[previous-sha]
```

## Backup & Recovery

### Backup Schedule

| Component | Frequency | Retention |
|-----------|-----------|-----------|
| Cosmos DB | Continuous | 30 days |
| Storage Blobs | Daily | 90 days |
| Container Images | On build | 6 months |
| Configuration | On change | Indefinite |

### Recovery Procedures

**Database Recovery**:
```bash
# Initiate point-in-time restore
az cosmosdb restore \
  --account-name [cosmos-account] \
  --target-account-name [new-account] \
  --restore-timestamp "2025-08-28T10:00:00Z"
```

**Storage Recovery**:
```bash
# Restore deleted blob
az storage blob undelete \
  --container-name [container] \
  --name [blob-name] \
  --account-name [storage-account]
```

## Performance Tuning

### Container App Optimization

- Set appropriate CPU/Memory limits
- Configure auto-scaling rules
- Optimize health probe intervals
- Use connection pooling

### Database Optimization

- Index frequently queried fields
- Optimize partition keys
- Adjust throughput based on load
- Monitor query performance

### Application Optimization

- Enable response caching
- Implement request batching
- Optimize image sizes
- Minimize external API calls

## Security Operations

### Regular Security Tasks

- Review access logs weekly
- Rotate secrets quarterly
- Update dependencies monthly
- Scan for vulnerabilities daily

### Security Monitoring

```bash
# Check recent auth failures
az monitor activity-log list \
  --resource-group rg-cybermat-prd \
  --start-time 2025-08-28T00:00:00Z \
  --query "[?contains(operationName.value, 'Microsoft.Authorization')]"

# Review Container App access
az containerapp logs show \
  --name web-cybermat-prd-aca \
  --resource-group rg-cybermat-prd \
  --query "[?contains(Log, '401') || contains(Log, '403')]"
```

## Maintenance Windows

### Scheduled Maintenance

- **Time**: Sundays 2 AM - 6 AM UTC
- **Frequency**: Monthly
- **Notification**: 72 hours advance notice

### Emergency Maintenance

- Security patches: Immediate
- Critical bugs: Within 4 hours
- Performance issues: Next maintenance window

## Contact Information

### Escalation Path

1. **L1 Support**: Monitor alerts, basic troubleshooting
2. **L2 Support**: Advanced diagnostics, configuration changes
3. **L3 Support**: Code changes, architecture decisions
4. **On-Call**: 24/7 for P1/P2 incidents

### Communication Channels

- **Alerts**: Sent to ops-alerts@company.com
- **Incidents**: Create in ServiceNow
- **Updates**: Post in #platform-status Slack
- **Escalation**: Page via PagerDuty
# AECMA Production Alerts Configuration

## Overview
This directory contains alert rule definitions and action group templates for monitoring the AECMA production environment based on defined SLOs.

## Directory Structure
```
alerts/
├── rules/
│   ├── availability-alerts.yaml    # Availability SLO alerts
│   ├── latency-alerts.yaml         # Latency SLO alerts
│   └── error-rate-alerts.yaml      # Error rate SLO alerts
├── templates/
│   └── action-groups.yaml          # Action group definitions
└── docs/
    ├── README.md                   # This file
    └── slo-definitions.md          # SLO specifications
```

## SLO-Based Alerting Strategy

### Service Level Objectives
- **Availability**: 99.9% monthly uptime
- **Latency**: P95 < 2 seconds
- **Error Rate**: < 1% of requests result in 5xx errors

### Alert Severities
- **Critical**: SLO breach or imminent breach
- **Warning**: SLO at risk or performance degradation
- **Emergency**: Service completely unavailable

## Alert Rule Categories

### Availability Alerts
- **AECMA-Availability-Critical**: Below 99.9% availability
- **AECMA-Availability-Warning**: Below 99.95% availability
- **AECMA-Service-Down**: No requests detected
- **AECMA-Error-Budget-Fast-Burn**: Error budget consuming too quickly

### Latency Alerts
- **AECMA-Latency-P95-Critical**: P95 latency > 2 seconds
- **AECMA-Latency-P95-Warning**: P95 latency > 1.5 seconds
- **AECMA-Latency-P99-High**: P99 latency > 5 seconds
- **AECMA-Database-Slow-Queries**: Database queries > 500ms
- **AECMA-API-Endpoint-Slow**: Specific endpoints performing poorly

### Error Rate Alerts
- **AECMA-Error-Rate-Critical**: 5xx error rate > 1%
- **AECMA-Error-Rate-Warning**: 5xx error rate > 0.5%
- **AECMA-500-Errors-Spike**: High number of HTTP 500 errors
- **AECMA-502-503-Errors**: Service unavailable errors
- **AECMA-Application-Errors**: Application-level errors
- **AECMA-Auth-Failures**: Authentication failure spike
- **AECMA-Database-Errors**: Database connection issues

## Action Groups

### Critical Response (ag-aecma-critical)
- **Response Time**: 5 minutes
- **Notifications**: Email, SMS, Slack, PagerDuty
- **Recipients**: On-call engineers, team leads

### Warning Response (ag-aecma-warning)
- **Response Time**: 15 minutes
- **Notifications**: Email, Slack, Teams
- **Recipients**: Development team, DevOps

### Emergency Response (ag-aecma-emergency)
- **Response Time**: Immediate
- **Notifications**: Email, SMS, voice calls, PagerDuty
- **Recipients**: Incident commander, management

### Security Response (ag-aecma-security)
- **Response Time**: 15 minutes
- **Notifications**: Email, SIEM integration
- **Recipients**: Security team, compliance team

## Deployment Instructions

### Prerequisites
- Azure Monitor workspace configured
- Log Analytics workspace with AECMA logs
- Action groups created with valid contact information
- Appropriate RBAC permissions for alert management

### Manual Deployment

#### 1. Create Action Groups
```bash
# Update contact information in templates/action-groups.yaml
# Deploy via Azure CLI or Portal
az monitor action-group create \
  --resource-group $RESOURCE_GROUP \
  --name "ag-aecma-critical" \
  --short-name "aecma-crit" \
  --email "oncall@company.com"
```

#### 2. Deploy Alert Rules
```bash
# Deploy availability alerts
az monitor scheduled-query create \
  --resource-group $RESOURCE_GROUP \
  --name "AECMA-Availability-Critical" \
  --scopes $LOG_ANALYTICS_WORKSPACE_ID \
  --condition-query "$(cat alerts/rules/availability-alerts.yaml | yq '.alerts[0].query')" \
  --condition-threshold 99.9 \
  --condition-operator "LessThan" \
  --evaluation-frequency "PT1M" \
  --window-size "PT30M" \
  --severity 1 \
  --action-groups "/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/ag-aecma-critical"
```

### Automated Deployment
Use the deployment script (when created in future PR):
```bash
./scripts/deploy_alerts.sh --environment production --resource-group $RG --workspace $WORKSPACE
```

## Testing Alerts

### Synthetic Testing
```bash
# Test availability alert
curl -f https://your-app.azurecontainerapps.io/health || echo "Service down - should trigger alert"

# Test latency alert (simulate slow response)
curl -w "%{time_total}" https://your-app.azurecontainerapps.io/api/slow-endpoint

# Test error rate alert (simulate errors)
for i in {1..20}; do curl https://your-app.azurecontainerapps.io/api/error-endpoint; done
```

### Alert Validation
1. **Verify alert rules are active**: Check Azure Monitor alerts dashboard
2. **Test action groups**: Send test notifications
3. **Validate escalation**: Ensure alerts reach correct recipients
4. **Check alert dependencies**: Verify no circular dependencies

## Maintenance

### Weekly Tasks
- Review alert noise and false positives
- Update contact information in action groups
- Validate alert thresholds against SLO performance

### Monthly Tasks
- Analyze alert effectiveness and response times
- Update SLO thresholds based on service performance
- Review and update escalation procedures

### Quarterly Tasks
- Complete review of all alert rules
- Update business contact information
- Validate disaster recovery alert procedures

## Troubleshooting

### Common Issues
- **Alert not firing**: Check KQL query syntax and data availability
- **Too many false positives**: Adjust thresholds or time windows
- **Notifications not received**: Verify action group configuration
- **Query performance**: Optimize KQL queries for large datasets

### Alert Rule Debugging
```bash
# Test KQL query in Log Analytics
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(30m)
| extend StatusCode = extract(@"HTTP/\d\.\d\s(\d{3})", 1, Log_s)
| where isnotnull(StatusCode)
| summarize TotalRequests = count(), SuccessfulRequests = countif(StatusCode startswith "2")
| extend AvailabilityPercent = (SuccessfulRequests * 100.0) / TotalRequests
```

## Related Documentation
- [SLO Definitions](slo-definitions.md)
- [Monitoring Alerts Overview](../../docs/monitoring-alerts.md)
- [Incident Response Procedures](../../docs/incident-response.md)
- [On-call Runbook](../../docs/oncall.md)
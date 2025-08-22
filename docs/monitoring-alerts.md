# Production Monitoring and Alerts Guide

## Overview

This guide provides comprehensive monitoring and alerting setup for the AI-Enabled Cyber Maturity Assessment platform production environment, including Log Analytics KQL queries, alert rules, and escalation procedures.

## Monitoring Architecture

### Components
- **Azure Application Insights**: Application performance monitoring
- **Azure Log Analytics**: Centralized logging and queries
- **Azure Monitor**: Metrics collection and alerting
- **Container Apps Logs**: Application-specific logging
- **Health Endpoints**: Built-in application health checks

### Data Flow
1. Applications emit logs and metrics
2. Azure Monitor collects and stores data
3. Log Analytics processes and indexes logs
4. Alert rules evaluate conditions
5. Notifications sent via configured channels

## Key Performance Indicators (KPIs)

### Application Performance
- **Response Time**: API response time < 2s (P95)
- **Availability**: System uptime > 99.9%
- **Error Rate**: Application errors < 1%
- **Throughput**: Requests per second capacity

### Infrastructure Health
- **CPU Utilization**: < 80% average
- **Memory Usage**: < 85% average
- **Storage Usage**: < 80% capacity
- **Network Latency**: < 100ms average

### Business Metrics
- **Active Users**: Daily/monthly active users
- **Assessment Completions**: Successful assessment completions
- **Authentication Success**: AAD authentication success rate
- **Feature Usage**: Core feature adoption rates

## Log Analytics KQL Queries

### Application Health Monitoring

#### Basic Health Check
```kql
// Application health status over time
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "health"
| summarize count() by bin(TimeGenerated, 5m), ContainerAppName_s
| render timechart
```

#### Error Rate Monitoring
```kql
// Application error rate calculation
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where Log_s contains "ERROR" or Log_s contains "Exception"
| summarize ErrorCount = count() by bin(TimeGenerated, 1h)
| extend TotalRequests = 1000 // Adjust based on actual traffic
| extend ErrorRate = (ErrorCount * 100.0) / TotalRequests
| where ErrorRate > 1.0
| project TimeGenerated, ErrorCount, ErrorRate
| render timechart
```

#### Response Time Analysis
```kql
// API response time monitoring
AppTraces
| where TimeGenerated > ago(1h)
| where Message contains "API"
| extend Duration = todouble(customDimensions["Duration"])
| where Duration > 0
| summarize 
    P50 = percentile(Duration, 50),
    P95 = percentile(Duration, 95),
    P99 = percentile(Duration, 99),
    AvgDuration = avg(Duration)
    by bin(TimeGenerated, 5m)
| where P95 > 2000  // Alert if P95 > 2 seconds
| render timechart
```

### Security Monitoring

#### Authentication Failures
```kql
// Failed authentication attempts
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "authentication" and Log_s contains "failed"
| summarize FailedAttempts = count() by bin(TimeGenerated, 5m), 
    User = extract("user=([^\\s]+)", 1, Log_s),
    IP = extract("ip=([^\\s]+)", 1, Log_s)
| where FailedAttempts > 5  // Alert on > 5 failures per 5 minutes
| order by TimeGenerated desc
```

#### Suspicious Activity Detection
```kql
// Detect potential security threats
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "suspicious" or Log_s contains "blocked" or Log_s contains "unauthorized"
| extend Severity = case(
    Log_s contains "blocked", "High",
    Log_s contains "unauthorized", "Medium",
    "Low"
)
| summarize EventCount = count() by Severity, bin(TimeGenerated, 5m)
| where EventCount > 0
| order by TimeGenerated desc
```

### Performance Monitoring

#### Container Resource Usage
```kql
// Container resource utilization
Perf
| where TimeGenerated > ago(1h)
| where ObjectName == "K8SContainer"
| where CounterName in ("cpuUsageNanoCores", "memoryWorkingSetBytes")
| extend ResourceType = case(
    CounterName == "cpuUsageNanoCores", "CPU",
    CounterName == "memoryWorkingSetBytes", "Memory",
    "Unknown"
)
| summarize avg(CounterValue) by bin(TimeGenerated, 5m), InstanceName, ResourceType
| render timechart
```

#### Database Connection Monitoring
```kql
// Database connection health
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where Log_s contains "database" or Log_s contains "cosmos"
| extend ConnectionStatus = case(
    Log_s contains "connected", "Success",
    Log_s contains "timeout", "Timeout",
    Log_s contains "failed", "Failed",
    "Unknown"
)
| summarize count() by bin(TimeGenerated, 5m), ConnectionStatus
| render timechart
```

### Business Intelligence Queries

#### User Activity Analysis
```kql
// User engagement metrics
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where Log_s contains "user_action"
| extend Action = extract("action=([^\\s]+)", 1, Log_s)
| extend UserId = extract("user_id=([^\\s]+)", 1, Log_s)
| summarize UniqueUsers = dcount(UserId), TotalActions = count() by Action
| order by TotalActions desc
```

#### Assessment Completion Rates
```kql
// Assessment completion tracking
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(7d)
| where Log_s contains "assessment"
| extend Status = case(
    Log_s contains "started", "Started",
    Log_s contains "completed", "Completed",
    Log_s contains "abandoned", "Abandoned",
    "Unknown"
)
| summarize count() by Status, bin(TimeGenerated, 1d)
| render columnchart
```

## Alert Rules Configuration

### Critical Alerts (Immediate Response)

#### Application Down Alert
```json
{
  "alertName": "Application Unavailable",
  "description": "Application health check failing",
  "severity": "Critical",
  "condition": {
    "query": "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(5m) | where Log_s contains 'health' | summarize count()",
    "threshold": "< 1",
    "evaluationFrequency": "1 minute",
    "windowSize": "5 minutes"
  },
  "actions": [
    "PagerDuty notification",
    "SMS to on-call engineer",
    "Email to technical team"
  ]
}
```

#### High Error Rate Alert
```json
{
  "alertName": "High Application Error Rate",
  "description": "Application error rate exceeds threshold",
  "severity": "Critical",
  "condition": {
    "query": "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(10m) | where Log_s contains 'ERROR' | summarize ErrorCount = count() | extend ErrorRate = ErrorCount / 1000.0",
    "threshold": "> 0.05",
    "evaluationFrequency": "5 minutes",
    "windowSize": "10 minutes"
  },
  "actions": [
    "PagerDuty notification",
    "Email to technical team"
  ]
}
```

### Warning Alerts (Monitor and Plan)

#### Performance Degradation
```json
{
  "alertName": "API Response Time Degradation",
  "description": "API P95 response time exceeds SLA",
  "severity": "Warning",
  "condition": {
    "query": "AppTraces | where TimeGenerated > ago(15m) | extend Duration = todouble(customDimensions['Duration']) | summarize P95 = percentile(Duration, 95)",
    "threshold": "> 2000",
    "evaluationFrequency": "5 minutes",
    "windowSize": "15 minutes"
  },
  "actions": [
    "Email to technical team",
    "Slack notification"
  ]
}
```

#### Resource Utilization Warning
```json
{
  "alertName": "High Resource Utilization",
  "description": "Container resource usage approaching limits",
  "severity": "Warning",
  "condition": {
    "query": "Perf | where TimeGenerated > ago(10m) | where CounterName == 'cpuUsageNanoCores' | summarize avg(CounterValue)",
    "threshold": "> 80",
    "evaluationFrequency": "5 minutes", 
    "windowSize": "10 minutes"
  },
  "actions": [
    "Email to operations team",
    "Slack notification"
  ]
}
```

### Security Alerts

#### Authentication Failure Spike
```json
{
  "alertName": "Authentication Failure Spike",
  "description": "Unusual number of authentication failures",
  "severity": "High",
  "condition": {
    "query": "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(5m) | where Log_s contains 'authentication' and Log_s contains 'failed' | summarize count()",
    "threshold": "> 10",
    "evaluationFrequency": "1 minute",
    "windowSize": "5 minutes"
  },
  "actions": [
    "Email to security team",
    "SMS to security on-call",
    "Slack notification"
  ]
}
```

## Notification Channels

### Email Notifications
- **Technical Team**: technical-team@company.com
- **Security Team**: security-team@company.com
- **Operations Team**: operations-team@company.com
- **Management**: management-team@company.com

### Slack Integration
- **Channel**: #production-alerts
- **Webhook URL**: Configure in Azure Monitor
- **Message Format**: Include alert severity, affected component, and runbook link

### PagerDuty Integration
- **Service Key**: Configure in Azure Monitor
- **Escalation Policy**: 
  1. Primary on-call engineer (immediate)
  2. Secondary on-call engineer (after 15 minutes)
  3. Technical lead (after 30 minutes)
  4. Management (after 1 hour)

### SMS Notifications
- **Critical Alerts Only**: Configure phone numbers in Azure Monitor
- **Rate Limiting**: Maximum 3 SMS per hour per recipient
- **Backup Contacts**: Maintain current contact list

## Dashboard Configuration

### Executive Dashboard
- **Availability**: 99.9% uptime target
- **Performance**: Average response time trend
- **User Activity**: Daily active users
- **Incident Count**: Monthly incident trend

### Technical Dashboard
- **System Health**: Real-time status of all components
- **Performance Metrics**: Response times, error rates, throughput
- **Resource Utilization**: CPU, memory, storage usage
- **Security Events**: Authentication failures, suspicious activity

### Business Dashboard
- **User Engagement**: Assessment completion rates
- **Feature Usage**: Core feature adoption
- **Revenue Impact**: Business-critical metrics
- **Customer Satisfaction**: Support ticket trends

## Incident Response Integration

### Alert Triage Process
1. **Immediate Assessment** (< 5 minutes)
   - Verify alert accuracy
   - Assess impact and severity
   - Determine response team

2. **Initial Response** (< 15 minutes)
   - Execute immediate mitigation
   - Notify stakeholders
   - Begin diagnostic process

3. **Resolution** (Target: < 2 hours)
   - Implement fix or workaround
   - Verify system restoration
   - Communicate resolution

4. **Post-Incident** (< 24 hours)
   - Conduct post-mortem
   - Update runbooks
   - Implement preventive measures

### Runbook Links
- **Application Down**: [Link to runbook]
- **Performance Issues**: [Link to runbook]
- **Security Incidents**: [Link to runbook]
- **Database Issues**: [Link to runbook]

## Maintenance and Optimization

### Daily Tasks
- [ ] Review overnight alerts and incidents
- [ ] Check system performance trends
- [ ] Validate backup and monitoring systems
- [ ] Update on-call rotation if needed

### Weekly Tasks
- [ ] Analyze performance trends and capacity planning
- [ ] Review and update alert thresholds
- [ ] Test notification channels and escalation
- [ ] Update monitoring documentation

### Monthly Tasks
- [ ] Conduct monitoring system health check
- [ ] Review and optimize expensive queries
- [ ] Update dashboard configurations
- [ ] Training updates for operations team

### Quarterly Tasks
- [ ] Comprehensive monitoring review
- [ ] Alert rule effectiveness analysis
- [ ] Disaster recovery testing for monitoring
- [ ] Budget and capacity planning review

## Troubleshooting Common Issues

### Missing Logs
```bash
# Check Log Analytics agent status
kubectl get pods -n kube-system | grep omsagent

# Verify container app logging configuration
az containerapp show --name myapp --resource-group myrg --query properties.configuration.ingress
```

### Alert Fatigue
- **Review Thresholds**: Adjust based on historical data
- **Consolidate Alerts**: Group related alerts
- **Implement Dependencies**: Avoid cascading alerts
- **Regular Cleanup**: Remove obsolete or ineffective alerts

### Performance Impact
- **Query Optimization**: Use time filters and summarization
- **Sampling**: Implement log sampling for high-volume applications
- **Retention Policies**: Configure appropriate data retention
- **Cost Monitoring**: Track Log Analytics costs and optimize

## Best Practices

### Query Writing
- Always include time filters (`TimeGenerated > ago()`)
- Use summarization to reduce data volume
- Implement proper indexing strategies
- Test queries before implementing in alerts

### Alert Design
- Use meaningful names and descriptions
- Include actionable information in alerts
- Set appropriate severity levels
- Test notification channels regularly

### Dashboard Creation
- Focus on key metrics that drive decisions
- Use appropriate visualization types
- Implement drill-down capabilities
- Regular review and optimization

---

**Document Version**: 1.0  
**Last Updated**: [DATE]  
**Next Review**: [DATE + 3 months]  
**Owner**: Operations Team  
**Approvers**: Technical Lead, Security Lead
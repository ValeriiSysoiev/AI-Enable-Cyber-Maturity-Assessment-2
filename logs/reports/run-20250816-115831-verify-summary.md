# Release Gate Report - 20250816-115831

## Gate Results
- **Pre-deploy Gate**: 
- **Post-deploy Gate**: ✅ PASSED
- **Overall Result**: ✅ RELEASE APPROVED

## Configuration
- **Error Threshold**: 0
- **Monitor Duration**: 20 minutes
- **Check Interval**: 1 minute

## KQL Queries Used
```kql
// Recent errors (pre-deploy)
ContainerAppConsoleLogs_CL 
| where TimeGenerated > ago(60m)
| where ContainerName_s in ('api-aaa-demo', 'web-aaa-demo')
| where Log_s contains 'ERROR' or Log_s contains 'error' or Log_s contains '"status":5'
| summarize ErrorCount = count()

// New revision errors (post-deploy)
ContainerAppConsoleLogs_CL 
| where TimeGenerated > ago(2m)
| where ContainerName_s in ('api-aaa-demo', 'web-aaa-demo')
| where Log_s contains 'ERROR' or Log_s contains 'error' or Log_s contains '"status":5'
| summarize ErrorCount = count()
```

## Log Analytics Links
- [View Recent Errors](https://portal.azure.com/#blade/Microsoft_Azure_Monitoring_Logs/LogsBlade/resourceId/%2Fsubscriptions%2F10233675-d493-4a97-9c81-4001e353a7bb%2FresourceGroups%2Frg-aaa-demo%2Fproviders%2FMicrosoft.OperationalInsights%2Fworkspaces%2Fb8581246-5082-4c30-acd6-f49f0f616012)
- [Container App Logs](https://portal.azure.com/#blade/Microsoft_Azure_Monitoring_Logs/LogsBlade/resourceId/%2Fsubscriptions%2F10233675-d493-4a97-9c81-4001e353a7bb%2FresourceGroups%2Frg-aaa-demo%2Fproviders%2FMicrosoft.App%2FcontainerApps%2Fapi-aaa-demo)

## Recommendations
- Release is healthy and ready for production traffic
- Monitor application metrics for the next 24 hours
- Review error logs for any patterns or issues

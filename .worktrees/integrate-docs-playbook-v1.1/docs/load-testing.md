# Load Testing Guide

This document provides comprehensive guidance for load testing the AI-Enabled Cyber Maturity Assessment platform using k6.

## Overview

Load testing validates system performance under various traffic patterns, ensuring the platform can handle enterprise-scale usage while maintaining acceptable response times and reliability.

## Architecture

Our load testing strategy covers:
- **Authentication flows** (demo mode + AAD simulation)
- **Core business logic** (engagements, assessments, scoring)
- **Enterprise features** (RAG search, GDPR operations, admin functions)
- **Infrastructure components** (API, frontend, database, storage)

## Setup

### Prerequisites

```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz --strip-components 1
sudo mv k6 /usr/local/bin/

# Install Node.js for test data generation
npm install

# Verify installation
k6 version
```

### Configuration

Load tests are configured through environment variables:

```bash
# Target environment
export TARGET_ENV=local          # local, dev, staging, prod
export API_BASE_URL=https://api-demo.example.com
export WEB_BASE_URL=https://web-demo.example.com

# Performance thresholds
export P95_THRESHOLD_MS=1000     # 95th percentile response time
export MAX_ERROR_RATE=0.01       # Maximum 1% error rate
export RPS_TARGET=100            # Target requests per second

# Test behavior
export MAX_VUS=500               # Maximum virtual users
export DURATION_OVERRIDE=5m      # Override test duration
export RAMP_UP_TIME=30s          # Gradual load increase

# Feature toggles
export ENABLE_RAG_TESTING=true   # Test RAG search endpoints
export ENABLE_DOCUMENT_UPLOAD=false  # Skip large file uploads
export ENABLE_GDPR_TESTING=true # Test GDPR export/purge flows

# Authentication
export AUTH_MODE=demo            # demo or aad
export TEST_USER_EMAIL=loadtest@example.com
export TEST_ADMIN_EMAIL=admin@example.com

# Monitoring
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export ENABLE_DETAILED_METRICS=true
export CLEANUP_RATE=0.8          # Clean up 80% of test data
```

## Test Scenarios

### 1. Smoke Test

**Purpose**: Basic functionality validation  
**Load**: 1 user for 30 seconds  
**Use Case**: CI/CD pipeline validation

```bash
./run-tests.sh -s smoke -e dev
```

**What it tests**:
- API health endpoints
- Authentication flows
- Basic CRUD operations
- Service connectivity

### 2. Load Test

**Purpose**: Normal operating conditions  
**Load**: 100 concurrent users over 9 minutes  
**Pattern**: Gradual ramp-up → sustained load → ramp-down

```bash
./run-tests.sh -s load -e staging -d 10m
```

**User Journey**:
1. User authentication (2 requests)
2. Browse engagements (3 requests)
3. Create/update assessment (5 requests)
4. Generate scores (2 requests)
5. Export results (1 request)

### 3. Stress Test

**Purpose**: Peak capacity testing  
**Load**: 500 concurrent users over 15 minutes  
**Tolerance**: Higher error rates acceptable

```bash
./run-tests.sh -s stress -e staging -v
```

**Validation**:
- System doesn't crash under high load
- Graceful degradation of performance
- Auto-scaling triggers work correctly
- Circuit breakers activate appropriately

### 4. Spike Test

**Purpose**: Sudden traffic spike handling  
**Load**: 100→1000→100 users (rapid transitions)

```bash
./run-tests.sh -s spike -e prod
```

**Scenarios**:
- Breaking news driving traffic
- Conference demos
- Marketing campaign launches
- Security incident response

### 5. Soak Test

**Purpose**: Memory leak and stability detection  
**Load**: 50 users for 30 minutes  
**Focus**: Long-term stability

```bash
./run-tests.sh -s soak -e staging -d 30m
```

**Monitors**:
- Memory usage over time
- Connection pool exhaustion
- Database connection leaks
- Cache efficiency degradation

### 6. Breakpoint Test

**Purpose**: Find system limits  
**Load**: Gradual increase until failure  
**Output**: Maximum sustainable throughput

```bash
./run-tests.sh -s breakpoint -e staging --find-limits
```

**Results**: Capacity planning data for infrastructure scaling decisions

## Test Data Management

### Data Generation

Test data is generated programmatically:

```javascript
// Generate realistic user data
const users = generateUsers(100);  // 100 concurrent users
const engagements = generateEngagements(20);  // 20 test engagements
const assessments = generateAssessments(50);  // 50 test assessments

// Enterprise test data
const aadGroups = generateAADGroups();
const gdprRequests = generateGDPRScenarios();
const performanceProfiles = generateUserProfiles();
```

### Data Cleanup

Automatic cleanup prevents test data accumulation:

```bash
# Cleanup after each test run
export CLEANUP_RATE=0.8  # Clean up 80% of data

# Manual cleanup
k6 run scenarios/cleanup.js --env TARGET_ENV=staging
```

### Data Isolation

Each test run uses unique identifiers:

```javascript
const testRunId = `loadtest-${Date.now()}`;
const userPrefix = `user-${testRunId}`;
const engagementPrefix = `eng-${testRunId}`;
```

## Performance Thresholds

### Response Time Targets

```javascript
export const thresholds = {
  // API response times
  'http_req_duration{endpoint:api}': ['p(95)<1000'],
  'http_req_duration{endpoint:search}': ['p(95)<2000'],
  'http_req_duration{endpoint:rag}': ['p(95)<5000'],
  
  // Frontend performance
  'http_req_duration{type:page}': ['p(95)<3000'],
  'http_req_duration{type:api}': ['p(95)<1000'],
  
  // Error rates
  'http_req_failed{endpoint:critical}': ['rate<0.001'],  // 0.1%
  'http_req_failed{endpoint:standard}': ['rate<0.01'],   // 1%
  'http_req_failed{endpoint:bulk}': ['rate<0.05'],       // 5%
  
  // Throughput
  'http_reqs': ['rate>50'],  // Minimum 50 RPS
  
  // Enterprise features
  'gdpr_export_duration': ['p(95)<30000'],      // 30s
  'cache_hit_rate': ['value>0.8'],              // 80%
  'auth_response_time': ['p(95)<500'],          // 500ms
};
```

### Scalability Targets

| Metric | Development | Staging | Production |
|--------|-------------|---------|------------|
| Concurrent Users | 50 | 200 | 1000 |
| Requests/Second | 25 | 100 | 500 |
| P95 Response Time | 2s | 1s | 500ms |
| Error Rate | <5% | <1% | <0.1% |
| Uptime | 95% | 99% | 99.9% |

## Enterprise Features Testing

### AAD Authentication Flow

```javascript
export function testAADAuthentication() {
  group('AAD Authentication', () => {
    // 1. Initiate AAD login
    const loginResponse = http.get(`${WEB_BASE_URL}/signin`);
    check(loginResponse, {
      'AAD login page loads': (r) => r.status === 200,
      'Contains AAD redirect': (r) => r.body.includes('login.microsoftonline.com'),
    });
    
    // 2. Simulate AAD callback
    const callbackResponse = http.get(`${WEB_BASE_URL}/api/auth/callback/azure-ad`, {
      headers: {
        'Authorization': `Bearer ${generateTestJWT()}`,
        'X-Correlation-ID': generateCorrelationId(),
      }
    });
    
    // 3. Verify group mapping
    const groupsResponse = http.get(`${API_BASE_URL}/admin/auth-diagnostics`);
    check(groupsResponse, {
      'Group diagnostics accessible': (r) => r.status === 200,
      'Groups properly mapped': (r) => JSON.parse(r.body).groups.length > 0,
    });
  });
}
```

### GDPR Export/Purge Testing

```javascript
export function testGDPROperations() {
  group('GDPR Operations', () => {
    // 1. Request data export
    const exportResponse = http.post(`${API_BASE_URL}/gdpr/engagements/${engagementId}/export`, {
      engagement_id: engagementId,
      include_documents: true,
      export_format: 'json'
    });
    
    check(exportResponse, {
      'Export request accepted': (r) => r.status === 202,
      'Job ID returned': (r) => JSON.parse(r.body).job_id !== undefined,
    });
    
    // 2. Monitor export progress
    const jobId = JSON.parse(exportResponse.body).job_id;
    let exportComplete = false;
    let attempts = 0;
    
    while (!exportComplete && attempts < 30) {
      sleep(2);
      const statusResponse = http.get(`${API_BASE_URL}/gdpr/admin/jobs/${jobId}`);
      const status = JSON.parse(statusResponse.body).status;
      
      if (status === 'completed') {
        exportComplete = true;
      }
      attempts++;
    }
    
    check(exportComplete, {
      'Export completes within 60s': () => exportComplete,
    });
    
    // 3. Test purge request (dry run only)
    const purgeResponse = http.post(`${API_BASE_URL}/gdpr/engagements/${engagementId}/purge`, {
      engagement_id: engagementId,
      purge_type: 'soft_delete',
      confirm_purge: false,  // Dry run
      reason: 'Load testing'
    });
    
    check(purgeResponse, {
      'Purge validation succeeds': (r) => r.status === 200,
    });
  });
}
```

### RAG Search Performance

```javascript
export function testRAGPerformance() {
  group('RAG Search', () => {
    const searchQueries = [
      'security framework compliance',
      'risk assessment methodology',
      'data governance policies',
      'incident response procedures'
    ];
    
    searchQueries.forEach(query => {
      const searchResponse = http.post(`${API_BASE_URL}/api/evidence/search`, {
        query: query,
        max_results: 10,
        include_citations: true
      });
      
      check(searchResponse, {
        'RAG search responds': (r) => r.status === 200,
        'Results include citations': (r) => {
          const results = JSON.parse(r.body);
          return results.citations && results.citations.length > 0;
        },
        'Response time acceptable': (r) => r.timings.duration < 5000,
      });
    });
  });
}
```

## CI/CD Integration

### GitHub Actions Workflow

The load testing workflow supports:

```yaml
name: Load Testing
on:
  workflow_dispatch:
    inputs:
      scenario:
        description: 'Test scenario'
        required: true
        default: 'smoke'
        type: choice
        options:
          - smoke
          - load
          - stress
          - spike
          - soak
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - dev
          - staging
          - prod
      duration:
        description: 'Test duration (e.g., 5m, 1h)'
        required: false
        default: ''
```

### Automated Triggers

```yaml
# Scheduled smoke tests
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours

# Performance regression detection
on:
  pull_request:
    paths:
      - 'app/**'
      - 'web/**'
      - 'infra/**'
```

### Results Integration

Results are automatically:
- Stored in GitHub Actions artifacts
- Posted to Slack channels
- Compared against baselines
- Used to gate deployments

## Monitoring and Alerting

### Real-time Monitoring

During tests, monitor:

```bash
# Container Apps metrics
az monitor metrics list --resource $CONTAINER_APP_ID \
  --metric "Requests,ResponseTime,CpuUsage,MemoryUsage"

# Cosmos DB metrics  
az monitor metrics list --resource $COSMOS_DB_ID \
  --metric "TotalRequests,RequestUnits,PartitionKeyStatistics"

# Application Insights
az monitor app-insights query --app $APP_INSIGHTS \
  --analytics-query "requests | summarize count() by bin(timestamp, 1m)"
```

### Performance Alerts

Configure alerts for:
- Response time > P95 threshold
- Error rate > 1%
- Resource utilization > 80%
- Queue depth > 100 messages

### Dashboards

Load testing dashboards display:
- Real-time performance metrics
- Historical trend analysis
- Capacity utilization
- Error rate tracking
- Cost impact analysis

## Troubleshooting

### Common Issues

**High Response Times**
```bash
# Check cache hit rates
curl "${API_BASE_URL}/api/performance/metrics" | grep cache_hit_rate

# Verify database connection pooling
az cosmosdb sql database throughput show --account-name $COSMOS_DB \
  --name ai_maturity --resource-group $RG
```

**Memory Leaks**
```bash
# Monitor container memory usage
az containerapp logs show --name $API_APP --resource-group $RG \
  --type console --follow

# Check for connection leaks
kubectl top pods --namespace $NAMESPACE
```

**Authentication Failures**
```bash
# Check AAD service status
curl "${API_BASE_URL}/admin/auth-diagnostics"

# Verify token validation
az ad app show --id $AAD_CLIENT_ID --query "appId,displayName"
```

### Performance Optimization

**Database Optimization**
```bash
# Apply suggested Cosmos DB indexes
az cosmosdb sql container update --account-name $COSMOS_DB \
  --database-name ai_maturity --name assessments \
  --idx @cosmos_index_proposals.json
```

**Caching Optimization**
```bash
# Increase cache sizes
export CACHE_PRESETS_SIZE_MB=200
export CACHE_FRAMEWORK_SIZE_MB=100

# Adjust TTL values
export CACHE_PRESETS_TTL_SECONDS=7200
```

**Auto-scaling Configuration**
```bash
# Configure Container Apps scaling
az containerapp update --name $API_APP --resource-group $RG \
  --min-replicas 2 --max-replicas 20 \
  --scale-rule-name "http-requests" \
  --scale-rule-http-concurrency 100
```

## Best Practices

### Test Design

1. **Realistic User Behavior**
   - Model actual user workflows
   - Include think time between requests
   - Vary data sizes and patterns

2. **Gradual Load Introduction**
   - Ramp up load gradually
   - Allow system warm-up time
   - Monitor auto-scaling triggers

3. **Data Management**
   - Use unique test data per run
   - Clean up after tests
   - Avoid production data contamination

### Environment Management

1. **Staging Environment**
   - Mirror production configuration
   - Use production-like data volumes
   - Test with realistic network latency

2. **Baseline Establishment**
   - Run baseline tests before changes
   - Track performance trends over time
   - Set realistic performance goals

3. **Coordination**
   - Schedule tests during low usage
   - Coordinate with development team
   - Communicate test windows

### Results Analysis

1. **Trend Analysis**
   - Compare results over time
   - Identify performance regressions
   - Track improvement initiatives

2. **Capacity Planning**
   - Determine scaling triggers
   - Plan infrastructure investments
   - Model growth scenarios

3. **Optimization Priorities**
   - Focus on high-impact improvements
   - Balance cost vs. performance
   - Consider user experience impact

## Advanced Scenarios

### Multi-Region Testing

Test cross-region performance:

```javascript
const regions = ['us-east', 'eu-west', 'asia-pacific'];

regions.forEach(region => {
  group(`Region: ${region}`, () => {
    const baseUrl = `https://api-${region}.example.com`;
    testCoreWorkflows(baseUrl);
  });
});
```

### Disaster Recovery Testing

Simulate component failures:

```javascript
export function testFailoverScenarios() {
  // Test database failover
  group('Database Failover', () => {
    // Normal operation
    testAssessmentWorkflow();
    
    // Simulate primary region failure
    // (requires manual infrastructure changes)
    
    // Verify failover to secondary region
    testAssessmentWorkflow();
  });
}
```

### Security Load Testing

Test authentication under load:

```javascript
export function testAuthenticationLoad() {
  group('Authentication Load', () => {
    // Generate high volume of auth requests
    for (let i = 0; i < 1000; i++) {
      const authResponse = authenticateUser(`user${i}@example.com`);
      check(authResponse, {
        'Auth succeeds under load': (r) => r.status === 200,
        'Response time acceptable': (r) => r.timings.duration < 1000,
      });
    }
  });
}
```

## Conclusion

This load testing framework provides comprehensive validation of the AI-Enabled Cyber Maturity Assessment platform's performance under various conditions. Regular load testing ensures the system can handle enterprise-scale usage while maintaining acceptable performance and reliability.

For additional support or questions about load testing procedures, consult the development team or reference the troubleshooting section above.
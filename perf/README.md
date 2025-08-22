# Performance Testing with K6

## Overview
This directory contains K6 performance tests for the AECMA platform, designed to validate SLO compliance and detect performance regressions through automated nightly testing.

## Test Types

### Smoke Test (`smoke.js`)
- **Purpose**: Basic health check and SLO validation
- **Duration**: 2 minutes
- **Virtual Users**: 2
- **Endpoints Tested**:
  - Health check endpoint
  - API version endpoint
  - Assessment list (if authenticated)
  - Static content

### Hot Path Test (`hot-path.js`)
- **Purpose**: Test critical user journeys under load
- **Duration**: 3 minutes (30s ramp-up, 2m steady, 30s ramp-down)
- **Virtual Users**: 5-10
- **Scenarios Tested**:
  - List engagements
  - Get assessment frameworks
  - Create assessment
  - Get assessment details
  - Search functionality

## SLO Thresholds

Both tests validate against production SLOs:
- **Latency**: P95 < 2 seconds
- **Error Rate**: < 1% of requests
- **Availability**: All health checks pass

## Nightly Automation

### Workflow Configuration
The nightly workflow (`perf-nightly.yml`) runs automatically at 2 AM UTC and can be manually triggered with custom parameters.

### Prerequisites
1. Set `PERF_ENABLED=1` in repository variables
2. Configure target URLs:
   - Staging: `STAGING_URL` or `ACA_APP_WEB` + `ACA_ENV`
   - Production: `PROD_URL` or `ACA_APP_WEB_PROD` + `ACA_ENV_PROD`
3. Optional: Set `PERF_API_KEY` secret for authenticated tests

### Environment Variables
```bash
# Required
PERF_ENABLED=1

# Target URLs (choose one method per environment)
STAGING_URL=https://your-staging-app.azurecontainerapps.io
# OR
ACA_APP_WEB=your-staging-app
ACA_ENV=your-staging-env

PROD_URL=https://your-prod-app.azurecontainerapps.io
# OR  
ACA_APP_WEB_PROD=your-prod-app
ACA_ENV_PROD=your-prod-env

# Optional authentication
PERF_API_KEY=your-api-key-for-authenticated-tests
```

## Manual Execution

### Local Testing
```bash
# Install k6
# On macOS: brew install k6
# On Ubuntu: see workflow for installation steps

# Run smoke test locally
k6 run perf/k6/smoke.js --env BASE_URL=http://localhost:8000

# Run hot path test with authentication
k6 run perf/k6/hot-path.js \
  --env BASE_URL=https://your-app.com \
  --env API_KEY=your-api-key
```

### Manual Workflow Trigger
1. Go to GitHub Actions
2. Select "Nightly Performance Tests"
3. Click "Run workflow"
4. Choose environment and test type
5. Click "Run workflow"

## Artifacts and Reporting

### Generated Artifacts
- `smoke-summary.json` - Smoke test metrics
- `hot-path-summary.json` - Hot path test metrics
- `hot-path-summary.html` - HTML performance report
- `nightly-report.md` - Combined test summary

### Artifact Access
1. Navigate to workflow run in GitHub Actions
2. Scroll to "Artifacts" section
3. Download `performance-results-{environment}-{run-number}`
4. Extract and review JSON/HTML reports

## SLO Violation Handling

### Automatic Issue Creation
When SLO violations are detected during scheduled runs:
1. GitHub issue is automatically created
2. Issue includes violation details and troubleshooting steps
3. Issue is assigned to the workflow triggerer
4. Performance and SLO violation labels are applied

### Manual Investigation
For SLO violations:
1. Review test artifacts for specific failures
2. Check application logs during test timeframe
3. Analyze infrastructure metrics (CPU, memory, network)
4. Identify performance bottlenecks
5. Implement fixes and re-run tests

## Customization

### Adding New Tests
1. Create new `.js` file in `perf/k6/`
2. Follow existing test patterns
3. Include SLO threshold validation
4. Add summary output functions
5. Update workflow to include new test

### Test Configuration
Modify `options` object in test files:
```javascript
export const options = {
  vus: 10,           // Virtual users
  duration: '5m',    // Test duration
  thresholds: {
    http_req_duration: ['p95<2000'],  // SLO thresholds
    http_req_failed: ['rate<0.01'],
  },
};
```

### Environment-Specific Tests
Use environment variables for configuration:
```javascript
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || '';
const TEST_DATA_SIZE = __ENV.TEST_DATA_SIZE || '100';
```

## Troubleshooting

### Common Issues
- **k6 installation fails**: Check package repository configuration
- **Network timeouts**: Increase timeout values in test params
- **Authentication failures**: Verify API_KEY secret configuration
- **SLO false positives**: Review and adjust thresholds

### Test Debugging
```bash
# Enable verbose output
k6 run --verbose perf/k6/smoke.js

# Run with specific configuration
k6 run perf/k6/smoke.js \
  --env BASE_URL=https://staging.example.com \
  --env DEBUG=true \
  --http-debug="full"

# Single iteration for debugging
k6 run --vus 1 --iterations 1 perf/k6/hot-path.js
```

### Performance Analysis
1. **High latency**: Check database query performance, external API calls
2. **High error rate**: Review application logs, check authentication
3. **Test failures**: Verify endpoints exist and are accessible
4. **Resource constraints**: Monitor container resource usage

## Integration with Monitoring

### Metrics Correlation
Performance test results should be correlated with:
- Application Insights metrics
- Container Apps resource utilization
- Azure Load Balancer metrics
- Database performance counters

### Alerting Integration
Consider setting up alerts for:
- Consecutive performance test failures
- SLO violation trend analysis
- Performance regression detection
- Infrastructure resource exhaustion

## References
- [K6 Documentation](https://k6.io/docs/)
- [K6 Test Types](https://k6.io/docs/test-types/)
- [SLO Definitions](../docs/alerts/slo-definitions.md)
- [Load Testing Best Practices](../docs/load-testing.md)
# Load Testing Infrastructure

Comprehensive k6-based load testing framework for the AI-Enabled Cyber Maturity Assessment platform.

## Overview

This load testing infrastructure provides enterprise-scale performance validation through multiple test scenarios:

- **Smoke Tests**: Basic functionality validation with minimal load
- **Load Tests**: Normal operating conditions (100 concurrent users)
- **Stress Tests**: Peak load testing (500 concurrent users)
- **Spike Tests**: Sudden traffic surge handling
- **Soak Tests**: Extended duration stability testing (30 minutes)
- **Breakpoint Tests**: System capacity limit discovery

## Quick Start

### Prerequisites

1. **k6 Installation**:
   ```bash
   # macOS
   brew install k6
   
   # Ubuntu/Debian
   sudo gpg -k
   sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6
   ```

2. **Environment Setup**:
   ```bash
   # Set target environment
   export TARGET_ENV=local  # or dev, staging, prod
   
   # For non-local environments, set API URLs
   export DEV_API_URL=https://dev-api.example.com
   export STAGING_API_URL=https://staging-api.example.com
   export PROD_API_URL=https://prod-api.example.com
   ```

### Running Tests

1. **Quick Smoke Test**:
   ```bash
   cd e2e/load
   k6 run scenarios/smoke.js
   ```

2. **Load Test (100 users)**:
   ```bash
   k6 run scenarios/load.js
   ```

3. **Custom Duration**:
   ```bash
   export DURATION_OVERRIDE=5m
   k6 run scenarios/load.js
   ```

4. **With Results Export**:
   ```bash
   k6 run --out json=reports/load-test-$(date +%Y%m%d-%H%M%S).json scenarios/load.js
   ```

## Test Scenarios

### Smoke Test (`scenarios/smoke.js`)
**Purpose**: Validate basic functionality with minimal load  
**Load**: 1 virtual user for 30 seconds  
**Use Cases**:
- Pre-deployment validation
- CI/CD pipeline integration
- Quick health checks

**Key Metrics**:
- All endpoints respond correctly
- Authentication works
- Basic CRUD operations functional

### Load Test (`scenarios/load.js`)
**Purpose**: Simulate normal operating conditions  
**Load**: Ramp to 100 concurrent users over 9 minutes  
**Use Cases**:
- Capacity planning
- Performance regression testing
- SLA validation

**User Patterns**:
- 60% create engagements
- 80% complete assessments
- 40% manage documents
- 25% perform RAG searches

### Stress Test (`scenarios/stress.js`)
**Purpose**: Test system under extreme load conditions  
**Load**: Ramp to 500 concurrent users over 15 minutes  
**Use Cases**:
- Peak capacity testing
- Failure mode analysis
- Recovery behavior validation

**Acceptance Criteria**:
- Error rate < 15%
- P95 response time < 5s
- No complete system failures

### Spike Test (`scenarios/spike.js`)
**Purpose**: Test sudden traffic surge handling  
**Load**: Sudden spike from 100 to 1000 users  
**Use Cases**:
- Auto-scaling validation
- Circuit breaker testing
- Viral load scenarios

**Key Observations**:
- Auto-scaling response time
- Circuit breaker activation
- Service degradation patterns

### Soak Test (`scenarios/soak.js`)
**Purpose**: Long-term stability and memory leak detection  
**Load**: 50 concurrent users for 30 minutes  
**Use Cases**:
- Memory leak detection
- Resource degradation analysis
- Long-term stability validation

**Monitoring**:
- Memory usage trends
- Performance degradation
- Resource exhaustion patterns

### Breakpoint Test (`scenarios/breakpoint.js`)
**Purpose**: Find system capacity limits  
**Load**: Gradually increase from 100 to 800+ RPS  
**Use Cases**:
- Capacity planning
- Infrastructure sizing
- Bottleneck identification

**Outputs**:
- Maximum sustainable RPS
- Performance cliff identification
- Resource utilization patterns

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TARGET_ENV` | Target environment | `local` | `dev`, `staging`, `prod` |
| `DEV_API_URL` | Development API URL | - | `https://dev-api.example.com` |
| `AUTH_MODE` | Authentication mode | `demo` | `demo`, `aad` |
| `DURATION_OVERRIDE` | Override test duration | - | `5m`, `30s`, `1h` |
| `MAX_VUS` | Maximum virtual users | `2000` | `500`, `1000` |
| `P95_THRESHOLD_MS` | P95 response time threshold | `2000` | `1500`, `3000` |
| `MAX_ERROR_RATE` | Maximum acceptable error rate | `0.05` | `0.02`, `0.10` |
| `CLEANUP_RATE` | Test data cleanup percentage | `0.1` | `0.05`, `1.0` |
| `ENABLE_RAG_TESTING` | Enable RAG search testing | `true` | `false` |
| `SLACK_WEBHOOK_URL` | Slack notifications | - | `https://hooks.slack.com/...` |

### Performance Thresholds

Default performance thresholds can be customized per environment:

```javascript
// Example threshold configuration
const thresholds = {
  'http_req_duration': ['p(95)<2000', 'p(99)<5000'],
  'http_req_failed': ['rate<0.05'],
  'checks': ['rate>0.95']
};
```

### Feature Flags

Control which features are tested:

```bash
export ENABLE_RAG_TESTING=true
export ENABLE_DOCUMENT_UPLOAD=true
export ENABLE_GDPR_TESTING=false
export ENABLE_ADMIN_TESTING=true
```

## CI/CD Integration

### GitHub Actions Workflow

The load testing workflow (`.github/workflows/load-testing.yml`) provides:

- Manual trigger with scenario selection
- Scheduled smoke tests (weekdays 2 AM UTC)
- Release validation
- Multi-environment support
- Slack notifications
- Artifact collection

### Triggering Load Tests

1. **Manual Trigger**:
   - Go to Actions tab in GitHub
   - Select "Load Testing" workflow
   - Click "Run workflow"
   - Choose scenario and environment

2. **API Trigger**:
   ```bash
   curl -X POST \
     -H "Accept: application/vnd.github.v3+json" \
     -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/owner/repo/actions/workflows/load-testing.yml/dispatches \
     -d '{"ref":"main","inputs":{"scenario":"load","environment":"staging"}}'
   ```

### Results and Artifacts

- Test results are stored as GitHub Actions artifacts
- JSON reports include detailed metrics
- Markdown summaries for easy review
- 30-day retention for historical analysis

## Interpreting Results

### Key Metrics

1. **Response Time**:
   - **P95 < 2s**: Excellent
   - **P95 2-5s**: Acceptable
   - **P95 > 5s**: Investigation needed

2. **Error Rate**:
   - **< 2%**: Excellent
   - **2-5%**: Acceptable
   - **> 5%**: Investigation needed

3. **Throughput**:
   - **RPS**: Requests per second
   - **VUs**: Virtual users (concurrent)
   - **Efficiency**: Actual vs theoretical throughput

### Performance Analysis

#### Good Performance Indicators
```
✅ P95 response time: 800ms
✅ Error rate: 1.2%
✅ Throughput: 150 RPS
✅ No timeouts or circuit breaker activations
```

#### Warning Signs
```
⚠️ P95 response time: 3.5s (degrading)
⚠️ Error rate: 4.8% (elevated)
⚠️ Memory usage trending upward
⚠️ Cache hit rate declining
```

#### Critical Issues
```
❌ P95 response time: 8s+ (unacceptable)
❌ Error rate: 15%+ (system struggling)
❌ Timeouts and 5xx errors
❌ Circuit breakers activating
```

### Common Issues and Solutions

| Issue | Symptoms | Likely Causes | Solutions |
|-------|----------|---------------|-----------|
| High Response Times | P95 > 5s | Database bottlenecks, unoptimized queries | Query optimization, indexing, caching |
| High Error Rate | > 5% failures | Resource exhaustion, configuration issues | Scale resources, review configs |
| Memory Leaks | Increasing memory over time | Unclosed connections, memory retention | Profile application, fix leaks |
| Capacity Limits | Performance cliff at specific load | CPU/memory/connection limits | Horizontal scaling, optimization |
| Auth Failures | Authentication errors under load | Session management issues | Session optimization, load balancing |

### Trend Analysis

Monitor these trends over time:

1. **Baseline Performance**: Establish baseline metrics for comparison
2. **Regression Detection**: Watch for degradation across releases
3. **Capacity Planning**: Track maximum sustainable load
4. **Seasonal Patterns**: Understand load variations

## Advanced Usage

### Custom Scenarios

Create custom test scenarios by extending base patterns:

```javascript
import { getTestConfig } from '../k6.config.js';
import { createAuthSession } from '../utils/auth.js';

const config = getTestConfig('custom');
export const options = {
  ...config.options,
  scenarios: {
    custom_scenario: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },
        { duration: '3m', target: 50 },
        { duration: '1m', target: 0 }
      ]
    }
  }
};

export default function() {
  // Custom test logic
}
```

### Performance Profiling

For detailed performance analysis:

1. **Enable detailed metrics**:
   ```bash
   export ENABLE_DETAILED_METRICS=true
   ```

2. **Monitor system resources**:
   ```bash
   # During test execution
   kubectl top pods  # For Kubernetes deployments
   az monitor metrics list  # For Azure deployments
   ```

3. **Application Insights integration**:
   - Performance counters
   - Custom telemetry
   - Real-time monitoring

### Data Management

#### Test Data Lifecycle

1. **Creation**: Tests generate realistic data
2. **Usage**: Data used across test operations
3. **Cleanup**: Automatic cleanup based on `CLEANUP_RATE`
4. **Retention**: Configurable retention policies

#### Cleanup Strategies

- **Immediate**: 100% cleanup after each test
- **Periodic**: Cleanup percentage of test data
- **Retention**: Keep data for specified duration
- **Manual**: No automatic cleanup

### Troubleshooting

#### Common Issues

1. **Test won't start**:
   ```bash
   # Check environment connectivity
   curl $DEV_API_URL/health
   
   # Verify authentication
   export AUTH_MODE=demo
   ```

2. **High failure rate**:
   ```bash
   # Reduce concurrent load
   export MAX_VUS=50
   
   # Enable verbose logging
   k6 run --verbose scenarios/smoke.js
   ```

3. **Memory issues**:
   ```bash
   # Increase cleanup rate
   export CLEANUP_RATE=0.5
   
   # Reduce test duration
   export DURATION_OVERRIDE=2m
   ```

#### Debug Mode

Enable debug output:

```bash
export K6_LOG_OUTPUT=stdout
export K6_LOG_LEVEL=debug
k6 run scenarios/smoke.js
```

## Best Practices

### Test Design

1. **Start Small**: Begin with smoke tests before load tests
2. **Realistic Patterns**: Model actual user behavior
3. **Gradual Increase**: Ramp up load gradually
4. **Environment Parity**: Test environments should match production
5. **Data Cleanup**: Always clean up test data

### Performance Monitoring

1. **Baseline Establishment**: Record baseline performance metrics
2. **Continuous Monitoring**: Run tests regularly
3. **Trend Analysis**: Track performance over time
4. **Alert Thresholds**: Set appropriate alert levels
5. **Correlation**: Correlate test results with system metrics

### CI/CD Integration

1. **Gate Quality**: Use tests as quality gates
2. **Fast Feedback**: Keep test duration reasonable
3. **Parallel Execution**: Run multiple scenarios in parallel
4. **Result Archival**: Store results for historical analysis
5. **Notification Strategy**: Alert on failures and trends

## Security Considerations

### Test Data

- Use synthetic data, never production data
- Implement data encryption for sensitive scenarios
- Follow data retention policies
- Clean up test data regularly

### Access Control

- Limit load testing to authorized personnel
- Use dedicated test accounts
- Implement proper authentication
- Monitor test execution logs

### Network Security

- Run tests from authorized networks
- Use VPN for remote testing
- Implement rate limiting awareness
- Coordinate with security teams

## Support and Maintenance

### Regular Maintenance

1. **k6 Updates**: Keep k6 version current
2. **Threshold Review**: Adjust thresholds based on system changes
3. **Scenario Updates**: Update scenarios as features evolve
4. **Environment Sync**: Keep test environments aligned

### Troubleshooting Support

For issues with load testing:

1. Check this documentation
2. Review test logs and results
3. Validate environment configuration
4. Consult with DevOps/Platform teams

### Contributing

To contribute improvements:

1. Follow existing code patterns
2. Add appropriate documentation
3. Test changes thoroughly
4. Submit pull requests for review

---

## Summary

This load testing infrastructure provides comprehensive performance validation for the AI-Enabled Cyber Maturity Assessment platform. Use the appropriate scenarios for your testing needs, monitor key metrics, and iterate based on results to ensure optimal system performance.

For questions or support, please refer to the troubleshooting section or contact the platform team.
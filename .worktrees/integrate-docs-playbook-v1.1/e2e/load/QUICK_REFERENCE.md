# Load Testing Quick Reference

## Common Commands

### Basic Test Execution
```bash
# Smoke test (quick validation)
k6 run scenarios/smoke.js

# Load test (100 users)
k6 run scenarios/load.js

# Stress test (500 users)
k6 run scenarios/stress.js

# Custom duration
DURATION_OVERRIDE=5m k6 run scenarios/load.js

# With JSON output
k6 run --out json=results.json scenarios/load.js
```

### Environment Setup
```bash
# Local testing
export TARGET_ENV=local

# Development environment
export TARGET_ENV=dev
export DEV_API_URL=https://dev-api.example.com

# Staging environment
export TARGET_ENV=staging
export STAGING_API_URL=https://staging-api.example.com
export AUTH_MODE=aad

# Production (read-only tests)
export TARGET_ENV=prod
export PROD_API_URL=https://api.example.com
export AUTH_MODE=aad
```

### Configuration Overrides
```bash
# Performance thresholds
export P95_THRESHOLD_MS=1500
export MAX_ERROR_RATE=0.02

# Test behavior
export MAX_VUS=200
export CLEANUP_RATE=0.5
export ENABLE_RAG_TESTING=false

# Monitoring
export ENABLE_DETAILED_METRICS=true
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## Scenario Quick Guide

| Scenario | Duration | Load | Purpose |
|----------|----------|------|---------|
| `smoke` | 30s | 1 user | Quick validation |
| `load` | 9m | 100 users | Normal operations |
| `stress` | 15m | 500 users | Peak capacity |
| `spike` | 12m | 100→1000→100 | Traffic surges |
| `soak` | 30m | 50 users | Stability testing |
| `breakpoint` | 40m | 100→800+ RPS | Capacity limits |

## Performance Thresholds

### Response Time Guidelines
- **Excellent**: P95 < 1s
- **Good**: P95 < 2s  
- **Acceptable**: P95 < 5s
- **Poor**: P95 > 5s

### Error Rate Guidelines
- **Excellent**: < 1%
- **Good**: < 2%
- **Acceptable**: < 5%
- **Poor**: > 5%

### Throughput Expectations
- **Basic**: 10-50 RPS
- **Moderate**: 50-200 RPS
- **High**: 200+ RPS

## Quick Troubleshooting

### Test Won't Start
```bash
# Check connectivity
curl $DEV_API_URL/health

# Verify k6 installation
k6 version

# Test minimal scenario
k6 run --duration 10s --vus 1 scenarios/smoke.js
```

### High Error Rates
```bash
# Reduce load
export MAX_VUS=10
export DURATION_OVERRIDE=1m

# Check auth configuration
export AUTH_MODE=demo

# Increase cleanup
export CLEANUP_RATE=1.0
```

### Memory/Performance Issues
```bash
# Minimal test
export MAX_VUS=5
export DURATION_OVERRIDE=30s
export CLEANUP_RATE=1.0

# Disable features
export ENABLE_RAG_TESTING=false
export ENABLE_DOCUMENT_UPLOAD=false
```

## Results Interpretation

### JSON Output Analysis
```bash
# Extract key metrics
jq '.metrics."http_req_duration".values[] | .value' results.json | sort -n

# Count errors
jq '.metrics."http_req_failed".values[] | select(.value == 1)' results.json | wc -l

# Get response time percentiles
jq '.metrics."http_req_duration".values[] | .value' results.json | sort -n | awk '{all[NR] = $0} END{print "P95:", all[int(NR*0.95)]}'
```

### Success Criteria Checklist
- [ ] Test completed without crashes
- [ ] Error rate < 5%
- [ ] P95 response time < threshold
- [ ] No timeouts or circuit breaker activations
- [ ] Memory usage stable
- [ ] All business functions working

## CI/CD Integration

### GitHub Actions Trigger
```bash
# Manual workflow dispatch
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/actions/workflows/load-testing.yml/dispatches \
  -d '{"ref":"main","inputs":{"scenario":"load","environment":"staging"}}'
```

### Local CI Simulation
```bash
# Run all scenarios locally
for scenario in smoke load stress; do
  echo "Running $scenario test..."
  TARGET_ENV=local k6 run scenarios/${scenario}.js
done
```

## Environment-Specific Notes

### Local Development
- Use `demo` auth mode
- Higher error tolerance
- Full cleanup enabled
- All features enabled for testing

### Development Environment
- Mix of `demo` and `aad` auth
- Moderate thresholds
- Partial cleanup
- Most features enabled

### Staging Environment
- Production-like configuration
- Strict thresholds
- Minimal cleanup
- Full feature testing

### Production Environment
- Read-only operations only
- Strictest thresholds
- No data creation
- Monitoring focus

## Feature Testing Matrix

| Feature | Smoke | Load | Stress | Spike | Soak | Breakpoint |
|---------|-------|------|--------|-------|------|------------|
| Authentication | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Engagements | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Assessments | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Documents | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| RAG Search | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Admin Ops | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| GDPR Ops | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Monitoring Dashboards

### Key Metrics to Watch
```
Response Time:
- http_req_duration (P50, P95, P99)

Error Rates:
- http_req_failed
- checks (success rate)

Throughput:
- http_reqs (total requests)
- iteration_duration

System Health:
- memory_usage_mb
- cpu_usage_percent
- cache_hit_rate
```

### Alert Conditions
```javascript
// Response time alerts
http_req_duration{p95} > 2000ms

// Error rate alerts  
http_req_failed{rate} > 0.05

// System resource alerts
memory_usage_mb > 1500
cpu_usage_percent > 80
```

## Data Management

### Cleanup Rates by Scenario
- **Smoke**: 100% (immediate cleanup)
- **Load**: 10% (periodic cleanup)
- **Stress**: 5% (minimal cleanup)
- **Spike**: 2% (very minimal)
- **Soak**: 2% (prevent accumulation)
- **Breakpoint**: 1% (maximum performance)

### Test Data Types
- Engagements: Auto-cleanup after test
- Assessments: Auto-cleanup after test  
- Documents: Configurable cleanup
- User sessions: Always cleaned up
- Temporary files: Auto-removed

## Emergency Procedures

### Stop All Tests
```bash
# Kill local k6 processes
pkill k6

# For containerized tests
docker stop $(docker ps -q --filter "ancestor=loadimpact/k6")
```

### Quick System Check
```bash
#!/bin/bash
echo "=== System Health Check ==="
curl -s $DEV_API_URL/health | jq .
curl -s $DEV_API_URL/version | jq .app_version
echo "=== Load Test Status ==="
ps aux | grep k6
echo "=== Disk Space ==="
df -h | grep -E "/$|/tmp"
```

### Recovery Steps
1. Stop all running tests
2. Check system resources
3. Clean up test data manually if needed
4. Restart with smoke test
5. Gradually increase load

---

*For detailed information, see the full [README.md](README.md)*
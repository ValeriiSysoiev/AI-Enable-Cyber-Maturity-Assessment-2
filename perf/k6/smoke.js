import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const responseTime = new Trend('response_time');

// Test configuration for smoke testing
export const options = {
  vus: 2, // 2 virtual users
  duration: '2m', // Run for 2 minutes
  thresholds: {
    http_req_duration: ['p95<2000'], // 95% of requests must complete below 2s (SLO)
    http_req_failed: ['rate<0.01'], // Error rate must be below 1% (SLO)
    errors: ['rate<0.01'],
  },
};

// Environment configuration
const BASE_URL = __ENV.BASE_URL || 'https://your-app.azurecontainerapps.io';
const API_KEY = __ENV.API_KEY || '';

// Test data
const testUser = {
  email: 'test@example.com',
  password: 'TestPassword123!',
};

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-smoke-test/1.0',
    },
    timeout: '30s',
  };

  // Add API key if provided
  if (API_KEY) {
    params.headers['Authorization'] = `Bearer ${API_KEY}`;
  }

  // Test 1: Health Check
  const healthResponse = http.get(`${BASE_URL}/health`, params);
  
  const healthCheck = check(healthResponse, {
    'health endpoint responds': (r) => r.status === 200,
    'health response time < 1s': (r) => r.timings.duration < 1000,
    'health has correct content': (r) => r.body.includes('healthy') || r.body.includes('ok'),
  });
  
  if (!healthCheck) {
    errorRate.add(1);
  }
  responseTime.add(healthResponse.timings.duration);

  sleep(1);

  // Test 2: API Version Endpoint
  const versionResponse = http.get(`${BASE_URL}/api/version`, params);
  
  const versionCheck = check(versionResponse, {
    'version endpoint responds': (r) => r.status === 200,
    'version response time < 1s': (r) => r.timings.duration < 1000,
    'version has valid JSON': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    },
  });

  if (!versionCheck) {
    errorRate.add(1);
  }
  responseTime.add(versionResponse.timings.duration);

  sleep(1);

  // Test 3: Hot Path - Assessment List (if authenticated)
  if (API_KEY) {
    const assessmentsResponse = http.get(`${BASE_URL}/api/assessments`, params);
    
    const assessmentsCheck = check(assessmentsResponse, {
      'assessments endpoint responds': (r) => r.status === 200 || r.status === 401,
      'assessments response time < 2s': (r) => r.timings.duration < 2000,
    });

    if (!assessmentsCheck) {
      errorRate.add(1);
    }
    responseTime.add(assessmentsResponse.timings.duration);
  }

  sleep(2);

  // Test 4: Static Assets
  const staticResponse = http.get(`${BASE_URL}/`, params);
  
  const staticCheck = check(staticResponse, {
    'static content loads': (r) => r.status === 200 || r.status === 404,
    'static response time < 3s': (r) => r.timings.duration < 3000,
  });

  if (!staticCheck) {
    errorRate.add(1);
  }
  responseTime.add(staticResponse.timings.duration);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'artifacts/perf/smoke-summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = '\n' + indent + '📊 K6 Smoke Test Summary\n';
  summary += indent + '========================\n\n';
  
  // Test duration
  const duration = data.state.testRunDurationMs / 1000;
  summary += indent + `⏱️  Duration: ${duration.toFixed(2)}s\n`;
  
  // Request stats
  const httpReqs = data.metrics.http_reqs;
  if (httpReqs) {
    summary += indent + `📈 Requests: ${httpReqs.values.count} total\n`;
    summary += indent + `📊 RPS: ${(httpReqs.values.rate || 0).toFixed(2)}\n`;
  }
  
  // Response time stats
  const httpDuration = data.metrics.http_req_duration;
  if (httpDuration) {
    summary += indent + `⚡ Response Time (avg): ${httpDuration.values.avg.toFixed(2)}ms\n`;
    summary += indent + `📊 Response Time (p95): ${httpDuration.values['p(95)'].toFixed(2)}ms\n`;
  }
  
  // Error rate
  const httpFailed = data.metrics.http_req_failed;
  if (httpFailed) {
    const errorPct = (httpFailed.values.rate * 100).toFixed(2);
    summary += indent + `❌ Error Rate: ${errorPct}%\n`;
  }
  
  // SLO status
  summary += indent + '\n🎯 SLO Compliance:\n';
  const p95 = httpDuration?.values['p(95)'] || 0;
  const errorRate = httpFailed?.values.rate || 0;
  
  summary += indent + `   Latency P95 < 2s: ${p95 < 2000 ? '✅' : '❌'} (${p95.toFixed(2)}ms)\n`;
  summary += indent + `   Error Rate < 1%: ${errorRate < 0.01 ? '✅' : '❌'} (${(errorRate * 100).toFixed(2)}%)\n`;
  
  return summary + '\n';
}
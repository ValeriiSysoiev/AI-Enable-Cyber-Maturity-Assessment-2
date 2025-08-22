import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const responseTime = new Trend('response_time');
export const assessmentCreated = new Counter('assessments_created');

// Test configuration for hot path testing
export const options = {
  stages: [
    { duration: '30s', target: 5 },  // Ramp up
    { duration: '2m', target: 10 },  // Steady state
    { duration: '30s', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p95<2000', 'p99<5000'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.01'],
    assessments_created: ['count>0'],
  },
};

// Environment configuration
const BASE_URL = __ENV.BASE_URL || 'https://your-app.azurecontainerapps.io';
const API_KEY = __ENV.API_KEY || '';

// Test data
const testEngagement = {
  name: `Performance Test Engagement ${Date.now()}`,
  description: 'Automated performance test engagement',
  framework: 'NIST CSF 2.0',
  start_date: new Date().toISOString().split('T')[0],
};

const testAssessment = {
  title: `Perf Test Assessment ${Date.now()}`,
  description: 'Performance testing assessment',
  framework_id: 'csf-2.0',
};

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-hot-path-test/1.0',
    },
    timeout: '30s',
  };

  // Add API key if provided
  if (API_KEY) {
    params.headers['Authorization'] = `Bearer ${API_KEY}`;
  }

  // Hot Path 1: List Engagements
  const engagementsResponse = http.get(`${BASE_URL}/api/engagements`, params);
  
  const engagementsCheck = check(engagementsResponse, {
    'engagements list loads': (r) => r.status === 200 || r.status === 401,
    'engagements response time < 2s': (r) => r.timings.duration < 2000,
    'engagements returns JSON': (r) => {
      try {
        const data = JSON.parse(r.body);
        return Array.isArray(data) || typeof data === 'object';
      } catch {
        return false;
      }
    },
  });

  if (!engagementsCheck) {
    errorRate.add(1);
  }
  responseTime.add(engagementsResponse.timings.duration);

  sleep(1);

  // Hot Path 2: Get Assessment Frameworks
  const frameworksResponse = http.get(`${BASE_URL}/api/frameworks`, params);
  
  const frameworksCheck = check(frameworksResponse, {
    'frameworks list loads': (r) => r.status === 200 || r.status === 401,
    'frameworks response time < 1.5s': (r) => r.timings.duration < 1500,
  });

  if (!frameworksCheck) {
    errorRate.add(1);
  }
  responseTime.add(frameworksResponse.timings.duration);

  sleep(1);

  // Hot Path 3: Create Assessment (if authenticated)
  if (API_KEY && engagementsResponse.status === 200) {
    const createAssessmentResponse = http.post(
      `${BASE_URL}/api/assessments`,
      JSON.stringify(testAssessment),
      params
    );
    
    const createCheck = check(createAssessmentResponse, {
      'assessment creation succeeds': (r) => r.status === 201 || r.status === 200,
      'assessment creation time < 3s': (r) => r.timings.duration < 3000,
      'assessment returns valid data': (r) => {
        try {
          const data = JSON.parse(r.body);
          return data.id || data.assessment_id;
        } catch {
          return false;
        }
      },
    });

    if (createCheck) {
      assessmentCreated.add(1);
    } else {
      errorRate.add(1);
    }
    responseTime.add(createAssessmentResponse.timings.duration);

    // Hot Path 4: Get Assessment Details
    if (createAssessmentResponse.status < 300) {
      try {
        const assessment = JSON.parse(createAssessmentResponse.body);
        const assessmentId = assessment.id || assessment.assessment_id;
        
        if (assessmentId) {
          const detailsResponse = http.get(`${BASE_URL}/api/assessments/${assessmentId}`, params);
          
          const detailsCheck = check(detailsResponse, {
            'assessment details load': (r) => r.status === 200,
            'assessment details time < 2s': (r) => r.timings.duration < 2000,
          });

          if (!detailsCheck) {
            errorRate.add(1);
          }
          responseTime.add(detailsResponse.timings.duration);
        }
      } catch (e) {
        console.warn('Failed to parse assessment response:', e);
        errorRate.add(1);
      }
    }
  }

  sleep(2);

  // Hot Path 5: Search/Query Operation
  const searchResponse = http.get(`${BASE_URL}/api/search?q=cyber&limit=10`, params);
  
  const searchCheck = check(searchResponse, {
    'search responds': (r) => r.status === 200 || r.status === 404 || r.status === 401,
    'search response time < 3s': (r) => r.timings.duration < 3000,
  });

  if (!searchCheck) {
    errorRate.add(1);
  }
  responseTime.add(searchResponse.timings.duration);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'artifacts/perf/hot-path-summary.json': JSON.stringify(data, null, 2),
    'artifacts/perf/hot-path-summary.html': htmlSummary(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function htmlSummary(data) {
  const duration = data.state.testRunDurationMs / 1000;
  const httpReqs = data.metrics.http_reqs?.values || {};
  const httpDuration = data.metrics.http_req_duration?.values || {};
  const httpFailed = data.metrics.http_req_failed?.values || {};
  
  return `
<!DOCTYPE html>
<html>
<head>
    <title>K6 Hot Path Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .pass { color: #4CAF50; } .fail { color: #F44336; }
        .chart { width: 100%; height: 200px; border: 1px solid #ddd; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>🚀 K6 Hot Path Performance Report</h1>
    <p><strong>Test Duration:</strong> ${duration.toFixed(2)}s</p>
    
    <div class="metric">
        <h3>📊 Request Statistics</h3>
        <p>Total Requests: ${httpReqs.count || 0}</p>
        <p>Requests/sec: ${(httpReqs.rate || 0).toFixed(2)}</p>
    </div>
    
    <div class="metric">
        <h3>⚡ Response Time</h3>
        <p>Average: ${(httpDuration.avg || 0).toFixed(2)}ms</p>
        <p>P95: ${(httpDuration['p(95)'] || 0).toFixed(2)}ms</p>
        <p>P99: ${(httpDuration['p(99)'] || 0).toFixed(2)}ms</p>
    </div>
    
    <div class="metric">
        <h3>🎯 SLO Compliance</h3>
        <p class="${(httpDuration['p(95)'] || 0) < 2000 ? 'pass' : 'fail'}">
            P95 Latency < 2s: ${((httpDuration['p(95)'] || 0) < 2000 ? '✅' : '❌')} (${(httpDuration['p(95)'] || 0).toFixed(2)}ms)
        </p>
        <p class="${(httpFailed.rate || 0) < 0.01 ? 'pass' : 'fail'}">
            Error Rate < 1%: ${((httpFailed.rate || 0) < 0.01 ? '✅' : '❌')} (${((httpFailed.rate || 0) * 100).toFixed(2)}%)
        </p>
    </div>
    
    <p><em>Generated: ${new Date().toISOString()}</em></p>
</body>
</html>`;
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  
  let summary = '\n' + indent + '🚀 K6 Hot Path Test Summary\n';
  summary += indent + '============================\n\n';
  
  const duration = data.state.testRunDurationMs / 1000;
  summary += indent + `⏱️  Duration: ${duration.toFixed(2)}s\n`;
  
  const httpReqs = data.metrics.http_reqs;
  if (httpReqs) {
    summary += indent + `📈 Requests: ${httpReqs.values.count} total\n`;
    summary += indent + `📊 RPS: ${(httpReqs.values.rate || 0).toFixed(2)}\n`;
  }
  
  const httpDuration = data.metrics.http_req_duration;
  if (httpDuration) {
    summary += indent + `⚡ Response Time (avg): ${httpDuration.values.avg.toFixed(2)}ms\n`;
    summary += indent + `📊 Response Time (p95): ${httpDuration.values['p(95)'].toFixed(2)}ms\n`;
    summary += indent + `📊 Response Time (p99): ${httpDuration.values['p(99)'].toFixed(2)}ms\n`;
  }
  
  const httpFailed = data.metrics.http_req_failed;
  if (httpFailed) {
    const errorPct = (httpFailed.values.rate * 100).toFixed(2);
    summary += indent + `❌ Error Rate: ${errorPct}%\n`;
  }
  
  summary += indent + '\n🎯 SLO Compliance:\n';
  const p95 = httpDuration?.values['p(95)'] || 0;
  const errorRate = httpFailed?.values.rate || 0;
  
  summary += indent + `   Latency P95 < 2s: ${p95 < 2000 ? '✅' : '❌'} (${p95.toFixed(2)}ms)\n`;
  summary += indent + `   Error Rate < 1%: ${errorRate < 0.01 ? '✅' : '❌'} (${(errorRate * 100).toFixed(2)}%)\n`;
  
  return summary + '\n';
}
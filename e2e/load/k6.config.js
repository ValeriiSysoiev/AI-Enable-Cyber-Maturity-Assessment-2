/**
 * k6 Load Testing Configuration
 * 
 * Centralized configuration for all load testing scenarios.
 * Supports multiple environments and test scenarios.
 */

import { check } from 'k6';

// Environment configuration
export const environments = {
  local: {
    baseUrl: 'http://localhost:8000',
    webUrl: 'http://localhost:3000',
    authMode: 'demo'
  },
  dev: {
    baseUrl: process.env.DEV_API_URL || 'https://dev-api.example.com',
    webUrl: process.env.DEV_WEB_URL || 'https://dev.example.com',
    authMode: process.env.AUTH_MODE || 'demo'
  },
  staging: {
    baseUrl: process.env.STAGING_API_URL || 'https://staging-api.example.com',
    webUrl: process.env.STAGING_WEB_URL || 'https://staging.example.com',
    authMode: process.env.AUTH_MODE || 'aad'
  },
  prod: {
    baseUrl: process.env.PROD_API_URL || 'https://api.example.com',
    webUrl: process.env.PROD_WEB_URL || 'https://app.example.com',
    authMode: process.env.AUTH_MODE || 'aad'
  }
};

// Get current environment
export const getCurrentEnvironment = () => {
  const env = process.env.TARGET_ENV || 'local';
  if (!environments[env]) {
    throw new Error(`Unknown environment: ${env}. Valid options: ${Object.keys(environments).join(', ')}`);
  }
  return environments[env];
};

// Test scenarios configuration
export const scenarios = {
  smoke: {
    description: 'Basic functionality validation with minimal load',
    executor: 'constant-vus',
    vus: 1,
    duration: '30s',
    tags: { test_type: 'smoke' }
  },
  
  load: {
    description: 'Normal operating load (100 concurrent users)',
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 20 },  // Ramp up
      { duration: '5m', target: 100 }, // Stay at 100 users
      { duration: '2m', target: 0 }    // Ramp down
    ],
    tags: { test_type: 'load' }
  },
  
  stress: {
    description: 'Peak load testing (500 concurrent users)',
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 100 }, // Ramp up to normal load
      { duration: '5m', target: 500 }, // Peak load
      { duration: '5m', target: 500 }, // Stay at peak
      { duration: '2m', target: 100 }, // Ramp down to normal
      { duration: '1m', target: 0 }    // Complete ramp down
    ],
    tags: { test_type: 'stress' }
  },
  
  spike: {
    description: 'Sudden traffic spikes',
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '10s', target: 100 }, // Normal load
      { duration: '1m', target: 100 },  // Stay normal
      { duration: '10s', target: 1000 }, // Sudden spike
      { duration: '3m', target: 1000 },  // Stay at spike
      { duration: '10s', target: 100 },  // Drop back
      { duration: '1m', target: 100 },   // Normal operation
      { duration: '10s', target: 0 }     // End
    ],
    tags: { test_type: 'spike' }
  },
  
  soak: {
    description: 'Extended duration testing (30 minutes)',
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 50 },   // Ramp up
      { duration: '26m', target: 50 },  // Stay at load for 26 minutes
      { duration: '2m', target: 0 }     // Ramp down
    ],
    tags: { test_type: 'soak' }
  },
  
  breakpoint: {
    description: 'Find system limits',
    executor: 'ramping-arrival-rate',
    startRate: 50,
    timeUnit: '1s',
    preAllocatedVUs: 50,
    maxVUs: 2000,
    stages: [
      { duration: '2m', target: 100 },  // Start at 100 RPS
      { duration: '5m', target: 200 },  // 200 RPS
      { duration: '5m', target: 300 },  // 300 RPS
      { duration: '5m', target: 400 },  // 400 RPS
      { duration: '5m', target: 500 },  // 500 RPS
      { duration: '5m', target: 600 },  // 600 RPS
      { duration: '5m', target: 700 },  // 700 RPS
      { duration: '5m', target: 800 },  // 800 RPS
    ],
    tags: { test_type: 'breakpoint' }
  }
};

// Performance thresholds
export const thresholds = {
  // HTTP request durations
  'http_req_duration': ['p(95)<2000', 'p(99)<5000'], // 95th percentile < 2s, 99th < 5s
  'http_req_duration{group:::api_health}': ['p(95)<500'], // Health checks should be fast
  'http_req_duration{group:::api_auth}': ['p(95)<1000'], // Auth should be fast
  'http_req_duration{group:::api_assessments}': ['p(95)<3000'], // Assessments can be slower
  'http_req_duration{group:::api_rag}': ['p(95)<5000'], // RAG operations can be slower
  
  // Success rates
  'http_req_failed': ['rate<0.05'], // Less than 5% failure rate
  'http_req_failed{group:::api_health}': ['rate<0.01'], // Health checks should almost never fail
  'http_req_failed{group:::api_auth}': ['rate<0.02'], // Auth failure tolerance
  
  // Request rates
  'http_reqs': ['rate>10'], // At least 10 requests per second
  
  // Check success rates
  'checks': ['rate>0.95'], // 95% of checks should pass
  'checks{group:::api_health}': ['rate>0.99'], // Health checks should almost always pass
  'checks{group:::authentication}': ['rate>0.95'], // Auth checks
  'checks{group:::business_logic}': ['rate>0.90'], // Business logic checks
};

// Custom options for different test types
export const options = {
  // Common options for all tests
  userAgent: 'k6-load-test/1.0.0 (AI-Cyber-Maturity-Assessment)',
  
  // HTTP configuration
  http: {
    responseType: 'text'
  },
  
  // TLS configuration
  tlsVersion: {
    min: 'tls1.2',
    max: 'tls1.3'
  },
  
  // DNS configuration
  dns: {
    ttl: '1m',
    select: 'roundRobin'
  },
  
  // Default thresholds (can be overridden per scenario)
  thresholds: thresholds,
  
  // Summary configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)', 'count'],
  summaryTimeUnit: 'ms',
  
  // Output configuration
  discardResponseBodies: false, // Keep for debugging
  
  // Console output
  quiet: false,
  verbose: false
};

// Test data configuration
export const testData = {
  // Demo users for authentication testing
  demoUsers: [
    { email: 'admin@example.com', role: 'admin' },
    { email: 'analyst@example.com', role: 'analyst' },
    { email: 'user@example.com', role: 'user' }
  ],
  
  // Sample engagement data
  engagements: {
    defaultName: 'Load Test Engagement',
    descriptions: [
      'Performance testing engagement for system validation',
      'Load testing scenario for capacity planning',
      'Stress testing engagement for resilience validation'
    ]
  },
  
  // Assessment presets
  presets: [
    'cyber-for-ai',
    'cscm-v3'
  ],
  
  // Sample document types for upload testing
  documentTypes: [
    { name: 'test-policy.txt', size: 1024, content: 'Sample policy document content for load testing.' },
    { name: 'test-procedure.txt', size: 2048, content: 'Sample procedure document with detailed steps for testing purposes.' },
    { name: 'test-assessment.txt', size: 512, content: 'Brief assessment document for load testing.' }
  ]
};

// Utility function to get test configuration
export const getTestConfig = (scenarioName = 'smoke') => {
  const env = getCurrentEnvironment();
  const scenario = scenarios[scenarioName];
  
  if (!scenario) {
    throw new Error(`Unknown scenario: ${scenarioName}. Valid options: ${Object.keys(scenarios).join(', ')}`);
  }
  
  return {
    environment: env,
    scenario: scenario,
    options: {
      ...options,
      scenarios: {
        [scenarioName]: scenario
      }
    }
  };
};

// Health check configuration
export const healthCheck = {
  endpoint: '/health',
  expectedStatus: 200,
  maxDuration: 500, // ms
  checks: [
    ['Health check status', (r) => r.status === 200],
    ['Health check response time', (r) => r.timings.duration < 500],
    ['Health check body contains status', (r) => r.body.includes('healthy')]
  ]
};

// Version check configuration
export const versionCheck = {
  endpoint: '/version',
  expectedStatus: 200,
  maxDuration: 1000, // ms
  checks: [
    ['Version endpoint status', (r) => r.status === 200],
    ['Version response time', (r) => r.timings.duration < 1000],
    ['Version body contains app_name', (r) => r.body.includes('app_name')],
    ['Version body is valid JSON', (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    }]
  ]
};

export default {
  environments,
  getCurrentEnvironment,
  scenarios,
  thresholds,
  options,
  testData,
  getTestConfig,
  healthCheck,
  versionCheck
};
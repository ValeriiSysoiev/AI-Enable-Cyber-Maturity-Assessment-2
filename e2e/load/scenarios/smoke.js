/**
 * Smoke Test Scenario
 * 
 * Basic functionality validation with minimal load.
 * Verifies that all critical endpoints are working correctly.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

import { getTestConfig, healthCheck, versionCheck } from '../k6.config.js';
import { createAuthSession, testAuthFlow } from '../utils/auth.js';
import { 
  generateEngagementData, 
  generateAssessmentData, 
  generateDocumentData,
  TestDataManager 
} from '../utils/test-data.js';

// Get test configuration
const config = getTestConfig('smoke');
export const options = config.options;

// Custom metrics
const apiErrors = new Rate('api_errors');
const authErrors = new Rate('auth_errors');
const businessLogicErrors = new Rate('business_logic_errors');
const responseTime = new Trend('custom_response_time');
const functionsExecuted = new Counter('functions_executed');

export function setup() {
  console.log('🚀 Starting Smoke Test Setup');
  console.log(`Environment: ${config.environment.baseUrl}`);
  console.log(`Auth Mode: ${config.environment.authMode}`);
  
  // Verify environment is accessible
  const healthResponse = http.get(`${config.environment.baseUrl}${healthCheck.endpoint}`);
  if (healthResponse.status !== healthCheck.expectedStatus) {
    throw new Error(`Environment health check failed: ${healthResponse.status}`);
  }
  
  console.log('✅ Environment health check passed');
  return { environment: config.environment };
}

export default function(data) {
  const { environment } = data;
  
  // Create authentication session
  const authSession = createAuthSession('smoke-test@example.com');
  const dataManager = new TestDataManager(authSession);
  
  let testsPassed = 0;
  let testsTotal = 0;
  
  try {
    // Test 1: Health and Version Endpoints
    group('System Health Checks', () => {
      testsTotal++;
      
      // Health check
      const healthResponse = http.get(`${environment.baseUrl}${healthCheck.endpoint}`, {
        tags: { group: 'api_health' }
      });
      
      const healthPassed = check(healthResponse, {
        'Health endpoint status 200': (r) => r.status === 200,
        'Health response time < 500ms': (r) => r.timings.duration < 500,
        'Health body contains status': (r) => r.body.includes('status')
      }, { group: 'api_health' });
      
      // Version check
      const versionResponse = http.get(`${environment.baseUrl}${versionCheck.endpoint}`, {
        tags: { group: 'api_health' }
      });
      
      const versionPassed = check(versionResponse, {
        'Version endpoint status 200': (r) => r.status === 200,
        'Version response time < 1000ms': (r) => r.timings.duration < 1000,
        'Version body contains app_name': (r) => r.body.includes('app_name'),
        'Version response is valid JSON': (r) => {
          try {
            JSON.parse(r.body);
            return true;
          } catch {
            return false;
          }
        }
      }, { group: 'api_health' });
      
      if (healthPassed && versionPassed) testsPassed++;
      functionsExecuted.add(1);
    });
    
    // Test 2: Authentication Flow
    group('Authentication', () => {
      testsTotal++;
      
      const authSuccess = authSession.login();
      const authPassed = check({ authSuccess }, {
        'Authentication successful': () => authSuccess
      }, { group: 'authentication' });
      
      if (!authSuccess) {
        authErrors.add(1);
        console.error('Authentication failed - skipping remaining tests');
        return;
      }
      
      if (authPassed) testsPassed++;
      functionsExecuted.add(1);
    });
    
    // Test 3: Presets API
    group('Presets Management', () => {
      testsTotal++;
      
      const presetsResponse = authSession.apiRequest('GET', '/presets', null, {
        'Content-Type': 'application/json'
      });
      
      const presetsPassed = check(presetsResponse, {
        'Presets list accessible': (r) => r.status === 200,
        'Presets response is JSON': (r) => {
          try {
            JSON.parse(r.body);
            return true;
          } catch {
            return false;
          }
        },
        'Presets list not empty': (r) => {
          try {
            const data = JSON.parse(r.body);
            return Array.isArray(data) && data.length > 0;
          } catch {
            return false;
          }
        }
      }, { group: 'api_presets' });
      
      if (presetsPassed) testsPassed++;
      functionsExecuted.add(1);
    });
    
    // Test 4: Engagement Creation and Management
    group('Engagement Management', () => {
      testsTotal++;
      
      const engagementData = generateEngagementData();
      
      // Create engagement
      const createResponse = authSession.apiRequest('POST', '/engagements', 
        JSON.stringify(engagementData), {
        'Content-Type': 'application/json'
      });
      
      let engagementId = null;
      const createPassed = check(createResponse, {
        'Engagement creation successful': (r) => r.status === 201 || r.status === 200,
        'Engagement response contains ID': (r) => {
          try {
            const data = JSON.parse(r.body);
            engagementId = data.id;
            return !!engagementId;
          } catch {
            return false;
          }
        }
      }, { group: 'api_engagements' });
      
      if (engagementId) {
        dataManager.trackEngagement(engagementId);
        
        // Retrieve engagement
        const getResponse = authSession.apiRequest('GET', `/engagements/${engagementId}`);
        
        const getPassed = check(getResponse, {
          'Engagement retrieval successful': (r) => r.status === 200,
          'Retrieved engagement has correct ID': (r) => {
            try {
              const data = JSON.parse(r.body);
              return data.id === engagementId;
            } catch {
              return false;
            }
          }
        }, { group: 'api_engagements' });
        
        if (createPassed && getPassed) testsPassed++;
      } else if (createPassed) {
        testsPassed++;
      }
      
      functionsExecuted.add(1);
    });
    
    // Test 5: Assessment Workflow
    group('Assessment Workflow', () => {
      testsTotal++;
      
      const assessmentData = generateAssessmentData();
      
      // Create assessment
      const createResponse = authSession.apiRequest('POST', '/assessments',
        JSON.stringify(assessmentData), {
        'Content-Type': 'application/json'
      });
      
      let assessmentId = null;
      const createPassed = check(createResponse, {
        'Assessment creation successful': (r) => r.status === 201 || r.status === 200,
        'Assessment response contains ID': (r) => {
          try {
            const data = JSON.parse(r.body);
            assessmentId = data.id;
            return !!assessmentId;
          } catch {
            return false;
          }
        }
      }, { group: 'api_assessments' });
      
      if (assessmentId) {
        dataManager.trackAssessment(assessmentId);
        
        // Get assessment scores (should work even with no answers)
        const scoresResponse = authSession.apiRequest('GET', `/assessments/${assessmentId}/scores`);
        
        const scoresPassed = check(scoresResponse, {
          'Assessment scores accessible': (r) => r.status === 200,
          'Scores response contains assessment_id': (r) => {
            try {
              const data = JSON.parse(r.body);
              return data.assessment_id === assessmentId;
            } catch {
              return false;
            }
          }
        }, { group: 'api_assessments' });
        
        if (createPassed && scoresPassed) testsPassed++;
      } else if (createPassed) {
        testsPassed++;
      }
      
      functionsExecuted.add(1);
    });
    
    // Test 6: Performance Metrics (if available)
    group('Performance Monitoring', () => {
      testsTotal++;
      
      const metricsResponse = authSession.apiRequest('GET', '/api/performance/metrics?time_window_minutes=5');
      
      const metricsPassed = check(metricsResponse, {
        'Performance metrics accessible': (r) => r.status === 200 || r.status === 404, // 404 is ok if not configured
        'Performance metrics response time acceptable': (r) => r.timings.duration < 2000
      }, { group: 'api_monitoring' });
      
      if (metricsPassed) testsPassed++;
      functionsExecuted.add(1);
    });
    
    // Test 7: RAG Status (if enabled)
    group('RAG Services', () => {
      testsTotal++;
      
      const ragStatusResponse = authSession.apiRequest('GET', '/rag/status');
      
      const ragPassed = check(ragStatusResponse, {
        'RAG status endpoint accessible': (r) => r.status === 200 || r.status === 404, // 404 ok if disabled
        'RAG status response time acceptable': (r) => r.timings.duration < 3000
      }, { group: 'api_rag' });
      
      if (ragPassed) testsPassed++;
      functionsExecuted.add(1);
    });
    
  } catch (error) {
    console.error(`Smoke test error: ${error.message}`);
    apiErrors.add(1);
  } finally {
    // Cleanup
    try {
      const cleanupResult = dataManager.cleanup();
      console.log(`Cleanup completed: ${JSON.stringify(cleanupResult.cleaned)}`);
      if (cleanupResult.errors.length > 0) {
        console.warn(`Cleanup errors: ${cleanupResult.errors.join(', ')}`);
      }
    } catch (error) {
      console.error(`Cleanup error: ${error.message}`);
    }
    
    // Logout
    try {
      authSession.logout();
    } catch (error) {
      console.error(`Logout error: ${error.message}`);
    }
  }
  
  // Report results
  const successRate = testsPassed / testsTotal;
  console.log(`Smoke test completed: ${testsPassed}/${testsTotal} tests passed (${(successRate * 100).toFixed(1)}%)`);
  
  if (successRate < 0.8) {
    console.error('Smoke test failed - success rate below 80%');
    businessLogicErrors.add(1);
  }
  
  // Brief pause between iterations
  sleep(1);
}

export function teardown(data) {
  console.log('🏁 Smoke Test Teardown');
  console.log('Smoke test scenario completed successfully');
}
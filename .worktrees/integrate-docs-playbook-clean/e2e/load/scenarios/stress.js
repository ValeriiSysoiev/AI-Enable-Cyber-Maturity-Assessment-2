/**
 * Stress Test Scenario
 * 
 * Peak load testing with 500 concurrent users.
 * Tests system behavior under high stress conditions.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

import { getTestConfig } from '../k6.config.js';
import { createAuthSession, getRandomTestUser } from '../utils/auth.js';
import { 
  generateEngagementData, 
  generateAssessmentData, 
  generateAnswerData,
  generateDocumentData,
  generateRAGQueries,
  TestDataManager,
  getRandomUserPattern,
  getThinkTime
} from '../utils/test-data.js';

// Get test configuration
const config = getTestConfig('stress');
export const options = config.options;

// Custom metrics for stress testing
const userSessions = new Counter('user_sessions');
const peakConcurrentUsers = new Gauge('peak_concurrent_users');
const systemErrors = new Rate('system_errors');
const timeoutErrors = new Rate('timeout_errors');
const resourceExhaustion = new Rate('resource_exhaustion');
const degradedPerformance = new Rate('degraded_performance');
const sessionFailures = new Rate('session_failures');
const criticalErrors = new Counter('critical_errors');
const stressResponseTime = new Trend('stress_response_time');
const errorRecoveryTime = new Trend('error_recovery_time');

// Stress test thresholds (more lenient than normal operation)
const stressThresholds = {
  'http_req_duration': ['p(95)<5000', 'p(99)<10000'], // Allow higher response times
  'http_req_failed': ['rate<0.15'], // Accept up to 15% failure rate
  'system_errors': ['rate<0.20'], // System errors should be under 20%
  'timeout_errors': ['rate<0.10'], // Timeouts under 10%
  'session_failures': ['rate<0.25'], // Session failures under 25%
};

// Override thresholds for stress test
options.thresholds = stressThresholds;

export function setup() {
  console.log('⚡ Starting Stress Test Setup');
  console.log(`Target: ${config.environment.baseUrl}`);
  console.log('Scenario: 500 concurrent users, peak load conditions');
  console.log('Expected: Some degradation and errors under extreme load');
  
  // Pre-stress health check
  const healthResponse = http.get(`${config.environment.baseUrl}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Environment not ready for stress testing: ${healthResponse.status}`);
  }
  
  console.log('✅ Environment ready for stress testing');
  console.log('⚠️  High load incoming - monitoring for degradation patterns...');
  
  return { 
    environment: config.environment,
    startTime: Date.now()
  };
}

export default function(data) {
  const { environment } = data;
  const sessionStart = Date.now();
  
  // Track peak concurrent users
  peakConcurrentUsers.add(1);
  
  // Aggressive user behavior under stress
  const userEmail = getRandomTestUser();
  const userPattern = {
    thinkTime: { min: 0.5, max: 2 }, // Reduced think time under stress
    errorTolerance: 0.3 // Higher error tolerance
  };
  
  let authSession = null;
  let dataManager = null;
  let sessionSuccess = true;
  
  try {
    userSessions.add(1);
    
    // Step 1: Aggressive Authentication
    group('Stress Authentication', () => {
      authSession = createAuthSession(userEmail);
      dataManager = new TestDataManager(authSession);
      
      const authStart = Date.now();
      const authSuccess = authSession.login();
      const authDuration = Date.now() - authStart;
      
      const authCheck = check({ authSuccess, authDuration }, {
        'Stress auth successful': ({ authSuccess }) => authSuccess,
        'Auth under stress time acceptable': ({ authDuration }) => authDuration < 10000 // 10s max
      }, { group: 'stress_auth' });
      
      if (!authSuccess) {
        sessionFailures.add(1);
        sessionSuccess = false;
        return;
      }
      
      if (authDuration > 5000) {
        degradedPerformance.add(1);
      }
      
      stressResponseTime.add(authDuration);
    });
    
    if (!sessionSuccess) return;
    
    // Step 2: Rapid System Probing
    group('Rapid System Access', () => {
      const operations = [
        () => authSession.apiRequest('GET', '/version'),
        () => authSession.apiRequest('GET', '/health'),
        () => authSession.apiRequest('GET', '/presets'),
        () => authSession.apiRequest('GET', '/engagements'),
        () => authSession.apiRequest('GET', '/api/performance/metrics?time_window_minutes=1')
      ];
      
      // Execute operations rapidly
      operations.forEach((operation, index) => {
        try {
          const response = operation();
          const isSuccess = response.status < 400;
          
          check(response, {
            [`Rapid operation ${index + 1} success`]: (r) => r.status < 400,
            [`Rapid operation ${index + 1} not timeout`]: (r) => r.status !== 408 && r.status !== 504
          }, { group: 'stress_rapid' });
          
          if (response.status >= 500) {
            systemErrors.add(1);
          }
          
          if (response.status === 408 || response.status === 504) {
            timeoutErrors.add(1);
          }
          
          stressResponseTime.add(response.timings.duration);
        } catch (error) {
          systemErrors.add(1);
          criticalErrors.add(1);
        }
        
        // Minimal pause between operations
        sleep(0.1);
      });
    });
    
    // Step 3: Concurrent Data Operations
    group('Concurrent Data Stress', () => {
      const concurrentOperations = [];
      
      // Create multiple engagements rapidly
      for (let i = 0; i < 3; i++) {
        const engagementData = generateEngagementData();
        try {
          const response = authSession.apiRequest('POST', '/engagements',
            JSON.stringify(engagementData), {
            'Content-Type': 'application/json'
          });
          
          const success = check(response, {
            [`Concurrent engagement ${i + 1} created`]: (r) => r.status < 400
          }, { group: 'stress_data' });
          
          if (success && response.body) {
            try {
              const data = JSON.parse(response.body);
              if (data.id) {
                dataManager.trackEngagement(data.id);
              }
            } catch {
              // Ignore parse errors under stress
            }
          }
          
          stressResponseTime.add(response.timings.duration);
        } catch (error) {
          systemErrors.add(1);
        }
        
        sleep(0.1);
      }
      
      // Create and populate assessment rapidly
      try {
        const assessmentData = generateAssessmentData();
        const assessmentResponse = authSession.apiRequest('POST', '/assessments',
          JSON.stringify(assessmentData), {
          'Content-Type': 'application/json'
        });
        
        if (assessmentResponse.status < 400) {
          let assessmentId = null;
          try {
            const data = JSON.parse(assessmentResponse.body);
            assessmentId = data.id;
            dataManager.trackAssessment(assessmentId);
          } catch {
            // Ignore parse errors
          }
          
          // Rapid-fire answers
          if (assessmentId) {
            for (let i = 0; i < 5; i++) {
              const answerData = generateAnswerData(`pillar_${i + 1}`, `question_${i + 1}`);
              try {
                const answerResponse = authSession.apiRequest('POST', 
                  `/assessments/${assessmentId}/answers`,
                  JSON.stringify(answerData), {
                  'Content-Type': 'application/json'
                });
                
                check(answerResponse, {
                  [`Rapid answer ${i + 1} submitted`]: (r) => r.status < 400
                }, { group: 'stress_data' });
                
                stressResponseTime.add(answerResponse.timings.duration);
              } catch (error) {
                systemErrors.add(1);
              }
              
              sleep(0.05); // Very brief pause
            }
            
            // Get scores under stress
            try {
              const scoresResponse = authSession.apiRequest('GET', 
                `/assessments/${assessmentId}/scores`);
              
              check(scoresResponse, {
                'Stress scores calculation': (r) => r.status < 400
              }, { group: 'stress_data' });
              
              stressResponseTime.add(scoresResponse.timings.duration);
            } catch (error) {
              systemErrors.add(1);
            }
          }
        }
      } catch (error) {
        systemErrors.add(1);
        criticalErrors.add(1);
      }
    });
    
    // Step 4: Resource Intensive Operations
    group('Resource Intensive Stress', () => {
      // Multiple document operations
      if (Math.random() < 0.5) {
        for (let i = 0; i < 2; i++) {
          const documentData = generateDocumentData();
          try {
            const uploadResponse = authSession.apiRequest('POST', '/documents',
              JSON.stringify(documentData), {
              'Content-Type': 'application/json'
            });
            
            const uploadSuccess = check(uploadResponse, {
              [`Stress document upload ${i + 1}`]: (r) => r.status < 400
            }, { group: 'stress_resources' });
            
            if (uploadResponse.status === 413 || uploadResponse.status === 507) {
              resourceExhaustion.add(1);
            }
            
            stressResponseTime.add(uploadResponse.timings.duration);
          } catch (error) {
            systemErrors.add(1);
          }
          
          sleep(0.1);
        }
      }
      
      // RAG operations under stress
      if (Math.random() < 0.3) {
        const queries = generateRAGQueries();
        const query = queries[Math.floor(Math.random() * queries.length)];
        
        try {
          const searchResponse = authSession.apiRequest('POST', '/rag/search', 
            JSON.stringify({
              query: query,
              engagement_id: 'stress-test-engagement',
              max_results: 10
            }), {
            'Content-Type': 'application/json'
          });
          
          check(searchResponse, {
            'Stress RAG search': (r) => r.status < 400 || r.status === 404,
            'RAG not timing out': (r) => r.status !== 408 && r.status !== 504
          }, { group: 'stress_resources' });
          
          if (searchResponse.timings.duration > 15000) {
            degradedPerformance.add(1);
          }
          
          stressResponseTime.add(searchResponse.timings.duration);
        } catch (error) {
          systemErrors.add(1);
        }
      }
    });
    
    // Step 5: Error Recovery Testing
    group('Error Recovery', () => {
      // Deliberately trigger some error conditions to test recovery
      const errorTests = [
        () => authSession.apiRequest('GET', '/nonexistent-endpoint'),
        () => authSession.apiRequest('POST', '/assessments', 'invalid-json'),
        () => authSession.apiRequest('GET', '/assessments/invalid-id'),
      ];
      
      errorTests.forEach((test, index) => {
        try {
          const recoveryStart = Date.now();
          const response = test();
          const recoveryTime = Date.now() - recoveryStart;
          
          check(response, {
            [`Error recovery ${index + 1} handled`]: (r) => r.status >= 400 && r.status < 500, // Expected error
            [`Error recovery ${index + 1} not crash`]: (r) => r.status !== 500 && r.status !== 502 && r.status !== 503
          }, { group: 'stress_recovery' });
          
          errorRecoveryTime.add(recoveryTime);
        } catch (error) {
          criticalErrors.add(1);
        }
        
        sleep(0.1);
      });
    });
    
    // Minimal think time under stress
    sleep(getThinkTime(userPattern) * 0.5);
    
  } catch (error) {
    console.error(`Critical stress test error for ${userEmail}: ${error.message}`);
    criticalErrors.add(1);
    sessionFailures.add(1);
  } finally {
    // Minimal cleanup under stress (avoid overwhelming system further)
    try {
      if (authSession && Math.random() < 0.05) { // Only 5% cleanup to reduce load
        const cleanupResult = dataManager.cleanup();
        if (cleanupResult.errors.length > 5) {
          console.warn(`High cleanup error rate for ${userEmail}: ${cleanupResult.errors.length}`);
        }
      }
    } catch (error) {
      // Ignore cleanup errors under stress
    }
    
    // Quick logout
    try {
      if (authSession) {
        authSession.logout();
      }
    } catch (error) {
      // Ignore logout errors under stress
    }
    
    // Decrement concurrent users
    peakConcurrentUsers.add(-1);
  }
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  
  console.log('⚡ Stress Test Teardown');
  console.log(`Stress test duration: ${duration}s`);
  console.log('System stress testing completed');
  console.log('Review metrics for performance degradation patterns and failure modes');
  
  // Brief cooldown period
  sleep(5);
}
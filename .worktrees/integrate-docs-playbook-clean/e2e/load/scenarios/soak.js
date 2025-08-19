/**
 * Soak Test Scenario
 * 
 * Extended duration testing (30 minutes) with sustained load.
 * Tests for memory leaks, resource degradation, and long-term stability.
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
const config = getTestConfig('soak');
export const options = config.options;

// Soak test specific metrics
const userSessions = new Counter('user_sessions');
const sessionDuration = new Trend('session_duration');
const memoryLeakIndicator = new Trend('memory_leak_indicator');
const performanceDegradation = new Rate('performance_degradation');
const stabilityErrors = new Rate('stability_errors');
const resourceExhaustion = new Rate('resource_exhaustion');
const longRunningOperations = new Counter('long_running_operations');
const cacheEfficiency = new Trend('cache_efficiency');
const connectionPoolHealth = new Rate('connection_pool_health');
const soakCycles = new Counter('soak_cycles');

// Performance baseline tracking
let baselineResponseTime = null;
let performanceHistory = [];

export function setup() {
  console.log('⏱️  Starting Soak Test Setup');
  console.log(`Target: ${config.environment.baseUrl}`);
  console.log('Scenario: 30-minute sustained load test');
  console.log('Testing: Memory leaks, resource degradation, long-term stability');
  
  // Establish performance baseline
  const baselineChecks = [];
  for (let i = 0; i < 5; i++) {
    const start = Date.now();
    const response = http.get(`${config.environment.baseUrl}/health`);
    const duration = Date.now() - start;
    
    if (response.status === 200) {
      baselineChecks.push(duration);
    }
    
    sleep(1);
  }
  
  if (baselineChecks.length > 0) {
    baselineResponseTime = baselineChecks.reduce((a, b) => a + b) / baselineChecks.length;
    console.log(`✅ Baseline response time: ${baselineResponseTime.toFixed(2)}ms`);
  }
  
  console.log('Starting extended load testing - monitoring for degradation...');
  return { 
    environment: config.environment,
    baseline: baselineResponseTime,
    startTime: Date.now()
  };
}

export default function(data) {
  const { environment, baseline } = data;
  const sessionStart = Date.now();
  const testRuntime = (sessionStart - data.startTime) / 1000 / 60; // minutes
  
  // Track soak test progress
  soakCycles.add(1);
  
  // Realistic user behavior with sustained activity
  const userEmail = getRandomTestUser();
  const userPattern = getRandomUserPattern();
  
  let authSession = null;
  let dataManager = null;
  
  try {
    userSessions.add(1);
    
    // Step 1: Sustainable Authentication
    group('Soak Authentication', () => {
      authSession = createAuthSession(userEmail);
      dataManager = new TestDataManager(authSession);
      
      const authStart = Date.now();
      const authSuccess = authSession.login();
      const authDuration = Date.now() - authStart;
      
      const authCheck = check({ authSuccess, authDuration }, {
        'Soak auth successful': ({ authSuccess }) => authSuccess,
        'Auth performance stable': ({ authDuration }) => {
          if (baseline) {
            return authDuration < (baseline * 3); // Allow 3x baseline during soak
          }
          return authDuration < 5000;
        }
      }, { group: 'soak_auth' });
      
      if (!authSuccess) {
        stabilityErrors.add(1);
        return;
      }
      
      // Track performance degradation over time
      if (baseline && authDuration > (baseline * 2)) {
        performanceDegradation.add(1);
      }
      
      performanceHistory.push(authDuration);
      if (performanceHistory.length > 100) {
        performanceHistory.shift(); // Keep last 100 measurements
      }
    });
    
    if (!authSession) return;
    
    // Step 2: Long-term System Health Monitoring
    group('System Health Over Time', () => {
      const healthStart = Date.now();
      const healthResponse = authSession.apiRequest('GET', '/health');
      const healthDuration = Date.now() - healthStart;
      
      const healthCheck = check(healthResponse, {
        'Health endpoint stable': (r) => r.status === 200,
        'Health response time stable': (r) => {
          if (baseline) {
            return r.timings.duration < (baseline * 2);
          }
          return r.timings.duration < 1000;
        }
      }, { group: 'soak_health' });
      
      // Memory leak detection (increasing response times over time)
      if (performanceHistory.length >= 10) {
        const recent = performanceHistory.slice(-5).reduce((a, b) => a + b) / 5;
        const older = performanceHistory.slice(-10, -5).reduce((a, b) => a + b) / 5;
        const degradationRatio = recent / older;
        
        memoryLeakIndicator.add(degradationRatio);
        
        if (degradationRatio > 1.5) {
          console.warn(`Potential memory leak detected - ${degradationRatio.toFixed(2)}x degradation`);
        }
      }
      
      // Check performance metrics for resource monitoring
      if (Math.random() < 0.1) { // 10% sample rate
        const metricsResponse = authSession.apiRequest('GET', 
          '/api/performance/metrics?time_window_minutes=5');
        
        if (metricsResponse.status === 200) {
          try {
            const metrics = JSON.parse(metricsResponse.body);
            const cacheHitRate = metrics.performance_statistics?.cache_hit_rate || 0;
            const memoryUsage = metrics.performance_statistics?.memory_usage_mb || 0;
            
            cacheEfficiency.add(cacheHitRate);
            
            // Detect resource exhaustion patterns
            if (memoryUsage > 1000) { // > 1GB memory usage
              resourceExhaustion.add(1);
            }
            
            if (cacheHitRate < 0.7) { // Cache efficiency below 70%
              console.warn(`Cache efficiency degraded: ${(cacheHitRate * 100).toFixed(1)}%`);
            }
            
          } catch (error) {
            // Ignore parse errors
          }
        }
      }
    });
    
    // Step 3: Sustained Business Operations
    group('Sustained Business Logic', () => {
      // Rotate between different operations to simulate real usage
      const operationCycle = Math.floor(testRuntime) % 4;
      
      switch (operationCycle) {
        case 0:
          // Engagement management cycle
          engagementOperations(authSession, dataManager, testRuntime);
          break;
        case 1:
          // Assessment workflow cycle
          assessmentOperations(authSession, dataManager, testRuntime);
          break;
        case 2:
          // Document management cycle
          documentOperations(authSession, dataManager, testRuntime);
          break;
        case 3:
          // Data analysis cycle
          analysisOperations(authSession, dataManager, testRuntime);
          break;
      }
    });
    
    // Step 4: Long-running Operations Test
    group('Long-running Operations', () => {
      if (Math.random() < 0.05) { // 5% chance for heavy operations
        longRunningOperations.add(1);
        
        // Simulate complex assessment with many answers
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
            
            // Submit many answers to create processing load
            if (assessmentId) {
              for (let i = 0; i < 15; i++) {
                const answerData = generateAnswerData(`pillar_${(i % 5) + 1}`, `question_${i + 1}`);
                
                const answerResponse = authSession.apiRequest('POST', 
                  `/assessments/${assessmentId}/answers`,
                  JSON.stringify(answerData), {
                  'Content-Type': 'application/json'
                });
                
                check(answerResponse, {
                  'Long-running answer processing': (r) => r.status < 400
                }, { group: 'soak_longrunning' });
                
                sleep(0.2); // Brief pause between answers
              }
              
              // Final score calculation
              const scoresResponse = authSession.apiRequest('GET', 
                `/assessments/${assessmentId}/scores`);
              
              check(scoresResponse, {
                'Long-running score calculation': (r) => r.status === 200,
                'Score calculation not timing out': (r) => r.timings.duration < 30000
              }, { group: 'soak_longrunning' });
            }
          }
          
        } catch (error) {
          stabilityErrors.add(1);
        }
      }
    });
    
    // Step 5: Connection Pool Health
    group('Connection Pool Health', () => {
      // Rapid sequential requests to test connection pooling
      const poolTestStart = Date.now();
      const rapidRequests = [];
      
      for (let i = 0; i < 5; i++) {
        try {
          const response = authSession.apiRequest('GET', '/version');
          rapidRequests.push(response.status === 200);
        } catch (error) {
          rapidRequests.push(false);
        }
        sleep(0.1);
      }
      
      const poolTestDuration = Date.now() - poolTestStart;
      const successRate = rapidRequests.filter(Boolean).length / rapidRequests.length;
      
      connectionPoolHealth.add(successRate);
      
      check({ successRate, poolTestDuration }, {
        'Connection pool healthy': ({ successRate }) => successRate >= 0.8,
        'Pool test reasonable time': ({ poolTestDuration }) => poolTestDuration < 3000
      }, { group: 'soak_connections' });
    });
    
    // Realistic think time for sustained operation
    const thinkTime = getThinkTime(userPattern);
    sleep(thinkTime);
    
  } catch (error) {
    console.error(`Soak test error for ${userEmail} at ${testRuntime.toFixed(1)}min: ${error.message}`);
    stabilityErrors.add(1);
  } finally {
    // Periodic cleanup to prevent resource accumulation
    if (Math.random() < 0.02) { // 2% cleanup rate to avoid overwhelming system
      try {
        const cleanupResult = dataManager.cleanup();
        if (cleanupResult.errors.length > 0) {
          console.warn(`Soak cleanup issues: ${cleanupResult.errors.length} items`);
        }
      } catch (error) {
        console.error(`Soak cleanup error: ${error.message}`);
      }
    }
    
    try {
      if (authSession) {
        authSession.logout();
      }
    } catch (error) {
      // Ignore logout errors
    }
    
    // Track session duration
    const sessionEnd = Date.now();
    const duration = (sessionEnd - sessionStart) / 1000;
    sessionDuration.add(duration);
  }
}

function engagementOperations(authSession, dataManager, testRuntime) {
  try {
    // List existing engagements
    const listResponse = authSession.apiRequest('GET', '/engagements');
    check(listResponse, {
      'Sustained engagement listing': (r) => r.status === 200
    }, { group: 'soak_engagements' });
    
    // Occasionally create new engagement
    if (Math.random() < 0.1) {
      const engagementData = generateEngagementData();
      const createResponse = authSession.apiRequest('POST', '/engagements',
        JSON.stringify(engagementData), {
        'Content-Type': 'application/json'
      });
      
      if (createResponse.status < 400) {
        try {
          const data = JSON.parse(createResponse.body);
          if (data.id) {
            dataManager.trackEngagement(data.id);
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
    
    sleep(1);
  } catch (error) {
    stabilityErrors.add(1);
  }
}

function assessmentOperations(authSession, dataManager, testRuntime) {
  try {
    const assessmentData = generateAssessmentData();
    const createResponse = authSession.apiRequest('POST', '/assessments',
      JSON.stringify(assessmentData), {
      'Content-Type': 'application/json'
    });
    
    check(createResponse, {
      'Sustained assessment creation': (r) => r.status < 400
    }, { group: 'soak_assessments' });
    
    if (createResponse.status < 400) {
      let assessmentId = null;
      try {
        const data = JSON.parse(createResponse.body);
        assessmentId = data.id;
        dataManager.trackAssessment(assessmentId);
      } catch {
        // Ignore parse errors
      }
      
      // Add some answers
      if (assessmentId) {
        for (let i = 0; i < 3; i++) {
          const answerData = generateAnswerData(`pillar_${i + 1}`, `question_${i + 1}`);
          authSession.apiRequest('POST', `/assessments/${assessmentId}/answers`,
            JSON.stringify(answerData), {
            'Content-Type': 'application/json'
          });
          sleep(0.5);
        }
      }
    }
    
    sleep(1);
  } catch (error) {
    stabilityErrors.add(1);
  }
}

function documentOperations(authSession, dataManager, testRuntime) {
  try {
    // List documents
    const listResponse = authSession.apiRequest('GET', '/documents');
    check(listResponse, {
      'Sustained document listing': (r) => r.status === 200
    }, { group: 'soak_documents' });
    
    // Occasionally upload document
    if (Math.random() < 0.2) {
      const documentData = generateDocumentData();
      const uploadResponse = authSession.apiRequest('POST', '/documents',
        JSON.stringify(documentData), {
        'Content-Type': 'application/json'
      });
      
      if (uploadResponse.status < 400) {
        try {
          const data = JSON.parse(uploadResponse.body);
          if (data.id) {
            dataManager.trackDocument(data.id);
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
    
    sleep(1);
  } catch (error) {
    stabilityErrors.add(1);
  }
}

function analysisOperations(authSession, dataManager, testRuntime) {
  try {
    // RAG operations
    if (Math.random() < 0.3) {
      const queries = generateRAGQueries();
      const query = queries[Math.floor(Math.random() * queries.length)];
      
      const searchResponse = authSession.apiRequest('POST', '/rag/search', 
        JSON.stringify({
          query: query,
          engagement_id: 'soak-test-engagement',
          max_results: 5
        }), {
        'Content-Type': 'application/json'
      });
      
      check(searchResponse, {
        'Sustained RAG operations': (r) => r.status < 500,
        'RAG not degrading': (r) => r.timings.duration < 15000
      }, { group: 'soak_analysis' });
    }
    
    sleep(1);
  } catch (error) {
    stabilityErrors.add(1);
  }
}

export function teardown(data) {
  const totalDuration = (Date.now() - data.startTime) / 1000 / 60; // minutes
  
  console.log('⏱️  Soak Test Teardown');
  console.log(`Total test duration: ${totalDuration.toFixed(2)} minutes`);
  
  if (performanceHistory.length > 0) {
    const avgPerformance = performanceHistory.reduce((a, b) => a + b) / performanceHistory.length;
    console.log(`Average response time: ${avgPerformance.toFixed(2)}ms`);
    
    if (data.baseline) {
      const degradation = avgPerformance / data.baseline;
      console.log(`Performance ratio: ${degradation.toFixed(2)}x baseline`);
      if (degradation > 1.5) {
        console.warn('⚠️  Significant performance degradation detected');
      }
    }
  }
  
  console.log('Soak test completed - review memory_leak_indicator and performance_degradation metrics');
}
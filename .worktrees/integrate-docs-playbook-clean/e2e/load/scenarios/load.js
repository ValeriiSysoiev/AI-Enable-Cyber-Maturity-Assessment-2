/**
 * Load Test Scenario
 * 
 * Normal operating load with 100 concurrent users.
 * Simulates realistic user behavior patterns and workflows.
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
const config = getTestConfig('load');
export const options = config.options;

// Custom metrics
const userSessions = new Counter('user_sessions');
const engagementsCreated = new Counter('engagements_created');
const assessmentsCompleted = new Counter('assessments_completed');
const documentsUploaded = new Counter('documents_uploaded');
const ragSearches = new Counter('rag_searches');
const businessErrors = new Rate('business_errors');
const userThinkTime = new Trend('user_think_time');
const sessionDuration = new Trend('session_duration');
const concurrentUsers = new Gauge('concurrent_users');

export function setup() {
  console.log('🔄 Starting Load Test Setup');
  console.log(`Target: ${config.environment.baseUrl}`);
  console.log(`Auth Mode: ${config.environment.authMode}`);
  console.log('Scenario: 100 concurrent users, realistic workflows');
  
  // Verify environment
  const healthResponse = http.get(`${config.environment.baseUrl}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Environment not ready: ${healthResponse.status}`);
  }
  
  console.log('✅ Environment ready for load testing');
  return { environment: config.environment };
}

export default function(data) {
  const { environment } = data;
  const sessionStart = Date.now();
  
  // Increment concurrent users counter
  concurrentUsers.add(1);
  
  // Select user behavior pattern
  const userPattern = getRandomUserPattern();
  const userEmail = getRandomTestUser();
  
  // Create authentication session
  const authSession = createAuthSession(userEmail);
  const dataManager = new TestDataManager(authSession);
  
  try {
    // User session workflow
    userSessions.add(1);
    
    // Step 1: Authentication
    group('User Authentication', () => {
      const authSuccess = authSession.login();
      
      check({ authSuccess }, {
        'User login successful': () => authSuccess
      }, { group: 'authentication' });
      
      if (!authSuccess) {
        businessErrors.add(1);
        return; // Exit if auth fails
      }
      
      // Simulate user reading/reviewing after login
      const thinkTime = getThinkTime(userPattern);
      userThinkTime.add(thinkTime);
      sleep(thinkTime);
    });
    
    // Step 2: Dashboard and System Overview
    group('Dashboard Navigation', () => {
      // Check system version and health
      const versionResponse = authSession.apiRequest('GET', '/version');
      check(versionResponse, {
        'Dashboard version check': (r) => r.status === 200
      }, { group: 'navigation' });
      
      // List existing engagements
      const engagementsResponse = authSession.apiRequest('GET', '/engagements');
      check(engagementsResponse, {
        'Engagements list loaded': (r) => r.status === 200
      }, { group: 'navigation' });
      
      // Check available presets
      const presetsResponse = authSession.apiRequest('GET', '/presets');
      check(presetsResponse, {
        'Presets loaded': (r) => r.status === 200
      }, { group: 'navigation' });
      
      sleep(getThinkTime(userPattern));
    });
    
    // Step 3: Engagement Management (60% of users)
    if (Math.random() < 0.6) {
      group('Engagement Management', () => {
        const engagementData = generateEngagementData();
        
        // Create new engagement
        const createResponse = authSession.apiRequest('POST', '/engagements',
          JSON.stringify(engagementData), {
          'Content-Type': 'application/json'
        });
        
        let engagementId = null;
        const createSuccess = check(createResponse, {
          'Engagement created': (r) => r.status === 201 || r.status === 200,
          'Engagement has ID': (r) => {
            try {
              const data = JSON.parse(r.body);
              engagementId = data.id;
              return !!engagementId;
            } catch {
              return false;
            }
          }
        }, { group: 'engagements' });
        
        if (createSuccess && engagementId) {
          engagementsCreated.add(1);
          dataManager.trackEngagement(engagementId);
          
          // Retrieve engagement details
          const getResponse = authSession.apiRequest('GET', `/engagements/${engagementId}`);
          check(getResponse, {
            'Engagement details retrieved': (r) => r.status === 200
          }, { group: 'engagements' });
          
          sleep(getThinkTime(userPattern));
        }
      });
    }
    
    // Step 4: Assessment Workflow (80% of users)
    if (Math.random() < 0.8) {
      group('Assessment Workflow', () => {
        const assessmentData = generateAssessmentData();
        
        // Create assessment
        const createResponse = authSession.apiRequest('POST', '/assessments',
          JSON.stringify(assessmentData), {
          'Content-Type': 'application/json'
        });
        
        let assessmentId = null;
        const createSuccess = check(createResponse, {
          'Assessment created': (r) => r.status === 201 || r.status === 200,
          'Assessment has ID': (r) => {
            try {
              const data = JSON.parse(r.body);
              assessmentId = data.id;
              return !!assessmentId;
            } catch {
              return false;
            }
          }
        }, { group: 'assessments' });
        
        if (createSuccess && assessmentId) {
          dataManager.trackAssessment(assessmentId);
          
          // Simulate answering questions (3-8 answers)
          const answersCount = Math.floor(Math.random() * 6) + 3;
          
          for (let i = 0; i < answersCount; i++) {
            const answerData = generateAnswerData(`pillar_${i % 5 + 1}`, `question_${i + 1}`);
            
            const answerResponse = authSession.apiRequest('POST', 
              `/assessments/${assessmentId}/answers`,
              JSON.stringify(answerData), {
              'Content-Type': 'application/json'
            });
            
            check(answerResponse, {
              'Answer submitted': (r) => r.status === 200
            }, { group: 'assessments' });
            
            // Think time between answers
            sleep(getThinkTime(userPattern) * 0.5);
          }
          
          // Get assessment scores
          const scoresResponse = authSession.apiRequest('GET', 
            `/assessments/${assessmentId}/scores`);
          
          const scoresSuccess = check(scoresResponse, {
            'Assessment scores calculated': (r) => r.status === 200,
            'Scores contain assessment ID': (r) => {
              try {
                const data = JSON.parse(r.body);
                return data.assessment_id === assessmentId;
              } catch {
                return false;
              }
            }
          }, { group: 'assessments' });
          
          if (scoresSuccess) {
            assessmentsCompleted.add(1);
          }
          
          sleep(getThinkTime(userPattern));
        }
      });
    }
    
    // Step 5: Document Management (40% of users)
    if (Math.random() < 0.4) {
      group('Document Management', () => {
        // List existing documents
        const listResponse = authSession.apiRequest('GET', '/documents');
        check(listResponse, {
          'Documents list loaded': (r) => r.status === 200
        }, { group: 'documents' });
        
        // Upload document (30% of users in this group)
        if (Math.random() < 0.3) {
          const documentData = generateDocumentData();
          
          // Create form data for file upload
          const formData = {
            name: documentData.name,
            content: documentData.content,
            description: documentData.description
          };
          
          const uploadResponse = authSession.apiRequest('POST', '/documents',
            JSON.stringify(formData), {
            'Content-Type': 'application/json'
          });
          
          const uploadSuccess = check(uploadResponse, {
            'Document uploaded': (r) => r.status === 201 || r.status === 200
          }, { group: 'documents' });
          
          if (uploadSuccess) {
            documentsUploaded.add(1);
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
        
        sleep(getThinkTime(userPattern));
      });
    }
    
    // Step 6: RAG Search (if enabled, 25% of users)
    if (Math.random() < 0.25) {
      group('RAG Search Operations', () => {
        // Check if RAG is available
        const ragStatusResponse = authSession.apiRequest('GET', '/rag/status');
        
        if (ragStatusResponse.status === 200) {
          const queries = generateRAGQueries();
          const query = queries[Math.floor(Math.random() * queries.length)];
          
          // Simulate search request
          const searchResponse = authSession.apiRequest('POST', '/rag/search', 
            JSON.stringify({
              query: query,
              engagement_id: 'demo-engagement',
              max_results: 5
            }), {
            'Content-Type': 'application/json'
          });
          
          const searchSuccess = check(searchResponse, {
            'RAG search executed': (r) => r.status === 200 || r.status === 404, // 404 if no documents
            'RAG search response time acceptable': (r) => r.timings.duration < 10000
          }, { group: 'rag' });
          
          if (searchSuccess) {
            ragSearches.add(1);
          }
        }
        
        sleep(getThinkTime(userPattern));
      });
    }
    
    // Step 7: Performance Monitoring (admin users, 10% chance)
    if (Math.random() < 0.1) {
      group('System Monitoring', () => {
        // Check performance metrics
        const metricsResponse = authSession.apiRequest('GET', 
          '/api/performance/metrics?time_window_minutes=5');
        
        check(metricsResponse, {
          'Performance metrics accessible': (r) => r.status === 200 || r.status === 403 || r.status === 404
        }, { group: 'monitoring' });
        
        // Check RAG metrics if available
        const ragMetricsResponse = authSession.apiRequest('GET', '/rag/metrics');
        check(ragMetricsResponse, {
          'RAG metrics accessible': (r) => r.status === 200 || r.status === 403 || r.status === 404
        }, { group: 'monitoring' });
        
        sleep(getThinkTime(userPattern) * 0.5);
      });
    }
    
    // Final think time before session end
    sleep(getThinkTime(userPattern));
    
  } catch (error) {
    console.error(`Load test error for user ${userEmail}: ${error.message}`);
    businessErrors.add(1);
  } finally {
    // Session cleanup
    try {
      // Only cleanup in a subset of cases to avoid overwhelming the system
      if (Math.random() < 0.1) { // 10% cleanup rate
        const cleanupResult = dataManager.cleanup();
        if (cleanupResult.errors.length > 0) {
          console.warn(`Cleanup errors for ${userEmail}: ${cleanupResult.errors.length} items`);
        }
      }
    } catch (error) {
      console.error(`Cleanup error for ${userEmail}: ${error.message}`);
    }
    
    // Logout
    try {
      authSession.logout();
    } catch (error) {
      console.error(`Logout error for ${userEmail}: ${error.message}`);
    }
    
    // Track session duration
    const sessionEnd = Date.now();
    const duration = (sessionEnd - sessionStart) / 1000; // seconds
    sessionDuration.add(duration);
    
    // Decrement concurrent users
    concurrentUsers.add(-1);
  }
}

export function teardown(data) {
  console.log('🏁 Load Test Teardown');
  console.log('Load test completed - analyzing results...');
  
  // Here you could add additional cleanup or result analysis
  // For example, querying performance metrics for final analysis
}
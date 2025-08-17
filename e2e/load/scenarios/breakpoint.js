/**
 * Breakpoint Test Scenario
 * 
 * Gradually increases load to find system breaking points.
 * Uses arrival rate scaling to identify maximum sustainable RPS.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

import { getTestConfig } from '../k6.config.js';
import { createAuthSession, getRandomTestUser } from '../utils/auth.js';
import { 
  generateEngagementData, 
  generateAssessmentData,
  TestDataManager
} from '../utils/test-data.js';

// Get test configuration
const config = getTestConfig('breakpoint');
export const options = config.options;

// Breakpoint-specific metrics
const currentRPS = new Gauge('current_rps');
const systemCapacity = new Gauge('system_capacity');
const breakpointReached = new Gauge('breakpoint_reached');
const saturationPoint = new Gauge('saturation_point');
const errorRateByRPS = new Trend('error_rate_by_rps');
const responseTimeByRPS = new Trend('response_time_by_rps');
const throughputEfficiency = new Trend('throughput_efficiency');
const resourceUtilization = new Trend('resource_utilization');
const queueLength = new Trend('queue_length');
const systemStability = new Rate('system_stability');

// Breaking point detection
let lastSuccessfulRPS = 0;
let errorRateThreshold = 0.05; // 5% error rate threshold
let responseTimeThreshold = 5000; // 5s response time threshold
let breakpointDetected = false;

export function setup() {
  console.log('🔍 Starting Breakpoint Test Setup');
  console.log(`Target: ${config.environment.baseUrl}`);
  console.log('Scenario: Gradually increasing load to find system limits');
  console.log('Monitoring: Error rates, response times, throughput efficiency');
  
  // Establish baseline capacity
  const baselineResponse = http.get(`${config.environment.baseUrl}/health`);
  if (baselineResponse.status !== 200) {
    throw new Error(`Environment not ready for breakpoint testing: ${baselineResponse.status}`);
  }
  
  console.log('✅ Environment ready for breakpoint testing');
  console.log('📈 Starting gradual load increase...');
  
  return { 
    environment: config.environment,
    startTime: Date.now(),
    stage: 0
  };
}

export default function(data) {
  const { environment } = data;
  
  // Estimate current stage based on time and k6 scenario configuration
  const elapsed = (Date.now() - data.startTime) / 1000 / 60; // minutes
  const currentStage = Math.floor(elapsed / 5); // 5-minute stages
  const estimatedRPS = 100 + (currentStage * 100); // Starting at 100 RPS, +100 each stage
  
  currentRPS.add(estimatedRPS);
  
  const userEmail = getRandomTestUser();
  let authSession = null;
  let dataManager = null;
  
  const operationStart = Date.now();
  let operationSuccess = true;
  
  try {
    // Step 1: Lightweight Authentication
    authSession = createAuthSession(userEmail);
    dataManager = new TestDataManager(authSession);
    
    const authSuccess = authSession.login();
    if (!authSuccess) {
      operationSuccess = false;
      return;
    }
    
    // Step 2: Core System Test
    group('Breakpoint Core Operations', () => {
      const coreOps = [
        {
          name: 'health_check',
          op: () => authSession.apiRequest('GET', '/health'),
          weight: 0.3
        },
        {
          name: 'version_check',
          op: () => authSession.apiRequest('GET', '/version'),
          weight: 0.2
        },
        {
          name: 'presets_list',
          op: () => authSession.apiRequest('GET', '/presets'),
          weight: 0.2
        },
        {
          name: 'engagements_list',
          op: () => authSession.apiRequest('GET', '/engagements'),
          weight: 0.3
        }
      ];
      
      // Execute core operations based on weights
      const selectedOp = selectWeightedOperation(coreOps);
      
      try {
        const response = selectedOp.op();
        const success = response.status < 400;
        
        operationSuccess = operationSuccess && success;
        
        // Record metrics by RPS level
        responseTimeByRPS.add(response.timings.duration);
        
        check(response, {
          [`${selectedOp.name} successful at ${estimatedRPS} RPS`]: (r) => r.status < 400,
          [`${selectedOp.name} reasonable response time`]: (r) => r.timings.duration < responseTimeThreshold,
          [`${selectedOp.name} not server error`]: (r) => r.status < 500
        }, { group: `breakpoint_core_${currentStage}` });
        
        // Detect queueing/throttling
        if (response.status === 429 || response.headers['X-RateLimit-Remaining']) {
          const remaining = response.headers['X-RateLimit-Remaining'] || '0';
          queueLength.add(parseInt(remaining));
        }
        
      } catch (error) {
        operationSuccess = false;
        console.error(`Core operation failed at ${estimatedRPS} RPS: ${error.message}`);
      }
    });
    
    // Step 3: Business Logic Under Load
    group('Breakpoint Business Operations', () => {
      // Only test business logic every few requests to focus on throughput
      if (Math.random() < 0.3) {
        const businessOps = [
          {
            name: 'create_engagement',
            op: () => {
              const engagementData = generateEngagementData();
              return authSession.apiRequest('POST', '/engagements',
                JSON.stringify(engagementData), {
                'Content-Type': 'application/json'
              });
            },
            weight: 0.4
          },
          {
            name: 'create_assessment',
            op: () => {
              const assessmentData = generateAssessmentData();
              return authSession.apiRequest('POST', '/assessments',
                JSON.stringify(assessmentData), {
                'Content-Type': 'application/json'
              });
            },
            weight: 0.6
          }
        ];
        
        const selectedOp = selectWeightedOperation(businessOps);
        
        try {
          const response = selectedOp.op();
          const success = response.status < 400;
          
          operationSuccess = operationSuccess && success;
          
          check(response, {
            [`${selectedOp.name} successful at ${estimatedRPS} RPS`]: (r) => r.status < 400,
            [`${selectedOp.name} not timing out`]: (r) => r.timings.duration < 15000
          }, { group: `breakpoint_business_${currentStage}` });
          
          // Track created resources for potential cleanup
          if (success && response.body) {
            try {
              const data = JSON.parse(response.body);
              if (data.id) {
                if (selectedOp.name === 'create_engagement') {
                  dataManager.trackEngagement(data.id);
                } else if (selectedOp.name === 'create_assessment') {
                  dataManager.trackAssessment(data.id);
                }
              }
            } catch {
              // Ignore parse errors during breakpoint testing
            }
          }
          
        } catch (error) {
          operationSuccess = false;
          console.error(`Business operation failed at ${estimatedRPS} RPS: ${error.message}`);
        }
      }
    });
    
    // Step 4: System Health Monitoring
    group('Breakpoint Health Monitoring', () => {
      // Sample system metrics periodically
      if (Math.random() < 0.05) { // 5% sampling rate
        try {
          const metricsResponse = authSession.apiRequest('GET', 
            '/api/performance/metrics?time_window_minutes=1');
          
          if (metricsResponse.status === 200) {
            try {
              const metrics = JSON.parse(metricsResponse.body);
              const stats = metrics.performance_statistics || {};
              
              // Track resource utilization
              const memoryUsage = stats.memory_usage_mb || 0;
              const cpuUsage = stats.cpu_usage_percent || 0;
              const avgResponseTime = stats.avg_response_time_ms || 0;
              const errorRate = 1 - (stats.cache_hit_rate || 0.9); // Simplified error rate estimate
              
              resourceUtilization.add(Math.max(memoryUsage / 1000, cpuUsage / 100)); // Normalized
              errorRateByRPS.add(errorRate);
              
              // Calculate throughput efficiency
              const theoreticalMax = estimatedRPS * 1000; // 1000ms baseline
              const actualThroughput = theoreticalMax / Math.max(avgResponseTime, 1);
              const efficiency = actualThroughput / theoreticalMax;
              
              throughputEfficiency.add(efficiency);
              
              // Detect breakpoint conditions
              if (errorRate > errorRateThreshold || avgResponseTime > responseTimeThreshold) {
                if (!breakpointDetected) {
                  breakpointDetected = true;
                  breakpointReached.add(estimatedRPS);
                  console.warn(`⚠️  Breakpoint detected at ${estimatedRPS} RPS - Error rate: ${(errorRate * 100).toFixed(2)}%, Avg response: ${avgResponseTime.toFixed(0)}ms`);
                }
              } else {
                lastSuccessfulRPS = estimatedRPS;
                systemCapacity.add(lastSuccessfulRPS);
              }
              
            } catch (error) {
              console.error(`Metrics parsing error: ${error.message}`);
            }
          }
          
        } catch (error) {
          console.error(`Health monitoring error: ${error.message}`);
        }
      }
    });
    
  } catch (error) {
    operationSuccess = false;
    console.error(`Breakpoint test error at ${estimatedRPS} RPS: ${error.message}`);
  } finally {
    // No cleanup during breakpoint testing to maintain load
    // Quick logout only
    try {
      if (authSession) {
        authSession.logout();
      }
    } catch (error) {
      // Ignore logout errors during breakpoint testing
    }
    
    // Record operation success for stability tracking
    systemStability.add(operationSuccess ? 0 : 1);
    
    // Track operation duration
    const operationDuration = Date.now() - operationStart;
    if (operationDuration > 10000) { // Operations taking > 10s
      console.warn(`Slow operation detected: ${operationDuration}ms at ${estimatedRPS} RPS`);
    }
  }
  
  // No think time - maximize throughput for breakpoint testing
}

function selectWeightedOperation(operations) {
  const random = Math.random();
  let cumulativeWeight = 0;
  
  for (const op of operations) {
    cumulativeWeight += op.weight;
    if (random <= cumulativeWeight) {
      return op;
    }
  }
  
  // Fallback to first operation
  return operations[0];
}

export function teardown(data) {
  const testDuration = (Date.now() - data.startTime) / 1000 / 60; // minutes
  
  console.log('🔍 Breakpoint Test Teardown');
  console.log(`Test duration: ${testDuration.toFixed(2)} minutes`);
  
  if (lastSuccessfulRPS > 0) {
    console.log(`✅ Maximum sustainable capacity: ${lastSuccessfulRPS} RPS`);
    saturationPoint.add(lastSuccessfulRPS);
  }
  
  if (breakpointDetected) {
    console.log(`⚠️  System breakpoint detected - review error rates and response times`);
  } else {
    console.log(`ℹ️  No clear breakpoint found - system may handle higher loads`);
  }
  
  console.log('Key metrics to review:');
  console.log('- system_capacity: Maximum sustainable RPS');
  console.log('- breakpoint_reached: RPS at which system degraded');
  console.log('- throughput_efficiency: Efficiency vs theoretical maximum');
  console.log('- resource_utilization: CPU/Memory usage patterns');
}
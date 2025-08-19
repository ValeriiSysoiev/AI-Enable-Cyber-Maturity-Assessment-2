/**
 * Spike Test Scenario
 * 
 * Tests system behavior during sudden traffic spikes.
 * Simulates viral load patterns and sudden user influxes.
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

import { getTestConfig } from '../k6.config.js';
import { createAuthSession, getRandomTestUser } from '../utils/auth.js';
import { 
  generateEngagementData, 
  generateAssessmentData,
  TestDataManager,
  getRandomUserPattern,
  getThinkTime
} from '../utils/test-data.js';

// Get test configuration
const config = getTestConfig('spike');
export const options = config.options;

// Spike-specific metrics
const userSessions = new Counter('user_sessions');
const spikePhase = new Gauge('spike_phase'); // 0=normal, 1=spike, 2=recovery
const spikeRecoveryTime = new Trend('spike_recovery_time');
const spikeErrors = new Rate('spike_errors');
const spikeTimeouts = new Rate('spike_timeouts');
const circuitBreakerTriggered = new Rate('circuit_breaker_triggered');
const queueingTime = new Trend('queueing_time');
const autoscalingResponse = new Trend('autoscaling_response');
const emergencyFailures = new Counter('emergency_failures');

// Phase tracking for analysis
let currentPhase = 'normal';
let spikeStartTime = null;
let normalRecoveryTime = null;

export function setup() {
  console.log('📈 Starting Spike Test Setup');
  console.log(`Target: ${config.environment.baseUrl}`);
  console.log('Scenario: Sudden traffic spikes from 100 to 1000 users');
  console.log('Testing: Auto-scaling, circuit breakers, graceful degradation');
  
  // Baseline health check
  const healthResponse = http.get(`${config.environment.baseUrl}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Environment not ready for spike testing: ${healthResponse.status}`);
  }
  
  console.log('✅ Environment ready for spike testing');
  return { 
    environment: config.environment,
    testStart: Date.now()
  };
}

export default function(data) {
  const { environment } = data;
  const sessionStart = Date.now();
  
  // Determine current phase based on __VU and __ITER
  const currentVUs = __ENV.K6_VUS || 100;
  const currentTime = Date.now();
  
  // Phase detection logic
  if (currentVUs > 800) {
    if (currentPhase !== 'spike') {
      currentPhase = 'spike';
      spikeStartTime = currentTime;
      spikePhase.add(1);
      console.log('🔥 SPIKE PHASE DETECTED - High load incoming!');
    }
  } else if (currentVUs < 200 && currentPhase === 'spike') {
    currentPhase = 'recovery';
    normalRecoveryTime = currentTime;
    spikePhase.add(2);
    console.log('📉 Recovery phase - monitoring system stabilization');
  } else if (currentVUs < 200) {
    currentPhase = 'normal';
    spikePhase.add(0);
  }
  
  const userEmail = getRandomTestUser();
  let authSession = null;
  let dataManager = null;
  
  try {
    userSessions.add(1);
    
    // Step 1: Authentication under spike conditions
    group('Spike Authentication', () => {
      const authStart = Date.now();
      authSession = createAuthSession(userEmail);
      dataManager = new TestDataManager(authSession);
      
      const authSuccess = authSession.login();
      const authDuration = Date.now() - authStart;
      
      // Different thresholds based on phase
      let maxAuthTime = 2000; // Normal
      if (currentPhase === 'spike') {
        maxAuthTime = 8000; // Allow longer during spike
      } else if (currentPhase === 'recovery') {
        maxAuthTime = 4000; // Moderate during recovery
      }
      
      const authCheck = check({ authSuccess, authDuration, currentPhase }, {
        'Spike auth successful': ({ authSuccess }) => authSuccess,
        'Auth time within spike threshold': ({ authDuration }) => authDuration < maxAuthTime,
        'Auth not timing out': ({ authDuration }) => authDuration < 15000
      }, { group: `spike_auth_${currentPhase}` });
      
      if (!authSuccess) {
        spikeErrors.add(1);
        if (currentPhase === 'spike') {
          emergencyFailures.add(1);
        }
        return;
      }
      
      if (authDuration > 10000) {
        spikeTimeouts.add(1);
      }
      
      // Detect if we're being queued/throttled
      if (authDuration > 5000 && currentPhase === 'spike') {
        queueingTime.add(authDuration);
      }
    });
    
    if (!authSession) return;
    
    // Step 2: Critical Path Operations
    group('Critical Path Under Spike', () => {
      const criticalOps = [
        {
          name: 'health_check',
          operation: () => authSession.apiRequest('GET', '/health'),
          critical: true
        },
        {
          name: 'version_info',
          operation: () => authSession.apiRequest('GET', '/version'),
          critical: true
        },
        {
          name: 'presets_list',
          operation: () => authSession.apiRequest('GET', '/presets'),
          critical: false
        }
      ];
      
      criticalOps.forEach(op => {
        try {
          const opStart = Date.now();
          const response = op.operation();
          const opDuration = Date.now() - opStart;
          
          // Circuit breaker detection
          if (response.status === 503 || response.status === 429) {
            circuitBreakerTriggered.add(1);
            console.log(`Circuit breaker triggered for ${op.name}`);
          }
          
          const success = check(response, {
            [`${op.name} responds`]: (r) => r.status < 500,
            [`${op.name} not rate limited`]: (r) => r.status !== 429,
            [`${op.name} reasonable time`]: (r) => {
              const threshold = currentPhase === 'spike' ? 10000 : 3000;
              return r.timings.duration < threshold;
            }
          }, { group: `spike_critical_${currentPhase}` });
          
          if (!success && op.critical) {
            emergencyFailures.add(1);
          }
          
          if (response.status >= 500) {
            spikeErrors.add(1);
          }
          
        } catch (error) {
          spikeErrors.add(1);
          if (op.critical) {
            emergencyFailures.add(1);
          }
        }
        
        // Reduced think time during spike
        const thinkTime = currentPhase === 'spike' ? 0.1 : 0.5;
        sleep(thinkTime);
      });
    });
    
    // Step 3: Load-adapted Behavior
    group('Spike-Adapted Operations', () => {
      if (currentPhase === 'normal') {
        // Normal behavior - full feature usage
        normalBehavior(authSession, dataManager);
      } else if (currentPhase === 'spike') {
        // Spike behavior - essential operations only
        spikeBehavior(authSession, dataManager);
      } else if (currentPhase === 'recovery') {
        // Recovery behavior - gradual feature re-introduction
        recoveryBehavior(authSession, dataManager);
      }
    });
    
    // Step 4: System Health Monitoring
    group('Spike Health Monitoring', () => {
      if (Math.random() < 0.1) { // 10% of users check health
        try {
          const metricsResponse = authSession.apiRequest('GET', 
            '/api/performance/metrics?time_window_minutes=1');
          
          check(metricsResponse, {
            'Performance metrics available during spike': (r) => r.status < 500,
            'Metrics response reasonable': (r) => r.timings.duration < 5000
          }, { group: `spike_monitoring_${currentPhase}` });
          
          // Try to detect auto-scaling response
          if (metricsResponse.status === 200) {
            try {
              const data = JSON.parse(metricsResponse.body);
              const avgResponseTime = data.performance_statistics?.avg_response_time_ms || 0;
              
              if (avgResponseTime > 0) {
                autoscalingResponse.add(avgResponseTime);
              }
            } catch {
              // Ignore parse errors during spike
            }
          }
          
        } catch (error) {
          spikeErrors.add(1);
        }
      }
    });
    
  } catch (error) {
    console.error(`Spike test error for ${userEmail}: ${error.message}`);
    spikeErrors.add(1);
    emergencyFailures.add(1);
  } finally {
    // No cleanup during spike to avoid adding load
    if (currentPhase !== 'spike' && Math.random() < 0.05) {
      try {
        dataManager.cleanup();
      } catch (error) {
        // Ignore cleanup errors
      }
    }
    
    try {
      if (authSession) {
        authSession.logout();
      }
    } catch (error) {
      // Ignore logout errors during spike
    }
  }
}

function normalBehavior(authSession, dataManager) {
  // Full feature usage during normal load
  const engagementData = generateEngagementData();
  
  try {
    const createResponse = authSession.apiRequest('POST', '/engagements',
      JSON.stringify(engagementData), {
      'Content-Type': 'application/json'
    });
    
    check(createResponse, {
      'Normal engagement creation': (r) => r.status < 400
    }, { group: 'spike_normal' });
    
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
    
  } catch (error) {
    spikeErrors.add(1);
  }
  
  sleep(1);
}

function spikeBehavior(authSession, dataManager) {
  // Essential operations only during spike
  try {
    // Only check existing data, don't create new
    const engagementsResponse = authSession.apiRequest('GET', '/engagements');
    
    check(engagementsResponse, {
      'Spike engagement list': (r) => r.status < 500, // Allow some degradation
      'Spike not completely broken': (r) => r.status !== 503
    }, { group: 'spike_essential' });
    
  } catch (error) {
    spikeErrors.add(1);
  }
  
  // Minimal think time during spike
  sleep(0.1);
}

function recoveryBehavior(authSession, dataManager) {
  // Gradual feature re-introduction during recovery
  try {
    // Test both read and light write operations
    const presetsResponse = authSession.apiRequest('GET', '/presets');
    
    check(presetsResponse, {
      'Recovery presets access': (r) => r.status === 200,
      'Recovery performance improving': (r) => r.timings.duration < 3000
    }, { group: 'spike_recovery' });
    
    // Light assessment creation to test recovery
    if (Math.random() < 0.3) {
      const assessmentData = generateAssessmentData();
      const assessmentResponse = authSession.apiRequest('POST', '/assessments',
        JSON.stringify(assessmentData), {
        'Content-Type': 'application/json'
      });
      
      check(assessmentResponse, {
        'Recovery assessment creation': (r) => r.status < 400
      }, { group: 'spike_recovery' });
      
      if (assessmentResponse.status < 400) {
        try {
          const data = JSON.parse(assessmentResponse.body);
          if (data.id) {
            dataManager.trackAssessment(data.id);
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
    
  } catch (error) {
    spikeErrors.add(1);
  }
  
  sleep(0.5);
}

export function teardown(data) {
  const testDuration = (Date.now() - data.testStart) / 1000;
  
  console.log('📈 Spike Test Teardown');
  console.log(`Test duration: ${testDuration}s`);
  
  if (spikeStartTime && normalRecoveryTime) {
    const recoveryTime = (normalRecoveryTime - spikeStartTime) / 1000;
    console.log(`Spike duration: ${recoveryTime}s`);
    spikeRecoveryTime.add(recoveryTime);
  }
  
  console.log('Spike test completed - analyze auto-scaling and recovery patterns');
  console.log('Key metrics: circuit_breaker_triggered, spike_recovery_time, emergency_failures');
}
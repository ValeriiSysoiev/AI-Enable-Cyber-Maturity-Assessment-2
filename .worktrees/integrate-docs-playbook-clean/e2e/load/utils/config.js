/**
 * Configuration management utilities for k6 load testing
 * 
 * Handles environment-specific configuration, secrets management,
 * and runtime parameter overrides.
 */

import { getCurrentEnvironment } from '../k6.config.js';

/**
 * Configuration loader with environment variable support
 */
export class ConfigLoader {
  constructor() {
    this.config = {};
    this.environment = getCurrentEnvironment();
    this.loadConfiguration();
  }
  
  /**
   * Load configuration from environment variables and defaults
   */
  loadConfiguration() {
    // Base configuration
    this.config = {
      // Environment settings
      environment: {
        name: process.env.TARGET_ENV || 'local',
        baseUrl: this.environment.baseUrl,
        webUrl: this.environment.webUrl,
        authMode: this.environment.authMode
      },
      
      // Test execution settings
      execution: {
        durationOverride: process.env.DURATION_OVERRIDE || null,
        maxVUs: parseInt(process.env.MAX_VUS) || 2000,
        rampUpTime: process.env.RAMP_UP_TIME || '2m',
        steadyStateTime: process.env.STEADY_STATE_TIME || '5m',
        rampDownTime: process.env.RAMP_DOWN_TIME || '2m'
      },
      
      // Performance thresholds
      thresholds: {
        responseTime: {
          p95: parseInt(process.env.P95_THRESHOLD_MS) || 2000,
          p99: parseInt(process.env.P99_THRESHOLD_MS) || 5000,
          max: parseInt(process.env.MAX_RESPONSE_TIME_MS) || 10000
        },
        errorRate: {
          max: parseFloat(process.env.MAX_ERROR_RATE) || 0.05,
          critical: parseFloat(process.env.CRITICAL_ERROR_RATE) || 0.15
        },
        throughput: {
          min: parseInt(process.env.MIN_RPS) || 10
        }
      },
      
      // Test data settings
      testData: {
        cleanupRate: parseFloat(process.env.CLEANUP_RATE) || 0.1,
        dataRetentionHours: parseInt(process.env.DATA_RETENTION_HOURS) || 24,
        maxTestEntities: parseInt(process.env.MAX_TEST_ENTITIES) || 1000
      },
      
      // Authentication settings
      auth: {
        sessionTimeout: parseInt(process.env.AUTH_SESSION_TIMEOUT) || 3600,
        retryAttempts: parseInt(process.env.AUTH_RETRY_ATTEMPTS) || 3,
        timeoutMs: parseInt(process.env.AUTH_TIMEOUT_MS) || 10000
      },
      
      // Monitoring and reporting
      monitoring: {
        enableDetailedMetrics: process.env.ENABLE_DETAILED_METRICS === 'true',
        metricsInterval: parseInt(process.env.METRICS_INTERVAL_SEC) || 30,
        enableSlackNotifications: process.env.ENABLE_SLACK_NOTIFICATIONS !== 'false',
        slackWebhookUrl: process.env.SLACK_WEBHOOK_URL || null
      },
      
      // Feature flags
      features: {
        enableRAGTesting: process.env.ENABLE_RAG_TESTING !== 'false',
        enableDocumentUpload: process.env.ENABLE_DOCUMENT_UPLOAD !== 'false',
        enableGDPRTesting: process.env.ENABLE_GDPR_TESTING === 'true',
        enableAdminTesting: process.env.ENABLE_ADMIN_TESTING === 'true'
      },
      
      // Resource limits
      resources: {
        maxConcurrentSessions: parseInt(process.env.MAX_CONCURRENT_SESSIONS) || 500,
        maxMemoryUsageMB: parseInt(process.env.MAX_MEMORY_MB) || 2048,
        maxCPUPercent: parseInt(process.env.MAX_CPU_PERCENT) || 80
      }
    };
    
    // Validate configuration
    this.validateConfiguration();
  }
  
  /**
   * Validate configuration values
   */
  validateConfiguration() {
    const errors = [];
    
    // Required URLs
    if (!this.config.environment.baseUrl) {
      errors.push('Base URL is required');
    }
    
    // Valid thresholds
    if (this.config.thresholds.responseTime.p95 <= 0) {
      errors.push('P95 threshold must be positive');
    }
    
    if (this.config.thresholds.errorRate.max < 0 || this.config.thresholds.errorRate.max > 1) {
      errors.push('Error rate threshold must be between 0 and 1');
    }
    
    // Resource limits
    if (this.config.resources.maxConcurrentSessions <= 0) {
      errors.push('Max concurrent sessions must be positive');
    }
    
    if (errors.length > 0) {
      throw new Error(`Configuration validation failed: ${errors.join(', ')}`);
    }
  }
  
  /**
   * Get configuration value with path notation
   */
  get(path, defaultValue = null) {
    const keys = path.split('.');
    let value = this.config;
    
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return defaultValue;
      }
    }
    
    return value;
  }
  
  /**
   * Check if feature is enabled
   */
  isFeatureEnabled(featureName) {
    return this.get(`features.${featureName}`, false);
  }
  
  /**
   * Get environment-specific configuration
   */
  getEnvironmentConfig() {
    return this.config.environment;
  }
  
  /**
   * Get performance thresholds
   */
  getThresholds() {
    return this.config.thresholds;
  }
  
  /**
   * Get test execution parameters
   */
  getExecutionConfig() {
    return this.config.execution;
  }
  
  /**
   * Override configuration at runtime
   */
  override(path, value) {
    const keys = path.split('.');
    let current = this.config;
    
    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current)) {
        current[key] = {};
      }
      current = current[key];
    }
    
    current[keys[keys.length - 1]] = value;
  }
  
  /**
   * Export configuration for logging
   */
  toJSON() {
    // Remove sensitive information
    const safeCopy = JSON.parse(JSON.stringify(this.config));
    
    if (safeCopy.monitoring && safeCopy.monitoring.slackWebhookUrl) {
      safeCopy.monitoring.slackWebhookUrl = '[REDACTED]';
    }
    
    return safeCopy;
  }
}

/**
 * Environment-specific configuration overrides
 */
export const environmentOverrides = {
  local: {
    'thresholds.responseTime.p95': 1000,
    'thresholds.errorRate.max': 0.10,
    'testData.cleanupRate': 0.5,
    'features.enableGDPRTesting': false
  },
  
  dev: {
    'thresholds.responseTime.p95': 2000,
    'thresholds.errorRate.max': 0.08,
    'testData.cleanupRate': 0.2,
    'features.enableGDPRTesting': true
  },
  
  staging: {
    'thresholds.responseTime.p95': 1500,
    'thresholds.errorRate.max': 0.05,
    'testData.cleanupRate': 0.1,
    'features.enableGDPRTesting': true,
    'features.enableAdminTesting': true
  },
  
  prod: {
    'thresholds.responseTime.p95': 1000,
    'thresholds.errorRate.max': 0.02,
    'testData.cleanupRate': 0.05,
    'features.enableGDPRTesting': false,
    'features.enableDocumentUpload': false
  }
};

/**
 * Scenario-specific configuration overrides
 */
export const scenarioOverrides = {
  smoke: {
    'execution.maxVUs': 5,
    'thresholds.responseTime.p95': 1000,
    'testData.cleanupRate': 1.0
  },
  
  load: {
    'execution.maxVUs': 200,
    'thresholds.responseTime.p95': 2000,
    'testData.cleanupRate': 0.1
  },
  
  stress: {
    'execution.maxVUs': 1000,
    'thresholds.responseTime.p95': 5000,
    'thresholds.errorRate.max': 0.15,
    'testData.cleanupRate': 0.05
  },
  
  spike: {
    'execution.maxVUs': 1500,
    'thresholds.responseTime.p95': 8000,
    'thresholds.errorRate.max': 0.20,
    'testData.cleanupRate': 0.02
  },
  
  soak: {
    'execution.maxVUs': 100,
    'thresholds.responseTime.p95': 3000,
    'testData.cleanupRate': 0.02,
    'testData.dataRetentionHours': 1
  },
  
  breakpoint: {
    'execution.maxVUs': 2000,
    'thresholds.responseTime.p95': 10000,
    'thresholds.errorRate.max': 0.30,
    'testData.cleanupRate': 0.01
  }
};

/**
 * Create configured instance
 */
export function createConfig(scenario = 'smoke') {
  const config = new ConfigLoader();
  
  // Apply environment overrides
  const envName = config.get('environment.name');
  if (environmentOverrides[envName]) {
    Object.entries(environmentOverrides[envName]).forEach(([path, value]) => {
      config.override(path, value);
    });
  }
  
  // Apply scenario overrides
  if (scenarioOverrides[scenario]) {
    Object.entries(scenarioOverrides[scenario]).forEach(([path, value]) => {
      config.override(path, value);
    });
  }
  
  return config;
}

/**
 * Configuration validation utilities
 */
export const validators = {
  /**
   * Validate URL format
   */
  isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },
  
  /**
   * Validate percentage value
   */
  isValidPercentage(value) {
    return typeof value === 'number' && value >= 0 && value <= 1;
  },
  
  /**
   * Validate duration string
   */
  isValidDuration(duration) {
    if (typeof duration !== 'string') return false;
    return /^\d+[smh]$/.test(duration);
  },
  
  /**
   * Validate positive integer
   */
  isPositiveInteger(value) {
    return Number.isInteger(value) && value > 0;
  }
};

/**
 * Configuration presets for common scenarios
 */
export const configPresets = {
  // Quick validation test
  quickTest: {
    'execution.durationOverride': '30s',
    'execution.maxVUs': 5,
    'testData.cleanupRate': 1.0
  },
  
  // Performance regression test
  regressionTest: {
    'execution.durationOverride': '5m',
    'execution.maxVUs': 50,
    'thresholds.responseTime.p95': 1500,
    'monitoring.enableDetailedMetrics': true
  },
  
  // Capacity planning test
  capacityTest: {
    'execution.durationOverride': '15m',
    'execution.maxVUs': 300,
    'monitoring.enableDetailedMetrics': true,
    'testData.cleanupRate': 0.05
  }
};

export default {
  ConfigLoader,
  createConfig,
  environmentOverrides,
  scenarioOverrides,
  validators,
  configPresets
};
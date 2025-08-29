/**
 * Session Configuration Module
 * 
 * Centralized session management configuration following security best practices
 */

// Session timeout configurations (in seconds)
export const SESSION_CONFIG = {
  // Maximum session age - how long until forced re-authentication
  MAX_AGE: {
    PRODUCTION: 8 * 60 * 60,        // 8 hours for production
    STAGING: 12 * 60 * 60,           // 12 hours for staging
    DEVELOPMENT: 24 * 60 * 60,       // 24 hours for development
    E2E_TESTING: 2 * 60 * 60,        // 2 hours for E2E tests
  },
  
  // Session update interval - how often to refresh the session for active users
  UPDATE_AGE: {
    PRODUCTION: 60 * 60,             // Every hour in production
    STAGING: 2 * 60 * 60,            // Every 2 hours in staging
    DEVELOPMENT: 4 * 60 * 60,        // Every 4 hours in development
    E2E_TESTING: 30 * 60,            // Every 30 minutes for E2E
  },
  
  // Idle timeout - logout after inactivity (client-side enforcement)
  IDLE_TIMEOUT: {
    PRODUCTION: 30 * 60,             // 30 minutes
    STAGING: 60 * 60,                // 1 hour
    DEVELOPMENT: 2 * 60 * 60,        // 2 hours
    E2E_TESTING: 15 * 60,            // 15 minutes
  },
  
  // Warning before session expiry
  WARNING_BEFORE_EXPIRY: 5 * 60,    // 5 minutes warning
} as const;

/**
 * Get session configuration based on environment
 */
export function getSessionConfig() {
  const env = process.env.NODE_ENV || 'development';
  const isE2E = process.env.DEMO_E2E === '1';
  const isProduction = env === 'production' && !isE2E;
  const isStaging = process.env.ENVIRONMENT === 'staging';
  
  let configKey: keyof typeof SESSION_CONFIG.MAX_AGE;
  
  if (isE2E) {
    configKey = 'E2E_TESTING';
  } else if (isProduction) {
    configKey = 'PRODUCTION';
  } else if (isStaging) {
    configKey = 'STAGING';
  } else {
    configKey = 'DEVELOPMENT';
  }
  
  return {
    maxAge: SESSION_CONFIG.MAX_AGE[configKey],
    updateAge: SESSION_CONFIG.UPDATE_AGE[configKey],
    idleTimeout: SESSION_CONFIG.IDLE_TIMEOUT[configKey],
    warningBeforeExpiry: SESSION_CONFIG.WARNING_BEFORE_EXPIRY,
    environment: configKey.toLowerCase(),
  };
}

/**
 * Format seconds to human-readable duration
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0 && minutes > 0) {
    return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
  } else if (hours > 0) {
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  } else {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  }
}

/**
 * Calculate remaining session time
 */
export function getRemainingSessionTime(sessionStart: Date, maxAge: number): number {
  const now = new Date().getTime();
  const start = sessionStart.getTime();
  const elapsed = (now - start) / 1000; // Convert to seconds
  const remaining = maxAge - elapsed;
  
  return Math.max(0, remaining);
}

/**
 * Check if session should show expiry warning
 */
export function shouldShowExpiryWarning(
  sessionStart: Date, 
  maxAge: number,
  warningBefore: number = SESSION_CONFIG.WARNING_BEFORE_EXPIRY
): boolean {
  const remaining = getRemainingSessionTime(sessionStart, maxAge);
  return remaining > 0 && remaining <= warningBefore;
}

/**
 * Check if user has been idle too long
 */
export function isUserIdle(lastActivity: Date, idleTimeout: number): boolean {
  const now = new Date().getTime();
  const last = lastActivity.getTime();
  const idleTime = (now - last) / 1000; // Convert to seconds
  
  return idleTime >= idleTimeout;
}

/**
 * Security recommendations for session management
 */
export const SESSION_SECURITY_RECOMMENDATIONS = {
  // Maximum recommended session ages by security level
  HIGH_SECURITY: 4 * 60 * 60,      // 4 hours for high security environments
  MEDIUM_SECURITY: 8 * 60 * 60,     // 8 hours for medium security
  LOW_SECURITY: 12 * 60 * 60,       // 12 hours for low security
  
  // Recommended idle timeouts
  IDLE_HIGH_SECURITY: 15 * 60,      // 15 minutes
  IDLE_MEDIUM_SECURITY: 30 * 60,    // 30 minutes
  IDLE_LOW_SECURITY: 60 * 60,       // 1 hour
  
  // Best practices
  REQUIRE_REAUTHENTICATION_FOR_SENSITIVE_OPERATIONS: true,
  LOG_SESSION_EVENTS: true,
  IMPLEMENT_SESSION_FIXATION_PROTECTION: true,
  USE_SECURE_COOKIES: true,
  IMPLEMENT_CSRF_PROTECTION: true,
};
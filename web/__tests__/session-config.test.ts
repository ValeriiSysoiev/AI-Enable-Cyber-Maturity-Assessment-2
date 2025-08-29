import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { 
  getSessionConfig,
  formatDuration,
  getRemainingSessionTime,
  shouldShowExpiryWarning,
  isUserIdle,
  SESSION_CONFIG
} from '../lib/session-config';

describe('Session Configuration', () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('getSessionConfig', () => {
    it('should return production config in production', () => {
      process.env.NODE_ENV = 'production';
      process.env.DEMO_E2E = undefined;
      
      const config = getSessionConfig();
      
      expect(config.maxAge).toBe(SESSION_CONFIG.MAX_AGE.PRODUCTION);
      expect(config.updateAge).toBe(SESSION_CONFIG.UPDATE_AGE.PRODUCTION);
      expect(config.idleTimeout).toBe(SESSION_CONFIG.IDLE_TIMEOUT.PRODUCTION);
      expect(config.environment).toBe('production');
    });

    it('should return E2E config when E2E flag is set', () => {
      process.env.NODE_ENV = 'production';
      process.env.DEMO_E2E = '1';
      
      const config = getSessionConfig();
      
      expect(config.maxAge).toBe(SESSION_CONFIG.MAX_AGE.E2E_TESTING);
      expect(config.updateAge).toBe(SESSION_CONFIG.UPDATE_AGE.E2E_TESTING);
      expect(config.environment).toBe('e2e_testing');
    });

    it('should return development config in development', () => {
      process.env.NODE_ENV = 'development';
      
      const config = getSessionConfig();
      
      expect(config.maxAge).toBe(SESSION_CONFIG.MAX_AGE.DEVELOPMENT);
      expect(config.updateAge).toBe(SESSION_CONFIG.UPDATE_AGE.DEVELOPMENT);
      expect(config.environment).toBe('development');
    });

    it('should return staging config when environment is staging', () => {
      process.env.NODE_ENV = 'production';
      process.env.ENVIRONMENT = 'staging';
      
      const config = getSessionConfig();
      
      expect(config.maxAge).toBe(SESSION_CONFIG.MAX_AGE.STAGING);
      expect(config.environment).toBe('staging');
    });
  });

  describe('formatDuration', () => {
    it('should format hours and minutes correctly', () => {
      expect(formatDuration(3661)).toBe('1 hour 1 minute');
      expect(formatDuration(7200)).toBe('2 hours');
      expect(formatDuration(3600)).toBe('1 hour');
      expect(formatDuration(60)).toBe('1 minute');
      expect(formatDuration(120)).toBe('2 minutes');
      expect(formatDuration(5400)).toBe('1 hour 30 minutes');
    });
  });

  describe('getRemainingSessionTime', () => {
    it('should calculate remaining time correctly', () => {
      const now = new Date();
      const sessionStart = new Date(now.getTime() - 1000 * 60 * 60); // 1 hour ago
      const maxAge = 8 * 60 * 60; // 8 hours
      
      const remaining = getRemainingSessionTime(sessionStart, maxAge);
      
      // Should have approximately 7 hours left (within a few seconds tolerance)
      expect(remaining).toBeGreaterThan(7 * 60 * 60 - 10);
      expect(remaining).toBeLessThan(7 * 60 * 60 + 10);
    });

    it('should return 0 for expired sessions', () => {
      const now = new Date();
      const sessionStart = new Date(now.getTime() - 1000 * 60 * 60 * 10); // 10 hours ago
      const maxAge = 8 * 60 * 60; // 8 hours
      
      const remaining = getRemainingSessionTime(sessionStart, maxAge);
      
      expect(remaining).toBe(0);
    });
  });

  describe('shouldShowExpiryWarning', () => {
    it('should show warning when close to expiry', () => {
      const now = new Date();
      const maxAge = 8 * 60 * 60; // 8 hours
      const warningBefore = 5 * 60; // 5 minutes
      
      // Session that expires in 4 minutes
      const sessionStart = new Date(now.getTime() - (maxAge - 4 * 60) * 1000);
      
      expect(shouldShowExpiryWarning(sessionStart, maxAge, warningBefore)).toBe(true);
    });

    it('should not show warning when session is fresh', () => {
      const now = new Date();
      const sessionStart = now;
      const maxAge = 8 * 60 * 60;
      
      expect(shouldShowExpiryWarning(sessionStart, maxAge)).toBe(false);
    });

    it('should not show warning for expired sessions', () => {
      const now = new Date();
      const sessionStart = new Date(now.getTime() - 10 * 60 * 60 * 1000); // 10 hours ago
      const maxAge = 8 * 60 * 60;
      
      expect(shouldShowExpiryWarning(sessionStart, maxAge)).toBe(false);
    });
  });

  describe('isUserIdle', () => {
    it('should detect idle users', () => {
      const now = new Date();
      const lastActivity = new Date(now.getTime() - 35 * 60 * 1000); // 35 minutes ago
      const idleTimeout = 30 * 60; // 30 minutes
      
      expect(isUserIdle(lastActivity, idleTimeout)).toBe(true);
    });

    it('should not flag active users as idle', () => {
      const now = new Date();
      const lastActivity = new Date(now.getTime() - 10 * 60 * 1000); // 10 minutes ago
      const idleTimeout = 30 * 60; // 30 minutes
      
      expect(isUserIdle(lastActivity, idleTimeout)).toBe(false);
    });
  });

  describe('Security Best Practices', () => {
    it('should have 8 hour max for production', () => {
      expect(SESSION_CONFIG.MAX_AGE.PRODUCTION).toBe(8 * 60 * 60);
    });

    it('should have shorter session for E2E testing', () => {
      expect(SESSION_CONFIG.MAX_AGE.E2E_TESTING).toBeLessThan(SESSION_CONFIG.MAX_AGE.PRODUCTION);
    });

    it('should have reasonable idle timeouts', () => {
      expect(SESSION_CONFIG.IDLE_TIMEOUT.PRODUCTION).toBe(30 * 60); // 30 minutes
      expect(SESSION_CONFIG.IDLE_TIMEOUT.PRODUCTION).toBeLessThanOrEqual(60 * 60); // Max 1 hour
    });

    it('should update sessions regularly', () => {
      expect(SESSION_CONFIG.UPDATE_AGE.PRODUCTION).toBe(60 * 60); // Every hour
      expect(SESSION_CONFIG.UPDATE_AGE.PRODUCTION).toBeLessThanOrEqual(2 * 60 * 60); // Max 2 hours
    });

    it('should warn before expiry', () => {
      expect(SESSION_CONFIG.WARNING_BEFORE_EXPIRY).toBe(5 * 60); // 5 minutes
      expect(SESSION_CONFIG.WARNING_BEFORE_EXPIRY).toBeGreaterThanOrEqual(3 * 60); // At least 3 minutes
    });
  });
});
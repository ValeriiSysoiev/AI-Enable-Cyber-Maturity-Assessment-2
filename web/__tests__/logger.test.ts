/**
 * Tests for production-safe logger
 */
import { createLogger, isLoggingEnabled, isDebugEnabled } from '../lib/logger';

describe('Production-Safe Logger', () => {
  let originalEnv: NodeJS.ProcessEnv;
  let consoleSpy: {
    debug: jest.SpyInstance;
    info: jest.SpyInstance;
    warn: jest.SpyInstance;
    error: jest.SpyInstance;
  };

  beforeEach(() => {
    // Save original environment
    originalEnv = { ...process.env };
    
    // Mock console methods
    consoleSpy = {
      debug: jest.spyOn(console, 'debug').mockImplementation(),
      info: jest.spyOn(console, 'info').mockImplementation(),
      warn: jest.spyOn(console, 'warn').mockImplementation(),
      error: jest.spyOn(console, 'error').mockImplementation()
    };
  });

  afterEach(() => {
    // Restore environment
    process.env = originalEnv;
    
    // Restore console
    Object.values(consoleSpy).forEach(spy => spy.mockRestore());
  });

  describe('Environment-based behavior', () => {
    it('should not log in production by default', () => {
      process.env.NODE_ENV = 'production';
      delete process.env.DEBUG;
      
      const logger = createLogger('test');
      logger.debug('debug message');
      logger.info('info message');
      logger.warn('warn message');
      logger.error('error message');
      
      expect(consoleSpy.debug).not.toHaveBeenCalled();
      expect(consoleSpy.info).not.toHaveBeenCalled();
      expect(consoleSpy.warn).not.toHaveBeenCalled();
      expect(consoleSpy.error).not.toHaveBeenCalled();
    });

    it('should log in development', () => {
      process.env.NODE_ENV = 'development';
      
      const logger = createLogger('test');
      logger.info('test message');
      
      expect(consoleSpy.info).toHaveBeenCalled();
    });

    it('should log in production when DEBUG is enabled', () => {
      process.env.NODE_ENV = 'production';
      process.env.DEBUG = 'true';
      
      const logger = createLogger('test');
      logger.info('test message');
      
      expect(consoleSpy.info).toHaveBeenCalled();
    });
  });

  describe('Log levels', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'development';
    });

    it('should respect log level hierarchy', () => {
      process.env.LOG_LEVEL = 'warn';
      
      const logger = createLogger('test');
      logger.debug('debug');
      logger.info('info');
      logger.warn('warn');
      logger.error('error');
      
      expect(consoleSpy.debug).not.toHaveBeenCalled();
      expect(consoleSpy.info).not.toHaveBeenCalled();
      expect(consoleSpy.warn).toHaveBeenCalled();
      expect(consoleSpy.error).toHaveBeenCalled();
    });

    it('should log all levels when set to debug', () => {
      process.env.LOG_LEVEL = 'debug';
      
      const logger = createLogger('test');
      logger.debug('debug');
      logger.info('info');
      logger.warn('warn');
      logger.error('error');
      
      expect(consoleSpy.debug).toHaveBeenCalled();
      expect(consoleSpy.info).toHaveBeenCalled();
      expect(consoleSpy.warn).toHaveBeenCalled();
      expect(consoleSpy.error).toHaveBeenCalled();
    });
  });

  describe('Data sanitization', () => {
    it('should sanitize sensitive data in production', () => {
      process.env.NODE_ENV = 'production';
      process.env.DEBUG = 'true';
      
      const logger = createLogger('test');
      logger.info('User login', {
        email: 'user@example.com',
        password: 'secret123',
        token: 'jwt-token-here',
        api_key: 'sk-12345',
        client_secret: 'client-secret-value',
        normalData: 'this is fine'
      });
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      
      expect(callArgs).toContain('[REDACTED]');
      expect(callArgs).not.toContain('secret123');
      expect(callArgs).not.toContain('jwt-token-here');
      expect(callArgs).not.toContain('sk-12345');
      expect(callArgs).not.toContain('client-secret-value');
      expect(callArgs).toContain('this is fine');
    });

    it('should not sanitize data in development', () => {
      process.env.NODE_ENV = 'development';
      
      const logger = createLogger('test');
      logger.info('User login', {
        password: 'secret123',
        normalData: 'this is fine'
      });
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      
      expect(callArgs).toContain('secret123');
      expect(callArgs).toContain('this is fine');
    });

    it('should sanitize nested sensitive data', () => {
      process.env.NODE_ENV = 'production';
      process.env.DEBUG = 'true';
      
      const logger = createLogger('test');
      logger.info('Config', {
        database: {
          host: 'localhost',
          password: 'db-password'
        },
        auth: {
          client_secret: 'oauth-secret',
          public_key: 'public-key-ok'
        }
      });
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      
      expect(callArgs).not.toContain('db-password');
      expect(callArgs).not.toContain('oauth-secret');
      expect(callArgs).toContain('localhost');
      expect(callArgs).toContain('public-key-ok');
    });
  });

  describe('Context management', () => {
    it('should include context in log messages', () => {
      process.env.NODE_ENV = 'development';
      
      const logger = createLogger('auth');
      logger.info('Login successful');
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      expect(callArgs).toContain('[auth]');
    });

    it('should support child loggers with nested context', () => {
      process.env.NODE_ENV = 'development';
      
      const parentLogger = createLogger('api');
      const childLogger = parentLogger.child('auth');
      
      childLogger.info('Processing request');
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      expect(callArgs).toContain('[api:auth]');
    });
  });

  describe('Helper functions', () => {
    it('should correctly report if logging is enabled', () => {
      process.env.NODE_ENV = 'production';
      delete process.env.DEBUG;
      expect(isLoggingEnabled()).toBe(false);
      
      process.env.NODE_ENV = 'development';
      expect(isLoggingEnabled()).toBe(true);
      
      process.env.NODE_ENV = 'production';
      process.env.DEBUG = '1';
      expect(isLoggingEnabled()).toBe(true);
    });

    it('should correctly report if debug logging is enabled', () => {
      process.env.NODE_ENV = 'development';
      process.env.LOG_LEVEL = 'info';
      expect(isDebugEnabled()).toBe(false);
      
      process.env.LOG_LEVEL = 'debug';
      expect(isDebugEnabled()).toBe(true);
    });
  });

  describe('Message formatting', () => {
    it('should format messages with timestamp and level', () => {
      process.env.NODE_ENV = 'development';
      
      const logger = createLogger('test');
      logger.info('Test message');
      
      const callArgs = consoleSpy.info.mock.calls[0][0];
      
      expect(callArgs).toMatch(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\]/);
      expect(callArgs).toContain('[INFO]');
      expect(callArgs).toContain('Test message');
    });

    it('should handle undefined data gracefully', () => {
      process.env.NODE_ENV = 'development';
      
      const logger = createLogger('test');
      logger.info('Message without data');
      
      expect(consoleSpy.info).toHaveBeenCalled();
      const callArgs = consoleSpy.info.mock.calls[0][0];
      expect(callArgs).toContain('Message without data');
    });
  });
});
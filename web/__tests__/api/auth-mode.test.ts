/**
 * Unit tests for /api/auth/mode endpoint
 * 
 * Verifies correct authentication mode detection based on environment
 */

import { NextRequest } from 'next/server';
import { GET } from '../../app/api/auth/mode/route';

describe('/api/auth/mode endpoint', () => {
  // Store original env vars
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset environment before each test
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    // Restore original environment
    process.env = originalEnv;
  });

  describe('Production Environment', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'production';
    });

    test('should return AAD mode when properly configured', async () => {
      // Set up AAD configuration
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
      process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';
      process.env.DEMO_E2E = '0';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('aad');
      expect(data.enabled).toBe(true);
      expect(data.aadEnabled).toBe(true);
      expect(data.demoEnabled).toBe(false);
    });

    test('should return AAD mode even if demo flag is set in production', async () => {
      // Production should ignore demo flag
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
      process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';
      process.env.DEMO_E2E = '1'; // Should be ignored

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('aad');
      expect(data.demoEnabled).toBe(false); // Always false in production
    });

    test('should return error when AAD is not configured', async () => {
      // Missing AAD configuration
      process.env.AUTH_MODE = undefined;
      process.env.AZURE_AD_CLIENT_ID = undefined;
      process.env.AZURE_AD_TENANT_ID = undefined;
      process.env.AZURE_AD_CLIENT_SECRET = undefined;

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.mode).toBe('error');
      expect(data.enabled).toBe(false);
      expect(data.error).toBe('Azure AD authentication is required in production');
    });

    test('should return error when AAD is partially configured', async () => {
      // Incomplete AAD configuration
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      // Missing tenant ID and secret

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.mode).toBe('error');
      expect(data.enabled).toBe(false);
      expect(data.aadEnabled).toBe(false);
    });

    test('should never return demo mode in production', async () => {
      // Even with demo flag set and no AAD
      process.env.DEMO_E2E = '1';
      process.env.AUTH_MODE = undefined;

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.mode).not.toBe('demo');
      expect(data.mode).toBe('error');
    });
  });

  describe('Development Environment', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'development';
    });

    test('should return AAD mode when configured in development', async () => {
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
      process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';
      process.env.DEMO_E2E = '0';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('aad');
      expect(data.aadEnabled).toBe(true);
    });

    test('should return demo mode when AAD not configured', async () => {
      process.env.AUTH_MODE = undefined;
      process.env.DEMO_E2E = '1';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('demo');
      expect(data.demoEnabled).toBe(true);
    });

    test('should fallback to demo when AAD not fully configured', async () => {
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      // Missing other AAD vars
      process.env.DEMO_E2E = undefined;

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('demo');
      expect(data.aadEnabled).toBe(false);
    });

    test('should prefer AAD over demo when both available', async () => {
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
      process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';
      process.env.DEMO_E2E = '0'; // Demo disabled

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('aad');
    });
  });

  describe('Test Environment', () => {
    beforeEach(() => {
      process.env.NODE_ENV = 'test';
    });

    test('should allow demo mode in test environment', async () => {
      process.env.DEMO_E2E = '1';
      process.env.AUTH_MODE = undefined;

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('demo');
      expect(data.demoEnabled).toBe(true);
    });

    test('should allow AAD mode in test environment', async () => {
      process.env.AUTH_MODE = 'aad';
      process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
      process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
      process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';
      process.env.DEMO_E2E = '0';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('aad');
      expect(data.aadEnabled).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    test('should handle AUTH_MODE set to non-aad value', async () => {
      process.env.NODE_ENV = 'development';
      process.env.AUTH_MODE = 'oauth'; // Invalid value
      process.env.DEMO_E2E = '1';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('demo');
      expect(data.aadEnabled).toBe(false);
    });

    test('should handle empty string environment variables', async () => {
      process.env.NODE_ENV = 'development';
      process.env.AUTH_MODE = '';
      process.env.AZURE_AD_CLIENT_ID = '';
      process.env.DEMO_E2E = '';

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.mode).toBe('demo');
      expect(data.aadEnabled).toBe(false);
      expect(data.demoEnabled).toBe(false);
    });

    test('should handle whitespace in environment variables', async () => {
      process.env.NODE_ENV = 'production';
      process.env.AUTH_MODE = ' aad '; // With whitespace
      process.env.AZURE_AD_CLIENT_ID = ' test-client-id ';
      process.env.AZURE_AD_TENANT_ID = ' test-tenant-id ';
      process.env.AZURE_AD_CLIENT_SECRET = ' test-secret ';

      const response = await GET();
      const data = await response.json();

      // Should fail because AUTH_MODE doesn't exactly match 'aad'
      expect(response.status).toBe(500);
      expect(data.mode).toBe('error');
      expect(data.aadEnabled).toBe(false);
    });
  });
});
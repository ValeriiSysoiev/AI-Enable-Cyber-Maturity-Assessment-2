import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';

describe('Auth Provider Security', () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    // Clear module cache to reload auth config
    jest.resetModules();
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should not enable demo provider in production without E2E flag', () => {
    process.env.NODE_ENV = 'production';
    process.env.DEMO_E2E = undefined;
    process.env.AUTH_MODE = 'aad';
    process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
    process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
    process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';

    const { authOptions } = require('../lib/auth');
    const providers = authOptions.providers;
    
    // Should only have Azure AD provider
    expect(providers).toHaveLength(1);
    expect(providers[0].id).toBe('azure-ad');
  });

  it('should allow demo provider in development', () => {
    process.env.NODE_ENV = 'development';
    process.env.DEMO_E2E = undefined;
    process.env.AUTH_MODE = undefined;

    const { authOptions } = require('../lib/auth');
    const providers = authOptions.providers;
    
    // Should have demo provider in development
    expect(providers.length).toBeGreaterThan(0);
    // Check for credentials provider (demo uses CredentialsProvider)
    const demoProvider = providers.find((p: any) => p.type === 'credentials' || p.name === 'Demo');
    expect(demoProvider).toBeDefined();
  });

  it('should allow demo provider in E2E testing', () => {
    process.env.NODE_ENV = 'production';
    process.env.DEMO_E2E = '1';
    process.env.AUTH_MODE = 'aad';
    process.env.AZURE_AD_CLIENT_ID = 'test-client-id';
    process.env.AZURE_AD_TENANT_ID = 'test-tenant-id';
    process.env.AZURE_AD_CLIENT_SECRET = 'test-secret';

    const { authOptions } = require('../lib/auth');
    const providers = authOptions.providers;
    
    // Should have both providers for E2E testing
    expect(providers.length).toBeGreaterThanOrEqual(2);
  });

  it('should throw error in production without any provider', () => {
    process.env.NODE_ENV = 'production';
    process.env.DEMO_E2E = undefined;
    process.env.AUTH_MODE = undefined;
    process.env.AZURE_AD_CLIENT_ID = undefined;

    expect(() => {
      require('../lib/auth');
    }).toThrow('Production requires authentication provider configuration');
  });

  it('should validate email format in demo provider', async () => {
    process.env.NODE_ENV = 'development';

    const { authOptions } = require('../lib/auth');
    const demoProvider = authOptions.providers.find((p: any) => p.name === 'Demo');
    
    if (demoProvider && demoProvider.authorize) {
      // Invalid email should return null
      const result1 = await demoProvider.authorize({ email: 'invalid-email' });
      expect(result1).toBeNull();
      
      // Valid email should return user
      const result2 = await demoProvider.authorize({ email: 'test@example.com' });
      expect(result2).toBeDefined();
      expect(result2?.email).toBe('test@example.com');
      expect(result2?.role).toBe('demo'); // Should not be admin
    }
  });
});
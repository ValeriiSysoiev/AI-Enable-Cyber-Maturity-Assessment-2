import { describe, it, expect, beforeEach } from '@jest/globals';
import { addSecurityHeaders, validateOrigin } from '../lib/security-headers';
import { NextRequest, NextResponse } from 'next/server';

describe('Security Headers', () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = process.env;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('addSecurityHeaders', () => {
    it('should add security headers in production', () => {
      process.env.NODE_ENV = 'production';
      
      const response = new NextResponse();
      const securedResponse = addSecurityHeaders(response);
      
      expect(securedResponse.headers.get('X-Frame-Options')).toBe('SAMEORIGIN');
      expect(securedResponse.headers.get('X-Content-Type-Options')).toBe('nosniff');
      expect(securedResponse.headers.get('X-XSS-Protection')).toBe('1; mode=block');
      expect(securedResponse.headers.get('Referrer-Policy')).toBe('strict-origin-when-cross-origin');
      expect(securedResponse.headers.get('Content-Security-Policy')).toContain("default-src 'self'");
      expect(securedResponse.headers.get('Strict-Transport-Security')).toContain('max-age=63072000');
    });

    it('should not add security headers in development', () => {
      process.env.NODE_ENV = 'development';
      
      const response = new NextResponse();
      const securedResponse = addSecurityHeaders(response);
      
      expect(securedResponse.headers.get('X-Frame-Options')).toBeNull();
      expect(securedResponse.headers.get('Strict-Transport-Security')).toBeNull();
    });
  });

  describe('validateOrigin', () => {
    it('should validate correct origin in production', () => {
      process.env.NODE_ENV = 'production';
      
      const request = new NextRequest('https://example.com', {
        headers: {
          origin: 'https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io',
          host: 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io'
        }
      });
      
      expect(validateOrigin(request)).toBe(true);
    });

    it('should reject invalid origin in production', () => {
      process.env.NODE_ENV = 'production';
      
      const request = new NextRequest('https://example.com', {
        headers: {
          origin: 'https://malicious.com',
          host: 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io'
        }
      });
      
      expect(validateOrigin(request)).toBe(false);
    });

    it('should allow any origin in development', () => {
      process.env.NODE_ENV = 'development';
      
      const request = new NextRequest('https://example.com', {
        headers: {
          origin: 'http://localhost:3000',
          host: 'localhost:3000'
        }
      });
      
      expect(validateOrigin(request)).toBe(true);
    });
  });
});

describe('Configuration Security', () => {
  it('should not expose secrets in next.config.js', () => {
    const nextConfig = require('../next.config.js');
    
    // Ensure no sensitive environment variables are exposed
    expect(nextConfig.env?.AZURE_AD_CLIENT_SECRET).toBeUndefined();
    expect(nextConfig.env?.NEXTAUTH_SECRET).toBeUndefined();
    expect(nextConfig.publicRuntimeConfig?.AZURE_AD_CLIENT_SECRET).toBeUndefined();
    expect(nextConfig.serverRuntimeConfig).toBeUndefined();
  });
});

describe('Admin Authorization', () => {
  it('should not allow admin access in production via client-side check', () => {
    process.env.NODE_ENV = 'production';
    const { isAdmin } = require('../lib/auth');
    
    // Mock localStorage
    const localStorageMock = {
      getItem: jest.fn().mockReturnValue('va.sysoiev@audit3a.com')
    };
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    
    // Should return false in production regardless of email
    expect(isAdmin()).toBe(false);
  });
});
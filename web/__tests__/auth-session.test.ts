import { describe, it, expect } from '@jest/globals';
import { authOptions } from '../lib/auth';

describe('Auth Session Security', () => {
  it('should have secure session timeout configuration', () => {
    // Session should not exceed 8 hours for security
    expect(authOptions.session?.maxAge).toBeLessThanOrEqual(8 * 60 * 60);
    
    // Should use JWT strategy
    expect(authOptions.session?.strategy).toBe('jwt');
    
    // Should have update age configured
    expect(authOptions.session?.updateAge).toBeDefined();
    expect(authOptions.session?.updateAge).toBeLessThanOrEqual(60 * 60);
  });

  it('should not have excessive session timeout', () => {
    const maxAge = authOptions.session?.maxAge || 0;
    const hours = maxAge / (60 * 60);
    
    // Session should not exceed 8 hours
    expect(hours).toBeLessThanOrEqual(8);
    
    // Session should not be less than 1 hour (too restrictive)
    expect(hours).toBeGreaterThanOrEqual(1);
  });

  it('should have proper secret configuration', () => {
    // In production, should use environment variable
    if (process.env.NODE_ENV === 'production') {
      expect(process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET).toBeDefined();
    }
  });
});
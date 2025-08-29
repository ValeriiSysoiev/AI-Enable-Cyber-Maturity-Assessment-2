/**
 * Tests for secure demo session management
 */
import {
  generateSecureToken,
  hashToken,
  createDemoSession,
  validateDemoSession,
  revokeDemoSession,
  cleanupExpiredSessions,
  checkRateLimit,
  clearAllSessions
} from '../lib/demo-session';

describe('Demo Session Security', () => {
  beforeEach(() => {
    // Clear all sessions before each test
    clearAllSessions();
  });

  describe('Token Generation', () => {
    it('should generate secure random tokens', () => {
      const token1 = generateSecureToken();
      const token2 = generateSecureToken();
      
      // Tokens should be unique
      expect(token1).not.toBe(token2);
      
      // Tokens should be 64 characters (32 bytes in hex)
      expect(token1).toHaveLength(64);
      expect(token2).toHaveLength(64);
      
      // Tokens should be hex strings
      expect(token1).toMatch(/^[0-9a-f]{64}$/);
      expect(token2).toMatch(/^[0-9a-f]{64}$/);
    });

    it('should create consistent hashes', () => {
      const token = 'test-token';
      const hash1 = hashToken(token);
      const hash2 = hashToken(token);
      
      // Same token should produce same hash
      expect(hash1).toBe(hash2);
      
      // Hash should be 64 characters (SHA-256 in hex)
      expect(hash1).toHaveLength(64);
    });

    it('should create different hashes for different tokens', () => {
      const hash1 = hashToken('token1');
      const hash2 = hashToken('token2');
      
      expect(hash1).not.toBe(hash2);
    });
  });

  describe('Session Creation', () => {
    it('should create a valid session', () => {
      const email = 'test@example.com';
      const { token, session } = createDemoSession(email);
      
      expect(token).toHaveLength(64);
      expect(session.email).toBe(email.toLowerCase());
      expect(session.createdAt).toBeInstanceOf(Date);
      expect(session.expiresAt).toBeInstanceOf(Date);
      expect(session.expiresAt.getTime()).toBeGreaterThan(session.createdAt.getTime());
    });

    it('should reject invalid email formats', () => {
      const invalidEmails = [
        'not-an-email',
        '@example.com',
        'user@',
        'user @example.com',
        'user@example',
        ''
      ];
      
      for (const email of invalidEmails) {
        expect(() => createDemoSession(email)).toThrow('Invalid email format');
      }
    });

    it('should normalize email to lowercase', () => {
      const { session } = createDemoSession('Test@EXAMPLE.COM');
      expect(session.email).toBe('test@example.com');
    });

    it('should store IP and user agent when provided', () => {
      const email = 'test@example.com';
      const ipAddress = '192.168.1.1';
      const userAgent = 'Mozilla/5.0';
      
      const { session } = createDemoSession(email, ipAddress, userAgent);
      
      expect(session.ipAddress).toBe(ipAddress);
      expect(session.userAgent).toBe(userAgent);
    });
  });

  describe('Session Validation', () => {
    it('should validate a valid session', () => {
      const email = 'test@example.com';
      const { token } = createDemoSession(email);
      
      const validation = validateDemoSession(token);
      
      expect(validation.valid).toBe(true);
      expect(validation.email).toBe(email);
      expect(validation.reason).toBeUndefined();
    });

    it('should reject invalid token formats', () => {
      const invalidTokens = [
        '',
        'short',
        'not-64-chars',
        null,
        undefined,
        123,
        'a'.repeat(63),
        'a'.repeat(65)
      ];
      
      for (const token of invalidTokens) {
        const validation = validateDemoSession(token as any);
        expect(validation.valid).toBe(false);
        expect(validation.reason).toBe('Invalid token format');
      }
    });

    it('should reject non-existent sessions', () => {
      const fakeToken = '0'.repeat(64);
      const validation = validateDemoSession(fakeToken);
      
      expect(validation.valid).toBe(false);
      expect(validation.reason).toBe('Session not found');
    });

    it('should reject expired sessions', () => {
      // Create a session and manually expire it
      const email = 'test@example.com';
      const { token, session } = createDemoSession(email);
      
      // Manually set expiry to past
      session.expiresAt = new Date(Date.now() - 1000);
      
      const validation = validateDemoSession(token);
      
      expect(validation.valid).toBe(false);
      expect(validation.reason).toBe('Session expired');
    });

    it('should validate IP address when configured', () => {
      const originalEnv = process.env.DEMO_VALIDATE_IP;
      process.env.DEMO_VALIDATE_IP = '1';
      
      try {
        const email = 'test@example.com';
        const ipAddress = '192.168.1.1';
        const { token } = createDemoSession(email, ipAddress);
        
        // Should succeed with same IP
        let validation = validateDemoSession(token, ipAddress);
        expect(validation.valid).toBe(true);
        
        // Should fail with different IP
        validation = validateDemoSession(token, '192.168.1.2');
        expect(validation.valid).toBe(false);
        expect(validation.reason).toBe('IP address mismatch');
      } finally {
        process.env.DEMO_VALIDATE_IP = originalEnv;
      }
    });

    it('should validate user agent when configured', () => {
      const originalEnv = process.env.DEMO_VALIDATE_UA;
      process.env.DEMO_VALIDATE_UA = '1';
      
      try {
        const email = 'test@example.com';
        const userAgent = 'Mozilla/5.0';
        const { token } = createDemoSession(email, undefined, userAgent);
        
        // Should succeed with same user agent
        let validation = validateDemoSession(token, undefined, userAgent);
        expect(validation.valid).toBe(true);
        
        // Should fail with different user agent
        validation = validateDemoSession(token, undefined, 'Chrome/99.0');
        expect(validation.valid).toBe(false);
        expect(validation.reason).toBe('User agent mismatch');
      } finally {
        process.env.DEMO_VALIDATE_UA = originalEnv;
      }
    });
  });

  describe('Session Revocation', () => {
    it('should revoke an existing session', () => {
      const email = 'test@example.com';
      const { token } = createDemoSession(email);
      
      // Session should be valid initially
      let validation = validateDemoSession(token);
      expect(validation.valid).toBe(true);
      
      // Revoke the session
      const revoked = revokeDemoSession(token);
      expect(revoked).toBe(true);
      
      // Session should no longer be valid
      validation = validateDemoSession(token);
      expect(validation.valid).toBe(false);
      expect(validation.reason).toBe('Session not found');
    });

    it('should handle revoking non-existent sessions', () => {
      const fakeToken = '0'.repeat(64);
      const revoked = revokeDemoSession(fakeToken);
      expect(revoked).toBe(false);
    });
  });

  describe('Session Cleanup', () => {
    it('should clean up expired sessions', () => {
      // Create multiple sessions
      const { token: token1 } = createDemoSession('user1@example.com');
      const { token: token2, session: session2 } = createDemoSession('user2@example.com');
      const { token: token3, session: session3 } = createDemoSession('user3@example.com');
      
      // Manually expire some sessions
      session2.expiresAt = new Date(Date.now() - 1000);
      session3.expiresAt = new Date(Date.now() - 1000);
      
      // Clean up expired sessions
      const cleaned = cleanupExpiredSessions();
      expect(cleaned).toBe(2);
      
      // Check that only non-expired session remains
      expect(validateDemoSession(token1).valid).toBe(true);
      expect(validateDemoSession(token2).valid).toBe(false);
      expect(validateDemoSession(token3).valid).toBe(false);
    });
  });

  describe('Rate Limiting', () => {
    it('should allow requests within rate limit', () => {
      const identifier = 'test-ip';
      
      for (let i = 0; i < 5; i++) {
        expect(checkRateLimit(identifier)).toBe(true);
      }
    });

    it('should block requests exceeding rate limit', () => {
      const identifier = 'test-ip';
      
      // Use up the rate limit
      for (let i = 0; i < 5; i++) {
        checkRateLimit(identifier);
      }
      
      // Next request should be blocked
      expect(checkRateLimit(identifier)).toBe(false);
    });

    it('should use different limits for different identifiers', () => {
      const identifier1 = 'ip-1';
      const identifier2 = 'ip-2';
      
      // Use up rate limit for identifier1
      for (let i = 0; i < 5; i++) {
        checkRateLimit(identifier1);
      }
      
      // identifier2 should still be allowed
      expect(checkRateLimit(identifier2)).toBe(true);
      
      // identifier1 should be blocked
      expect(checkRateLimit(identifier1)).toBe(false);
    });
  });

  describe('Security Edge Cases', () => {
    it('should not allow session hijacking with modified token', () => {
      const email = 'test@example.com';
      const { token } = createDemoSession(email);
      
      // Try to use a modified token
      const modifiedToken = token.substring(0, 63) + (token[63] === '0' ? '1' : '0');
      
      const validation = validateDemoSession(modifiedToken);
      expect(validation.valid).toBe(false);
      expect(validation.reason).toBe('Session not found');
    });

    it('should handle concurrent session creation', () => {
      const emails = ['user1@example.com', 'user2@example.com', 'user3@example.com'];
      const sessions = emails.map(email => createDemoSession(email));
      
      // All sessions should be valid
      for (const { token } of sessions) {
        const validation = validateDemoSession(token);
        expect(validation.valid).toBe(true);
      }
      
      // All tokens should be unique
      const tokens = sessions.map(s => s.token);
      const uniqueTokens = new Set(tokens);
      expect(uniqueTokens.size).toBe(tokens.length);
    });

    it('should prevent token reuse after revocation', () => {
      const email = 'test@example.com';
      const { token } = createDemoSession(email);
      
      // Revoke the session
      revokeDemoSession(token);
      
      // Try to validate the revoked token multiple times
      for (let i = 0; i < 3; i++) {
        const validation = validateDemoSession(token);
        expect(validation.valid).toBe(false);
        expect(validation.reason).toBe('Session not found');
      }
    });
  });
});
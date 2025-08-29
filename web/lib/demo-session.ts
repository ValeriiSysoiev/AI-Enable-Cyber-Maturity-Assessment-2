/**
 * Secure demo session management with token validation
 */
import { createHash, randomBytes } from 'crypto';

// In-memory session store for demo mode (in production, use Redis or database)
const demoSessions = new Map<string, DemoSession>();

// Session expiry time (8 hours, matching JWT session timeout)
const SESSION_EXPIRY_MS = 8 * 60 * 60 * 1000;

// Clean up expired sessions every hour
const CLEANUP_INTERVAL_MS = 60 * 60 * 1000;

interface DemoSession {
  email: string;
  token: string;
  createdAt: Date;
  expiresAt: Date;
  ipAddress?: string;
  userAgent?: string;
}

/**
 * Generate a secure random token
 */
export function generateSecureToken(): string {
  return randomBytes(32).toString('hex');
}

/**
 * Create a hash of the token for storage
 */
export function hashToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}

/**
 * Create a new demo session
 */
export function createDemoSession(
  email: string,
  ipAddress?: string,
  userAgent?: string
): { token: string; session: DemoSession } {
  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    throw new Error('Invalid email format');
  }

  // Generate secure token
  const token = generateSecureToken();
  const hashedToken = hashToken(token);
  
  const now = new Date();
  const expiresAt = new Date(now.getTime() + SESSION_EXPIRY_MS);
  
  const session: DemoSession = {
    email: email.toLowerCase(),
    token: hashedToken,
    createdAt: now,
    expiresAt,
    ipAddress,
    userAgent
  };
  
  // Store session with hashed token as key
  demoSessions.set(hashedToken, session);
  
  // Return unhashed token for client
  return { token, session };
}

/**
 * Validate a demo session token
 */
export function validateDemoSession(
  token: string,
  ipAddress?: string,
  userAgent?: string
): { valid: boolean; email?: string; reason?: string } {
  if (!token || typeof token !== 'string' || token.length !== 64) {
    return { valid: false, reason: 'Invalid token format' };
  }
  
  const hashedToken = hashToken(token);
  const session = demoSessions.get(hashedToken);
  
  if (!session) {
    return { valid: false, reason: 'Session not found' };
  }
  
  // Check expiry
  if (new Date() > session.expiresAt) {
    demoSessions.delete(hashedToken);
    return { valid: false, reason: 'Session expired' };
  }
  
  // Optional: Validate IP address consistency
  if (process.env.DEMO_VALIDATE_IP === '1' && ipAddress && session.ipAddress) {
    if (ipAddress !== session.ipAddress) {
      return { valid: false, reason: 'IP address mismatch' };
    }
  }
  
  // Optional: Validate user agent consistency
  if (process.env.DEMO_VALIDATE_UA === '1' && userAgent && session.userAgent) {
    if (userAgent !== session.userAgent) {
      return { valid: false, reason: 'User agent mismatch' };
    }
  }
  
  return { valid: true, email: session.email };
}

/**
 * Revoke a demo session
 */
export function revokeDemoSession(token: string): boolean {
  const hashedToken = hashToken(token);
  return demoSessions.delete(hashedToken);
}

/**
 * Clean up expired sessions
 */
export function cleanupExpiredSessions(): number {
  const now = new Date();
  let cleaned = 0;
  
  for (const [hashedToken, session] of demoSessions.entries()) {
    if (now > session.expiresAt) {
      demoSessions.delete(hashedToken);
      cleaned++;
    }
  }
  
  return cleaned;
}

/**
 * Get session count (for monitoring)
 */
export function getSessionCount(): number {
  return demoSessions.size;
}

/**
 * Clear all sessions (for testing or emergency)
 */
export function clearAllSessions(): void {
  demoSessions.clear();
}

// Set up periodic cleanup
if (typeof window === 'undefined') {
  // Only run on server side
  setInterval(() => {
    const cleaned = cleanupExpiredSessions();
    if (cleaned > 0) {
      console.log(`Cleaned up ${cleaned} expired demo sessions`);
    }
  }, CLEANUP_INTERVAL_MS);
}

/**
 * Rate limiting for session creation
 */
const rateLimitMap = new Map<string, number[]>();
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
const MAX_ATTEMPTS = 5;

export function checkRateLimit(identifier: string): boolean {
  const now = Date.now();
  const attempts = rateLimitMap.get(identifier) || [];
  
  // Remove old attempts outside the window
  const recentAttempts = attempts.filter(time => now - time < RATE_LIMIT_WINDOW_MS);
  
  if (recentAttempts.length >= MAX_ATTEMPTS) {
    return false; // Rate limit exceeded
  }
  
  recentAttempts.push(now);
  rateLimitMap.set(identifier, recentAttempts);
  
  return true;
}

// Clean up rate limit map periodically
if (typeof window === 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [identifier, attempts] of rateLimitMap.entries()) {
      const recentAttempts = attempts.filter(time => now - time < RATE_LIMIT_WINDOW_MS);
      if (recentAttempts.length === 0) {
        rateLimitMap.delete(identifier);
      } else {
        rateLimitMap.set(identifier, recentAttempts);
      }
    }
  }, RATE_LIMIT_WINDOW_MS);
}
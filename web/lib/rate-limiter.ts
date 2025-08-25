/**
 * Rate Limiting Utility
 * 
 * Implements token bucket algorithm with sliding window for rate limiting
 * across different API endpoints with configurable limits.
 */

interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  keyGenerator?: (request: any) => string;
}

interface RateLimitEntry {
  count: number;
  resetTime: number;
  tokens: number;
  lastRefill: number;
}

class RateLimiter {
  private cache = new Map<string, RateLimitEntry>();
  private config: RateLimitConfig;

  constructor(config: RateLimitConfig) {
    this.config = {
      keyGenerator: (req) => req.headers?.get?.('x-forwarded-for') || req.headers?.get?.('x-real-ip') || 'anonymous',
      ...config
    };

    // Clean up expired entries every minute
    setInterval(() => this.cleanup(), 60000);
  }

  /**
   * Check if a request should be rate limited
   */
  isRateLimited(request: any): { limited: boolean; resetTime?: number; remaining?: number } {
    const key = this.config.keyGenerator!(request);
    const now = Date.now();
    
    let entry = this.cache.get(key);

    if (!entry || now > entry.resetTime) {
      // Create new or reset expired entry
      entry = {
        count: 1,
        resetTime: now + this.config.windowMs,
        tokens: this.config.maxRequests - 1,
        lastRefill: now
      };
      this.cache.set(key, entry);
      return { 
        limited: false, 
        resetTime: entry.resetTime, 
        remaining: entry.tokens 
      };
    }

    // Token bucket refill logic
    const timeSinceLastRefill = now - entry.lastRefill;
    const tokensToAdd = Math.floor(timeSinceLastRefill / (this.config.windowMs / this.config.maxRequests));
    
    if (tokensToAdd > 0) {
      entry.tokens = Math.min(this.config.maxRequests, entry.tokens + tokensToAdd);
      entry.lastRefill = now;
    }

    if (entry.tokens > 0) {
      entry.tokens--;
      entry.count++;
      return { 
        limited: false, 
        resetTime: entry.resetTime, 
        remaining: entry.tokens 
      };
    }

    return { 
      limited: true, 
      resetTime: entry.resetTime, 
      remaining: 0 
    };
  }

  /**
   * Clean up expired entries
   */
  private cleanup() {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.resetTime) {
        this.cache.delete(key);
      }
    }
  }
}

// Pre-configured rate limiters for different endpoints
export const rateLimiters = {
  // General proxy endpoints: 100 requests per minute
  proxy: new RateLimiter({
    windowMs: 60000, // 1 minute
    maxRequests: 100,
    keyGenerator: (req) => `proxy:${req.headers?.get?.('x-user-email') || req.headers?.get?.('x-forwarded-for') || 'anonymous'}`
  }),

  // Admin endpoints: 20 requests per minute (more restrictive)
  admin: new RateLimiter({
    windowMs: 60000, // 1 minute
    maxRequests: 20,
    keyGenerator: (req) => `admin:${req.headers?.get?.('x-user-email') || 'anonymous'}`
  }),

  // Authentication endpoints: 10 requests per minute (most restrictive)
  auth: new RateLimiter({
    windowMs: 60000, // 1 minute
    maxRequests: 10,
    keyGenerator: (req) => `auth:${req.headers?.get?.('x-forwarded-for') || req.headers?.get?.('x-real-ip') || 'anonymous'}`
  })
};

/**
 * Rate limiting middleware function
 */
export function withRateLimit(limiter: RateLimiter) {
  return function(handler: (request: any, ...args: any[]) => Promise<Response>) {
    return async function(request: any, ...args: any[]): Promise<Response> {
      const result = limiter.isRateLimited(request);
      
      if (result.limited) {
        // Log rate limit violation for security monitoring
        console.warn('Rate limit exceeded', {
          userAgent: request.headers?.get?.('user-agent'),
          userEmail: request.headers?.get?.('x-user-email'),
          ip: request.headers?.get?.('x-forwarded-for') || request.headers?.get?.('x-real-ip'),
          url: request.url,
          timestamp: new Date().toISOString()
        });

        const response = new Response(
          JSON.stringify({
            error: 'Rate limit exceeded',
            message: 'Too many requests. Please try again later.',
            retryAfter: Math.ceil((result.resetTime! - Date.now()) / 1000)
          }),
          {
            status: 429,
            headers: {
              'Content-Type': 'application/json',
              'X-RateLimit-Limit': String(limiter['config'].maxRequests),
              'X-RateLimit-Remaining': '0',
              'X-RateLimit-Reset': String(Math.ceil(result.resetTime! / 1000)),
              'Retry-After': String(Math.ceil((result.resetTime! - Date.now()) / 1000))
            }
          }
        );
        
        return response;
      }

      // Add rate limit headers to successful responses
      const response = await handler(request, ...args);
      
      if (response.headers && result.remaining !== undefined) {
        response.headers.set('X-RateLimit-Limit', String(limiter['config'].maxRequests));
        response.headers.set('X-RateLimit-Remaining', String(result.remaining));
        response.headers.set('X-RateLimit-Reset', String(Math.ceil(result.resetTime! / 1000)));
      }

      return response;
    };
  };
}

export default RateLimiter;
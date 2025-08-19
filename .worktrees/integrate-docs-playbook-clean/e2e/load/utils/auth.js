/**
 * Authentication utilities for k6 load testing
 * 
 * Supports both demo mode and AAD authentication flows
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { getCurrentEnvironment } from '../k6.config.js';

/**
 * Demo authentication session
 * Simulates the demo mode authentication flow
 */
export class DemoAuthSession {
  constructor(userEmail = 'user@example.com') {
    this.userEmail = userEmail;
    this.sessionId = null;
    this.cookies = {};
    this.headers = {};
    this.env = getCurrentEnvironment();
  }
  
  /**
   * Initialize demo session
   * @returns {boolean} Success status
   */
  login() {
    return group('Demo Authentication', () => {
      // Step 1: Check auth mode
      const authModeResponse = http.get(`${this.env.webUrl}/api/auth/mode`);
      const authModeCheck = check(authModeResponse, {
        'Auth mode endpoint accessible': (r) => r.status === 200,
        'Auth mode is demo': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.mode === 'demo';
          } catch {
            return false;
          }
        }
      });
      
      if (!authModeCheck) {
        console.error('Demo auth mode not available or not configured');
        return false;
      }
      
      // Step 2: Start demo session
      const sessionResponse = http.post(`${this.env.webUrl}/api/auth/session`, JSON.stringify({
        email: this.userEmail,
        mode: 'demo'
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
      
      const sessionCheck = check(sessionResponse, {
        'Demo session created': (r) => r.status === 200,
        'Session response has session data': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.session && data.user;
          } catch {
            return false;
          }
        }
      });
      
      if (sessionCheck) {
        // Extract session information
        try {
          const sessionData = JSON.parse(sessionResponse.body);
          this.sessionId = sessionData.session.id;
          
          // Extract cookies from response
          const setCookieHeaders = sessionResponse.headers['Set-Cookie'] || [];
          if (Array.isArray(setCookieHeaders)) {
            setCookieHeaders.forEach(cookie => this.parseCookie(cookie));
          } else if (setCookieHeaders) {
            this.parseCookie(setCookieHeaders);
          }
          
          // Set authentication headers
          this.headers = {
            'X-User-Email': this.userEmail,
            'X-Session-ID': this.sessionId,
            'Cookie': this.getCookieString()
          };
          
          return true;
        } catch (error) {
          console.error('Failed to parse session response:', error);
          return false;
        }
      }
      
      return false;
    });
  }
  
  /**
   * Parse cookie from Set-Cookie header
   */
  parseCookie(cookieString) {
    const parts = cookieString.split(';')[0].split('=');
    if (parts.length === 2) {
      this.cookies[parts[0].trim()] = parts[1].trim();
    }
  }
  
  /**
   * Get cookie string for requests
   */
  getCookieString() {
    return Object.entries(this.cookies)
      .map(([name, value]) => `${name}=${value}`)
      .join('; ');
  }
  
  /**
   * Get authenticated request headers
   */
  getHeaders() {
    return this.headers;
  }
  
  /**
   * Make authenticated API request
   */
  apiRequest(method, endpoint, body = null, additionalHeaders = {}) {
    const url = `${this.env.baseUrl}${endpoint}`;
    const headers = {
      ...this.getHeaders(),
      ...additionalHeaders
    };
    
    let response;
    switch (method.toUpperCase()) {
      case 'GET':
        response = http.get(url, { headers });
        break;
      case 'POST':
        response = http.post(url, body, { headers });
        break;
      case 'PUT':
        response = http.put(url, body, { headers });
        break;
      case 'DELETE':
        response = http.del(url, body, { headers });
        break;
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
    
    return response;
  }
  
  /**
   * Logout and cleanup session
   */
  logout() {
    if (this.sessionId) {
      const response = http.post(`${this.env.webUrl}/api/auth/session/logout`, null, {
        headers: this.getHeaders()
      });
      
      check(response, {
        'Demo logout successful': (r) => r.status === 200
      });
      
      this.sessionId = null;
      this.cookies = {};
      this.headers = {};
    }
  }
}

/**
 * AAD authentication session (simulated)
 * For load testing, we'll simulate AAD flows without actual Azure AD interaction
 */
export class AADAuthSession {
  constructor(userEmail = 'user@example.com', tenantId = null) {
    this.userEmail = userEmail;
    this.tenantId = tenantId;
    this.accessToken = null;
    this.headers = {};
    this.env = getCurrentEnvironment();
  }
  
  /**
   * Simulate AAD authentication
   * In real AAD scenarios, this would involve OAuth2 flows
   */
  login() {
    return group('AAD Authentication', () => {
      // Check if AAD mode is enabled
      const authModeResponse = http.get(`${this.env.webUrl}/api/auth/mode`);
      const authModeCheck = check(authModeResponse, {
        'Auth mode endpoint accessible': (r) => r.status === 200,
        'Auth mode is AAD': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.mode === 'aad';
          } catch {
            return false;
          }
        }
      });
      
      if (!authModeCheck) {
        console.warn('AAD auth mode not available - this is expected in demo environments');
        return false;
      }
      
      // Simulate AAD token (in real scenarios, this would be obtained from Azure AD)
      this.accessToken = this.generateMockAADToken();
      
      // Set authentication headers
      this.headers = {
        'Authorization': `Bearer ${this.accessToken}`,
        'X-User-Email': this.userEmail
      };
      
      if (this.tenantId) {
        this.headers['X-Tenant-ID'] = this.tenantId;
      }
      
      return true;
    });
  }
  
  /**
   * Generate mock AAD token for testing purposes
   * Note: This is only for load testing simulation
   */
  generateMockAADToken() {
    // Create a simple mock JWT-like token
    const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({
      sub: this.userEmail,
      aud: 'ai-cyber-maturity-assessment',
      iss: 'https://sts.windows.net/mock-tenant/',
      exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour expiry
      iat: Math.floor(Date.now() / 1000),
      email: this.userEmail,
      tid: this.tenantId || 'mock-tenant-id'
    }));
    const signature = 'mock-signature-for-load-testing';
    
    return `${header}.${payload}.${signature}`;
  }
  
  /**
   * Get authenticated request headers
   */
  getHeaders() {
    return this.headers;
  }
  
  /**
   * Make authenticated API request
   */
  apiRequest(method, endpoint, body = null, additionalHeaders = {}) {
    const url = `${this.env.baseUrl}${endpoint}`;
    const headers = {
      ...this.getHeaders(),
      ...additionalHeaders
    };
    
    let response;
    switch (method.toUpperCase()) {
      case 'GET':
        response = http.get(url, { headers });
        break;
      case 'POST':
        response = http.post(url, body, { headers });
        break;
      case 'PUT':
        response = http.put(url, body, { headers });
        break;
      case 'DELETE':
        response = http.del(url, body, { headers });
        break;
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
    
    return response;
  }
  
  /**
   * Logout (AAD logout would typically involve token revocation)
   */
  logout() {
    this.accessToken = null;
    this.headers = {};
  }
}

/**
 * Authentication factory
 * Creates the appropriate auth session based on environment
 */
export function createAuthSession(userEmail = 'user@example.com', options = {}) {
  const env = getCurrentEnvironment();
  
  if (env.authMode === 'demo') {
    return new DemoAuthSession(userEmail);
  } else if (env.authMode === 'aad') {
    return new AADAuthSession(userEmail, options.tenantId);
  } else {
    throw new Error(`Unsupported auth mode: ${env.authMode}`);
  }
}

/**
 * Test authentication flow
 * Utility function to test authentication in isolation
 */
export function testAuthFlow(userEmail = 'user@example.com') {
  const authSession = createAuthSession(userEmail);
  
  return group('Authentication Flow Test', () => {
    const loginSuccess = authSession.login();
    
    if (loginSuccess) {
      // Test authenticated request
      const testResponse = authSession.apiRequest('GET', '/version');
      const testCheck = check(testResponse, {
        'Authenticated request successful': (r) => r.status === 200,
        'Version endpoint accessible with auth': (r) => r.body.includes('app_name')
      });
      
      // Cleanup
      authSession.logout();
      
      return testCheck;
    }
    
    return false;
  });
}

/**
 * Get random test user
 */
export function getRandomTestUser() {
  const testUsers = [
    'user1@example.com',
    'user2@example.com',
    'analyst@example.com',
    'admin@example.com',
    'test.user@example.com',
    'load.test@example.com'
  ];
  
  return testUsers[Math.floor(Math.random() * testUsers.length)];
}

/**
 * Performance test authentication
 * Tests authentication performance under load
 */
export function benchmarkAuth(iterations = 10) {
  const results = {
    successful: 0,
    failed: 0,
    totalTime: 0,
    minTime: Infinity,
    maxTime: 0
  };
  
  for (let i = 0; i < iterations; i++) {
    const startTime = Date.now();
    const authSession = createAuthSession(getRandomTestUser());
    
    const success = authSession.login();
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    results.totalTime += duration;
    results.minTime = Math.min(results.minTime, duration);
    results.maxTime = Math.max(results.maxTime, duration);
    
    if (success) {
      results.successful++;
      authSession.logout();
    } else {
      results.failed++;
    }
  }
  
  results.avgTime = results.totalTime / iterations;
  results.successRate = results.successful / iterations;
  
  return results;
}

export default {
  DemoAuthSession,
  AADAuthSession,
  createAuthSession,
  testAuthFlow,
  getRandomTestUser,
  benchmarkAuth
};
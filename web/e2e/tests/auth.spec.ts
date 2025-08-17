import { test, expect } from '@playwright/test';

/**
 * AAD Authentication E2E Tests
 * Tests authentication flows, session management, and authorization
 */

test.describe('Authentication Flow', () => {
  test('authentication mode detection', async ({ page }) => {
    await test.step('Check authentication configuration', async () => {
      const response = await page.goto('/api/auth/mode');
      expect(response?.status()).toBe(200);
      
      const authMode = await page.textContent('body');
      expect(authMode).toBeTruthy();
      
      console.log(`Authentication mode: ${authMode}`);
    });
  });

  test('signin page behavior', async ({ page }) => {
    await test.step('Navigate to signin page', async () => {
      await page.goto('/signin');
      await page.waitForLoadState('networkidle');
    });

    await test.step('Verify signin options', async () => {
      // Check for AAD signin button or demo mode
      const hasAADSignin = await page.locator('button:has-text("Microsoft"), button:has-text("Azure"), a[href*="microsoft"]').isVisible();
      const hasDemoMode = await page.locator('button:has-text("Demo"), text=/demo mode/i').isVisible();
      
      expect(hasAADSignin || hasDemoMode).toBeTruthy();
      
      if (hasAADSignin) {
        console.log('AAD authentication available');
      } else if (hasDemoMode) {
        console.log('Demo mode authentication available');
      }
    });
  });

  test('unauthorized access protection', async ({ page }) => {
    await test.step('Attempt to access protected routes', async () => {
      const protectedRoutes = [
        '/engagements',
        '/admin/ops',
        '/admin/presets'
      ];

      for (const route of protectedRoutes) {
        const response = await page.goto(route);
        
        // Should redirect to signin or show auth required
        if (response && response.status() === 200) {
          // If page loads, check if it shows auth requirement
          const requiresAuth = await page.locator('text=/sign in|login|authenticate/i').isVisible();
          const isSigninPage = page.url().includes('/signin');
          
          expect(requiresAuth || isSigninPage).toBeTruthy();
        } else {
          // Redirect or error is also acceptable
          expect(response?.status()).not.toBe(404);
        }
      }
    });
  });

  test('session management', async ({ page }) => {
    await test.step('Check session endpoint', async () => {
      const response = await page.goto('/api/auth/session');
      
      // Should return session info (empty for unauthenticated)
      expect(response?.status()).toBe(200);
      
      const sessionData = await page.textContent('body');
      expect(sessionData).toBeTruthy();
    });
  });
});

test.describe('AAD Integration', () => {
  test.skip(({ }, testInfo) => {
    const hasAADConfig = process.env.AAD_CLIENT_ID && process.env.AAD_TENANT_ID;
    if (!hasAADConfig) {
      testInfo.annotations.push({ type: 'condition', description: 'AAD not configured' });
    }
    return !hasAADConfig;
  });

  test('AAD signin flow initiation', async ({ page }) => {
    await test.step('Navigate to AAD signin', async () => {
      await page.goto('/signin');
      
      const aadSigninButton = page.locator('button:has-text("Microsoft"), button:has-text("Azure"), a[href*="microsoft"]').first();
      
      if (await aadSigninButton.isVisible()) {
        // Click AAD signin button
        await aadSigninButton.click();
        
        // Should redirect to Microsoft login
        await page.waitForURL('**/login.microsoftonline.com/**', { timeout: 10000 });
        
        expect(page.url()).toContain('login.microsoftonline.com');
        console.log('Successfully redirected to AAD login');
      } else {
        test.skip('AAD signin not available');
      }
    });
  });

  test('AAD callback handling', async ({ page }) => {
    await test.step('Test AAD callback endpoint', async () => {
      // Test that the callback endpoint exists
      const response = await page.goto('/api/auth/callback/azure-ad');
      
      // Should handle callback (might return error without proper parameters)
      expect(response?.status()).toBeLessThan(500);
    });
  });

  test('AAD logout flow', async ({ page }) => {
    await test.step('Test logout endpoint', async () => {
      const response = await page.goto('/api/auth/signout');
      
      // Should handle signout request
      expect(response?.status()).toBeLessThan(500);
    });
  });
});

test.describe('Authorization Scenarios', () => {
  test('admin route protection', async ({ page }) => {
    await test.step('Test admin route access', async () => {
      const response = await page.goto('/admin/ops');
      
      // Should require authentication
      if (response && response.status() === 200) {
        // Check if content shows auth requirement
        const requiresAuth = await page.locator('text=/unauthorized|access denied|sign in/i').isVisible();
        const isSigninRedirect = page.url().includes('/signin');
        
        expect(requiresAuth || isSigninRedirect).toBeTruthy();
      }
    });
  });

  test('user route access', async ({ page }) => {
    await test.step('Test user route behavior', async () => {
      const userRoutes = [
        '/engagements',
        '/assessment/draft'
      ];

      for (const route of userRoutes) {
        const response = await page.goto(route);
        
        // Should either require auth or redirect to signin
        if (response && response.status() === 200) {
          const requiresAuth = await page.locator('text=/sign in|login/i').isVisible();
          const isSigninRedirect = page.url().includes('/signin');
          
          expect(requiresAuth || isSigninRedirect).toBeTruthy();
        }
      }
    });
  });
});

test.describe('Demo Mode Authentication', () => {
  test('demo mode signin', async ({ page }) => {
    await test.step('Navigate to signin and check for demo mode', async () => {
      await page.goto('/signin');
      
      const demoButton = page.locator('button:has-text("Demo"), button:has-text("Continue"), [data-testid="demo-signin"]');
      
      if (await demoButton.first().isVisible()) {
        await demoButton.first().click();
        
        // Should redirect to main application
        await page.waitForURL('**/', { timeout: 5000 });
        
        expect(page.url()).not.toContain('/signin');
        console.log('Demo mode signin successful');
      } else {
        console.log('Demo mode not available');
      }
    });
  });

  test('demo session behavior', async ({ page }) => {
    await test.step('Test demo session', async () => {
      await page.goto('/signin');
      
      const demoButton = page.locator('button:has-text("Demo"), button:has-text("Continue")');
      
      if (await demoButton.first().isVisible()) {
        await demoButton.first().click();
        await page.waitForURL('**/', { timeout: 5000 });
        
        // Test that protected routes are now accessible
        const response = await page.goto('/engagements');
        expect(response?.status()).toBe(200);
        
        // Should not require additional authentication
        const hasContent = await page.locator('main, [role="main"], .content').isVisible();
        expect(hasContent).toBeTruthy();
      }
    });
  });
});

test.describe('Security Headers', () => {
  test('security headers are present', async ({ page }) => {
    await test.step('Check for security headers', async () => {
      const response = await page.goto('/');
      
      if (response) {
        const headers = response.headers();
        
        // Check for important security headers
        const securityHeaders = [
          'x-frame-options',
          'x-content-type-options',
          'referrer-policy'
        ];
        
        securityHeaders.forEach(header => {
          if (headers[header]) {
            console.log(`✅ ${header}: ${headers[header]}`);
          } else {
            console.warn(`⚠️  Missing security header: ${header}`);
          }
        });
        
        // At least some security headers should be present
        const hasSecurityHeaders = securityHeaders.some(header => headers[header]);
        expect(hasSecurityHeaders).toBeTruthy();
      }
    });
  });

  test('authentication API security', async ({ page }) => {
    await test.step('Test auth API security', async () => {
      // Test that auth endpoints handle invalid requests properly
      const authEndpoints = [
        '/api/auth/session',
        '/api/auth/mode'
      ];

      for (const endpoint of authEndpoints) {
        const response = await page.goto(endpoint);
        
        // Should not expose sensitive information
        expect(response?.status()).toBeLessThan(500);
        
        if (response && response.status() === 200) {
          const content = await page.textContent('body');
          
          // Should not contain sensitive data
          expect(content).not.toMatch(/password|secret|key|token/i);
        }
      }
    });
  });
});

test.describe('Error Handling', () => {
  test('authentication errors are handled gracefully', async ({ page }) => {
    await test.step('Test invalid authentication state', async () => {
      // Clear any existing session
      await page.context().clearCookies();
      
      // Try to access protected content
      await page.goto('/engagements');
      
      // Should show appropriate error or redirect
      const hasErrorMessage = await page.locator('text=/error|unauthorized|access denied/i').isVisible();
      const isRedirected = page.url().includes('/signin');
      
      expect(hasErrorMessage || isRedirected).toBeTruthy();
    });
  });

  test('network errors in auth flow', async ({ page }) => {
    await test.step('Test auth with network issues', async () => {
      // Block auth-related requests
      await page.route('**/api/auth/**', route => route.abort());
      
      await page.goto('/signin');
      
      // Should handle network errors gracefully
      await page.waitForTimeout(2000);
      
      const hasErrorHandling = await page.locator('text=/error|failed|try again/i').isVisible();
      expect(hasErrorHandling).toBeTruthy();
    });
  });
});
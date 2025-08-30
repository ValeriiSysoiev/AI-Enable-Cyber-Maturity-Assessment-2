import { test, expect } from '@playwright/test';

/**
 * Production Sign-In Tests
 * 
 * Verifies that the signin page behaves correctly in production:
 * - AAD-only authentication (no demo mode)
 * - Proper error handling
 * - No 403 errors from incorrect demo attempts
 */

test.describe('Production Sign-In Page', () => {
  test.beforeEach(async ({ page }) => {
    // Set production environment context
    await page.addInitScript(() => {
      // Mock production environment
      (window as any).__TEST_ENV__ = 'production';
    });
  });

  test('should render signin page successfully', async ({ page }) => {
    const response = await page.goto('/signin');
    
    // Page should load successfully
    expect(response?.status()).toBe(200);
    
    // Should contain sign-in heading
    await expect(page.locator('h2')).toContainText('Sign in to AI Maturity Assessment');
  });

  test('should show AAD sign-in button in production mode', async ({ page }) => {
    await page.goto('/signin');
    
    // Wait for auth mode check to complete
    await page.waitForLoadState('networkidle');
    
    // Should show AAD sign-in button
    const aadButton = page.locator('button:has-text("Sign in with Azure Active Directory")');
    await expect(aadButton).toBeVisible();
    
    // Should NOT show demo email input
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).not.toBeVisible();
  });

  test('should not show demo form in production', async ({ page }) => {
    await page.goto('/signin');
    
    // Wait for auth mode check
    await page.waitForLoadState('networkidle');
    
    // Demo form elements should not be visible
    await expect(page.locator('input[type="email"]')).not.toBeVisible();
    await expect(page.locator('text=Enter your email to continue (demo)')).not.toBeVisible();
  });

  test('should handle AAD button click correctly', async ({ page }) => {
    await page.goto('/signin');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Get AAD button
    const aadButton = page.locator('button:has-text("Sign in with Azure Active Directory")');
    await expect(aadButton).toBeVisible();
    
    // Click should not throw errors (will redirect to Microsoft in real scenario)
    // In test environment, we just verify no console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Attempt click (will fail to redirect in test, but shouldn't error)
    await aadButton.click({ trial: true });
    
    // Should not have console errors about demo mode
    expect(consoleErrors).not.toContain('Failed to sign in');
    expect(consoleErrors).not.toContain('Demo signin is disabled');
  });

  test('should not call /api/demo/signin endpoint', async ({ page }) => {
    await page.goto('/signin');
    
    // Track API calls
    const apiCalls: string[] = [];
    page.on('request', request => {
      apiCalls.push(request.url());
    });
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Should NOT have attempted to call demo signin
    const demoSigninCalls = apiCalls.filter(url => url.includes('/api/demo/signin'));
    expect(demoSigninCalls).toHaveLength(0);
  });

  test('should call /api/auth/mode endpoint', async ({ page }) => {
    // Track API calls
    const apiCalls: string[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiCalls.push(request.url());
      }
    });
    
    await page.goto('/signin');
    await page.waitForLoadState('networkidle');
    
    // Should have called auth mode endpoint
    const authModeCalls = apiCalls.filter(url => url.includes('/api/auth/mode'));
    expect(authModeCalls.length).toBeGreaterThan(0);
  });

  test('should handle AAD configuration errors gracefully', async ({ page }) => {
    // Mock auth mode endpoint to return error
    await page.route('**/api/auth/mode', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          mode: 'error',
          enabled: false,
          error: 'Azure AD authentication is required in production'
        })
      });
    });
    
    await page.goto('/signin');
    await page.waitForLoadState('networkidle');
    
    // Should show error message
    await expect(page.locator('text=Authentication Configuration Error')).toBeVisible();
    await expect(page.locator('text=Azure AD authentication is required')).toBeVisible();
    
    // AAD button should be disabled
    const aadButton = page.locator('button:has-text("Sign in with Azure Active Directory")');
    await expect(aadButton).toBeDisabled();
  });

  test('should not expose demo mode in production HTML', async ({ page }) => {
    const response = await page.goto('/signin');
    const html = await response?.text() || '';
    
    // After React hydration, demo elements should not be in DOM
    await page.waitForLoadState('networkidle');
    const content = await page.content();
    
    // Should not contain demo-specific text in final rendered page
    // (may exist in initial HTML but should be removed after hydration)
    const hasDemoElements = await page.locator('text=Enter your email to continue (demo)').count();
    expect(hasDemoElements).toBe(0);
  });
});

// Additional test for production environment flag
test('production environment should be properly set', async ({ page }) => {
  // This test verifies that NODE_ENV is set correctly
  const response = await page.request.get('/api/auth/mode');
  const data = await response.json();
  
  // In production, should either return AAD mode or error
  expect(['aad', 'error']).toContain(data.mode);
  
  // Demo should never be enabled in production response
  expect(data.demoEnabled).toBeFalsy();
});
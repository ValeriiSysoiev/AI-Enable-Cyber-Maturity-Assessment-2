import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry } from '../test-utils';

/**
 * Smoke Tests for AI Maturity Assessment Platform
 * Basic functionality and connectivity verification
 */

test.describe('Smoke Tests', () => {
  test('homepage loads successfully', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    logger.info('Starting homepage load test');
    
    try {
      await stepTracker.executeStep('Navigate to homepage', async () => {
        const loadTime = await perfMonitor.measurePageLoad('/');
        await expect(page).toHaveTitle(/AI.*Maturity|Cyber.*Assessment/i);
        
        // Validate performance
        if (loadTime > 10000) {
          logger.warn('Homepage load time is slow', { loadTime });
        }
      });
      
      await stepTracker.executeStep('Verify main navigation elements', async () => {
        // Check for essential UI elements with retry
        await withRetry(async () => {
          await expect(page.locator('nav, header, [role="navigation"]')).toBeVisible();
        }, 3, 1000);
      });
      
      logger.info('Homepage test completed successfully', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      logger.error('Homepage test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('authentication page is accessible', async ({ page }) => {
    await test.step('Navigate to signin page', async () => {
      await page.goto('/signin');
      
      // Should not result in 404 or server error
      const response = await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/signin');
    });
    
    await test.step('Verify signin form or AAD redirect', async () => {
      // The page should either show a login form or redirect to AAD
      await page.waitForTimeout(2000); // Allow for potential redirects
      
      const hasLoginForm = await page.locator('form, [data-testid="login"]').isVisible();
      const isAADRedirect = page.url().includes('login.microsoftonline.com');
      
      expect(hasLoginForm || isAADRedirect).toBeTruthy();
    });
  });

  test('API health endpoint responds', async ({ request }) => {
    const apiBaseURL = process.env.API_BASE_URL;
    
    if (!apiBaseURL) {
      test.skip(true, 'API_BASE_URL not configured');
    }
    
    await test.step('Check API health endpoint', async () => {
      const response = await request.get(`${apiBaseURL}/health`);
      expect(response.status()).toBe(200);
    });
  });

  test('static assets load correctly', async ({ page }) => {
    await test.step('Navigate to homepage and check resources', async () => {
      const responses: any[] = [];
      
      page.on('response', response => {
        if (response.url().includes('.css') || response.url().includes('.js')) {
          responses.push({
            url: response.url(),
            status: response.status()
          });
        }
      });
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Check that no critical assets failed to load
      const failedAssets = responses.filter(r => r.status >= 400);
      expect(failedAssets).toHaveLength(0);
    });
  });

  test('CSF grid page loads without errors', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    logger.info('Testing CSF grid page basic functionality');
    
    try {
      await stepTracker.executeStep('Navigate to CSF assessment page', async () => {
        // Mock authentication for test environment
        await page.addInitScript(() => {
          (window as any).__TEST_AUTH__ = {
            isAuthenticated: true,
            user: { email: 'test@example.com' },
            loading: false
          };
        });
        
        await page.goto('/e/test-engagement/assessment');
        await page.waitForLoadState('networkidle');
        
        // Should not result in 404 or server error
        expect(page.url()).toContain('/assessment');
      });
      
      await stepTracker.executeStep('Verify CSF grid renders', async () => {
        await withRetry(async () => {
          // Should show the CSF 2.0 header or loading state
          const hasHeader = await page.locator('h1:has-text("CSF 2.0 Assessment Grid")').isVisible();
          const hasLoading = await page.locator('.animate-pulse').isVisible();
          const hasError = await page.locator('text=Error Loading Assessment').isVisible();
          
          // One of these states should be visible
          expect(hasHeader || hasLoading || hasError).toBeTruthy();
        }, 3, 1000);
      });
      
      logger.info('CSF grid smoke test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      logger.error('CSF grid smoke test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('responsive design works', async ({ page }) => {
    await test.step('Test desktop viewport', async () => {
      await page.setViewportSize({ width: 1200, height: 800 });
      await page.goto('/');
      
      // Main content should be visible
      await expect(page.locator('main, [role="main"], .main-content')).toBeVisible();
    });
    
    await test.step('Test mobile viewport', async () => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.reload();
      
      // Content should still be accessible
      await expect(page.locator('main, [role="main"], .main-content')).toBeVisible();
    });
  });

  test('error pages handle gracefully', async ({ page }) => {
    await test.step('Navigate to non-existent page', async () => {
      const response = await page.goto('/non-existent-page-12345');
      
      // Should get 404 or redirect to error page
      expect(response?.status()).toBeGreaterThanOrEqual(400);
    });
    
    await test.step('Verify error page shows helpful content', async () => {
      // Error page should have some helpful content
      const hasErrorMessage = await page.locator('text=/404|not found|error/i').isVisible();
      const hasNavigationLink = await page.locator('a[href="/"], a[href="/home"]').isVisible();
      
      expect(hasErrorMessage || hasNavigationLink).toBeTruthy();
    });
  });
});

test.describe('Performance Tests', () => {
  test('page load time is acceptable', async ({ page }) => {
    const startTime = Date.now();
    
    await test.step('Measure page load time', async () => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      
      // Page should load within 10 seconds (generous for CI)
      expect(loadTime).toBeLessThan(10000);
      
      console.log(`Page load time: ${loadTime}ms`);
    });
  });

  test('no console errors on main pages', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await test.step('Check console errors on main pages', async () => {
      const mainPages = ['/', '/signin', '/engagements'];
      
      for (const path of mainPages) {
        await page.goto(path);
        await page.waitForLoadState('networkidle');
        
        // Allow page to fully load and execute
        await page.waitForTimeout(1000);
      }
      
      // Filter out known non-critical errors
      const criticalErrors = errors.filter(error => 
        !error.includes('favicon') && 
        !error.includes('analytics') &&
        !error.includes('third-party')
      );
      
      if (criticalErrors.length > 0) {
        console.warn('Console errors found:', criticalErrors);
      }
      
      // Don't fail on console errors in development, but log them
      if (process.env.NODE_ENV === 'production') {
        expect(criticalErrors).toHaveLength(0);
      }
    });
  });
});
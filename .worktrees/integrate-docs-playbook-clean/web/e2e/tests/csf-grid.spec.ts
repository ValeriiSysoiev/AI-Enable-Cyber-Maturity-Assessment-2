import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry } from '../test-utils';

/**
 * CSF 2.0 Grid Assessment Tests
 * 
 * Comprehensive e2e tests for CSF grid functionality including:
 * - Grid rendering and performance
 * - Function collapsing/expanding
 * - Subcategory selection and details panel
 * - Responsive design validation
 * - Error handling and loading states
 */

test.describe('CSF 2.0 Grid Assessment', () => {
  const engagementId = 'test-engagement-123';
  const assessmentUrl = `/e/${engagementId}/assessment`;

  test.beforeEach(async ({ page }) => {
    // Mock authentication for test environment
    await page.addInitScript(() => {
      (window as any).__TEST_AUTH__ = {
        isAuthenticated: true,
        user: { email: 'test@example.com' },
        loading: false
      };
    });
  });

  test('CSF grid renders correctly with all functions', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    logger.info('Starting CSF grid render test');
    
    try {
      await stepTracker.executeStep('Navigate to assessment page', async () => {
        const loadTime = await perfMonitor.measurePageLoad(assessmentUrl);
        
        // Verify page loads within performance target (p95 < 2s)
        if (loadTime > 2000) {
          logger.warn('Assessment page load time exceeds target', { loadTime, target: 2000 });
        }
      });

      await stepTracker.executeStep('Verify CSF grid header and stats', async () => {
        await withRetry(async () => {
          await expect(page.locator('h1')).toContainText('CSF 2.0 Assessment Grid');
          await expect(page.locator('text=Engagement:')).toBeVisible();
          
          // Check stats display (functions, categories, subcategories counts)
          await expect(page.locator('text=Functions')).toBeVisible();
          await expect(page.locator('text=Categories')).toBeVisible(); 
          await expect(page.locator('text=Subcategories')).toBeVisible();
        }, 3, 1000);
      });

      await stepTracker.executeStep('Verify CSF functions are present', async () => {
        // Standard CSF 2.0 functions: GV, ID, PR, DE, RS, RC
        const expectedFunctions = ['GV', 'ID', 'PR', 'DE', 'RS', 'RC'];
        
        for (const functionId of expectedFunctions) {
          await withRetry(async () => {
            await expect(page.locator(`text=${functionId} -`)).toBeVisible();
          }, 3, 500);
        }
      });

      await stepTracker.executeStep('Verify initial collapsed state', async () => {
        // Functions should start collapsed
        const expandButtons = page.locator('button:has-text("+")');
        const expandButtonCount = await expandButtons.count();
        expect(expandButtonCount).toBeGreaterThan(0);
      });
      
      logger.info('CSF grid render test completed successfully', stepTracker.getStepsSummary());
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('function expansion and collapse functionality', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    logger.info('Testing function expand/collapse functionality');
    
    try {
      await page.goto(assessmentUrl);
      await page.waitForLoadState('networkidle');

      await stepTracker.executeStep('Expand first function', async () => {
        const firstFunction = page.locator('button').filter({ hasText: '+' }).first();
        await firstFunction.click();
        
        // Verify expansion
        await expect(firstFunction).toContainText('−');
        
        // Categories should be visible after expansion
        await expect(page.locator('div:has-text("Categories") >> div.border')).toBeVisible();
      });

      await stepTracker.executeStep('Collapse function', async () => {
        const expandedFunction = page.locator('button').filter({ hasText: '−' }).first();
        await expandedFunction.click();
        
        // Verify collapse
        await expect(expandedFunction).toContainText('+');
      });

      await stepTracker.executeStep('Expand multiple functions', async () => {
        const functionButtons = page.locator('button').filter({ hasText: '+' });
        const count = Math.min(await functionButtons.count(), 3); // Test up to 3 functions
        
        for (let i = 0; i < count; i++) {
          await functionButtons.nth(i).click();
          await expect(functionButtons.nth(i)).toContainText('−');
        }
      });
      
      logger.info('Function expand/collapse test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('subcategory selection and details panel', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    logger.info('Testing subcategory selection and details panel');
    
    try {
      await page.goto(assessmentUrl);
      await page.waitForLoadState('networkidle');

      await stepTracker.executeStep('Verify initial details panel state', async () => {
        await withRetry(async () => {
          await expect(page.locator('text=Select a Subcategory')).toBeVisible();
          await expect(page.locator('text=Click on any subcategory')).toBeVisible();
        }, 3, 1000);
      });

      await stepTracker.executeStep('Expand function and select subcategory', async () => {
        // Expand first function
        await page.locator('button').filter({ hasText: '+' }).first().click();
        
        // Wait for categories to appear
        await page.waitForTimeout(500);
        
        // Click on first available subcategory
        const firstSubcategory = page.locator('button').filter({ hasText: /^[A-Z]{2}\.[A-Z]{2}-\d+/ }).first();
        await expect(firstSubcategory).toBeVisible();
        await firstSubcategory.click();
      });

      await stepTracker.executeStep('Verify details panel content', async () => {
        await withRetry(async () => {
          // Details panel should show subcategory information
          await expect(page.locator('text=Assessment Score')).toBeVisible();
          await expect(page.locator('text=Rationale')).toBeVisible();
          await expect(page.locator('text=Evidence')).toBeVisible();
          
          // Placeholder content should be visible
          await expect(page.locator('text=Score: Not Assessed')).toBeVisible();
          await expect(page.locator('text=No rationale provided')).toBeVisible();
          await expect(page.locator('text=No evidence uploaded')).toBeVisible();
        }, 3, 1000);
      });

      await stepTracker.executeStep('Verify subcategory selection highlighting', async () => {
        // Selected subcategory should have highlighting
        const selectedSubcategory = page.locator('button.bg-blue-100');
        await expect(selectedSubcategory).toBeVisible();
      });
      
      logger.info('Subcategory selection test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('responsive design validation', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    logger.info('Testing responsive design');
    
    try {
      await page.goto(assessmentUrl);
      await page.waitForLoadState('networkidle');

      await stepTracker.executeStep('Test desktop layout', async () => {
        await page.setViewportSize({ width: 1200, height: 800 });
        await page.waitForTimeout(300);
        
        // Grid should be side-by-side on desktop
        const gridLayout = page.locator('.lg\\:col-span-2'); // CSF grid
        const detailsLayout = page.locator('.lg\\:col-span-1'); // Details panel
        
        await expect(gridLayout).toBeVisible();
        await expect(detailsLayout).toBeVisible();
      });

      await stepTracker.executeStep('Test tablet layout', async () => {
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.waitForTimeout(300);
        
        // Layout should still be functional
        await expect(page.locator('h1:has-text("CSF 2.0 Assessment Grid")')).toBeVisible();
      });

      await stepTracker.executeStep('Test mobile layout', async () => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.waitForTimeout(300);
        
        // Should be stacked vertically on mobile
        await expect(page.locator('h1:has-text("CSF 2.0 Assessment Grid")')).toBeVisible();
        
        // Functions should still be clickable
        const firstFunction = page.locator('button').filter({ hasText: '+' }).first();
        await expect(firstFunction).toBeVisible();
      });
      
      logger.info('Responsive design test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('error handling and loading states', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    logger.info('Testing error handling and loading states');
    
    try {
      await stepTracker.executeStep('Test loading state', async () => {
        // Intercept CSF API request to delay it
        await page.route('/api/proxy/api/v1/csf/functions', route => {
          setTimeout(() => route.continue(), 1000); // 1s delay
        });
        
        await page.goto(assessmentUrl);
        
        // Should show loading state
        await withRetry(async () => {
          const loadingElements = page.locator('.animate-pulse');
          const loadingCount = await loadingElements.count();
          expect(loadingCount).toBeGreaterThan(0);
        }, 3, 100);
      });

      await stepTracker.executeStep('Test error state', async () => {
        // Mock API failure
        await page.route('/api/proxy/api/v1/csf/functions', route => {
          route.fulfill({
            status: 500,
            body: JSON.stringify({ error: 'Server error' })
          });
        });
        
        await page.goto(assessmentUrl);
        await page.waitForTimeout(2000);
        
        // Should show error state
        await withRetry(async () => {
          await expect(page.locator('text=Error Loading Assessment')).toBeVisible();
          await expect(page.locator('button:has-text("Retry")')).toBeVisible();
        }, 3, 500);
      });
      
      logger.info('Error handling test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('performance and memoization validation', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    logger.info('Testing performance and memoization');
    
    try {
      await stepTracker.executeStep('Measure initial page load', async () => {
        const loadTime = await perfMonitor.measurePageLoad(assessmentUrl);
        logger.info('Initial load time', { loadTime });
        
        // Should meet p95 < 2s target
        if (loadTime > 2000) {
          logger.warn('Initial load exceeds 2s target', { loadTime });
        }
      });

      await stepTracker.executeStep('Test client-side navigation performance', async () => {
        // Expand multiple functions and measure interaction time
        const startTime = Date.now();
        
        const functionButtons = page.locator('button').filter({ hasText: '+' });
        const buttonCount = Math.min(await functionButtons.count(), 3);
        
        for (let i = 0; i < buttonCount; i++) {
          await functionButtons.nth(i).click();
          await page.waitForTimeout(100); // Small delay between clicks
        }
        
        const interactionTime = Date.now() - startTime;
        logger.info('Function expansion interaction time', { interactionTime });
        
        // Interactions should be fast
        expect(interactionTime).toBeLessThan(3000);
      });
      
      logger.info('Performance test completed successfully');
      
    } catch (error) {
      const errorRecovery = new ErrorRecovery(logger, page);
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });
});
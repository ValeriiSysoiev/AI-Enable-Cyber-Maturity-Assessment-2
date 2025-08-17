import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry } from '../test-utils';

/**
 * AAD Groups Authentication Tests
 * Tests enterprise AAD group-based authentication, role assignment, and tenant isolation
 */

test.describe('AAD Groups Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Set up AAD group environment
    await page.addInitScript(() => {
      // Mock AAD group claims for testing
      window.mockAADClaims = {
        groups: ['admin-group-id', 'lead-group-id'],
        tid: 'test-tenant-id',
        oid: 'test-user-object-id',
        preferred_username: 'test@company.com'
      };
    });
  });

  test('AAD group-based role assignment', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Configure AAD group mappings', async () => {
        // Test admin group assignment
        await page.goto('/api/auth/diagnostics');
        
        const response = await page.waitForResponse(/\/api\/auth\/diagnostics/);
        expect(response.status()).toBe(200);
        
        const diagnosticsData = await response.json();
        logger.info('AAD diagnostics data retrieved', { diagnosticsData });
      });

      await stepTracker.executeStep('Verify admin role assignment from AAD groups', async () => {
        // Navigate to admin interface
        await page.goto('/admin/ops');
        
        // Should have access due to admin group membership
        await withRetry(async () => {
          const hasAdminAccess = await page.locator('[data-testid="admin-interface"], .admin-panel, h1:has-text("Admin")').isVisible();
          expect(hasAdminAccess).toBeTruthy();
        }, 3, 2000);
        
        logger.info('Admin access verified for AAD group member');
      });

      await stepTracker.executeStep('Test group sync and caching', async () => {
        // Test group information caching
        const startTime = Date.now();
        await page.goto('/api/auth/groups');
        const cacheTime = Date.now() - startTime;
        
        // Subsequent call should be faster (cached)
        const startTime2 = Date.now();
        await page.reload();
        const cachedTime = Date.now() - startTime2;
        
        expect(cachedTime).toBeLessThan(cacheTime);
        logger.info('Group cache performance verified', { cacheTime, cachedTime });
      });

      logger.info('AAD group-based authentication test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('tenant isolation validation', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Set up multi-tenant test scenario', async () => {
        // Mock different tenant ID
        await page.addInitScript(() => {
          window.mockAADClaims = {
            ...window.mockAADClaims,
            tid: 'different-tenant-id'
          };
        });
        
        await page.goto('/engagements');
      });

      await stepTracker.executeStep('Verify tenant isolation in data access', async () => {
        // Should not see engagements from other tenants
        const response = await page.waitForResponse(/\/api\/engagements/);
        
        if (response.status() === 200) {
          const engagements = await response.json();
          
          // All engagements should belong to current tenant
          engagements.forEach((engagement: any) => {
            expect(engagement.tenantId).toBe('different-tenant-id');
          });
          
          logger.info('Tenant isolation verified', { engagementCount: engagements.length });
        }
      });

      await stepTracker.executeStep('Test cross-tenant access prevention', async () => {
        // Try to access specific engagement from different tenant
        const crossTenantResponse = await page.goto('/api/engagements/cross-tenant-engagement-id');
        
        // Should return 403 or 404
        expect(crossTenantResponse?.status()).toBeGreaterThanOrEqual(400);
        logger.info('Cross-tenant access blocked successfully');
      });

    } catch (error) {
      logger.error('Tenant isolation test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('admin auth diagnostics interface', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access auth diagnostics page', async () => {
        await page.goto('/admin/auth-diagnostics');
        
        // Should load diagnostics interface
        await expect(page.locator('h1:has-text("Authentication Diagnostics"), [data-testid="auth-diagnostics"]')).toBeVisible();
      });

      await stepTracker.executeStep('Verify AAD token information display', async () => {
        // Should show current user's AAD information
        await expect(page.locator('text=Tenant ID')).toBeVisible();
        await expect(page.locator('text=Object ID')).toBeVisible();
        await expect(page.locator('text=Groups')).toBeVisible();
        
        // Check for group memberships display
        const groupsList = page.locator('[data-testid="user-groups"], .groups-list');
        await expect(groupsList).toBeVisible();
        
        logger.info('AAD token information displayed correctly');
      });

      await stepTracker.executeStep('Test group role mapping display', async () => {
        // Should show role mappings
        await expect(page.locator('text=Role Mappings, text=Group Roles')).toBeVisible();
        
        // Should show mapped roles
        const roleDisplay = page.locator('[data-testid="role-mappings"], .role-mappings');
        await expect(roleDisplay).toBeVisible();
        
        logger.info('Group role mappings displayed correctly');
      });

      await stepTracker.executeStep('Test diagnostics API access', async () => {
        // Test direct API access
        const response = await page.goto('/api/auth/diagnostics');
        expect(response?.status()).toBe(200);
        
        const diagnosticsData = await page.textContent('body');
        const parsedData = JSON.parse(diagnosticsData || '{}');
        
        expect(parsedData).toHaveProperty('user');
        expect(parsedData).toHaveProperty('groups');
        expect(parsedData).toHaveProperty('roles');
        
        logger.info('Diagnostics API working correctly', { dataKeys: Object.keys(parsedData) });
      });

    } catch (error) {
      logger.error('Auth diagnostics test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('AAD Feature Flag Behavior', () => {
  test('AAD enabled mode functionality', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Verify AAD signin option available', async () => {
        await page.goto('/signin');
        
        const aadSigninButton = page.locator('button:has-text("Microsoft"), button:has-text("Azure AD"), [data-testid="aad-signin"]');
        await expect(aadSigninButton).toBeVisible();
        
        logger.info('AAD signin option available when enabled');
      });

      await stepTracker.executeStep('Test AAD-specific routes', async () => {
        // AAD-specific endpoints should be available
        const aadRoutes = [
          '/api/auth/callback/azure-ad',
          '/api/auth/groups',
          '/api/auth/diagnostics'
        ];

        for (const route of aadRoutes) {
          const response = await page.goto(route);
          expect(response?.status()).toBeLessThan(500);
          logger.info(`AAD route accessible: ${route}`, { status: response?.status() });
        }
      });

      await stepTracker.executeStep('Verify group-based access controls', async () => {
        // Mock admin group membership
        await page.addInitScript(() => {
          window.mockAADClaims = {
            groups: ['admin-group-id'],
            tid: 'test-tenant-id'
          };
        });

        await page.goto('/admin/ops');
        
        // Should have admin access
        const hasAdminAccess = await page.locator('[data-testid="admin-interface"], .admin-panel').isVisible();
        expect(hasAdminAccess).toBeTruthy();
        
        logger.info('Group-based access control working');
      });

    } catch (error) {
      logger.error('AAD enabled mode test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('AAD disabled mode fallback', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Mock AAD disabled configuration', async () => {
        // Mock environment where AAD is disabled
        await page.addInitScript(() => {
          window.authConfig = {
            aadEnabled: false,
            demoMode: true
          };
        });

        await page.goto('/signin');
      });

      await stepTracker.executeStep('Verify demo mode fallback', async () => {
        // Should show demo mode option instead of AAD
        const demoSignin = page.locator('button:has-text("Demo"), button:has-text("Continue"), [data-testid="demo-signin"]');
        await expect(demoSignin).toBeVisible();
        
        // AAD options should not be visible
        const aadSignin = page.locator('button:has-text("Microsoft"), button:has-text("Azure")');
        await expect(aadSignin).not.toBeVisible();
        
        logger.info('Demo mode fallback working when AAD disabled');
      });

      await stepTracker.executeStep('Test demo mode authentication', async () => {
        const demoButton = page.locator('button:has-text("Demo"), button:has-text("Continue")').first();
        await demoButton.click();
        
        // Should redirect to main application
        await page.waitForURL('**/', { timeout: 5000 });
        expect(page.url()).not.toContain('/signin');
        
        logger.info('Demo mode authentication successful');
      });

      await stepTracker.executeStep('Verify role-based access without AAD groups', async () => {
        // Should use fallback role assignment
        await page.goto('/admin/ops');
        
        // Demo mode should have admin access or show appropriate message
        const hasAdminAccess = await page.locator('[data-testid="admin-interface"], .admin-panel').isVisible();
        const hasAccessMessage = await page.locator('text=/admin access|demo mode/i').isVisible();
        
        expect(hasAdminAccess || hasAccessMessage).toBeTruthy();
        logger.info('Role-based access working in demo mode');
      });

    } catch (error) {
      logger.error('AAD disabled mode test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('AAD Group Sync and Caching', () => {
  test('group synchronization functionality', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await test.step('Test initial group sync', async () => {
        const syncTime = await perfMonitor.measureAction('group_sync', async () => {
          await page.goto('/api/auth/sync-groups');
        });
        
        expect(syncTime).toBeLessThan(5000);
        logger.info('Group sync completed within performance threshold');
      });

      await test.step('Verify group cache behavior', async () => {
        // First call - should populate cache
        const firstCall = await perfMonitor.measureAction('first_group_call', async () => {
          await page.goto('/api/auth/groups');
        });
        
        // Second call - should use cache
        const secondCall = await perfMonitor.measureAction('cached_group_call', async () => {
          await page.goto('/api/auth/groups');
        });
        
        expect(secondCall).toBeLessThan(firstCall);
        logger.info('Group caching working effectively', { firstCall, secondCall });
      });

      await test.step('Test cache invalidation', async () => {
        // Force cache invalidation
        await page.goto('/api/auth/invalidate-group-cache', { method: 'POST' });
        
        // Next call should be slower (cache miss)
        const postInvalidationTime = await perfMonitor.measureAction('post_invalidation_call', async () => {
          await page.goto('/api/auth/groups');
        });
        
        expect(postInvalidationTime).toBeGreaterThan(100);
        logger.info('Cache invalidation working correctly');
      });

    } catch (error) {
      logger.error('Group sync test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('concurrent group access handling', async ({ browser }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    try {
      await test.step('Test concurrent group requests', async () => {
        // Create multiple browser contexts to simulate concurrent users
        const contexts = await Promise.all([
          browser.newContext(),
          browser.newContext(),
          browser.newContext()
        ]);

        const pages = await Promise.all(contexts.map(ctx => ctx.newPage()));
        
        // Simulate concurrent group access
        const promises = pages.map((page, index) => 
          page.goto(`/api/auth/groups?user=${index}`)
        );

        const responses = await Promise.all(promises);
        
        // All requests should succeed
        responses.forEach((response, index) => {
          expect(response?.status()).toBe(200);
          logger.info(`Concurrent request ${index} successful`);
        });

        // Cleanup
        await Promise.all(contexts.map(ctx => ctx.close()));
      });

    } catch (error) {
      logger.error('Concurrent access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('AAD Error Handling', () => {
  test('AAD service unavailable scenarios', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await test.step('Test AAD service timeout', async () => {
        // Mock AAD service timeout
        await page.route('**/login.microsoftonline.com/**', route => {
          setTimeout(() => route.abort(), 10000);
        });

        await page.goto('/signin');
        const aadButton = page.locator('button:has-text("Microsoft"), button:has-text("Azure")').first();
        
        if (await aadButton.isVisible()) {
          await aadButton.click();
          
          // Should handle timeout gracefully
          await page.waitForTimeout(3000);
          
          const hasErrorMessage = await page.locator('text=/error|timeout|unavailable/i').isVisible();
          expect(hasErrorMessage).toBeTruthy();
          
          logger.info('AAD timeout handled gracefully');
        }
      });

      await test.step('Test invalid AAD response', async () => {
        // Mock invalid AAD response
        await page.route('**/api/auth/callback/azure-ad**', route => {
          route.fulfill({
            status: 400,
            body: JSON.stringify({ error: 'invalid_request' })
          });
        });

        await page.goto('/api/auth/callback/azure-ad?code=invalid');
        
        // Should handle invalid response
        const hasErrorHandling = await page.locator('text=/error|invalid|failed/i').isVisible();
        expect(hasErrorHandling).toBeTruthy();
        
        logger.info('Invalid AAD response handled correctly');
      });

    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('group membership edge cases', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    try {
      await test.step('Test user with no group memberships', async () => {
        await page.addInitScript(() => {
          window.mockAADClaims = {
            groups: [],
            tid: 'test-tenant-id',
            oid: 'test-user-object-id'
          };
        });

        await page.goto('/engagements');
        
        // Should handle gracefully with default permissions
        const hasDefaultAccess = await page.locator('[data-testid="engagements-list"], .engagements').isVisible();
        expect(hasDefaultAccess).toBeTruthy();
        
        logger.info('User with no groups handled correctly');
      });

      await test.step('Test user with unrecognized groups', async () => {
        await page.addInitScript(() => {
          window.mockAADClaims = {
            groups: ['unknown-group-id-1', 'unknown-group-id-2'],
            tid: 'test-tenant-id'
          };
        });

        await page.goto('/admin/ops');
        
        // Should deny admin access for unrecognized groups
        const hasUnauthorizedMessage = await page.locator('text=/unauthorized|access denied|insufficient permissions/i').isVisible();
        const isRedirected = page.url().includes('/signin');
        
        expect(hasUnauthorizedMessage || isRedirected).toBeTruthy();
        logger.info('Unrecognized groups handled securely');
      });

    } catch (error) {
      logger.error('Group membership edge case test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
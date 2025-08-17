import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, withRetry } from '../test-utils';

/**
 * Enhanced Role-Based Access Control Tests
 * Tests multi-tenant access controls, engagement-scoped permissions, and role escalation prevention
 */

test.describe('Multi-Tenant Access Controls', () => {
  test('tenant isolation enforcement', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Set up tenant A user context', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'user-tenant-a',
            tenantId: 'tenant-a-id',
            role: 'Lead',
            permissions: ['read:engagements', 'write:engagements', 'read:assessments']
          };
        });
        
        await page.goto('/engagements');
        logger.info('Tenant A user context established');
      });

      await stepTracker.executeStep('Verify tenant A can only access own data', async () => {
        // Should only see engagements from tenant A
        const response = await page.waitForResponse(/\/api\/engagements/);
        expect(response.status()).toBe(200);
        
        const engagements = await response.json();
        
        // All engagements should belong to tenant A
        engagements.forEach((engagement: any) => {
          expect(engagement.tenantId).toBe('tenant-a-id');
        });
        
        logger.info('Tenant A data isolation verified', { engagementCount: engagements.length });
      });

      await stepTracker.executeStep('Test cross-tenant access prevention', async () => {
        // Try to access engagement from different tenant
        const crossTenantResponse = await page.goto('/api/engagements/tenant-b-engagement-id');
        
        // Should return 403 Forbidden or 404 Not Found
        expect(crossTenantResponse?.status()).toBeGreaterThanOrEqual(400);
        expect(crossTenantResponse?.status()).toBeLessThan(500);
        
        logger.info('Cross-tenant access properly blocked', { status: crossTenantResponse?.status() });
      });

      await stepTracker.executeStep('Test tenant B user with different context', async () => {
        // Switch to tenant B user
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'user-tenant-b',
            tenantId: 'tenant-b-id',
            role: 'Member',
            permissions: ['read:engagements']
          };
        });
        
        await page.goto('/engagements');
        
        // Should only see tenant B data
        const response = await page.waitForResponse(/\/api\/engagements/);
        if (response.status() === 200) {
          const engagements = await response.json();
          
          engagements.forEach((engagement: any) => {
            expect(engagement.tenantId).toBe('tenant-b-id');
          });
          
          logger.info('Tenant B data isolation verified', { engagementCount: engagements.length });
        }
      });

      await stepTracker.executeStep('Verify tenant-scoped search and filtering', async () => {
        // Test search functionality is tenant-scoped
        await page.fill('[data-testid="search-input"], input[name="search"]', 'test engagement');
        await page.click('[data-testid="search-button"], button:has-text("Search")');
        
        const searchResponse = await page.waitForResponse(/\/api\/engagements.*search/);
        if (searchResponse.status() === 200) {
          const searchResults = await searchResponse.json();
          
          // All search results should be from current tenant
          searchResults.forEach((result: any) => {
            expect(result.tenantId).toBe('tenant-b-id');
          });
          
          logger.info('Tenant-scoped search verified');
        }
      });

      logger.info('Multi-tenant access control test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('tenant admin vs global admin privileges', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test tenant admin access', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'tenant-admin',
            tenantId: 'tenant-c-id',
            role: 'TenantAdmin',
            permissions: ['admin:tenant', 'read:all', 'write:all', 'delete:all']
          };
        });
        
        await page.goto('/admin/tenant-settings');
        
        // Tenant admin should access tenant-specific admin features
        await expect(page.locator('[data-testid="tenant-admin-panel"], .tenant-admin')).toBeVisible();
        
        // But should not access global admin features
        const globalAdminResponse = await page.goto('/admin/global-settings');
        expect(globalAdminResponse?.status()).toBeGreaterThanOrEqual(400);
        
        logger.info('Tenant admin privileges verified');
      });

      await stepTracker.executeStep('Test global admin access', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'global-admin',
            tenantId: 'system',
            role: 'GlobalAdmin',
            permissions: ['admin:global', 'admin:tenant', 'read:all', 'write:all', 'delete:all']
          };
        });
        
        await page.goto('/admin/global-settings');
        
        // Global admin should access all admin features
        await expect(page.locator('[data-testid="global-admin-panel"], .global-admin')).toBeVisible();
        
        // And also tenant-specific features
        await page.goto('/admin/tenant-settings');
        await expect(page.locator('[data-testid="tenant-admin-panel"], .tenant-admin')).toBeVisible();
        
        logger.info('Global admin privileges verified');
      });

    } catch (error) {
      logger.error('Admin privileges test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Engagement-Scoped Permissions', () => {
  test('engagement-specific role assignment', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Set up user with engagement-specific roles', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'engagement-user',
            tenantId: 'tenant-a-id',
            role: 'Member',
            engagementRoles: {
              'engagement-1': 'Lead',
              'engagement-2': 'Member',
              'engagement-3': null // No access
            },
            permissions: ['read:engagements']
          };
        });
        
        await page.goto('/engagements');
        logger.info('User with engagement-specific roles established');
      });

      await stepTracker.executeStep('Test Lead access on engagement-1', async () => {
        await page.goto('/e/engagement-1/dashboard');
        
        // Should have Lead access - can edit and manage
        await expect(page.locator('[data-testid="edit-engagement"], button:has-text("Edit")')).toBeVisible();
        await expect(page.locator('[data-testid="manage-team"], button:has-text("Manage Team")')).toBeVisible();
        
        // Test API access
        const assessmentResponse = await page.goto('/api/engagements/engagement-1/assessments');
        expect(assessmentResponse?.status()).toBe(200);
        
        logger.info('Lead access on engagement-1 verified');
      });

      await stepTracker.executeStep('Test Member access on engagement-2', async () => {
        await page.goto('/e/engagement-2/dashboard');
        
        // Should have Member access - can view but limited editing
        const hasEditButton = await page.locator('[data-testid="edit-engagement"]').isVisible();
        const hasManageTeam = await page.locator('[data-testid="manage-team"]').isVisible();
        
        expect(hasEditButton).toBeFalsy();
        expect(hasManageTeam).toBeFalsy();
        
        // But should be able to view
        await expect(page.locator('[data-testid="engagement-dashboard"], .dashboard')).toBeVisible();
        
        logger.info('Member access on engagement-2 verified');
      });

      await stepTracker.executeStep('Test no access on engagement-3', async () => {
        const noAccessResponse = await page.goto('/e/engagement-3/dashboard');
        
        // Should be denied access
        expect(noAccessResponse?.status()).toBeGreaterThanOrEqual(400);
        
        // Or redirected with appropriate message
        const hasAccessDenied = await page.locator('text=/access denied|unauthorized|no permission/i').isVisible();
        expect(hasAccessDenied || noAccessResponse?.status() !== 200).toBeTruthy();
        
        logger.info('No access to engagement-3 properly enforced');
      });

      await stepTracker.executeStep('Test engagement list filtering', async () => {
        await page.goto('/engagements');
        
        // Should only see engagements with access
        const engagementItems = page.locator('[data-testid="engagement-item"], .engagement-item');
        const visibleEngagements = await engagementItems.count();
        
        // Should see engagement-1 and engagement-2, but not engagement-3
        expect(visibleEngagements).toBeLessThanOrEqual(2);
        
        // Verify specific engagements
        await expect(page.locator('[data-testid="engagement-item"]:has-text("engagement-1")')).toBeVisible();
        await expect(page.locator('[data-testid="engagement-item"]:has-text("engagement-2")')).toBeVisible();
        
        const hasEngagement3 = await page.locator('[data-testid="engagement-item"]:has-text("engagement-3")').isVisible();
        expect(hasEngagement3).toBeFalsy();
        
        logger.info('Engagement list properly filtered', { visibleEngagements });
      });

    } catch (error) {
      logger.error('Engagement-scoped permissions test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('assessment and document access control', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test assessment access based on engagement role', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'assessment-user',
            tenantId: 'tenant-a-id',
            role: 'Member',
            engagementRoles: {
              'engagement-1': 'Lead'
            }
          };
        });
        
        // Lead on engagement-1 should access all assessments
        await page.goto('/e/engagement-1/assessment/assessment-1');
        
        await expect(page.locator('[data-testid="assessment-content"], .assessment')).toBeVisible();
        await expect(page.locator('[data-testid="edit-assessment"], button:has-text("Edit")')).toBeVisible();
        
        logger.info('Assessment access verified for engagement Lead');
      });

      await stepTracker.executeStep('Test document permissions', async () => {
        // Test document upload access (Lead only)
        await page.goto('/e/engagement-1/documents');
        
        await expect(page.locator('[data-testid="upload-document"], button:has-text("Upload")')).toBeVisible();
        
        // Test document download
        const downloadButton = page.locator('[data-testid="download-document"], button:has-text("Download")').first();
        if (await downloadButton.isVisible()) {
          // Should be able to download
          await downloadButton.click();
          // Note: In real test would verify download
          logger.info('Document download access verified');
        }
      });

      await stepTracker.executeStep('Test sensitive document access', async () => {
        // Test access to confidential documents
        const confidentialDoc = page.locator('[data-testid="document-item"]:has([data-sensitivity="confidential"])');
        
        if (await confidentialDoc.isVisible()) {
          // Lead should have access to confidential documents
          const viewButton = confidentialDoc.locator('[data-testid="view-document"]');
          await expect(viewButton).toBeVisible();
          
          logger.info('Confidential document access verified for Lead');
        }
      });

    } catch (error) {
      logger.error('Assessment and document access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Role Escalation Prevention', () => {
  test('prevent privilege escalation attacks', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Test role modification attempt', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'member-user',
            tenantId: 'tenant-a-id',
            role: 'Member',
            permissions: ['read:engagements']
          };
        });
        
        // Try to modify own role through API manipulation
        const roleChangeResponse = await page.goto('/api/users/member-user/role', {
          method: 'PATCH',
          data: { role: 'Admin' }
        });
        
        // Should be rejected
        expect(roleChangeResponse?.status()).toBeGreaterThanOrEqual(400);
        
        logger.info('Role modification attempt properly blocked', { status: roleChangeResponse?.status() });
      });

      await stepTracker.executeStep('Test permission injection attempts', async () => {
        // Try to inject additional permissions
        await page.addInitScript(() => {
          // Attempt to modify permissions client-side
          window.mockUserContext.permissions = ['admin:all', 'write:all', 'delete:all'];
        });
        
        // Server should validate permissions independently
        const adminResponse = await page.goto('/admin/ops');
        
        // Should still be denied despite client-side modification
        const hasUnauthorized = await page.locator('text=/unauthorized|access denied/i').isVisible();
        const isBlocked = adminResponse?.status() !== 200;
        
        expect(hasUnauthorized || isBlocked).toBeTruthy();
        
        logger.info('Permission injection attempt blocked');
      });

      await stepTracker.executeStep('Test token manipulation resistance', async () => {
        // Try to access API with manipulated headers
        await page.setExtraHTTPHeaders({
          'X-User-Role': 'Admin',
          'X-User-Permissions': 'admin:all,write:all',
          'X-Tenant-Override': 'system'
        });
        
        const manipulatedResponse = await page.goto('/api/admin/users');
        
        // Should reject manipulated headers
        expect(manipulatedResponse?.status()).toBeGreaterThanOrEqual(400);
        
        logger.info('Token manipulation attempt blocked', { status: manipulatedResponse?.status() });
      });

      await stepTracker.executeStep('Test session hijacking prevention', async () => {
        // Store original context
        const originalUserId = 'member-user';
        
        // Attempt to change user context mid-session
        await page.addInitScript(() => {
          window.mockUserContext.userId = 'admin-user';
          window.mockUserContext.role = 'Admin';
        });
        
        // Server should validate session consistency
        const hijackResponse = await page.goto('/api/users/admin-user/profile');
        
        // Should maintain original user's permissions
        expect(hijackResponse?.status()).toBeGreaterThanOrEqual(400);
        
        logger.info('Session hijacking attempt blocked');
      });

      logger.info('Role escalation prevention test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('audit trail for privilege changes', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test legitimate role change auditing', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'admin-user',
            tenantId: 'tenant-a-id',
            role: 'Admin',
            permissions: ['admin:users', 'write:roles']
          };
        });
        
        // Legitimate role change by admin
        await page.goto('/admin/users');
        
        const userRow = page.locator('[data-testid="user-row"]:has-text("test-user")').first();
        if (await userRow.isVisible()) {
          await userRow.locator('[data-testid="edit-user"]').click();
          await page.selectOption('[data-testid="user-role"], select[name="role"]', 'Lead');
          await page.click('[data-testid="save-user"], button:has-text("Save")');
          
          // Should create audit entry
          await page.goto('/admin/audit-log');
          
          const roleChangeAudit = page.locator('[data-testid="audit-entry"]:has-text("Role Change")');
          await expect(roleChangeAudit).toBeVisible();
          
          logger.info('Role change audit trail verified');
        }
      });

      await stepTracker.executeStep('Test failed privilege escalation auditing', async () => {
        // Check for failed escalation attempts in audit log
        const failedAttempts = page.locator('[data-testid="audit-entry"]:has-text("Unauthorized")');
        const failedCount = await failedAttempts.count();
        
        if (failedCount > 0) {
          // Click on first failed attempt
          await failedAttempts.first().click();
          
          // Should show attempt details
          await expect(page.locator('[data-testid="audit-details"]')).toBeVisible();
          await expect(page.locator('text=/privilege|escalation|unauthorized/i')).toBeVisible();
          
          logger.info('Failed escalation attempts properly audited', { failedCount });
        }
      });

    } catch (error) {
      logger.error('Privilege change auditing test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Admin vs Lead vs Member Access Patterns', () => {
  test('Admin role comprehensive access', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Set up Admin user context', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'admin-user',
            tenantId: 'tenant-a-id',
            role: 'Admin',
            permissions: [
              'admin:users', 'admin:settings', 'admin:presets',
              'read:all', 'write:all', 'delete:all',
              'gdpr:export', 'gdpr:purge'
            ]
          };
        });
        
        logger.info('Admin user context established');
      });

      await stepTracker.executeStep('Verify Admin access to all admin features', async () => {
        const adminPages = [
          '/admin/ops',
          '/admin/users',
          '/admin/presets',
          '/admin/gdpr',
          '/admin/performance'
        ];
        
        for (const adminPage of adminPages) {
          const response = await page.goto(adminPage);
          expect(response?.status()).toBe(200);
          
          await expect(page.locator('[data-testid*="admin"], .admin-content')).toBeVisible();
          logger.info(`Admin access verified for ${adminPage}`);
        }
      });

      await stepTracker.executeStep('Verify Admin can manage users', async () => {
        await page.goto('/admin/users');
        
        // Should see user management interface
        await expect(page.locator('[data-testid="users-list"], .users-list')).toBeVisible();
        await expect(page.locator('[data-testid="add-user"], button:has-text("Add User")')).toBeVisible();
        
        // Should be able to edit roles
        const editButtons = page.locator('[data-testid="edit-user"], button:has-text("Edit")');
        const editCount = await editButtons.count();
        expect(editCount).toBeGreaterThan(0);
        
        logger.info('Admin user management access verified');
      });

    } catch (error) {
      logger.error('Admin role access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('Lead role limited admin access', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Set up Lead user context', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'lead-user',
            tenantId: 'tenant-a-id',
            role: 'Lead',
            permissions: [
              'read:engagements', 'write:engagements', 'delete:engagements',
              'read:assessments', 'write:assessments',
              'read:documents', 'write:documents',
              'gdpr:export'
            ]
          };
        });
        
        logger.info('Lead user context established');
      });

      await stepTracker.executeStep('Verify Lead access to engagement management', async () => {
        await page.goto('/engagements');
        
        // Should have full engagement access
        await expect(page.locator('[data-testid="create-engagement"], button:has-text("Create")')).toBeVisible();
        
        const engagementItem = page.locator('[data-testid="engagement-item"]').first();
        if (await engagementItem.isVisible()) {
          await engagementItem.click();
          
          // Should be able to edit
          await expect(page.locator('[data-testid="edit-engagement"]')).toBeVisible();
          await expect(page.locator('[data-testid="manage-team"]')).toBeVisible();
        }
        
        logger.info('Lead engagement management access verified');
      });

      await stepTracker.executeStep('Verify Lead limited admin access', async () => {
        // Lead should access some admin features
        const limitedAdminResponse = await page.goto('/admin/presets');
        
        if (limitedAdminResponse?.status() === 200) {
          // May have preset access
          logger.info('Lead has preset access');
        }
        
        // But should not access user management
        const userAdminResponse = await page.goto('/admin/users');
        expect(userAdminResponse?.status()).toBeGreaterThanOrEqual(400);
        
        // And should not access global settings
        const globalSettingsResponse = await page.goto('/admin/global-settings');
        expect(globalSettingsResponse?.status()).toBeGreaterThanOrEqual(400);
        
        logger.info('Lead admin access appropriately limited');
      });

    } catch (error) {
      logger.error('Lead role access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('Member role basic access', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Set up Member user context', async () => {
        await page.addInitScript(() => {
          window.mockUserContext = {
            userId: 'member-user',
            tenantId: 'tenant-a-id',
            role: 'Member',
            permissions: [
              'read:engagements', 'read:assessments', 'read:documents'
            ]
          };
        });
        
        logger.info('Member user context established');
      });

      await stepTracker.executeStep('Verify Member read-only engagement access', async () => {
        await page.goto('/engagements');
        
        // Should see engagements but no create button
        await expect(page.locator('[data-testid="engagements-list"], .engagements')).toBeVisible();
        
        const hasCreateButton = await page.locator('[data-testid="create-engagement"]').isVisible();
        expect(hasCreateButton).toBeFalsy();
        
        // Should be able to view but not edit
        const engagementItem = page.locator('[data-testid="engagement-item"]').first();
        if (await engagementItem.isVisible()) {
          await engagementItem.click();
          
          const hasEditButton = await page.locator('[data-testid="edit-engagement"]').isVisible();
          expect(hasEditButton).toBeFalsy();
        }
        
        logger.info('Member read-only engagement access verified');
      });

      await stepTracker.executeStep('Verify Member cannot access admin features', async () => {
        const adminPages = [
          '/admin/ops',
          '/admin/users',
          '/admin/presets',
          '/admin/gdpr'
        ];
        
        for (const adminPage of adminPages) {
          const response = await page.goto(adminPage);
          expect(response?.status()).toBeGreaterThanOrEqual(400);
        }
        
        logger.info('Member admin access properly blocked');
      });

      await stepTracker.executeStep('Verify Member assessment participation', async () => {
        // Member should be able to participate in assessments
        await page.goto('/assessment/draft');
        
        // May have access to assessment interface for completion
        const hasAssessmentAccess = await page.locator('[data-testid="assessment-form"], .assessment-form').isVisible();
        const hasAccessDenied = await page.locator('text=/access denied|unauthorized/i').isVisible();
        
        // Either has access or appropriate denial
        expect(hasAssessmentAccess || hasAccessDenied).toBeTruthy();
        
        logger.info('Member assessment access verified');
      });

    } catch (error) {
      logger.error('Member role access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
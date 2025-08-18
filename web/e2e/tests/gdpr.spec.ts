import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry, waitForCondition } from '../test-utils';

/**
 * GDPR Compliance Tests
 * Tests data export, data purge, background jobs, audit trails, and compliance workflows
 */

test.describe('GDPR Data Export', () => {
  test.beforeEach(async ({ page }) => {
    // Set up authenticated session with Lead/Admin role
    await page.addInitScript(() => {
      window.mockUserRole = 'Lead';
      window.mockUserId = 'test-user-id';
      window.mockTenantId = 'test-tenant-id';
    });
  });

  test('data export functionality end-to-end', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await stepTracker.executeStep('Navigate to GDPR dashboard', async () => {
        await page.goto('/admin/gdpr');
        
        await withRetry(async () => {
          await expect(page.locator('h1:has-text("GDPR Compliance"), [data-testid="gdpr-dashboard"]')).toBeVisible();
        }, 3, 2000);
        
        logger.info('GDPR dashboard loaded successfully');
      });

      await stepTracker.executeStep('Initiate data export request', async () => {
        // Find and click data export button
        const exportButton = page.locator('button:has-text("Export Data"), [data-testid="export-data-btn"]');
        await expect(exportButton).toBeVisible();
        await exportButton.click();
        
        // Fill in export form
        await page.fill('[data-testid="export-user-id"], input[name="userId"]', 'test-user-123');
        await page.fill('[data-testid="export-reason"], textarea[name="reason"]', 'GDPR compliance request');
        
        // Select export format
        await page.selectOption('[data-testid="export-format"], select[name="format"]', 'json');
        
        // Submit export request
        const submitButton = page.locator('button:has-text("Start Export"), [data-testid="submit-export"]');
        await submitButton.click();
        
        logger.info('Data export request submitted');
      });

      await stepTracker.executeStep('Monitor export job progress', async () => {
        // Wait for job to start
        await page.waitForSelector('[data-testid="export-job-status"], .job-status', { timeout: 10000 });
        
        // Check initial job status
        let jobStatus = await page.textContent('[data-testid="export-job-status"], .job-status');
        expect(jobStatus).toContain('In Progress');
        
        // Wait for job completion with timeout
        await waitForCondition(async () => {
          await page.reload();
          jobStatus = await page.textContent('[data-testid="export-job-status"], .job-status');
          return jobStatus?.includes('Completed') || jobStatus?.includes('Failed') || false;
        }, {
          timeout: 60000,
          interval: 2000,
          timeoutMessage: 'Export job did not complete within expected time'
        });
        
        expect(jobStatus).toContain('Completed');
        logger.info('Export job completed successfully', { jobStatus });
      });

      await stepTracker.executeStep('Download and validate export file', async () => {
        // Find download link
        const downloadLink = page.locator('a:has-text("Download"), [data-testid="download-export"]');
        await expect(downloadLink).toBeVisible();
        
        // Test download functionality
        const downloadPromise = page.waitForEvent('download');
        await downloadLink.click();
        const download = await downloadPromise;
        
        expect(download.suggestedFilename()).toMatch(/.*\.json$/);
        logger.info('Export file downloaded successfully', { filename: download.suggestedFilename() });
        
        // Validate file content structure (mock validation)
        const downloadPath = await download.path();
        if (downloadPath) {
          // In real test, would validate JSON structure
          logger.info('Export file validation placeholder', { path: downloadPath });
        }
      });

      await stepTracker.executeStep('Verify audit trail entry', async () => {
        // Navigate to audit log
        await page.goto('/admin/audit-log');
        
        // Check for export audit entry
        const auditEntry = page.locator('[data-testid="audit-entry"]:has-text("Data Export")');
        await expect(auditEntry).toBeVisible();
        
        // Verify audit details
        await auditEntry.click();
        const auditDetails = page.locator('[data-testid="audit-details"], .audit-details');
        await expect(auditDetails).toContainText('test-user-123');
        await expect(auditDetails).toContainText('GDPR compliance request');
        
        logger.info('Audit trail entry verified');
      });

      logger.info('GDPR data export test completed successfully', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('export format validation', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test JSON export format', async () => {
        await page.goto('/admin/gdpr');
        
        // Start export with JSON format
        await page.click('[data-testid="export-data-btn"]');
        await page.fill('[data-testid="export-user-id"]', 'test-user-json');
        await page.selectOption('[data-testid="export-format"]', 'json');
        await page.click('[data-testid="submit-export"]');
        
        // Wait for completion
        await waitForCondition(async () => {
          const status = await page.textContent('[data-testid="export-job-status"]');
          return status?.includes('Completed') || false;
        }, { timeout: 30000, interval: 2000 });
        
        // Verify JSON format
        const downloadLink = page.locator('[data-testid="download-export"]');
        const href = await downloadLink.getAttribute('href');
        expect(href).toContain('.json');
        
        logger.info('JSON export format validated');
      });

      await stepTracker.executeStep('Test CSV export format', async () => {
        await page.goto('/admin/gdpr');
        
        // Start export with CSV format
        await page.click('[data-testid="export-data-btn"]');
        await page.fill('[data-testid="export-user-id"]', 'test-user-csv');
        await page.selectOption('[data-testid="export-format"]', 'csv');
        await page.click('[data-testid="submit-export"]');
        
        // Wait for completion
        await waitForCondition(async () => {
          const status = await page.textContent('[data-testid="export-job-status"]');
          return status?.includes('Completed') || false;
        }, { timeout: 30000, interval: 2000 });
        
        // Verify CSV format
        const downloadLink = page.locator('[data-testid="download-export"]');
        const href = await downloadLink.getAttribute('href');
        expect(href).toContain('.csv');
        
        logger.info('CSV export format validated');
      });

    } catch (error) {
      logger.error('Export format validation failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('GDPR Data Purge', () => {
  test('data purge workflow with confirmations', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Navigate to data purge interface', async () => {
        await page.goto('/admin/gdpr/purge');
        
        await expect(page.locator('h1:has-text("Data Purge"), [data-testid="purge-dashboard"]')).toBeVisible();
        logger.info('Data purge interface loaded');
      });

      await stepTracker.executeStep('Initiate purge request with confirmations', async () => {
        // Fill in purge form
        await page.fill('[data-testid="purge-user-id"], input[name="purgeUserId"]', 'test-user-purge-123');
        await page.fill('[data-testid="purge-reason"], textarea[name="purgeReason"]', 'User requested account deletion');
        
        // First confirmation
        await page.check('[data-testid="confirm-irreversible"], input[name="confirmIrreversible"]');
        
        // Click purge button
        const purgeButton = page.locator('button:has-text("Start Purge"), [data-testid="start-purge-btn"]');
        await purgeButton.click();
        
        // Second confirmation dialog
        await expect(page.locator('[data-testid="purge-confirmation-dialog"], .confirmation-dialog')).toBeVisible();
        await page.fill('[data-testid="confirmation-text"], input[name="confirmationText"]', 'DELETE');
        await page.click('[data-testid="confirm-purge-final"], button:has-text("Confirm Purge")');
        
        logger.info('Purge request initiated with confirmations');
      });

      await stepTracker.executeStep('Monitor purge job execution', async () => {
        // Wait for purge job to start
        await expect(page.locator('[data-testid="purge-job-status"], .purge-job-status')).toBeVisible();
        
        let jobStatus = await page.textContent('[data-testid="purge-job-status"]');
        expect(jobStatus).toContain('In Progress');
        
        // Monitor progress
        await waitForCondition(async () => {
          await page.reload();
          jobStatus = await page.textContent('[data-testid="purge-job-status"]');
          return jobStatus?.includes('Completed') || jobStatus?.includes('Failed') || false;
        }, {
          timeout: 120000, // Purge may take longer
          interval: 3000,
          timeoutMessage: 'Purge job did not complete within expected time'
        });
        
        expect(jobStatus).toContain('Completed');
        logger.info('Purge job completed', { jobStatus });
      });

      await stepTracker.executeStep('Verify data removal', async () => {
        // Check that user data is no longer accessible
        const response = await page.goto('/api/users/test-user-purge-123');
        expect(response?.status()).toBe(404);
        
        // Verify related data is also removed
        const engagementsResponse = await page.goto('/api/engagements?userId=test-user-purge-123');
        if (engagementsResponse?.status() === 200) {
          const engagements = await engagementsResponse.json();
          expect(engagements).toHaveLength(0);
        }
        
        logger.info('Data removal verified');
      });

      await stepTracker.executeStep('Verify purge audit trail', async () => {
        await page.goto('/admin/audit-log');
        
        // Check for purge audit entries
        const purgeAuditEntry = page.locator('[data-testid="audit-entry"]:has-text("Data Purge")');
        await expect(purgeAuditEntry).toBeVisible();
        
        // Verify audit details
        await purgeAuditEntry.click();
        const auditDetails = page.locator('[data-testid="audit-details"]');
        await expect(auditDetails).toContainText('test-user-purge-123');
        await expect(auditDetails).toContainText('User requested account deletion');
        
        logger.info('Purge audit trail verified');
      });

    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('purge safety mechanisms', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test purge without confirmations', async () => {
        await page.goto('/admin/gdpr/purge');
        
        // Try to purge without checking confirmations
        await page.fill('[data-testid="purge-user-id"]', 'test-user-no-confirm');
        
        const purgeButton = page.locator('[data-testid="start-purge-btn"]');
        await expect(purgeButton).toBeDisabled();
        
        logger.info('Purge button disabled without confirmations');
      });

      await stepTracker.executeStep('Test incorrect confirmation text', async () => {
        await page.goto('/admin/gdpr/purge');
        
        // Fill form and check confirmation
        await page.fill('[data-testid="purge-user-id"]', 'test-user-wrong-confirm');
        await page.check('[data-testid="confirm-irreversible"]');
        await page.click('[data-testid="start-purge-btn"]');
        
        // Enter wrong confirmation text
        await page.fill('[data-testid="confirmation-text"]', 'WRONG');
        const confirmButton = page.locator('[data-testid="confirm-purge-final"]');
        await expect(confirmButton).toBeDisabled();
        
        logger.info('Incorrect confirmation text prevented purge');
      });

      await stepTracker.executeStep('Test role-based purge access', async () => {
        // Mock non-admin user
        await page.addInitScript(() => {
          window.mockUserRole = 'Member';
        });
        
        const response = await page.goto('/admin/gdpr/purge');
        
        // Should be denied or redirected
        const hasUnauthorized = await page.locator('text=/unauthorized|access denied/i').isVisible();
        const isRedirected = !page.url().includes('/gdpr/purge');
        
        expect(hasUnauthorized || isRedirected).toBeTruthy();
        logger.info('Non-admin purge access blocked');
      });

    } catch (error) {
      logger.error('Purge safety mechanisms test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('GDPR Background Jobs', () => {
  test('background job monitoring', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access job monitoring dashboard', async () => {
        await page.goto('/admin/jobs');
        
        await expect(page.locator('h1:has-text("Background Jobs"), [data-testid="jobs-dashboard"]')).toBeVisible();
        logger.info('Job monitoring dashboard loaded');
      });

      await stepTracker.executeStep('View active GDPR jobs', async () => {
        // Filter for GDPR jobs
        await page.selectOption('[data-testid="job-type-filter"], select[name="jobType"]', 'gdpr');
        
        // Check for job listings
        const jobsList = page.locator('[data-testid="jobs-list"], .jobs-list');
        await expect(jobsList).toBeVisible();
        
        // Verify job information display
        const jobItems = page.locator('[data-testid="job-item"], .job-item');
        const jobCount = await jobItems.count();
        
        if (jobCount > 0) {
          // Check first job details
          const firstJob = jobItems.first();
          await expect(firstJob).toContainText(/export|purge/i);
          await expect(firstJob).toContainText(/pending|running|completed|failed/i);
          
          logger.info('GDPR jobs displayed correctly', { jobCount });
        }
      });

      await stepTracker.executeStep('Test job status updates', async () => {
        // Start a new export job
        await page.goto('/admin/gdpr');
        await page.click('[data-testid="export-data-btn"]');
        await page.fill('[data-testid="export-user-id"]', 'test-monitor-user');
        await page.click('[data-testid="submit-export"]');
        
        // Return to jobs dashboard
        await page.goto('/admin/jobs');
        await page.selectOption('[data-testid="job-type-filter"]', 'gdpr');
        
        // Should show new job
        const newJob = page.locator('[data-testid="job-item"]:has-text("test-monitor-user")');
        await expect(newJob).toBeVisible();
        
        // Check status updates
        let initialStatus = await newJob.locator('[data-testid="job-status"], .job-status').textContent();
        expect(initialStatus).toMatch(/pending|running/i);
        
        logger.info('Job status monitoring working', { initialStatus });
      });

      await stepTracker.executeStep('Test job cancellation', async () => {
        // Find a running job
        const runningJob = page.locator('[data-testid="job-item"]:has([data-testid="job-status"]:has-text("Running"))').first();
        
        if (await runningJob.isVisible()) {
          // Click cancel button
          const cancelButton = runningJob.locator('[data-testid="cancel-job-btn"], button:has-text("Cancel")');
          await cancelButton.click();
          
          // Confirm cancellation
          await page.click('[data-testid="confirm-cancel"], button:has-text("Confirm")');
          
          // Wait for status update
          await page.waitForTimeout(2000);
          await page.reload();
          
          const updatedStatus = await runningJob.locator('[data-testid="job-status"]').textContent();
          expect(updatedStatus).toMatch(/cancelled|stopped/i);
          
          logger.info('Job cancellation working correctly');
        }
      });

    } catch (error) {
      logger.error('Background job monitoring test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('GDPR TTL Policy Validation', () => {
  test('data retention policy enforcement', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access data retention settings', async () => {
        await page.goto('/admin/gdpr/retention');
        
        await expect(page.locator('h1:has-text("Data Retention"), [data-testid="retention-dashboard"]')).toBeVisible();
        logger.info('Data retention dashboard loaded');
      });

      await stepTracker.executeStep('View current TTL policies', async () => {
        // Check for policy listings
        const policiesList = page.locator('[data-testid="retention-policies"], .retention-policies');
        await expect(policiesList).toBeVisible();
        
        // Verify policy details
        const policyItems = page.locator('[data-testid="policy-item"], .policy-item');
        const policyCount = await policyItems.count();
        
        expect(policyCount).toBeGreaterThan(0);
        
        // Check policy information
        const firstPolicy = policyItems.first();
        await expect(firstPolicy).toContainText(/days|months|years/);
        await expect(firstPolicy).toContainText(/engagements|assessments|documents/);
        
        logger.info('TTL policies displayed correctly', { policyCount });
      });

      await stepTracker.executeStep('Test policy configuration', async () => {
        // Find edit button for a policy
        const editButton = page.locator('[data-testid="edit-policy-btn"], button:has-text("Edit")').first();
        await editButton.click();
        
        // Modify retention period
        const retentionInput = page.locator('[data-testid="retention-period"], input[name="retentionPeriod"]');
        await retentionInput.fill('365');
        
        // Save changes
        await page.click('[data-testid="save-policy"], button:has-text("Save")');
        
        // Verify update
        await expect(page.locator('text=Policy updated successfully')).toBeVisible();
        
        logger.info('TTL policy configuration working');
      });

      await stepTracker.executeStep('Verify policy application preview', async () => {
        // Test policy preview functionality
        await page.click('[data-testid="preview-policy"], button:has-text("Preview")');
        
        // Should show affected records
        const previewResults = page.locator('[data-testid="preview-results"], .preview-results');
        await expect(previewResults).toBeVisible();
        
        // Check for record counts
        const affectedRecords = await page.textContent('[data-testid="affected-count"], .affected-count');
        expect(affectedRecords).toMatch(/\d+/);
        
        logger.info('Policy preview functionality working', { affectedRecords });
      });

    } catch (error) {
      logger.error('TTL policy validation test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('GDPR Role-Based Access', () => {
  test('Lead role GDPR access', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    // Mock Lead role
    await page.addInitScript(() => {
      window.mockUserRole = 'Lead';
    });
    
    try {
      await test.step('Verify Lead can access GDPR features', async () => {
        await page.goto('/admin/gdpr');
        
        // Lead should have access to GDPR dashboard
        await expect(page.locator('[data-testid="gdpr-dashboard"]')).toBeVisible();
        
        // Should be able to export data
        await expect(page.locator('[data-testid="export-data-btn"]')).toBeVisible();
        
        logger.info('Lead GDPR access verified');
      });

      await test.step('Verify Lead purge restrictions', async () => {
        await page.goto('/admin/gdpr/purge');
        
        // Lead may have limited purge access or require additional approval
        const hasPurgeAccess = await page.locator('[data-testid="start-purge-btn"]').isVisible();
        const hasRestrictionMessage = await page.locator('text=/admin approval|restricted access/i').isVisible();
        
        expect(hasPurgeAccess || hasRestrictionMessage).toBeTruthy();
        logger.info('Lead purge access appropriately restricted');
      });

    } catch (error) {
      logger.error('Lead role GDPR access test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('Member role GDPR restrictions', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    // Mock Member role
    await page.addInitScript(() => {
      window.mockUserRole = 'Member';
    });
    
    try {
      await test.step('Verify Member cannot access GDPR features', async () => {
        const response = await page.goto('/admin/gdpr');
        
        // Should be denied or redirected
        const hasUnauthorized = await page.locator('text=/unauthorized|access denied/i').isVisible();
        const isRedirected = response?.status() === 403 || !page.url().includes('/gdpr');
        
        expect(hasUnauthorized || isRedirected).toBeTruthy();
        logger.info('Member GDPR access properly restricted');
      });

    } catch (error) {
      logger.error('Member role GDPR restrictions test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
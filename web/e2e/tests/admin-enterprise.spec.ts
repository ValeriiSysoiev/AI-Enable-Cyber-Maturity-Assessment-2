import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry, waitForCondition } from '../test-utils';

/**
 * Admin Interface Tests for Enterprise Features
 * Tests auth diagnostics, GDPR admin dashboard, performance monitoring, and system health
 */

test.describe('Auth Diagnostics Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Set up admin user context
    await page.addInitScript(() => {
      window.mockUserContext = {
        userId: 'admin-user',
        tenantId: 'tenant-admin-id',
        role: 'Admin',
        permissions: ['admin:diagnostics', 'admin:auth', 'read:all']
      };
    });
  });

  test('comprehensive auth diagnostics page functionality', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Navigate to auth diagnostics page', async () => {
        await page.goto('/admin/auth-diagnostics');
        
        await withRetry(async () => {
          await expect(page.locator('h1:has-text("Authentication Diagnostics"), [data-testid="auth-diagnostics"]')).toBeVisible();
        }, 3, 2000);
        
        logger.info('Auth diagnostics page loaded successfully');
      });

      await stepTracker.executeStep('Verify current user information display', async () => {
        // Check for user information section
        const userInfoSection = page.locator('[data-testid="current-user-info"], .current-user-info');
        await expect(userInfoSection).toBeVisible();
        
        // Verify user details
        await expect(page.locator('[data-testid="user-id"], .user-id')).toContainText('admin-user');
        await expect(page.locator('[data-testid="user-tenant"], .user-tenant')).toContainText('tenant-admin-id');
        await expect(page.locator('[data-testid="user-role"], .user-role')).toContainText('Admin');
        
        logger.info('Current user information displayed correctly');
      });

      await stepTracker.executeStep('Test AAD token information display', async () => {
        // Check for AAD token section
        const aadTokenSection = page.locator('[data-testid="aad-token-info"], .aad-token-info');
        await expect(aadTokenSection).toBeVisible();
        
        // Should show token claims
        await expect(page.locator('[data-testid="token-claims"], .token-claims')).toBeVisible();
        
        // Check for essential AAD fields
        const tokenFields = [
          'Tenant ID',
          'Object ID',
          'UPN',
          'Groups',
          'Issued At',
          'Expires At'
        ];
        
        for (const field of tokenFields) {
          const fieldElement = page.locator(`text=${field}`);
          await expect(fieldElement).toBeVisible();
        }
        
        logger.info('AAD token information displayed correctly');
      });

      await stepTracker.executeStep('Test group memberships and role mapping', async () => {
        // Check groups section
        const groupsSection = page.locator('[data-testid="user-groups"], .user-groups');
        await expect(groupsSection).toBeVisible();
        
        // Should show group list
        const groupsList = page.locator('[data-testid="groups-list"], .groups-list');
        await expect(groupsList).toBeVisible();
        
        // Check role mapping section
        const roleMappingSection = page.locator('[data-testid="role-mappings"], .role-mappings');
        await expect(roleMappingSection).toBeVisible();
        
        // Should show how groups map to roles
        const mappingTable = page.locator('[data-testid="mapping-table"], .mapping-table');
        await expect(mappingTable).toBeVisible();
        
        logger.info('Group memberships and role mappings displayed');
      });

      await stepTracker.executeStep('Test session information and security details', async () => {
        // Check session section
        const sessionSection = page.locator('[data-testid="session-info"], .session-info');
        await expect(sessionSection).toBeVisible();
        
        // Should show session details
        await expect(page.locator('[data-testid="session-id"], .session-id')).toBeVisible();
        await expect(page.locator('[data-testid="session-created"], .session-created')).toBeVisible();
        await expect(page.locator('[data-testid="session-expires"], .session-expires')).toBeVisible();
        
        // Check security headers
        const securitySection = page.locator('[data-testid="security-headers"], .security-headers');
        await expect(securitySection).toBeVisible();
        
        logger.info('Session information and security details displayed');
      });

      await stepTracker.executeStep('Test diagnostics data refresh', async () => {
        // Test refresh functionality
        const refreshButton = page.locator('[data-testid="refresh-diagnostics"], button:has-text("Refresh")');
        await expect(refreshButton).toBeVisible();
        
        // Get initial timestamp
        const initialTimestamp = await page.textContent('[data-testid="last-updated"], .last-updated');
        
        await refreshButton.click();
        
        // Wait for refresh to complete
        await page.waitForTimeout(1000);
        
        // Check for updated timestamp
        const updatedTimestamp = await page.textContent('[data-testid="last-updated"], .last-updated');
        expect(updatedTimestamp).not.toBe(initialTimestamp);
        
        logger.info('Diagnostics data refresh working correctly');
      });

      logger.info('Auth diagnostics interface test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('auth configuration validation', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access auth configuration section', async () => {
        await page.goto('/admin/auth-diagnostics');
        
        // Navigate to configuration tab
        const configTab = page.locator('[data-testid="config-tab"], .tab:has-text("Configuration")');
        if (await configTab.isVisible()) {
          await configTab.click();
        }
        
        const configSection = page.locator('[data-testid="auth-config"], .auth-configuration');
        await expect(configSection).toBeVisible();
        
        logger.info('Auth configuration section accessed');
      });

      await stepTracker.executeStep('Verify AAD configuration display', async () => {
        // Check AAD settings
        const aadConfig = page.locator('[data-testid="aad-config"], .aad-configuration');
        await expect(aadConfig).toBeVisible();
        
        // Should show configuration status
        await expect(page.locator('[data-testid="aad-enabled"], .aad-enabled')).toBeVisible();
        await expect(page.locator('[data-testid="tenant-id-config"], .tenant-id')).toBeVisible();
        await expect(page.locator('[data-testid="client-id-config"], .client-id')).toBeVisible();
        
        logger.info('AAD configuration displayed correctly');
      });

      await stepTracker.executeStep('Test configuration validation', async () => {
        // Test configuration validation button
        const validateButton = page.locator('[data-testid="validate-config"], button:has-text("Validate")');
        await expect(validateButton).toBeVisible();
        
        await validateButton.click();
        
        // Wait for validation results
        await waitForCondition(async () => {
          const results = page.locator('[data-testid="validation-results"], .validation-results');
          return await results.isVisible();
        }, { timeout: 10000, interval: 1000 });
        
        // Check validation results
        const validationResults = page.locator('[data-testid="validation-results"]');
        await expect(validationResults).toBeVisible();
        
        // Should show status indicators
        const statusIndicators = page.locator('[data-testid="validation-status"], .status-indicator');
        const statusCount = await statusIndicators.count();
        expect(statusCount).toBeGreaterThan(0);
        
        logger.info('Configuration validation completed', { statusCount });
      });

    } catch (error) {
      logger.error('Auth configuration validation test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('GDPR Admin Dashboard', () => {
  test('comprehensive GDPR management interface', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Navigate to GDPR admin dashboard', async () => {
        await page.goto('/admin/gdpr');
        
        await expect(page.locator('h1:has-text("GDPR Administration"), [data-testid="gdpr-admin"]')).toBeVisible();
        logger.info('GDPR admin dashboard loaded');
      });

      await stepTracker.executeStep('Verify data export management section', async () => {
        const exportSection = page.locator('[data-testid="export-management"], .export-management');
        await expect(exportSection).toBeVisible();
        
        // Check export requests overview
        await expect(page.locator('[data-testid="active-exports"], .active-exports')).toBeVisible();
        await expect(page.locator('[data-testid="completed-exports"], .completed-exports')).toBeVisible();
        
        // Check export queue
        const exportQueue = page.locator('[data-testid="export-queue"], .export-queue');
        await expect(exportQueue).toBeVisible();
        
        logger.info('Data export management section verified');
      });

      await stepTracker.executeStep('Test bulk export management', async () => {
        // Check for bulk operations
        const bulkExportButton = page.locator('[data-testid="bulk-export"], button:has-text("Bulk Export")');
        await expect(bulkExportButton).toBeVisible();
        
        await bulkExportButton.click();
        
        // Should open bulk export dialog
        const bulkDialog = page.locator('[data-testid="bulk-export-dialog"], .bulk-export-dialog');
        await expect(bulkDialog).toBeVisible();
        
        // Should have user selection
        await expect(page.locator('[data-testid="user-selection"], .user-selection')).toBeVisible();
        await expect(page.locator('[data-testid="export-format-bulk"], select[name="format"]')).toBeVisible();
        
        // Cancel dialog
        await page.click('[data-testid="cancel-bulk"], button:has-text("Cancel")');
        
        logger.info('Bulk export management interface verified');
      });

      await stepTracker.executeStep('Verify data purge management section', async () => {
        const purgeSection = page.locator('[data-testid="purge-management"], .purge-management');
        await expect(purgeSection).toBeVisible();
        
        // Check purge requests overview
        await expect(page.locator('[data-testid="pending-purges"], .pending-purges')).toBeVisible();
        await expect(page.locator('[data-testid="completed-purges"], .completed-purges')).toBeVisible();
        
        // Check purge approval workflow
        const approvalSection = page.locator('[data-testid="purge-approvals"], .purge-approvals');
        await expect(approvalSection).toBeVisible();
        
        logger.info('Data purge management section verified');
      });

      await stepTracker.executeStep('Test retention policy management', async () => {
        // Navigate to retention tab
        const retentionTab = page.locator('[data-testid="retention-tab"], .tab:has-text("Retention")');
        if (await retentionTab.isVisible()) {
          await retentionTab.click();
        }
        
        const retentionSection = page.locator('[data-testid="retention-policies"], .retention-policies');
        await expect(retentionSection).toBeVisible();
        
        // Check policy configuration
        const policyTable = page.locator('[data-testid="policy-table"], .policy-table');
        await expect(policyTable).toBeVisible();
        
        // Should have edit capabilities
        const editPolicyButton = page.locator('[data-testid="edit-policy"], button:has-text("Edit")').first();
        if (await editPolicyButton.isVisible()) {
          await editPolicyButton.click();
          
          const policyDialog = page.locator('[data-testid="policy-dialog"], .policy-dialog');
          await expect(policyDialog).toBeVisible();
          
          await page.click('[data-testid="cancel-policy"], button:has-text("Cancel")');
        }
        
        logger.info('Retention policy management verified');
      });

      await stepTracker.executeStep('Test compliance reporting', async () => {
        // Navigate to reports tab
        const reportsTab = page.locator('[data-testid="reports-tab"], .tab:has-text("Reports")');
        if (await reportsTab.isVisible()) {
          await reportsTab.click();
        }
        
        const reportsSection = page.locator('[data-testid="compliance-reports"], .compliance-reports');
        await expect(reportsSection).toBeVisible();
        
        // Check for report generation
        const generateReportButton = page.locator('[data-testid="generate-report"], button:has-text("Generate Report")');
        await expect(generateReportButton).toBeVisible();
        
        // Check existing reports
        const reportsTable = page.locator('[data-testid="reports-table"], .reports-table');
        await expect(reportsTable).toBeVisible();
        
        logger.info('Compliance reporting interface verified');
      });

      logger.info('GDPR admin dashboard test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('GDPR audit trail and compliance monitoring', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access GDPR audit trail', async () => {
        await page.goto('/admin/gdpr/audit');
        
        const auditSection = page.locator('[data-testid="gdpr-audit"], .gdpr-audit');
        await expect(auditSection).toBeVisible();
        
        logger.info('GDPR audit trail accessed');
      });

      await stepTracker.executeStep('Verify audit entry filtering and search', async () => {
        // Check for filter options
        const filterSection = page.locator('[data-testid="audit-filters"], .audit-filters');
        await expect(filterSection).toBeVisible();
        
        // Test filter by action type
        await page.selectOption('[data-testid="action-filter"], select[name="action"]', 'export');
        
        // Test date range filter
        await page.fill('[data-testid="date-from"], input[name="dateFrom"]', '2024-01-01');
        await page.fill('[data-testid="date-to"], input[name="dateTo"]', '2024-12-31');
        
        // Apply filters
        await page.click('[data-testid="apply-filters"], button:has-text("Apply")');
        
        // Check filtered results
        const auditEntries = page.locator('[data-testid="audit-entry"], .audit-entry');
        const entryCount = await auditEntries.count();
        
        logger.info('Audit filtering working correctly', { entryCount });
      });

      await stepTracker.executeStep('Test audit entry details', async () => {
        // Click on first audit entry
        const firstEntry = page.locator('[data-testid="audit-entry"]').first();
        if (await firstEntry.isVisible()) {
          await firstEntry.click();
          
          // Should show detailed information
          const auditDetails = page.locator('[data-testid="audit-details"], .audit-details');
          await expect(auditDetails).toBeVisible();
          
          // Check for essential audit information
          await expect(page.locator('[data-testid="audit-timestamp"], .audit-timestamp')).toBeVisible();
          await expect(page.locator('[data-testid="audit-user"], .audit-user')).toBeVisible();
          await expect(page.locator('[data-testid="audit-action"], .audit-action')).toBeVisible();
          await expect(page.locator('[data-testid="audit-target"], .audit-target')).toBeVisible();
          
          logger.info('Audit entry details displayed correctly');
        }
      });

      await stepTracker.executeStep('Test compliance metrics dashboard', async () => {
        // Navigate to metrics
        await page.goto('/admin/gdpr/metrics');
        
        const metricsSection = page.locator('[data-testid="compliance-metrics"], .compliance-metrics');
        await expect(metricsSection).toBeVisible();
        
        // Check for key metrics
        const metricCards = page.locator('[data-testid="metric-card"], .metric-card');
        const metricCount = await metricCards.count();
        expect(metricCount).toBeGreaterThan(0);
        
        // Verify specific metrics
        await expect(page.locator('[data-testid="total-requests"], .total-requests')).toBeVisible();
        await expect(page.locator('[data-testid="pending-requests"], .pending-requests')).toBeVisible();
        await expect(page.locator('[data-testid="completion-rate"], .completion-rate')).toBeVisible();
        
        logger.info('Compliance metrics dashboard verified', { metricCount });
      });

    } catch (error) {
      logger.error('GDPR audit trail test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Performance Monitoring Interface', () => {
  test('system performance dashboard', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await stepTracker.executeStep('Navigate to performance monitoring dashboard', async () => {
        const loadTime = await perfMonitor.measurePageLoad('/admin/performance');
        
        await expect(page.locator('h1:has-text("System Performance"), [data-testid="performance-dashboard"]')).toBeVisible();
        
        logger.info('Performance monitoring dashboard loaded', { loadTime });
      });

      await stepTracker.executeStep('Verify real-time metrics display', async () => {
        // Check for real-time metrics section
        const realTimeSection = page.locator('[data-testid="realtime-metrics"], .realtime-metrics');
        await expect(realTimeSection).toBeVisible();
        
        // Check for key performance indicators
        const kpiCards = page.locator('[data-testid="kpi-card"], .kpi-card');
        const kpiCount = await kpiCards.count();
        expect(kpiCount).toBeGreaterThan(0);
        
        // Verify specific metrics
        await expect(page.locator('[data-testid="response-time-avg"], .response-time')).toBeVisible();
        await expect(page.locator('[data-testid="throughput"], .throughput')).toBeVisible();
        await expect(page.locator('[data-testid="error-rate"], .error-rate')).toBeVisible();
        await expect(page.locator('[data-testid="cpu-usage"], .cpu-usage')).toBeVisible();
        
        logger.info('Real-time metrics display verified', { kpiCount });
      });

      await stepTracker.executeStep('Test performance charts and graphs', async () => {
        // Check for charts section
        const chartsSection = page.locator('[data-testid="performance-charts"], .performance-charts');
        await expect(chartsSection).toBeVisible();
        
        // Look for specific chart types
        const responseTimeChart = page.locator('[data-testid="response-time-chart"], .response-time-chart');
        const throughputChart = page.locator('[data-testid="throughput-chart"], .throughput-chart');
        const errorRateChart = page.locator('[data-testid="error-rate-chart"], .error-rate-chart');
        
        await expect(responseTimeChart).toBeVisible();
        await expect(throughputChart).toBeVisible();
        await expect(errorRateChart).toBeVisible();
        
        // Test chart time range selection
        const timeRangeSelector = page.locator('[data-testid="time-range"], select[name="timeRange"]');
        if (await timeRangeSelector.isVisible()) {
          await timeRangeSelector.selectOption('1h');
          await page.waitForTimeout(1000); // Wait for chart update
          
          logger.info('Chart time range selection working');
        }
      });

      await stepTracker.executeStep('Test alert configuration', async () => {
        // Navigate to alerts tab
        const alertsTab = page.locator('[data-testid="alerts-tab"], .tab:has-text("Alerts")');
        if (await alertsTab.isVisible()) {
          await alertsTab.click();
        }
        
        const alertsSection = page.locator('[data-testid="alert-config"], .alert-configuration');
        await expect(alertsSection).toBeVisible();
        
        // Check for alert thresholds
        const thresholdInputs = page.locator('[data-testid="threshold-input"], input[type="number"]');
        const thresholdCount = await thresholdInputs.count();
        expect(thresholdCount).toBeGreaterThan(0);
        
        // Test threshold update
        const firstThreshold = thresholdInputs.first();
        await firstThreshold.fill('2000');
        
        const saveButton = page.locator('[data-testid="save-alerts"], button:has-text("Save")');
        await saveButton.click();
        
        await expect(page.locator('text=Alert settings saved')).toBeVisible();
        
        logger.info('Alert configuration interface verified', { thresholdCount });
      });

    } catch (error) {
      logger.error('Performance monitoring interface test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('database and query performance monitoring', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access database performance section', async () => {
        await page.goto('/admin/performance/database');
        
        const dbSection = page.locator('[data-testid="db-performance"], .db-performance');
        await expect(dbSection).toBeVisible();
        
        logger.info('Database performance section accessed');
      });

      await stepTracker.executeStep('Verify slow query analysis', async () => {
        // Check slow queries section
        const slowQueriesSection = page.locator('[data-testid="slow-queries"], .slow-queries');
        await expect(slowQueriesSection).toBeVisible();
        
        // Check query table
        const queryTable = page.locator('[data-testid="query-table"], .query-table');
        await expect(queryTable).toBeVisible();
        
        // Look for query details
        const queryRows = page.locator('[data-testid="query-row"], .query-row');
        const queryCount = await queryRows.count();
        
        if (queryCount > 0) {
          const firstQuery = queryRows.first();
          await expect(firstQuery).toContainText(/ms|seconds/);
          await expect(firstQuery).toContainText(/SELECT|UPDATE|INSERT|DELETE/i);
          
          // Test query details view
          await firstQuery.click();
          
          const queryDetails = page.locator('[data-testid="query-details"], .query-details');
          await expect(queryDetails).toBeVisible();
          
          logger.info('Slow query analysis working correctly', { queryCount });
        }
      });

      await stepTracker.executeStep('Test connection pool monitoring', async () => {
        // Check connection pool section
        const poolSection = page.locator('[data-testid="connection-pool"], .connection-pool');
        await expect(poolSection).toBeVisible();
        
        // Verify pool metrics
        await expect(page.locator('[data-testid="active-connections"], .active-connections')).toBeVisible();
        await expect(page.locator('[data-testid="pool-utilization"], .pool-utilization')).toBeVisible();
        await expect(page.locator('[data-testid="connection-wait-time"], .connection-wait-time')).toBeVisible();
        
        logger.info('Connection pool monitoring verified');
      });

    } catch (error) {
      logger.error('Database performance monitoring test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Background Job Management', () => {
  test('comprehensive job monitoring and management', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Navigate to job management dashboard', async () => {
        await page.goto('/admin/jobs');
        
        await expect(page.locator('h1:has-text("Background Jobs"), [data-testid="jobs-dashboard"]')).toBeVisible();
        logger.info('Job management dashboard loaded');
      });

      await stepTracker.executeStep('Verify job listing and filtering', async () => {
        // Check jobs list
        const jobsList = page.locator('[data-testid="jobs-list"], .jobs-list');
        await expect(jobsList).toBeVisible();
        
        // Test job type filtering
        const jobTypeFilter = page.locator('[data-testid="job-type-filter"], select[name="jobType"]');
        await expect(jobTypeFilter).toBeVisible();
        
        await jobTypeFilter.selectOption('gdpr');
        
        // Test status filtering
        const statusFilter = page.locator('[data-testid="status-filter"], select[name="status"]');
        if (await statusFilter.isVisible()) {
          await statusFilter.selectOption('running');
        }
        
        // Apply filters
        await page.click('[data-testid="apply-filters"], button:has-text("Apply")');
        
        const jobItems = page.locator('[data-testid="job-item"], .job-item');
        const jobCount = await jobItems.count();
        
        logger.info('Job filtering working correctly', { jobCount });
      });

      await stepTracker.executeStep('Test job details and management', async () => {
        // Click on first job if available
        const firstJob = page.locator('[data-testid="job-item"]').first();
        
        if (await firstJob.isVisible()) {
          await firstJob.click();
          
          // Should show job details
          const jobDetails = page.locator('[data-testid="job-details"], .job-details');
          await expect(jobDetails).toBeVisible();
          
          // Check for job information
          await expect(page.locator('[data-testid="job-id"], .job-id')).toBeVisible();
          await expect(page.locator('[data-testid="job-status"], .job-status')).toBeVisible();
          await expect(page.locator('[data-testid="job-created"], .job-created')).toBeVisible();
          
          // Check for job actions
          const jobActions = page.locator('[data-testid="job-actions"], .job-actions');
          await expect(jobActions).toBeVisible();
          
          logger.info('Job details display working correctly');
        }
      });

      await stepTracker.executeStep('Test job cancellation and retry', async () => {
        // Look for running jobs that can be cancelled
        const runningJob = page.locator('[data-testid="job-item"]:has([data-testid="job-status"]:has-text("Running"))').first();
        
        if (await runningJob.isVisible()) {
          const cancelButton = runningJob.locator('[data-testid="cancel-job"], button:has-text("Cancel")');
          
          if (await cancelButton.isVisible()) {
            await cancelButton.click();
            
            // Confirm cancellation
            const confirmDialog = page.locator('[data-testid="confirm-dialog"], .confirm-dialog');
            if (await confirmDialog.isVisible()) {
              await page.click('[data-testid="confirm-cancel"], button:has-text("Confirm")');
            }
            
            logger.info('Job cancellation tested');
          }
        }
        
        // Look for failed jobs that can be retried
        const failedJob = page.locator('[data-testid="job-item"]:has([data-testid="job-status"]:has-text("Failed"))').first();
        
        if (await failedJob.isVisible()) {
          const retryButton = failedJob.locator('[data-testid="retry-job"], button:has-text("Retry")');
          
          if (await retryButton.isVisible()) {
            await retryButton.click();
            
            logger.info('Job retry tested');
          }
        }
      });

      await stepTracker.executeStep('Test job queue management', async () => {
        // Navigate to queue management
        const queueTab = page.locator('[data-testid="queue-tab"], .tab:has-text("Queue")');
        if (await queueTab.isVisible()) {
          await queueTab.click();
        }
        
        const queueSection = page.locator('[data-testid="job-queue"], .job-queue');
        await expect(queueSection).toBeVisible();
        
        // Check queue statistics
        await expect(page.locator('[data-testid="queue-size"], .queue-size')).toBeVisible();
        await expect(page.locator('[data-testid="processing-rate"], .processing-rate')).toBeVisible();
        
        // Test queue operations
        const pauseQueueButton = page.locator('[data-testid="pause-queue"], button:has-text("Pause")');
        if (await pauseQueueButton.isVisible()) {
          // Don't actually pause in test, just verify button exists
          logger.info('Queue management controls available');
        }
      });

    } catch (error) {
      logger.error('Background job management test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('System Health Monitoring', () => {
  test('comprehensive system health dashboard', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Navigate to system health dashboard', async () => {
        await page.goto('/admin/health');
        
        await expect(page.locator('h1:has-text("System Health"), [data-testid="health-dashboard"]')).toBeVisible();
        logger.info('System health dashboard loaded');
      });

      await stepTracker.executeStep('Verify service status monitoring', async () => {
        // Check services section
        const servicesSection = page.locator('[data-testid="services-status"], .services-status');
        await expect(servicesSection).toBeVisible();
        
        // Check for individual service status
        const serviceItems = page.locator('[data-testid="service-item"], .service-item');
        const serviceCount = await serviceItems.count();
        expect(serviceCount).toBeGreaterThan(0);
        
        // Verify service information
        const firstService = serviceItems.first();
        await expect(firstService).toContainText(/healthy|unhealthy|degraded/i);
        
        logger.info('Service status monitoring verified', { serviceCount });
      });

      await stepTracker.executeStep('Test dependency checks', async () => {
        // Check dependencies section
        const dependenciesSection = page.locator('[data-testid="dependencies"], .dependencies');
        await expect(dependenciesSection).toBeVisible();
        
        // Should show external dependencies
        const dependencyItems = page.locator('[data-testid="dependency-item"], .dependency-item');
        const depCount = await dependencyItems.count();
        
        if (depCount > 0) {
          // Check dependency status
          const firstDep = dependencyItems.first();
          await expect(firstDep).toContainText(/connected|disconnected|error/i);
          
          logger.info('Dependency checks verified', { depCount });
        }
      });

      await stepTracker.executeStep('Test health check refresh', async () => {
        // Test refresh functionality
        const refreshButton = page.locator('[data-testid="refresh-health"], button:has-text("Refresh")');
        await expect(refreshButton).toBeVisible();
        
        const initialTimestamp = await page.textContent('[data-testid="last-check"], .last-check');
        
        await refreshButton.click();
        
        // Wait for refresh
        await page.waitForTimeout(2000);
        
        const updatedTimestamp = await page.textContent('[data-testid="last-check"], .last-check');
        expect(updatedTimestamp).not.toBe(initialTimestamp);
        
        logger.info('Health check refresh working correctly');
      });

      await stepTracker.executeStep('Verify system metrics overview', async () => {
        // Check system metrics
        const metricsSection = page.locator('[data-testid="system-metrics"], .system-metrics');
        await expect(metricsSection).toBeVisible();
        
        // Should show key system metrics
        await expect(page.locator('[data-testid="uptime"], .uptime')).toBeVisible();
        await expect(page.locator('[data-testid="memory-usage"], .memory-usage')).toBeVisible();
        await expect(page.locator('[data-testid="disk-usage"], .disk-usage')).toBeVisible();
        
        logger.info('System metrics overview verified');
      });

    } catch (error) {
      logger.error('System health monitoring test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
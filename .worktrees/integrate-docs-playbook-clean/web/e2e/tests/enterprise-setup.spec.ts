import { test as setup } from '@playwright/test';
import { EnterpriseTestUtils } from '../test-utils/enterprise';
import { EnterpriseDataGenerator } from '../test-utils';
import { TestLogger } from '../test-utils';

/**
 * Enterprise Setup Tests
 * Prepares the environment for enterprise feature testing
 */

setup('prepare enterprise test environment', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);
  const enterpriseUtils = new EnterpriseTestUtils(page, logger);
  const dataGenerator = EnterpriseDataGenerator;

  logger.info('Starting enterprise test environment setup');

  // Generate test data
  const testData = dataGenerator.generateTestData();

  // Store test data in browser context for use by other tests
  await page.addInitScript((data) => {
    window.enterpriseTestData = data;
  }, testData);

  // Setup basic enterprise configuration
  await page.goto('/');
  
  // Create admin session state
  await enterpriseUtils.setupEnterpriseAuth(
    {
      groups: ['admin-group-id', 'gdpr-officers-id'],
      tid: 'test-tenant-admin',
      oid: 'admin-setup-user',
      preferred_username: 'admin@test.com'
    },
    {
      userId: 'admin-setup-user',
      tenantId: 'test-tenant-admin',
      role: 'Admin',
      permissions: [
        'admin:all', 'gdpr:export', 'gdpr:purge', 
        'performance:monitor', 'admin:diagnostics'
      ],
      aadGroups: ['admin-group-id', 'gdpr-officers-id'],
      engagementRoles: {}
    }
  );

  // Save admin session state
  await page.context().storageState({ path: 'e2e/auth/admin-session.json' });
  logger.info('Admin session state saved');

  // Create multi-role session for RBAC testing
  await page.context().clearCookies();
  await enterpriseUtils.setupEnterpriseAuth(
    {
      groups: ['lead-group-id'],
      tid: 'test-tenant-lead',
      oid: 'lead-setup-user',
      preferred_username: 'lead@test.com'
    },
    {
      userId: 'lead-setup-user',
      tenantId: 'test-tenant-lead',
      role: 'Lead',
      permissions: [
        'read:engagements', 'write:engagements', 
        'read:assessments', 'write:assessments',
        'gdpr:export'
      ],
      aadGroups: ['lead-group-id'],
      engagementRoles: { 'engagement-1': 'Lead', 'engagement-2': 'Member' }
    }
  );

  // Save multi-role session state
  await page.context().storageState({ path: 'e2e/auth/multi-role-session.json' });
  logger.info('Multi-role session state saved');

  // Verify enterprise features are accessible
  await page.goto('/admin/health');
  
  // Setup complete
  logger.info('Enterprise test environment setup completed', {
    tenants: 1,
    users: testData.users.length,
    engagements: 0,
    aadGroups: 0,
    gdprRequests: 0
  });
});

setup('verify enterprise endpoints', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);

  logger.info('Verifying enterprise endpoints are available');

  const enterpriseEndpoints = [
    '/admin/auth-diagnostics',
    '/admin/gdpr',
    '/admin/performance',
    '/admin/jobs',
    '/admin/health',
    '/api/auth/groups',
    '/api/auth/diagnostics',
    '/api/gdpr/export',
    '/api/performance/metrics'
  ];

  let availableEndpoints = 0;
  
  for (const endpoint of enterpriseEndpoints) {
    try {
      const response = await page.goto(endpoint);
      
      // Not 404 means endpoint exists (even if requires auth)
      if (response && response.status() !== 404) {
        availableEndpoints++;
        logger.info(`Enterprise endpoint available: ${endpoint} (${response.status()})`);
      } else {
        logger.warn(`Enterprise endpoint not found: ${endpoint}`);
      }
    } catch (error) {
      logger.warn(`Error checking endpoint ${endpoint}`, { error: error instanceof Error ? error.message : error });
    }
  }

  logger.info('Enterprise endpoint verification completed', {
    available: availableEndpoints,
    total: enterpriseEndpoints.length,
    percentage: ((availableEndpoints / enterpriseEndpoints.length) * 100).toFixed(1) + '%'
  });
});

setup('initialize performance baseline', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);

  logger.info('Establishing performance baseline for enterprise features');

  // Warm up the application
  const warmupPages = [
    '/',
    '/signin',
    '/engagements',
    '/admin/performance'
  ];

  for (const warmupPage of warmupPages) {
    const startTime = Date.now();
    await page.goto(warmupPage);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;
    
    logger.info(`Baseline measurement: ${warmupPage}`, { loadTime });
  }

  // Initialize cache if available
  try {
    await page.request.post('/api/cache/init');
    logger.info('Cache initialization attempted');
  } catch (error) {
    logger.info('Cache initialization not available or failed');
  }

  logger.info('Performance baseline establishment completed');
});
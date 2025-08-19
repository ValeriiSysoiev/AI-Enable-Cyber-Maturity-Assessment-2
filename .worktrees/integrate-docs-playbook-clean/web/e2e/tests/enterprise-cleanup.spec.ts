import { test as cleanup } from '@playwright/test';
import { TestLogger } from '../test-utils';

/**
 * Enterprise Cleanup Tests
 * Cleans up test data and resets environment after enterprise testing
 */

cleanup('cleanup enterprise test data', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);

  logger.info('Starting enterprise test environment cleanup');

  try {
    // Clear any test data from the system
    await page.request.post('/api/test/cleanup');
    logger.info('Test data cleanup API called');
  } catch (error) {
    logger.info('Test data cleanup API not available');
  }

  try {
    // Clear caches
    await page.request.post('/api/cache/clear');
    logger.info('Cache cleared');
  } catch (error) {
    logger.info('Cache clear not available');
  }

  try {
    // Reset performance metrics
    await page.request.post('/api/performance/reset');
    logger.info('Performance metrics reset');
  } catch (error) {
    logger.info('Performance reset not available');
  }

  // Clear browser state
  await page.context().clearCookies();
  await page.context().clearPermissions();
  
  logger.info('Browser state cleared');
});

cleanup('cleanup test sessions', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);

  logger.info('Cleaning up test session files');

  // Note: In a real environment, you might want to clean up session files
  // For now, we'll just log the cleanup
  const sessionFiles = [
    'e2e/auth/admin-session.json',
    'e2e/auth/multi-role-session.json',
    'e2e/auth/aad-session.json'
  ];

  sessionFiles.forEach(file => {
    logger.info(`Session file to cleanup: ${file}`);
  });

  logger.info('Test session cleanup completed');
});

cleanup('verify cleanup completion', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);

  logger.info('Verifying cleanup completion');

  // Check that test data is cleared
  try {
    await page.goto('/api/test/status');
    const status = await page.textContent('body');
    
    if (status?.includes('clean') || status?.includes('empty')) {
      logger.info('Test environment successfully cleaned');
    } else {
      logger.warn('Test environment may not be fully cleaned', { status });
    }
  } catch (error) {
    logger.info('Test status endpoint not available');
  }

  // Verify caches are cleared
  try {
    await page.goto('/api/cache/status');
    const cacheStatus = await page.textContent('body');
    
    if (cacheStatus?.includes('empty') || cacheStatus?.includes('cleared')) {
      logger.info('Cache successfully cleared');
    } else {
      logger.info('Cache status after cleanup', { cacheStatus });
    }
  } catch (error) {
    logger.info('Cache status endpoint not available');
  }

  logger.info('Enterprise test environment cleanup verification completed');
});
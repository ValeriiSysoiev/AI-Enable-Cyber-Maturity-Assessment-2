import { test as teardown } from '@playwright/test';
import { TestLogger } from '../test-utils';
import fs from 'fs';
import path from 'path';

/**
 * AAD Authentication Cleanup for E2E Tests
 * Handles cleanup of authentication state and test data
 */

const authFile = 'e2e/auth/aad-session.json';

teardown('cleanup authentication session', async ({ }, testInfo) => {
  const logger = new TestLogger(testInfo);
  
  logger.info('Starting authentication cleanup');
  
  try {
    // Remove session file
    if (fs.existsSync(authFile)) {
      fs.unlinkSync(authFile);
      logger.info('Authentication session file removed', { path: authFile });
    } else {
      logger.info('No authentication session file to remove');
    }
    
    // Clean up any test data files
    const testDataDir = 'e2e/test-data';
    if (fs.existsSync(testDataDir)) {
      const files = fs.readdirSync(testDataDir);
      
      for (const file of files) {
        if (file.startsWith('test-') || file.startsWith('temp-')) {
          const filePath = path.join(testDataDir, file);
          fs.unlinkSync(filePath);
          logger.info('Removed test data file', { path: filePath });
        }
      }
    }
    
    // Clean up old screenshots and videos
    const testResultsDir = 'test-results';
    if (fs.existsSync(testResultsDir)) {
      const files = fs.readdirSync(testResultsDir);
      
      // Remove files older than 1 day
      const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
      
      for (const file of files) {
        const filePath = path.join(testResultsDir, file);
        
        try {
          const stats = fs.statSync(filePath);
          
          if (stats.mtime.getTime() < oneDayAgo) {
            if (stats.isFile()) {
              fs.unlinkSync(filePath);
              logger.info('Removed old test artifact', { path: filePath });
            }
          }
        } catch (statError) {
          logger.warn('Failed to check file stats', { path: filePath, error: statError });
        }
      }
    }
    
    logger.info('Authentication cleanup completed successfully');
    
  } catch (error) {
    logger.error('Authentication cleanup failed', { error: error instanceof Error ? error.message : error });
    // Don't throw error in cleanup to avoid masking test failures
  }
});

teardown('generate cleanup summary', async ({ }, testInfo) => {
  const logger = new TestLogger(testInfo);
  
  logger.info('Generating cleanup summary');
  
  try {
    const summary = {
      timestamp: new Date().toISOString(),
      authFileExists: fs.existsSync(authFile),
      testDataDirExists: fs.existsSync('e2e/test-data'),
      testResultsDirExists: fs.existsSync('test-results'),
      cleanupStatus: 'completed'
    };
    
    // Save cleanup summary
    const summaryPath = 'e2e/test-data/cleanup-summary.json';
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
    
    logger.info('Cleanup summary generated', summary);
    
  } catch (error) {
    logger.error('Failed to generate cleanup summary', { error: error instanceof Error ? error.message : error });
  }
});
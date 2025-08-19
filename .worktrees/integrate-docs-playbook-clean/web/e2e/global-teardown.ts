import { FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Global teardown for E2E tests
 * Handles cleanup and test result aggregation
 */
async function globalTeardown(config: FullConfig) {
  console.log('🧹 Running E2E test environment cleanup...');
  
  // Generate test summary
  const testResultsDir = path.join(process.cwd(), 'test-results');
  const reportDir = path.join(process.cwd(), 'playwright-report');
  
  try {
    // Check if test results exist
    if (fs.existsSync(testResultsDir)) {
      const files = fs.readdirSync(testResultsDir);
      console.log(`📊 Test artifacts generated: ${files.length} files`);
    }
    
    // Check if HTML report exists
    if (fs.existsSync(reportDir)) {
      console.log(`📋 HTML report available at: ${reportDir}/index.html`);
    }
    
    // Create summary for CI/CD
    const summary = {
      timestamp: new Date().toISOString(),
      testResultsDir,
      reportDir,
      environment: process.env.NODE_ENV || 'test',
      cleanup: 'completed'
    };
    
    fs.writeFileSync(
      path.join(process.cwd(), 'e2e/test-data/summary.json'),
      JSON.stringify(summary, null, 2)
    );
    
    console.log('✅ E2E test environment cleanup complete');
    
  } catch (error) {
    console.error(`❌ Error during cleanup: ${error}`);
  }
}

export default globalTeardown;
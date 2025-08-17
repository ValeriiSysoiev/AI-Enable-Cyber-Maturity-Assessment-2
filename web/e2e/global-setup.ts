import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Global setup for E2E tests
 * Handles environment validation and test data preparation
 */
async function globalSetup(config: FullConfig) {
  console.log('🔧 Setting up E2E test environment...');
  
  // Ensure required directories exist
  const dirs = [
    'e2e/auth',
    'e2e/test-data',
    'test-results',
    'playwright-report'
  ];
  
  for (const dir of dirs) {
    const fullPath = path.join(process.cwd(), dir);
    if (!fs.existsSync(fullPath)) {
      fs.mkdirSync(fullPath, { recursive: true });
      console.log(`📁 Created directory: ${dir}`);
    }
  }
  
  // Validate environment variables
  const requiredEnvVars = ['WEB_BASE_URL'];
  const optionalEnvVars = ['API_BASE_URL', 'AAD_CLIENT_ID', 'AAD_TENANT_ID'];
  
  console.log('🔍 Validating environment configuration...');
  
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      console.warn(`⚠️  Missing required environment variable: ${envVar}`);
    } else {
      console.log(`✅ ${envVar}: ${process.env[envVar]}`);
    }
  }
  
  for (const envVar of optionalEnvVars) {
    if (process.env[envVar]) {
      console.log(`✅ ${envVar}: configured`);
    } else {
      console.log(`ℹ️  Optional ${envVar}: not configured`);
    }
  }
  
  // Test basic connectivity
  const baseURL = process.env.WEB_BASE_URL || 'http://localhost:3000';
  
  try {
    console.log(`🌐 Testing connectivity to: ${baseURL}`);
    
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // Test basic connectivity with timeout
    await page.goto(baseURL, { timeout: 30000 });
    
    const title = await page.title();
    console.log(`✅ Web application accessible - Title: "${title}"`);
    
    await browser.close();
  } catch (error) {
    console.error(`❌ Failed to connect to web application: ${error}`);
    console.warn('⚠️  Some tests may fail due to connectivity issues');
  }
  
  // Prepare test data
  const testData = {
    timestamp: new Date().toISOString(),
    baseURL,
    environment: process.env.NODE_ENV || 'test',
    features: {
      aad: !!process.env.AAD_CLIENT_ID,
      api: !!process.env.API_BASE_URL,
    }
  };
  
  fs.writeFileSync(
    path.join(process.cwd(), 'e2e/test-data/environment.json'),
    JSON.stringify(testData, null, 2)
  );
  
  console.log('✅ E2E test environment setup complete');
}

export default globalSetup;
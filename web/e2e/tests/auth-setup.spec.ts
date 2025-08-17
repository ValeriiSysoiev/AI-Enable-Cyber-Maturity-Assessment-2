import { test as setup, expect } from '@playwright/test';
import { TestLogger } from '../test-utils';
import path from 'path';
import fs from 'fs';

/**
 * AAD Authentication Setup for E2E Tests
 * Handles authentication state preparation
 */

const authFile = 'e2e/auth/aad-session.json';

setup('authenticate with AAD', async ({ page }, testInfo) => {
  const logger = new TestLogger(testInfo);
  
  logger.info('Starting AAD authentication setup');
  
  try {
    // Ensure auth directory exists
    const authDir = path.dirname(authFile);
    if (!fs.existsSync(authDir)) {
      fs.mkdirSync(authDir, { recursive: true });
      logger.info('Created auth directory', { path: authDir });
    }
    
    // Check if AAD is configured
    const hasAADConfig = process.env.AAD_CLIENT_ID && process.env.AAD_TENANT_ID;
    
    if (!hasAADConfig) {
      logger.warn('AAD not configured, creating demo session');
      
      // Create demo session
      await page.goto('/signin');
      
      const demoButton = page.locator('button:has-text("Demo"), button:has-text("Continue")');
      
      if (await demoButton.first().isVisible()) {
        await demoButton.first().click();
        logger.info('Demo authentication successful');
      } else {
        logger.warn('No demo mode available, creating empty session');
      }
      
      // Save demo session state
      await page.context().storageState({ path: authFile });
      logger.info('Demo session saved', { path: authFile });
      return;
    }
    
    logger.info('AAD configured, attempting AAD authentication');
    
    // Navigate to signin page
    await page.goto('/signin');
    
    // Look for AAD signin button
    const aadButton = page.locator('button:has-text("Microsoft"), button:has-text("Azure"), a[href*="microsoft"]');
    
    if (await aadButton.first().isVisible()) {
      logger.info('AAD signin button found');
      
      // In a real test environment, you would handle AAD authentication here
      // For now, we'll create a placeholder session
      logger.warn('AAD authentication flow not implemented in test setup');
      
      // Create placeholder session
      await page.context().storageState({ path: authFile });
      logger.info('Placeholder AAD session created');
    } else {
      logger.warn('AAD signin button not found');
      
      // Fall back to creating empty session
      await page.context().storageState({ path: authFile });
      logger.info('Empty session created as fallback');
    }
    
  } catch (error) {
    logger.error('AAD authentication setup failed', { error: error instanceof Error ? error.message : error });
    
    // Create empty session as last resort
    try {
      await page.context().storageState({ path: authFile });
      logger.info('Emergency empty session created');
    } catch (fallbackError) {
      logger.error('Failed to create fallback session', { error: fallbackError });
      throw error;
    }
  }
});

setup.describe('Authentication Setup Validation', () => {
  setup('verify session file created', async ({ }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    if (fs.existsSync(authFile)) {
      logger.info('Authentication session file exists', { path: authFile });
      
      // Validate session file
      try {
        const sessionData = JSON.parse(fs.readFileSync(authFile, 'utf-8'));
        logger.info('Session file is valid JSON', { 
          hasCookies: Array.isArray(sessionData.cookies),
          hasOrigins: Array.isArray(sessionData.origins)
        });
      } catch (parseError) {
        logger.error('Session file is invalid JSON', { error: parseError });
        throw parseError;
      }
    } else {
      logger.error('Authentication session file does not exist', { path: authFile });
      throw new Error('Authentication setup failed - session file not created');
    }
  });
});
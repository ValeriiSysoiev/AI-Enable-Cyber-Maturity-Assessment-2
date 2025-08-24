import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery } from '../test-utils';

/**
 * Chat Shell UI Tests
 * Tests the chat interface, message sending, and RunCard functionality
 */

test.describe('Chat Shell', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to demo engagement for testing
    await page.goto('/e/demo/chat');
  });

  test('chat page loads and displays correctly', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const errorRecovery = new ErrorRecovery(logger, page);
    
    try {
      await stepTracker.executeStep('Verify chat page header', async () => {
        await expect(page.locator('h1')).toContainText('Chat Shell');
        await expect(page.locator('text=Send messages or use commands')).toBeVisible({ timeout: 20000 });
      });

      await stepTracker.executeStep('Verify main chat interface elements', async () => {
        // Check for message area
        await expect(page.locator('[class*="overflow-y-auto"]')).toBeVisible({ timeout: 20000 });
        
        // Check for command input
        await expect(page.locator('textarea[placeholder*="message"]')).toBeVisible({ timeout: 20000 });
        await expect(page.locator('button:has-text("Send")')).toBeVisible({ timeout: 20000 });
        
        // Check for RunCards sidebar
        await expect(page.locator('text=No commands executed yet')).toBeVisible({ timeout: 20000 });
      });

      logger.info('Chat page load test completed successfully');

    } catch (error) {
      await errorRecovery.captureErrorContext(error as Error);
      throw error;
    }
  });

  test('send regular message creates chat entry', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    const testMessage = 'Hello, this is a test message';
    
    try {
      await stepTracker.executeStep('Send a regular message', async () => {
        const input = page.locator('textarea[placeholder*="message"]');
        const sendButton = page.locator('button:has-text("Send")');
        
        await input.fill(testMessage);
        await sendButton.click();
      });

      await stepTracker.executeStep('Verify message appears in chat history', async () => {
        // Wait for message to appear
        await expect(page.locator(`text="${testMessage}"`)).toBeVisible({ timeout: 5000 });
        
        // Verify it's styled as a user message (right-aligned, blue background)
        const messageBubble = page.locator(`text="${testMessage}"`).locator('..');
        await expect(messageBubble).toHaveClass(/justify-end/);
      });

      logger.info('Regular message test completed successfully');

    } catch (error) {
      logger.error('Regular message test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('send command creates RunCard with queued status', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    const testCommand = '/ingest docs';
    
    try {
      await stepTracker.executeStep('Send a command message', async () => {
        const input = page.locator('textarea[placeholder*="message"]');
        const sendButton = page.locator('button:has-text("Send")');
        
        await input.fill(testCommand);
        
        // Verify command is detected (should show COMMAND indicator)
        await expect(page.locator('text=COMMAND')).toBeVisible({ timeout: 20000 });
        
        await sendButton.click();
      });

      await stepTracker.executeStep('Verify RunCard is created', async () => {
        // Wait for RunCard to appear in sidebar
        await expect(page.locator('text=Active Commands')).toBeVisible({ timeout: 5000 });
        
        // Check for command in RunCard
        await expect(page.locator(`code:has-text("${testCommand}")`)).toBeVisible({ timeout: 20000 });
        
        // Verify initial status is queued
        await expect(page.locator('text=QUEUED')).toBeVisible({ timeout: 20000 });
        await expect(page.locator('text=⏳')).toBeVisible({ timeout: 20000 });
      });

      await stepTracker.executeStep('Verify message also appears in chat', async () => {
        // Command should appear as both a chat message AND a RunCard
        await expect(page.locator(`text="${testCommand}"`)).toBeVisible({ timeout: 20000 });
      });

      logger.info('Command RunCard test completed successfully');

    } catch (error) {
      logger.error('Command RunCard test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('command autocomplete shows suggestions', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Test command autocomplete', async () => {
        const input = page.locator('textarea[placeholder*="message"]');
        
        // Start typing a command
        await input.fill('/');
        
        // Should show suggestions dropdown
        await expect(page.locator('text=/ingest')).toBeVisible({ timeout: 2000 });
        await expect(page.locator('text=/minutes')).toBeVisible({ timeout: 20000 });
        await expect(page.locator('text=/score')).toBeVisible({ timeout: 20000 });
        
        // Should show descriptions
        await expect(page.locator('text=Ingest and process documents')).toBeVisible({ timeout: 20000 });
      });

      await stepTracker.executeStep('Test suggestion selection', async () => {
        const input = page.locator('textarea[placeholder*="message"]');
        
        // Click on a suggestion
        await page.locator('text=/ingest').click();
        
        // Input should be filled with example
        await expect(input).toHaveValue('/ingest docs');
      });

      logger.info('Command autocomplete test completed successfully');

    } catch (error) {
      logger.error('Command autocomplete test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('chat history loads correctly on page refresh', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    const testMessage = 'This message should persist';
    
    try {
      await stepTracker.executeStep('Send a message', async () => {
        const input = page.locator('textarea[placeholder*="message"]');
        const sendButton = page.locator('button:has-text("Send")');
        
        await input.fill(testMessage);
        await sendButton.click();
        
        await expect(page.locator(`text="${testMessage}"`)).toBeVisible({ timeout: 20000 });
      });

      await stepTracker.executeStep('Refresh page and verify message persists', async () => {
        await page.reload();
        
        // Wait for page to load
        await expect(page.locator('h1:has-text("Chat Shell")')).toBeVisible({ timeout: 20000 });
        
        // Message should still be visible
        await expect(page.locator(`text="${testMessage}"`)).toBeVisible({ timeout: 5000 });
      });

      logger.info('Chat history persistence test completed successfully');

    } catch (error) {
      logger.error('Chat history persistence test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
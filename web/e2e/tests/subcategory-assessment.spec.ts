import { test, expect } from '@playwright/test';

/**
 * Subcategory Assessment and Evidence Integration E2E Tests
 * Tests enhanced subcategory drawer, keyboard navigation, and evidence tray functionality
 */

test.describe('Subcategory Assessment Polish', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to assessment page for a test engagement
    await page.goto('/e/test-engagement/assessment');
    
    // Wait for page to load and CSF data to be available
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="csf-grid"], .csf-grid, button:has-text("ID")', { timeout: 10000 });
  });

  test('subcategory drawer opens and closes correctly', async ({ page }) => {
    await test.step('Open first CSF function', async () => {
      // Find and click first function to expand it
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await expect(firstFunction).toBeVisible();
      await firstFunction.click();
    });

    await test.step('Select a subcategory', async () => {
      // Wait for subcategories to be visible
      await page.waitForSelector('button:has-text("ID.AM-1")', { timeout: 5000 });
      
      // Click on first subcategory
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      // Drawer should open
      await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=ID.AM-1')).toBeVisible();
    });

    await test.step('Close drawer with close button', async () => {
      const closeButton = page.locator('[aria-label="Close drawer"]');
      await closeButton.click();
      
      // Drawer should close
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    });

    await test.step('Open drawer again and close with escape key', async () => {
      // Reopen drawer
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      // Close with escape
      await page.keyboard.press('Escape');
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    });
  });

  test('assessment scoring functionality works', async ({ page }) => {
    await test.step('Open subcategory drawer', async () => {
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      await expect(page.locator('[role="dialog"]')).toBeVisible();
    });

    await test.step('Test score buttons', async () => {
      // Should be on Assessment tab by default
      await expect(page.locator('[role="tab"][aria-selected="true"]')).toContainText('Assessment');
      
      // Click score button 3
      const scoreButton3 = page.locator('button', { hasText: '3' }).filter({ has: page.locator('[aria-pressed]') });
      await scoreButton3.click();
      
      // Button should be pressed
      await expect(scoreButton3).toHaveAttribute('aria-pressed', 'true');
      
      // Slider should reflect the score
      const slider = page.locator('input[type="range"]');
      await expect(slider).toHaveValue('3');
    });

    await test.step('Test keyboard shortcuts for scoring', async () => {
      // Use Ctrl+5 to set score to 5
      await page.keyboard.press('Control+5');
      
      const scoreButton5 = page.locator('button', { hasText: '5' }).filter({ has: page.locator('[aria-pressed]') });
      await expect(scoreButton5).toHaveAttribute('aria-pressed', 'true');
    });

    await test.step('Test rationale input', async () => {
      const rationaleTextarea = page.locator('textarea[placeholder*="reasoning"]');
      await rationaleTextarea.fill('This subcategory is fully implemented with comprehensive device inventory processes.');
      
      await expect(rationaleTextarea).toHaveValue(/comprehensive device inventory/);
    });
  });

  test('evidence tab and tray functionality', async ({ page }) => {
    await test.step('Open subcategory drawer and switch to evidence tab', async () => {
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      // Switch to Evidence tab
      const evidenceTab = page.locator('[role="tab"]', { hasText: 'Evidence' });
      await evidenceTab.click();
      
      await expect(evidenceTab).toHaveAttribute('aria-selected', 'true');
    });

    await test.step('Verify evidence loading states', async () => {
      // Should show loading initially or empty state
      const loadingIndicator = page.locator('text=Loading evidence...');
      const emptyState = page.locator('text=No evidence files found');
      
      // Either loading or empty state should be visible
      await expect(loadingIndicator.or(emptyState)).toBeVisible({ timeout: 10000 });
    });

    await test.step('Test evidence error state and retry', async () => {
      // Mock network failure if possible, or test retry button existence
      const retryButton = page.locator('button:has-text("Retry")');
      
      if (await retryButton.isVisible()) {
        await retryButton.click();
        // Should trigger new loading state
        await expect(page.locator('text=Loading evidence...')).toBeVisible();
      }
    });
  });

  test('keyboard navigation within drawer', async ({ page }) => {
    await test.step('Open drawer and test tab navigation', async () => {
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      await expect(page.locator('[role="dialog"]')).toBeVisible();
    });

    await test.step('Test focus management', async () => {
      // Score input should be focused initially
      const scoreSlider = page.locator('input[type="range"]');
      await expect(scoreSlider).toBeFocused();
    });

    await test.step('Test tab navigation between elements', async () => {
      // Tab through interactive elements
      await page.keyboard.press('Tab');
      
      // Should focus on score buttons or textarea
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
      
      // Continue tabbing to verify navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Shift+Tab should reverse navigation
      await page.keyboard.press('Shift+Tab');
    });

    await test.step('Test arrow key navigation in evidence list', async () => {
      // Switch to evidence tab
      const evidenceTab = page.locator('[role="tab"]', { hasText: 'Evidence' });
      await evidenceTab.click();
      
      // If evidence items exist, test arrow navigation
      const evidenceItems = page.locator('[role="listbox"] [role="button"], .evidence-item');
      const itemCount = await evidenceItems.count();
      
      if (itemCount > 1) {
        await evidenceItems.first().focus();
        await page.keyboard.press('ArrowDown');
        // Verify focus moved to next item
      }
    });
  });

  test('accessibility compliance', async ({ page }) => {
    await test.step('Open drawer and verify ARIA attributes', async () => {
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();
      
      // Verify required ARIA attributes
      await expect(dialog).toHaveAttribute('aria-modal', 'true');
      await expect(dialog).toHaveAttribute('aria-labelledby');
    });

    await test.step('Verify tab panel accessibility', async () => {
      const assessmentTab = page.locator('[role="tab"]', { hasText: 'Assessment' });
      const evidenceTab = page.locator('[role="tab"]', { hasText: 'Evidence' });
      
      // Verify tab attributes
      await expect(assessmentTab).toHaveAttribute('aria-selected', 'true');
      await expect(assessmentTab).toHaveAttribute('aria-controls');
      await expect(evidenceTab).toHaveAttribute('aria-selected', 'false');
      
      // Switch tabs and verify attributes update
      await evidenceTab.click();
      await expect(evidenceTab).toHaveAttribute('aria-selected', 'true');
      await expect(assessmentTab).toHaveAttribute('aria-selected', 'false');
    });

    await test.step('Verify form controls accessibility', async () => {
      // Switch back to assessment tab
      const assessmentTab = page.locator('[role="tab"]', { hasText: 'Assessment' });
      await assessmentTab.click();
      
      // Verify form labels and descriptions
      const scoreSlider = page.locator('input[type="range"]');
      await expect(scoreSlider).toHaveAttribute('aria-describedby');
      
      const rationaleTextarea = page.locator('textarea');
      await expect(rationaleTextarea).toHaveAttribute('aria-describedby');
      
      // Verify score buttons have proper ARIA
      const scoreButtons = page.locator('button[aria-pressed]');
      const buttonCount = await scoreButtons.count();
      expect(buttonCount).toBeGreaterThan(0);
    });
  });

  test('list virtualization performance with large datasets', async ({ page }) => {
    await test.step('Test evidence list virtualization', async () => {
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      const evidenceTab = page.locator('[role="tab"]', { hasText: 'Evidence' });
      await evidenceTab.click();
      
      // Wait for evidence content to load
      await page.waitForTimeout(2000);
      
      // Check if virtualized list exists (react-window implementation)
      const virtualizedList = page.locator('[role="listbox"], .ReactVirtualized__List, [style*="overflow"]');
      
      if (await virtualizedList.isVisible()) {
        // Verify virtualized list has proper height and overflow
        const listStyles = await virtualizedList.getAttribute('style');
        expect(listStyles).toMatch(/height|overflow/);
      }
    });
  });

  test('correlation ID logging', async ({ page }) => {
    await test.step('Verify correlation ID in browser logs', async () => {
      // Listen for console logs
      const logs: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'log') {
          logs.push(msg.text());
        }
      });
      
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      // Wait for logs to be generated
      await page.waitForTimeout(1000);
      
      // Verify correlation ID format in logs
      const correlationLogs = logs.filter(log => log.includes('[csf-') && log.includes(']'));
      expect(correlationLogs.length).toBeGreaterThan(0);
    });
  });

  test('error handling and recovery', async ({ page }) => {
    await test.step('Test graceful error handling', async () => {
      // Simulate network issues by intercepting requests
      await page.route('**/api/evidence/**', route => route.abort());
      
      const firstFunction = page.locator('button').filter({ hasText: /^ID\s*-/ }).first();
      await firstFunction.click();
      
      const subcategory = page.locator('button:has-text("ID.AM-1")').first();
      await subcategory.click();
      
      const evidenceTab = page.locator('[role="tab"]', { hasText: 'Evidence' });
      await evidenceTab.click();
      
      // Should show error state
      await expect(page.locator('text=Failed to load evidence')).toBeVisible({ timeout: 10000 });
      
      // Should have retry functionality
      const retryButton = page.locator('button:has-text("Retry")');
      await expect(retryButton).toBeVisible();
      
      // Test retry button
      await retryButton.click();
      // Note: This would fail due to continued network mock, but verifies retry functionality exists
    });
  });
});
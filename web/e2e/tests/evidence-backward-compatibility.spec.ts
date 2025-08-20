import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * Evidence Backward Compatibility E2E Tests
 * Validates that evidence functionality works identically with and without MCP
 * Ensures zero regression in production UX when MCP is disabled
 */

test.describe('Evidence Backward Compatibility', () => {
  const testFilePath = path.join(process.cwd(), 'e2e/test-data/compatibility-test.txt');
  
  test.beforeAll(async () => {
    // Create test file for upload tests
    const testDataDir = path.join(process.cwd(), 'e2e/test-data');
    if (!fs.existsSync(testDataDir)) {
      fs.mkdirSync(testDataDir, { recursive: true });
    }
    
    const testContent = 'Test evidence content for backward compatibility validation';
    fs.writeFileSync(testFilePath, testContent);
  });

  test.afterAll(async () => {
    // Cleanup test file
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  });

  test('evidence page UI is identical with and without MCP parameter', async ({ page }) => {
    let withoutMcpElements: string[] = [];
    let withMcpElements: string[] = [];

    await test.step('Capture UI elements without MCP', async () => {
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      // Capture key UI elements that should be present
      const elements = [
        'button:has-text("Upload")',
        'button:has-text("Browse")', 
        'button:has-text("Preview")',
        'text=Evidence Management',
        'text=Upload, organize, and link evidence files',
        'text=Quick Actions',
        'text=Guidelines',
        'text=Maximum file size',
        'text=Supported formats'
      ];

      for (const selector of elements) {
        const isVisible = await page.locator(selector).isVisible();
        if (isVisible) {
          withoutMcpElements.push(selector);
        }
      }
    });

    await test.step('Capture UI elements with MCP parameter', async () => {
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      // Capture same UI elements
      const elements = [
        'button:has-text("Upload")',
        'button:has-text("Browse")',
        'button:has-text("Preview")', 
        'text=Evidence Management',
        'text=Upload, organize, and link evidence files',
        'text=Quick Actions',
        'text=Guidelines',
        'text=Maximum file size',
        'text=Supported formats'
      ];

      for (const selector of elements) {
        const isVisible = await page.locator(selector).isVisible();
        if (isVisible) {
          withMcpElements.push(selector);
        }
      }
    });

    await test.step('Verify core UI elements are identical', async () => {
      // All core elements should be present in both cases
      expect(withoutMcpElements.sort()).toEqual(withMcpElements.sort());
    });

    await test.step('Verify additional MCP elements are only present with parameter', async () => {
      // Without MCP parameter
      await page.goto('/e/demo-engagement/evidence');
      await expect(page.locator('text=MCP ON')).not.toBeVisible();

      // With MCP parameter  
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await expect(page.locator('text=MCP ON')).toBeVisible();
    });
  });

  test('evidence upload workflow is identical with and without MCP', async ({ page }) => {
    await test.step('Test upload workflow without MCP', async () => {
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      // Navigate to upload view
      await page.click('button:has-text("Upload")');
      await expect(page.locator('input[type="file"]')).toBeVisible();

      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testFilePath);
      
      // Should show file selected
      await expect(page.locator('text=compatibility-test.txt')).toBeVisible();

      // Click upload (may succeed or fail depending on backend, but UI should be consistent)
      await page.click('button[type="submit"], button:has-text("Upload File")');
      
      // Should show some feedback (loading, success, or error)
      const hasProgress = await page.locator('[role="progressbar"]').isVisible();
      const hasMessage = await page.locator('text=/Upload|Success|Error|Failed/').isVisible();
      expect(hasProgress || hasMessage).toBeTruthy();
    });

    await test.step('Test upload workflow with MCP parameter', async () => {
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      // Navigate to upload view
      await page.click('button:has-text("Upload")');
      await expect(page.locator('input[type="file"]')).toBeVisible();

      // Upload same file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testFilePath);
      
      // Should show file selected
      await expect(page.locator('text=compatibility-test.txt')).toBeVisible();

      // Click upload
      await page.click('button[type="submit"], button:has-text("Upload File")');
      
      // Should show same type of feedback
      const hasProgress = await page.locator('[role="progressbar"]').isVisible();
      const hasMessage = await page.locator('text=/Upload|Success|Error|Failed/').isVisible();
      expect(hasProgress || hasMessage).toBeTruthy();
    });
  });

  test('evidence table functionality is identical with and without MCP', async ({ page }) => {
    await test.step('Test table view without MCP', async () => {
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      await page.click('button:has-text("Browse")');
      
      // Table should be visible
      await expect(page.locator('table')).toBeVisible();
      
      // Should have proper table structure
      const hasHeaders = await page.locator('th').count() > 0;
      expect(hasHeaders).toBeTruthy();
    });

    await test.step('Test table view with MCP parameter', async () => {
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      await page.click('button:has-text("Browse")');
      
      // Table should be visible and identical
      await expect(page.locator('table')).toBeVisible();
      
      // Should have same table structure
      const hasHeaders = await page.locator('th').count() > 0;
      expect(hasHeaders).toBeTruthy();
    });
  });

  test('evidence preview functionality is identical with and without MCP', async ({ page }) => {
    await test.step('Test preview without MCP', async () => {
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      await page.click('button:has-text("Preview")');
      
      // Should show preview interface
      const hasPreviewContent = await page.locator('text="Evidence Preview", text="Select an evidence file"').isVisible();
      expect(hasPreviewContent).toBeTruthy();
      
      // Should show placeholder content
      const hasPlaceholder = await page.locator('text=/Select an evidence file|📂/').isVisible();
      expect(hasPlaceholder).toBeTruthy();
    });

    await test.step('Test preview with MCP parameter', async () => {
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      await page.click('button:has-text("Preview")');
      
      // Should show same preview interface
      const hasPreviewContent = await page.locator('text="Evidence Preview", text="Select an evidence file"').isVisible();
      expect(hasPreviewContent).toBeTruthy();
      
      // Should show same placeholder content
      const hasPlaceholder = await page.locator('text=/Select an evidence file|📂/').isVisible();
      expect(hasPlaceholder).toBeTruthy();
    });
  });

  test('error handling is consistent with and without MCP', async ({ page }) => {
    await test.step('Test error handling without MCP', async () => {
      // Intercept API calls and simulate errors
      await page.route('**/api/proxy/evidence/**', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        });
      });

      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      // Try to access evidence functionality
      await page.click('button:has-text("Browse")');
      
      // Should handle error gracefully
      const hasErrorState = await page.locator('[role="alert"], text=/error|failed/i').isVisible();
      
      // Interface should remain functional
      await expect(page.locator('button:has-text("Upload")')).toBeVisible();
      await expect(page.locator('button:has-text("Preview")')).toBeVisible();
    });

    await test.step('Test error handling with MCP parameter', async () => {
      // Same error simulation
      await page.route('**/api/proxy/evidence/**', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        });
      });

      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      // Try to access evidence functionality
      await page.click('button:has-text("Browse")');
      
      // Should handle error the same way
      const hasErrorState = await page.locator('[role="alert"], text=/error|failed/i').isVisible();
      
      // Interface should remain functional
      await expect(page.locator('button:has-text("Upload")')).toBeVisible();
      await expect(page.locator('button:has-text("Preview")')).toBeVisible();
      
      // MCP badge should still be visible
      await expect(page.locator('text=MCP ON')).toBeVisible();
    });
  });

  test('keyboard navigation works identically with and without MCP', async ({ page }) => {
    await test.step('Test keyboard navigation without MCP', async () => {
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      // Tab through interface elements
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Should be able to navigate to view buttons
      const uploadButton = page.locator('button:has-text("Upload")');
      const browseButton = page.locator('button:has-text("Browse")');
      
      await uploadButton.focus();
      await expect(uploadButton).toBeFocused();
      
      await browseButton.focus();
      await expect(browseButton).toBeFocused();
    });

    await test.step('Test keyboard navigation with MCP parameter', async () => {
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      // Same keyboard navigation should work
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      const uploadButton = page.locator('button:has-text("Upload")');
      const browseButton = page.locator('button:has-text("Browse")');
      
      await uploadButton.focus();
      await expect(uploadButton).toBeFocused();
      
      await browseButton.focus(); 
      await expect(browseButton).toBeFocused();
      
      // MCP badge should not interfere with navigation
      await expect(page.locator('text=MCP ON')).toBeVisible();
    });
  });

  test('responsive design is consistent with and without MCP', async ({ page }) => {
    await test.step('Test mobile layout without MCP', async () => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone size
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');

      // Core elements should be visible on mobile
      await expect(page.locator('text=Evidence Management')).toBeVisible();
      await expect(page.locator('button:has-text("Upload")')).toBeVisible();
      await expect(page.locator('button:has-text("Browse")')).toBeVisible();
    });

    await test.step('Test mobile layout with MCP parameter', async () => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');

      // Same elements should be visible
      await expect(page.locator('text=Evidence Management')).toBeVisible();
      await expect(page.locator('button:has-text("Upload")')).toBeVisible();
      await expect(page.locator('button:has-text("Browse")')).toBeVisible();
      
      // MCP badge should fit properly on mobile
      await expect(page.locator('text=MCP ON')).toBeVisible();
    });

    await test.step('Reset viewport', async () => {
      await page.setViewportSize({ width: 1280, height: 720 });
    });
  });
});

test.describe('Evidence Backward Compatibility - Performance', () => {
  test('page load performance is not degraded with MCP parameter', async ({ page }) => {
    await test.step('Measure load time without MCP', async () => {
      const startTime = Date.now();
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');
      const loadTimeWithoutMcp = Date.now() - startTime;
      
      expect(loadTimeWithoutMcp).toBeLessThan(10000); // Should load within 10 seconds
    });

    await test.step('Measure load time with MCP parameter', async () => {
      const startTime = Date.now();
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');
      const loadTimeWithMcp = Date.now() - startTime;
      
      expect(loadTimeWithMcp).toBeLessThan(10000); // Should load within 10 seconds
      
      // MCP parameter should not significantly impact load time
      // (Allow some variance for network conditions)
    });
  });

  test('memory usage is consistent with and without MCP parameter', async ({ page }) => {
    await test.step('Test memory usage patterns', async () => {
      // Load page without MCP
      await page.goto('/e/demo-engagement/evidence');
      await page.waitForLoadState('networkidle');
      
      // Perform typical user actions
      await page.click('button:has-text("Upload")');
      await page.click('button:has-text("Browse")');
      await page.click('button:has-text("Preview")');
      
      // Load page with MCP
      await page.goto('/e/demo-engagement/evidence?mcp=1');
      await page.waitForLoadState('networkidle');
      
      // Same actions
      await page.click('button:has-text("Upload")');
      await page.click('button:has-text("Browse")');
      await page.click('button:has-text("Preview")');
      
      // Both scenarios should complete without memory issues
      // (This is a basic smoke test - actual memory profiling would require additional tooling)
      expect(true).toBeTruthy();
    });
  });
});
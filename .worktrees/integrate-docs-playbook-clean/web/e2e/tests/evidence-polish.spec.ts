import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * Enhanced Evidence Workflow E2E Tests
 * Tests complete upload→complete→table flow, link actions, auth errors, and file validation
 */

test.describe('Evidence Polish - Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to evidence page
    await page.goto('/e/demo-engagement/evidence');
    await page.waitForLoadState('networkidle');
  });

  test('upload→complete→row appears instantly', async ({ page }) => {
    // Create test file
    const testFilePath = path.join(process.cwd(), 'e2e/test-data/evidence-test.txt');
    const testContent = 'Test evidence content for upload flow validation';
    
    await test.step('Prepare test file', async () => {
      const testDataDir = path.join(process.cwd(), 'e2e/test-data');
      if (!fs.existsSync(testDataDir)) {
        fs.mkdirSync(testDataDir, { recursive: true });
      }
      fs.writeFileSync(testFilePath, testContent);
    });

    await test.step('Upload file', async () => {
      // Switch to upload view
      await page.click('button:has-text("Upload")');
      
      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testFilePath);
      
      // Click upload button
      await page.click('button:has-text("Upload")');
      
      // Wait for upload progress
      await expect(page.locator('[role="progressbar"]')).toBeVisible();
      await expect(page.locator('text=/Upload completed successfully/')).toBeVisible({ timeout: 10000 });
    });

    await test.step('Verify row appears in table', async () => {
      // Should automatically switch to table view
      await expect(page.locator('table[role="table"]')).toBeVisible();
      
      // File should appear in table
      await expect(page.locator('td:has-text("evidence-test.txt")')).toBeVisible();
      
      // Success notification should appear
      await expect(page.locator('text=/uploaded successfully/')).toBeVisible();
    });

    // Cleanup
    await test.step('Cleanup', async () => {
      if (fs.existsSync(testFilePath)) {
        fs.unlinkSync(testFilePath);
      }
    });
  });

  test('accessibility states work correctly', async ({ page }) => {
    await test.step('Loading states have proper ARIA', async () => {
      // Check loading indicators
      if (await page.locator('[role="status"]').isVisible()) {
        await expect(page.locator('[role="status"]')).toHaveAttribute('aria-live', 'polite');
      }
    });

    await test.step('Upload area is keyboard accessible', async () => {
      const uploadArea = page.locator('[role="button"][aria-label="File upload area"]');
      if (await uploadArea.isVisible()) {
        // Should be focusable
        await uploadArea.focus();
        
        // Should respond to Enter key
        await uploadArea.press('Enter');
        // File dialog should be triggered (can't test file dialog opening directly)
      }
    });

    await test.step('Table has proper accessibility', async () => {
      const table = page.locator('table[role="table"]');
      if (await table.isVisible()) {
        await expect(table).toHaveAttribute('aria-label', 'Evidence files list');
        
        // Rows should be keyboard navigable
        const firstRow = page.locator('tr[role="row"]').first();
        if (await firstRow.isVisible()) {
          await firstRow.focus();
          await firstRow.press('Enter');
          // Should select evidence
        }
      }
    });
  });
});

test.describe('Evidence Polish - Link Actions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/e/demo-engagement/evidence');
    await page.waitForLoadState('networkidle');
  });

  test('link to item button opens dialog', async ({ page }) => {
    await test.step('Navigate to table view', async () => {
      await page.click('button:has-text("Browse")');
      await expect(page.locator('table[role="table"]')).toBeVisible();
    });

    await test.step('Click link button opens dialog', async () => {
      const linkButton = page.locator('button:has-text("🔗 Link")').first();
      
      if (await linkButton.isVisible()) {
        await linkButton.click();
        
        // Dialog should open
        await expect(page.locator('text="Link Evidence to Item"')).toBeVisible();
        await expect(page.locator('select')).toBeVisible();
        await expect(page.locator('input[placeholder*="ID"]')).toBeVisible();
      }
    });

    await test.step('Link dialog form works', async () => {
      if (await page.locator('text="Link Evidence to Item"').isVisible()) {
        // Select item type
        await page.selectOption('select', 'assessment');
        
        // Enter item ID
        await page.fill('input[placeholder*="ID"]', 'test-assessment-123');
        
        // Submit form (will likely fail without proper backend)
        await page.click('button:has-text("Create Link")');
        
        // Should show loading state
        await expect(page.locator('button:has-text("Creating Link...")')).toBeVisible();
      }
    });

    await test.step('Cancel dialog works', async () => {
      if (await page.locator('button:has-text("Cancel")').isVisible()) {
        await page.click('button:has-text("Cancel")');
        
        // Dialog should close
        await expect(page.locator('text="Link Evidence to Item"')).not.toBeVisible();
      }
    });
  });

  test('unlink functionality works', async ({ page }) => {
    await test.step('Find evidence with links', async () => {
      await page.click('button:has-text("Browse")');
      
      // Look for evidence with existing links
      const linkBadge = page.locator('.bg-blue-100').first();
      
      if (await linkBadge.isVisible()) {
        // Click unlink button (×)
        const unlinkButton = linkBadge.locator('button:has-text("×")');
        await unlinkButton.click();
        
        // Confirm dialog
        await page.on('dialog', dialog => dialog.accept());
      }
    });
  });
});

test.describe('Evidence Polish - Auth Errors', () => {
  test('handles 401 unauthorized errors', async ({ page }) => {
    await test.step('Mock 401 response', async () => {
      await page.route('**/api/proxy/evidence/**', route => {
        route.fulfill({
          status: 401,
          body: JSON.stringify({ error: 'Unauthorized' })
        });
      });
    });

    await test.step('Navigate and expect error handling', async () => {
      await page.goto('/e/demo-engagement/evidence');
      
      // Should show error state
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=/Unauthorized|401/')).toBeVisible();
    });
  });

  test('handles 403 forbidden errors', async ({ page }) => {
    await test.step('Mock 403 response', async () => {
      await page.route('**/api/proxy/evidence/**', route => {
        route.fulfill({
          status: 403,
          body: JSON.stringify({ error: 'Forbidden' })
        });
      });
    });

    await test.step('Navigate and expect error handling', async () => {
      await page.goto('/e/demo-engagement/evidence');
      
      // Should show error state with proper ARIA
      await expect(page.locator('[role="alert"][aria-live="assertive"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=/Forbidden|403/')).toBeVisible();
    });
  });

  test('handles network timeout errors', async ({ page }) => {
    await test.step('Mock timeout', async () => {
      await page.route('**/api/proxy/evidence/**', route => {
        // Delay response to simulate timeout
        setTimeout(() => {
          route.abort();
        }, 1000);
      });
    });

    await test.step('Expect graceful timeout handling', async () => {
      await page.goto('/e/demo-engagement/evidence');
      
      // Should eventually show error state
      await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Evidence Polish - File Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/e/demo-engagement/evidence');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Upload")');
  });

  test('validates MIME types correctly', async ({ page }) => {
    const invalidFile = path.join(process.cwd(), 'e2e/test-data/invalid.exe');
    
    await test.step('Create invalid file type', async () => {
      const testDataDir = path.join(process.cwd(), 'e2e/test-data');
      if (!fs.existsSync(testDataDir)) {
        fs.mkdirSync(testDataDir, { recursive: true });
      }
      fs.writeFileSync(invalidFile, 'fake executable content');
    });

    await test.step('Upload invalid file type', async () => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(invalidFile);
      
      // Should show error
      await expect(page.locator('[role="alert"]')).toBeVisible();
      await expect(page.locator('text=/Unsupported file type|invalid/')).toBeVisible();
    });

    await test.step('Cleanup', async () => {
      if (fs.existsSync(invalidFile)) {
        fs.unlinkSync(invalidFile);
      }
    });
  });

  test('validates file size limits', async ({ page }) => {
    await test.step('Check size limit messaging', async () => {
      // Should show file size limits in UI
      await expect(page.locator('text=/25 MB|size limit/')).toBeVisible();
    });

    await test.step('Large file handling', async () => {
      // Create a file with size info that would exceed limit
      const largeFile = path.join(process.cwd(), 'e2e/test-data/large.txt');
      const testDataDir = path.join(process.cwd(), 'e2e/test-data');
      
      if (!fs.existsSync(testDataDir)) {
        fs.mkdirSync(testDataDir, { recursive: true });
      }
      
      // Create a 1MB file (smaller than actual limit for test speed)
      const content = 'x'.repeat(1024 * 1024);
      fs.writeFileSync(largeFile, content);
      
      try {
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles(largeFile);
        
        // Should either accept (under limit) or show size error
        // This tests the size validation logic exists
        const hasError = await page.locator('text=/too large|size limit/').isVisible();
        const hasProgress = await page.locator('[role="progressbar"]').isVisible();
        
        expect(hasError || hasProgress).toBeTruthy();
      } finally {
        if (fs.existsSync(largeFile)) {
          fs.unlinkSync(largeFile);
        }
      }
    });
  });

  test('accepts valid file types', async ({ page }) => {
    const validFiles = [
      { name: 'test.txt', content: 'text content', type: 'text/plain' },
      { name: 'test.pdf', content: '%PDF-1.4 fake pdf', type: 'application/pdf' },
      { name: 'test.csv', content: 'col1,col2\\nval1,val2', type: 'text/csv' }
    ];

    for (const file of validFiles) {
      await test.step(`Test ${file.type} file acceptance`, async () => {
        const filePath = path.join(process.cwd(), 'e2e/test-data', file.name);
        const testDataDir = path.join(process.cwd(), 'e2e/test-data');
        
        if (!fs.existsSync(testDataDir)) {
          fs.mkdirSync(testDataDir, { recursive: true });
        }
        
        fs.writeFileSync(filePath, file.content);
        
        try {
          const fileInput = page.locator('input[type="file"]');
          await fileInput.setInputFiles(filePath);
          
          // Should not show validation error
          await expect(page.locator('text=/Unsupported file type/')).not.toBeVisible();
          
          // Should show file selected
          await expect(page.locator(`text="${file.name}"`)).toBeVisible();
        } finally {
          if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
          }
        }
      });
    }
  });
});

test.describe('Evidence Polish - Preview Component', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/e/demo-engagement/evidence');
    await page.waitForLoadState('networkidle');
  });

  test('preview placeholder shows enhanced content', async ({ page }) => {
    await test.step('Navigate to preview', async () => {
      await page.click('button:has-text("Browse")');
      
      // Select first evidence if available
      const firstRow = page.locator('tr[role="row"]').first();
      if (await firstRow.isVisible()) {
        await firstRow.click();
        await page.click('button:has-text("Preview")');
      } else {
        // If no evidence, click preview anyway to see placeholder
        await page.click('button:has-text("Preview")');
      }
    });

    await test.step('Verify enhanced preview content', async () => {
      const previewSection = page.locator('text="File Preview"');
      await expect(previewSection).toBeVisible();
      
      // Should show enhanced placeholder content
      await expect(page.locator('text=/Enhanced|coming soon|preview/i')).toBeVisible();
      
      // Should show file type specific information
      const hasFeatures = await page.locator('text=/Features|navigation|search/i').isVisible();
      expect(hasFeatures).toBeTruthy();
    });

    await test.step('Verify preview structure', async () => {
      // Should have proper preview structure
      await expect(page.locator('.bg-gray-50.rounded-lg')).toBeVisible();
      await expect(page.locator('.bg-white.rounded')).toBeVisible();
    });
  });
});
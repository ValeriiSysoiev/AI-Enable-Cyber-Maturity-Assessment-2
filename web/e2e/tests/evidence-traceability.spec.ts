import { test, expect } from '@playwright/test';

/**
 * Evidence Traceability Integration E2E Tests
 * Tests "View in context" functionality, citation copying, and anchor functionality
 */

test.describe('Evidence Traceability Features', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to an engagement page with evidence and citations
    await page.goto('/e/test-engagement/evidence');
    
    // Wait for page to load and evidence to be available
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="evidence-list"], .evidence-table, .evidence-item', { timeout: 10000 });
  });

  test('citation cards display correctly with metadata', async ({ page }) => {
    await test.step('Verify citation cards are visible', async () => {
      // Look for citation cards or citation list
      const citationCards = page.locator('[data-testid="citation-card"], .citation-card, .citation-item');
      
      if (await citationCards.count() > 0) {
        await expect(citationCards.first()).toBeVisible();
        
        // Check for citation metadata
        await expect(page.locator('text=/relevance|page|chunk/i').first()).toBeVisible();
      } else {
        console.warn('No citation cards found - may require evidence upload');
      }
    });

    await test.step('Verify citation excerpt display', async () => {
      // Look for citation excerpts or quoted text
      const excerpts = page.locator('[role="button"]:has-text(""), blockquote, .citation-excerpt');
      
      if (await excerpts.count() > 0) {
        await expect(excerpts.first()).toBeVisible();
      }
    });
  });

  test('copy citation functionality works', async ({ page }) => {
    await test.step('Find and click copy citation button', async () => {
      // Look for copy citation buttons
      const copyButtons = page.locator('button[aria-label*="copy"], button:has-text("copy"), .copy-citation');
      
      if (await copyButtons.count() > 0) {
        // Grant clipboard permissions
        await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
        
        await copyButtons.first().click();
        
        // Verify copy success indicator
        await expect(page.locator('text=/copied|success/i')).toBeVisible({ timeout: 3000 });
      } else {
        console.warn('No copy citation buttons found');
      }
    });

    await test.step('Verify clipboard content format', async () => {
      // Check if clipboard contains properly formatted citation
      const clipboardText = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
      
      if (clipboardText) {
        // Should contain document name and excerpt
        expect(clipboardText).toMatch(/[""'].*[""']/); // Should have quoted text
        expect(clipboardText).toMatch(/\.pdf|\.docx?|\.txt/i); // Should have file extension
      }
    });
  });

  test('view in context functionality opens document viewer', async ({ page }) => {
    await test.step('Click view in context button', async () => {
      // Look for view in context buttons or clickable citations
      const viewButtons = page.locator(
        'button[aria-label*="context"], button:has-text("view"), .view-context, [role="button"]:has-text("")'
      );
      
      if (await viewButtons.count() > 0) {
        await viewButtons.first().click();
        
        // Should open document viewer modal
        await expect(page.locator('[role="dialog"], .document-viewer, .modal')).toBeVisible({ timeout: 5000 });
      } else {
        console.warn('No view in context buttons found');
      }
    });

    await test.step('Verify document viewer content', async () => {
      const modal = page.locator('[role="dialog"], .document-viewer, .modal');
      
      if (await modal.isVisible()) {
        // Should show document title
        await expect(modal.locator('text=/\.pdf|\.docx?|\.txt/i')).toBeVisible();
        
        // Should have close button
        await expect(modal.locator('button[aria-label*="close"], .close-button')).toBeVisible();
        
        // Should show document content area
        await expect(modal.locator('.document-content, .content, pre, .prose')).toBeVisible();
      }
    });

    await test.step('Test document viewer interactions', async () => {
      const modal = page.locator('[role="dialog"], .document-viewer, .modal');
      
      if (await modal.isVisible()) {
        // Test copy citation from within viewer
        const copyButton = modal.locator('button:has-text("copy"), .copy-citation');
        if (await copyButton.isVisible()) {
          await copyButton.click();
          // Should show copy confirmation
          await expect(page.locator('text=/copied/i')).toBeVisible({ timeout: 3000 });
        }
        
        // Test close via button
        const closeButton = modal.locator('button[aria-label*="close"], .close-button').first();
        await closeButton.click();
        await expect(modal).not.toBeVisible();
      }
    });
  });

  test('document viewer keyboard navigation', async ({ page }) => {
    await test.step('Open document viewer', async () => {
      const viewButtons = page.locator(
        'button[aria-label*="context"], button:has-text("view"), .view-context, [role="button"]:has-text("")'
      );
      
      if (await viewButtons.count() > 0) {
        await viewButtons.first().click();
        await expect(page.locator('[role="dialog"], .document-viewer')).toBeVisible();
      } else {
        // Skip this test if no view buttons available
        test.skip();
      }
    });

    await test.step('Test escape key closes viewer', async () => {
      await page.keyboard.press('Escape');
      await expect(page.locator('[role="dialog"], .document-viewer')).not.toBeVisible();
    });
  });

  test('citation highlighting and anchor functionality', async ({ page }) => {
    await test.step('Open document with citation highlighting', async () => {
      const viewButtons = page.locator(
        'button[aria-label*="context"], button:has-text("view"), .view-context, [role="button"]:has-text("")'
      );
      
      if (await viewButtons.count() > 0) {
        await viewButtons.first().click();
        
        const modal = page.locator('[role="dialog"], .document-viewer');
        await expect(modal).toBeVisible();
        
        // Wait for content to load
        await page.waitForTimeout(2000);
        
        // Look for highlighted text or citation anchors
        const highlights = modal.locator('.highlight, .bg-yellow-200, mark, .citation-highlight');
        
        if (await highlights.count() > 0) {
          await expect(highlights.first()).toBeVisible();
          console.log('Citation highlighting found');
        } else {
          console.warn('No citation highlighting found - may be implementation dependent');
        }
      } else {
        test.skip();
      }
    });

    await test.step('Test scroll to highlighted citation', async () => {
      const modal = page.locator('[role="dialog"], .document-viewer');
      
      if (await modal.isVisible()) {
        // Check if highlighted content is in viewport
        const highlights = modal.locator('.highlight, .bg-yellow-200, mark, .citation-highlight');
        
        if (await highlights.count() > 0) {
          const firstHighlight = highlights.first();
          
          // Verify the highlight is visible in the viewport
          await expect(firstHighlight).toBeInViewport();
        }
      }
    });
  });

  test('citation export functionality', async ({ page }) => {
    await test.step('Test citation export options', async () => {
      // Look for export buttons in citation lists
      const exportButtons = page.locator('button:has-text("export"), .export-button, button:has-text("download")');
      
      if (await exportButtons.count() > 0) {
        // Set up download listener
        const downloadPromise = page.waitForEvent('download');
        
        await exportButtons.first().click();
        
        const download = await downloadPromise;
        
        // Verify download properties
        expect(download.suggestedFilename()).toMatch(/citation.*\.(json|csv)$/i);
        
        console.log(`Downloaded file: ${download.suggestedFilename()}`);
      } else {
        console.warn('No export buttons found');
      }
    });
  });

  test('multiple citation format support', async ({ page }) => {
    await test.step('Test different citation copy formats', async () => {
      const copyButtons = page.locator('button[aria-label*="copy"], button:has-text("copy")');
      
      if (await copyButtons.count() > 0) {
        await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
        
        // Test copying multiple citations
        const buttonCount = Math.min(await copyButtons.count(), 3);
        
        for (let i = 0; i < buttonCount; i++) {
          await copyButtons.nth(i).click();
          
          // Wait for copy to complete
          await page.waitForTimeout(500);
          
          const clipboardText = await page.evaluate(() => 
            navigator.clipboard.readText().catch(() => '')
          );
          
          if (clipboardText) {
            // Verify citation format consistency
            expect(clipboardText.length).toBeGreaterThan(10);
            console.log(`Citation ${i + 1} format: ${clipboardText.slice(0, 50)}...`);
          }
        }
      }
    });
  });

  test('accessibility compliance for traceability features', async ({ page }) => {
    await test.step('Verify ARIA attributes on interactive elements', async () => {
      // Check citation cards have proper ARIA labels
      const citationButtons = page.locator('[role="button"]');
      
      for (let i = 0; i < Math.min(await citationButtons.count(), 5); i++) {
        const button = citationButtons.nth(i);
        
        if (await button.isVisible()) {
          // Should have accessible name
          const ariaLabel = await button.getAttribute('aria-label');
          const textContent = await button.textContent();
          
          expect(ariaLabel || textContent).toBeTruthy();
        }
      }
    });

    await test.step('Test keyboard navigation through citations', async () => {
      // Tab through citation elements
      const focusableElements = page.locator('button, [role="button"], a, [tabindex="0"]');
      
      if (await focusableElements.count() > 0) {
        await focusableElements.first().focus();
        
        // Verify focus is visible
        const focusedElement = page.locator(':focus');
        await expect(focusedElement).toBeVisible();
        
        // Tab to next element
        await page.keyboard.press('Tab');
        
        // Verify focus moved
        const newFocusedElement = page.locator(':focus');
        await expect(newFocusedElement).toBeVisible();
      }
    });

    await test.step('Verify modal accessibility when opened', async () => {
      const viewButtons = page.locator('button[aria-label*="context"], button:has-text("view")');
      
      if (await viewButtons.count() > 0) {
        await viewButtons.first().click();
        
        const modal = page.locator('[role="dialog"]');
        if (await modal.isVisible()) {
          // Check required ARIA attributes
          await expect(modal).toHaveAttribute('aria-modal', 'true');
          await expect(modal).toHaveAttribute('aria-labelledby');
          
          // Check focus management
          const focusedElement = page.locator(':focus');
          await expect(focusedElement).toBeVisible();
        }
      }
    });
  });

  test('error handling for missing or corrupted documents', async ({ page }) => {
    await test.step('Test graceful handling of missing documents', async () => {
      // Simulate network errors for document loading
      await page.route('**/api/evidence/**', route => route.abort());
      
      const viewButtons = page.locator('button[aria-label*="context"], button:has-text("view")');
      
      if (await viewButtons.count() > 0) {
        await viewButtons.first().click();
        
        const modal = page.locator('[role="dialog"], .document-viewer');
        
        if (await modal.isVisible()) {
          // Should show error state
          await expect(page.locator('text=/error|failed|not found/i')).toBeVisible({ timeout: 10000 });
          
          // Should have retry option
          const retryButton = page.locator('button:has-text("retry"), .retry-button');
          if (await retryButton.isVisible()) {
            await expect(retryButton).toBeVisible();
          }
        }
      }
    });
  });
});
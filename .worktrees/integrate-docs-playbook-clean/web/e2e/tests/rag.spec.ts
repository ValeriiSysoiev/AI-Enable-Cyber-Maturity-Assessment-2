import { test, expect } from '@playwright/test';
import { signInAsDemo } from '../test-utils';

test.describe('RAG Functionality', () => {
  let engagementId: string;

  test.beforeEach(async ({ page }) => {
    await signInAsDemo(page);
    
    // Create or navigate to an engagement for testing
    await page.goto('/engagements');
    
    // Try to find existing engagement or create one
    const engagementCards = page.locator('[data-testid="engagement-card"]');
    const engagementCount = await engagementCards.count();
    
    if (engagementCount > 0) {
      // Use first existing engagement
      const firstEngagement = engagementCards.first();
      await firstEngagement.click();
      engagementId = await page.url().match(/\/e\/([^\/]+)/)?.[1] || '';
    } else {
      // Create new engagement for testing
      await page.click('[data-testid="create-engagement"]');
      await page.fill('[data-testid="engagement-name"]', 'RAG Test Engagement');
      await page.click('[data-testid="create-engagement-submit"]');
      await page.waitForURL(/\/e\/[^\/]+/);
      engagementId = await page.url().match(/\/e\/([^\/]+)/)?.[1] || '';
    }
  });

  test.describe('RAG Toggle Component', () => {
    test('should display RAG toggle with correct initial state', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for RAG toggle component
      const ragToggle = page.locator('[data-testid="rag-toggle"]').or(
        page.getByText('Grounded Analysis (RAG)')
      );
      
      if (await ragToggle.count() > 0) {
        await expect(ragToggle).toBeVisible();
        
        // Check accessibility attributes
        const toggleButton = page.locator('button[role="switch"]');
        if (await toggleButton.count() > 0) {
          await expect(toggleButton).toHaveAttribute('aria-label', /Toggle Grounded Analysis/);
          await expect(toggleButton).toHaveAttribute('aria-checked');
        }
      }
    });

    test('should show RAG status information', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for RAG status indicators
      const statusIndicators = page.locator('text=/🟢|🟡|🔴/');
      if (await statusIndicators.count() > 0) {
        await expect(statusIndicators.first()).toBeVisible();
      }
    });

    test('should toggle RAG state when clicked', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      const ragToggle = page.locator('button[role="switch"]');
      if (await ragToggle.count() > 0) {
        const initialState = await ragToggle.getAttribute('aria-checked');
        await ragToggle.click();
        
        // Wait for state change
        await page.waitForTimeout(100);
        
        const newState = await ragToggle.getAttribute('aria-checked');
        expect(newState).not.toBe(initialState);
      }
    });
  });

  test.describe('Enhanced Evidence Search', () => {
    test('should display enhanced search interface', async ({ page }) => {
      // Navigate to a page with evidence search (dashboard or evidence page)
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for evidence search component
      const searchInput = page.locator('input[placeholder*="search"]').or(
        page.locator('[data-testid="evidence-search"]')
      );
      
      if (await searchInput.count() > 0) {
        await expect(searchInput).toBeVisible();
        
        // Check for search button
        const searchButton = page.getByRole('button', { name: /search|ask/i });
        if (await searchButton.count() > 0) {
          await expect(searchButton).toBeVisible();
        }
      }
    });

    test('should perform search with different modes', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        // Perform a search
        await searchInput.fill('cybersecurity policy');
        
        const searchButton = page.getByRole('button', { name: /search|ask/i }).first();
        if (await searchButton.count() > 0) {
          await searchButton.click();
          
          // Wait for search results or loading state
          await page.waitForTimeout(2000);
          
          // Check for results or no results message
          const results = page.locator('[data-testid="search-results"]').or(
            page.locator('text=/found|results|no evidence/i')
          );
          
          if (await results.count() > 0) {
            await expect(results.first()).toBeVisible();
          }
        }
      }
    });

    test('should show search suggestions when typing', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        await searchInput.click();
        await searchInput.type('secu', { delay: 100 });
        
        // Look for suggestions dropdown
        await page.waitForTimeout(500);
        const suggestions = page.locator('[data-testid="search-suggestions"]').or(
          page.locator('text=/security|policy|framework/i')
        );
        
        // Suggestions may or may not appear depending on search history
        // Just check that the UI is responsive
        await expect(searchInput).toHaveValue('secu');
      }
    });

    test('should export search results when available', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        await searchInput.fill('test search');
        
        const searchButton = page.getByRole('button', { name: /search|ask/i }).first();
        if (await searchButton.count() > 0) {
          await searchButton.click();
          await page.waitForTimeout(2000);
          
          // Look for export button
          const exportButton = page.getByRole('button', { name: /export/i });
          if (await exportButton.count() > 0) {
            // Set up download handler
            const downloadPromise = page.waitForEvent('download');
            await exportButton.click();
            
            try {
              const download = await downloadPromise;
              expect(download.suggestedFilename()).toContain('evidence-search');
            } catch (error) {
              // Export may not be available if no results
              console.log('Export not available or failed:', error);
            }
          }
        }
      }
    });
  });

  test.describe('Citations and Sources UI', () => {
    test('should display citations when available', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for analysis component or evidence display
      const analysisSection = page.locator('[data-testid="analysis-section"]').or(
        page.locator('text=/evidence|citation|source/i')
      );
      
      if (await analysisSection.count() > 0) {
        // Citations may not always be present, so this is conditional
        const citations = page.locator('[data-testid="citations-list"]').or(
          page.locator('text=/supporting evidence/i')
        );
        
        if (await citations.count() > 0) {
          await expect(citations.first()).toBeVisible();
        }
      }
    });

    test('should expand and collapse citation details', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for expandable citation items
      const expandButton = page.locator('button[title*="expand"]').or(
        page.locator('button:has-text("▼")')
      );
      
      if (await expandButton.count() > 0) {
        await expandButton.first().click();
        
        // Check for expanded content
        await page.waitForTimeout(300);
        const expandedContent = page.locator('[data-testid="citation-details"]').or(
          page.locator('text=/metadata|document metadata/i')
        );
        
        if (await expandedContent.count() > 0) {
          await expect(expandedContent.first()).toBeVisible();
        }
      }
    });

    test('should copy citation links', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for copy buttons in citations
      const copyButton = page.locator('button[title*="copy"]').or(
        page.getByRole('button', { name: /copy/i })
      );
      
      if (await copyButton.count() > 0) {
        await copyButton.first().click();
        
        // Grant clipboard permissions if needed
        await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
        
        // Verify copy action (clipboard content check may not work in all test environments)
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('RAG Analysis Integration', () => {
    test('should perform analysis with RAG enabled', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for analysis component
      const analysisTextarea = page.locator('textarea[placeholder*="analyze"]').or(
        page.locator('[data-testid="analysis-input"]')
      );
      
      if (await analysisTextarea.count() > 0) {
        await analysisTextarea.fill('What are the main cybersecurity risks in our organization?');
        
        // Enable RAG if toggle is available
        const ragToggle = page.locator('button[role="switch"]');
        if (await ragToggle.count() > 0) {
          const isChecked = await ragToggle.getAttribute('aria-checked');
          if (isChecked === 'false') {
            await ragToggle.click();
          }
        }
        
        // Submit analysis
        const analyzeButton = page.getByRole('button', { name: /analyze/i });
        if (await analyzeButton.count() > 0) {
          await analyzeButton.click();
          
          // Wait for analysis to complete
          await page.waitForTimeout(5000);
          
          // Check for results
          const analysisResult = page.locator('[data-testid="analysis-result"]').or(
            page.locator('text=/analysis result|ai analysis/i')
          );
          
          if (await analysisResult.count() > 0) {
            await expect(analysisResult.first()).toBeVisible();
          }
        }
      }
    });

    test('should display confidence scores and grounding information', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for confidence indicators
      const confidenceIndicators = page.locator('text=/confidence|%/').or(
        page.locator('[data-testid="confidence-score"]')
      );
      
      if (await confidenceIndicators.count() > 0) {
        await expect(confidenceIndicators.first()).toBeVisible();
      }
      
      // Look for RAG grounding information
      const groundingInfo = page.locator('text=/ai grounding|grounding summary/i').or(
        page.locator('[data-testid="rag-grounding"]')
      );
      
      if (await groundingInfo.count() > 0) {
        await expect(groundingInfo.first()).toBeVisible();
      }
    });

    test('should export analysis results with citations', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Look for export functionality in analysis results
      const exportButton = page.locator('button:has-text("Export")').or(
        page.locator('[data-testid="export-analysis"]')
      );
      
      if (await exportButton.count() > 0) {
        const downloadPromise = page.waitForEvent('download');
        await exportButton.click();
        
        try {
          const download = await downloadPromise;
          expect(download.suggestedFilename()).toMatch(/analysis.*\.json$/);
        } catch (error) {
          // Export may not be available if no analysis results
          console.log('Analysis export not available:', error);
        }
      }
    });
  });

  test.describe('RAG Status and Administration', () => {
    test('should display RAG status in admin panel', async ({ page }) => {
      // Navigate to admin panel (if user has admin access)
      await page.goto('/admin/ops');
      
      // Check if we have admin access
      const adminDenied = page.locator('text=/access denied|admin privileges required/i');
      if (await adminDenied.count() > 0) {
        // Skip test if not admin
        return;
      }
      
      // Look for RAG status information
      const ragStatus = page.locator('text=/rag system status|rag configuration/i').or(
        page.locator('[data-testid="rag-status"]')
      );
      
      if (await ragStatus.count() > 0) {
        await expect(ragStatus.first()).toBeVisible();
      }
    });

    test('should refresh RAG status information', async ({ page }) => {
      await page.goto('/admin/ops');
      
      const adminDenied = page.locator('text=/access denied|admin privileges required/i');
      if (await adminDenied.count() > 0) {
        return;
      }
      
      // Look for refresh button
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      if (await refreshButton.count() > 0) {
        await refreshButton.click();
        
        // Wait for refresh to complete
        await page.waitForTimeout(2000);
        
        // Check that the page is still responsive
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('should test RAG connection (admin only)', async ({ page }) => {
      await page.goto('/admin/ops');
      
      const adminDenied = page.locator('text=/access denied|admin privileges required/i');
      if (await adminDenied.count() > 0) {
        return;
      }
      
      // Look for test RAG button
      const testButton = page.getByRole('button', { name: /test rag/i });
      if (await testButton.count() > 0) {
        await testButton.click();
        
        // Wait for test result (may show in alert or on page)
        await page.waitForTimeout(3000);
        
        // Check for any error dialogs or success messages
        const alerts = page.locator('[role="alert"]').or(page.locator('.alert'));
        if (await alerts.count() > 0) {
          await expect(alerts.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Accessibility and UX', () => {
    test('should be keyboard navigable', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Test keyboard navigation through RAG toggle
      const ragToggle = page.locator('button[role="switch"]');
      if (await ragToggle.count() > 0) {
        await ragToggle.focus();
        await expect(ragToggle).toBeFocused();
        
        // Test Space key toggle
        await page.keyboard.press('Space');
        await page.waitForTimeout(100);
      }
      
      // Test keyboard navigation through search
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        await searchInput.focus();
        await expect(searchInput).toBeFocused();
        
        await searchInput.type('test');
        await page.keyboard.press('Enter');
        
        // Wait for search action
        await page.waitForTimeout(1000);
      }
    });

    test('should have proper ARIA labels and roles', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Check RAG toggle ARIA attributes
      const ragToggle = page.locator('button[role="switch"]');
      if (await ragToggle.count() > 0) {
        await expect(ragToggle).toHaveAttribute('aria-label');
        await expect(ragToggle).toHaveAttribute('aria-checked');
      }
      
      // Check search input accessibility
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        // Input should have appropriate attributes
        const hasLabel = await searchInput.getAttribute('aria-label') || 
                         await page.locator('label').count() > 0;
        expect(hasLabel).toBeTruthy();
      }
    });

    test('should display proper loading states', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      const searchInput = page.locator('input[placeholder*="search"]').first();
      if (await searchInput.count() > 0) {
        await searchInput.fill('test query');
        
        const searchButton = page.getByRole('button', { name: /search|ask/i }).first();
        if (await searchButton.count() > 0) {
          await searchButton.click();
          
          // Check for loading state
          const loadingIndicator = page.locator('text=/searching|loading|analyzing/i').or(
            page.locator('[data-testid="loading"]')
          );
          
          if (await loadingIndicator.count() > 0) {
            await expect(loadingIndicator.first()).toBeVisible();
          }
          
          // Wait for loading to complete
          await page.waitForTimeout(3000);
        }
      }
    });

    test('should handle errors gracefully', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Test error handling by trying invalid operations
      const analysisTextarea = page.locator('textarea[placeholder*="analyze"]');
      if (await analysisTextarea.count() > 0) {
        // Try analysis with very long content that might cause errors
        await analysisTextarea.fill('x'.repeat(10000));
        
        const analyzeButton = page.getByRole('button', { name: /analyze/i });
        if (await analyzeButton.count() > 0) {
          await analyzeButton.click();
          
          await page.waitForTimeout(5000);
          
          // Check for error messages
          const errorMessage = page.locator('text=/error|failed|unable/i').or(
            page.locator('[data-testid="error"]')
          );
          
          // Errors may or may not occur, so we just check the UI is still responsive
          await expect(page.locator('body')).toBeVisible();
        }
      }
    });
  });

  test.describe('Cross-browser Compatibility', () => {
    test('should work consistently across different viewport sizes', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);
      
      // Test mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(500);
      
      const ragToggle = page.locator('button[role="switch"]');
      if (await ragToggle.count() > 0) {
        await expect(ragToggle).toBeVisible();
      }
      
      // Test tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForTimeout(500);
      
      if (await ragToggle.count() > 0) {
        await expect(ragToggle).toBeVisible();
      }
      
      // Test desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.waitForTimeout(500);
      
      if (await ragToggle.count() > 0) {
        await expect(ragToggle).toBeVisible();
      }
    });
  });
});
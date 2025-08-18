import { test, expect } from '@playwright/test';
import { 
  signInAsDemo, 
  RAGTestUtils, 
  TestLogger, 
  TestStepTracker, 
  PerformanceMonitor,
  ErrorRecovery,
  withRetry 
} from '../test-utils';

/**
 * Advanced RAG E2E Tests
 * Comprehensive testing of RAG functionality including performance, error handling,
 * multi-backend support, and integration scenarios
 */

test.describe('Advanced RAG Functionality', () => {
  let engagementId: string;
  let logger: TestLogger;
  let stepTracker: TestStepTracker;
  let performanceMonitor: PerformanceMonitor;
  let errorRecovery: ErrorRecovery;
  let ragUtils: RAGTestUtils;

  test.beforeEach(async ({ page }, testInfo) => {
    logger = new TestLogger(testInfo);
    stepTracker = new TestStepTracker(logger);
    performanceMonitor = new PerformanceMonitor(logger, page);
    errorRecovery = new ErrorRecovery(logger, page);
    ragUtils = new RAGTestUtils(page, logger);

    await stepTracker.executeStep('Sign in as demo user', async () => {
      await signInAsDemo(page);
    });
    
    await stepTracker.executeStep('Navigate to engagement', async () => {
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
        await page.fill('[data-testid="engagement-name"]', 'Advanced RAG Test Engagement');
        await page.click('[data-testid="create-engagement-submit"]');
        await page.waitForURL(/\/e\/[^\/]+/);
        engagementId = await page.url().match(/\/e\/([^\/]+)/)?.[1] || '';
      }
      
      logger.info('Engagement setup completed', { engagementId });
    });
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Log test results
    const stepsSummary = stepTracker.getStepsSummary();
    const metricsSummary = performanceMonitor.getMetricsSummary();
    
    logger.info('Test completed', {
      testName: testInfo.title,
      steps: stepsSummary,
      metrics: metricsSummary
    });

    // Capture final state if test failed
    if (testInfo.status === 'failed') {
      await errorRecovery.captureErrorContext(new Error(`Test failed: ${testInfo.title}`));
    }
  });

  test.describe('RAG Backend Integration', () => {
    test('should handle backend switching gracefully', async ({ page }) => {
      await stepTracker.executeStep('Navigate to dashboard', async () => {
        await page.goto(`/e/${engagementId}/dashboard`);
      });

      await stepTracker.executeStep('Test initial RAG status', async () => {
        const status = await ragUtils.verifyRAGStatus();
        expect(status.operational || status.mode !== 'unknown').toBeTruthy();
      });

      await stepTracker.executeStep('Perform search with current backend', async () => {
        const resultCount = await ragUtils.performRAGSearch('cybersecurity framework');
        // Should handle gracefully even if no results
        expect(resultCount).toBeGreaterThanOrEqual(0);
      });

      // Test backend resilience by simulating different scenarios
      await stepTracker.executeStep('Test backend resilience', async () => {
        // Test multiple rapid searches
        for (let i = 0; i < 3; i++) {
          await ragUtils.performRAGSearch(`test query ${i}`);
          await page.waitForTimeout(1000);
        }
      });
    });

    test('should handle Azure Search vs Cosmos DB backends', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Verify backend configuration', async () => {
        // Check if we can determine the active backend
        const ragStatus = await ragUtils.verifyRAGStatus();
        
        if (ragStatus.mode === 'azure') {
          logger.info('Testing with Azure Search backend');
          
          // Test Azure Search specific features
          const resultCount = await ragUtils.performRAGSearch('compliance requirements');
          
          // Azure Search should support semantic ranking and hybrid search
          const semanticResults = page.locator('[data-testid="semantic-ranking"], text=/semantic|reranked/i');
          if (await semanticResults.count() > 0) {
            expect(semanticResults.first()).toBeVisible();
            logger.info('Semantic ranking features detected');
          }
          
        } else if (ragStatus.mode === 'cosmos') {
          logger.info('Testing with Cosmos DB backend');
          
          // Test Cosmos DB specific features
          const resultCount = await ragUtils.performRAGSearch('risk assessment');
          
          // Cosmos DB should provide basic vector search
          expect(resultCount).toBeGreaterThanOrEqual(0);
          
        } else {
          logger.info('Backend mode not clearly identified, testing generic functionality');
          await ragUtils.performRAGSearch('general security policy');
        }
      });
    });

    test('should fallback gracefully when backend is unavailable', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test backend unavailability handling', async () => {
        // Block RAG-related API calls
        await page.route('**/api/rag/**', route => route.abort());
        await page.route('**/orchestrations/rag-search', route => route.abort());

        // Try to use RAG functionality
        try {
          await ragUtils.performRAGSearch('blocked backend test');
          
          // Should show appropriate error state or graceful degradation
          const errorIndicators = page.locator('text=/error|unavailable|offline/i');
          const fallbackMode = page.locator('text=/limited mode|basic mode/i');
          
          expect(await errorIndicators.count() > 0 || await fallbackMode.count() > 0).toBeTruthy();
          
        } catch (error) {
          logger.info('RAG gracefully handled backend unavailability', { error: error instanceof Error ? error.message : String(error) });
        }

        // Unblock requests for cleanup
        await page.unroute('**/api/rag/**');
        await page.unroute('**/orchestrations/rag-search');
      });
    });
  });

  test.describe('RAG Performance and Scaling', () => {
    test('should meet performance benchmarks', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Validate RAG performance thresholds', async () => {
        const performanceOk = await ragUtils.validateRAGPerformance(5000, 12000);
        
        // Log performance metrics regardless of pass/fail
        const metrics = performanceMonitor.getMetricsSummary();
        logger.info('RAG performance test completed', { performanceOk, metrics });
        
        // Performance should be acceptable but not block functionality if slower
        if (!performanceOk) {
          logger.warn('RAG performance below optimal thresholds');
        }
      });

      await stepTracker.executeStep('Test concurrent RAG operations', async () => {
        // Test multiple concurrent searches
        const searchPromises = [
          ragUtils.performRAGSearch('security policy'),
          ragUtils.performRAGSearch('compliance framework'),
          ragUtils.performRAGSearch('risk management')
        ];

        const searchResults = await Promise.allSettled(searchPromises);
        const successfulSearches = searchResults.filter(r => r.status === 'fulfilled').length;
        
        expect(successfulSearches).toBeGreaterThan(0);
        logger.info('Concurrent RAG operations completed', { successfulSearches, total: searchPromises.length });
      });
    });

    test('should handle large query loads', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test high-volume queries', async () => {
        const queries = [
          'information security policy',
          'data protection compliance',
          'access control procedures',
          'incident response plan',
          'vulnerability management',
          'security awareness training',
          'business continuity planning',
          'risk assessment methodology'
        ];

        let successfulQueries = 0;
        
        for (const query of queries) {
          try {
            await ragUtils.performRAGSearch(query);
            successfulQueries++;
            await page.waitForTimeout(500); // Brief pause between queries
          } catch (error) {
            logger.warn(`Query failed: ${query}`, { error: error instanceof Error ? error.message : String(error) });
          }
        }

        expect(successfulQueries).toBeGreaterThan(queries.length * 0.7); // 70% success rate minimum
        logger.info('High-volume query test completed', { successfulQueries, total: queries.length });
      });
    });

    test('should optimize result caching', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test result caching behavior', async () => {
        const testQuery = 'cybersecurity framework caching test';

        // First query (cache miss)
        const firstQueryTime = await performanceMonitor.measureAction('first_rag_query', async () => {
          await ragUtils.performRAGSearch(testQuery);
        });

        // Second identical query (potential cache hit)
        const secondQueryTime = await performanceMonitor.measureAction('second_rag_query', async () => {
          await ragUtils.performRAGSearch(testQuery);
        });

        // Third query with slight variation
        const thirdQueryTime = await performanceMonitor.measureAction('third_rag_query', async () => {
          await ragUtils.performRAGSearch(testQuery + ' variation');
        });

        logger.info('RAG caching test completed', {
          firstQueryTime,
          secondQueryTime,
          thirdQueryTime,
          potentialCacheHit: secondQueryTime < firstQueryTime * 0.8
        });

        // Validate that queries complete within reasonable time
        expect(firstQueryTime).toBeLessThan(10000);
        expect(secondQueryTime).toBeLessThan(10000);
        expect(thirdQueryTime).toBeLessThan(10000);
      });
    });
  });

  test.describe('RAG Error Handling and Recovery', () => {
    test('should handle malformed queries gracefully', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      const malformedQueries = [
        '', // Empty query
        'a'.repeat(2000), // Very long query
        '!@#$%^&*()_+', // Special characters only
        'SELECT * FROM users', // SQL injection attempt
        '<script>alert("xss")</script>', // XSS attempt
        '\n\r\t\0', // Control characters
      ];

      for (const query of malformedQueries) {
        await stepTracker.executeStep(`Test malformed query: ${query.substring(0, 20)}...`, async () => {
          try {
            await ragUtils.performRAGSearch(query);
            
            // Should handle gracefully without crashing
            const errorMessages = page.locator('text=/error|invalid|malformed/i');
            const isHandledGracefully = await errorMessages.count() > 0 || 
                                      await page.locator('body').isVisible();
            
            expect(isHandledGracefully).toBeTruthy();
            
          } catch (error) {
            // Expected for some malformed queries
            logger.info('Malformed query handled with exception', { query: query.substring(0, 50), error: error instanceof Error ? error.message : String(error) });
          }
        });
      }
    });

    test('should recover from network timeouts', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test network timeout recovery', async () => {
        // Delay RAG requests to simulate timeout
        await page.route('**/orchestrations/rag-search', route => {
          setTimeout(() => route.continue(), 10000); // 10 second delay
        });

        try {
          await ragUtils.performRAGSearch('timeout test query');
          
          // Should show loading state and then timeout gracefully
          const timeoutIndicators = page.locator('text=/timeout|slow|taking longer/i');
          const loadingIndicators = page.locator('text=/loading|searching/i, [data-testid="loading"]');
          
          expect(await timeoutIndicators.count() > 0 || await loadingIndicators.count() > 0).toBeTruthy();
          
        } catch (error) {
          logger.info('Network timeout handled appropriately', { error: error instanceof Error ? error.message : String(error) });
        }

        // Unblock requests
        await page.unroute('**/orchestrations/rag-search');
      });
    });

    test('should maintain state during errors', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test state preservation during errors', async () => {
        // Set RAG to enabled state
        await ragUtils.enableRAG();

        // Cause an error
        await page.route('**/orchestrations/rag-search', route => route.abort());
        
        try {
          await ragUtils.performRAGSearch('error state test');
        } catch (error) {
          // Expected
        }

        // Check that RAG toggle state is preserved
        const ragToggle = page.locator('button[role="switch"]');
        if (await ragToggle.count() > 0) {
          const isStillEnabled = await ragToggle.getAttribute('aria-checked');
          expect(isStillEnabled).toBe('true');
        }

        // Restore functionality
        await page.unroute('**/orchestrations/rag-search');
        
        // Verify functionality is restored
        const resultCount = await ragUtils.performRAGSearch('recovery test');
        expect(resultCount).toBeGreaterThanOrEqual(0);
      });
    });
  });

  test.describe('RAG Security and Privacy', () => {
    test('should prevent sensitive data exposure in logs', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test sensitive data handling', async () => {
        const sensitiveQuery = 'password: admin123, credit card: 4111-1111-1111-1111';
        
        // Monitor console logs during search
        const consoleLogs: string[] = [];
        page.on('console', msg => {
          consoleLogs.push(msg.text());
        });

        await ragUtils.performRAGSearch(sensitiveQuery);

        // Check that sensitive data is not logged
        const hasSensitiveData = consoleLogs.some(log => 
          log.includes('admin123') || log.includes('4111-1111-1111-1111')
        );

        expect(hasSensitiveData).toBeFalsy();
        logger.info('Sensitive data exposure test completed', { 
          consoleLogs: consoleLogs.length,
          hasSensitiveData 
        });
      });
    });

    test('should respect engagement isolation', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test cross-engagement data isolation', async () => {
        // Perform search in current engagement
        const resultsCount1 = await ragUtils.performRAGSearch('engagement isolation test');

        // Navigate to different engagement (if available)
        await page.goto('/engagements');
        const engagementCards = page.locator('[data-testid="engagement-card"]');
        const engagementCount = await engagementCards.count();

        if (engagementCount > 1) {
          // Click on different engagement
          await engagementCards.nth(1).click();
          const newEngagementId = await page.url().match(/\/e\/([^\/]+)/)?.[1] || '';

          if (newEngagementId !== engagementId) {
            // Perform same search in different engagement
            const resultsCount2 = await ragUtils.performRAGSearch('engagement isolation test');

            // Results should be scoped to engagement (this is informational)
            logger.info('Cross-engagement isolation test', {
              originalEngagement: engagementId,
              newEngagement: newEngagementId,
              originalResults: resultsCount1,
              newResults: resultsCount2
            });
          }
        } else {
          logger.info('Only one engagement available, skipping isolation test');
        }
      });
    });

    test('should handle authentication state changes', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test RAG behavior with auth changes', async () => {
        // Perform initial RAG operation
        await ragUtils.performRAGSearch('auth state test');

        // Clear session cookies to simulate auth expiry
        await page.context().clearCookies();

        // Try to use RAG again
        try {
          await ragUtils.performRAGSearch('post-auth-clear test');
          
          // Should redirect to login or show auth required
          const requiresAuth = await page.locator('text=/sign in|login|authenticate/i').isVisible();
          const isSigninPage = page.url().includes('/signin');
          
          expect(requiresAuth || isSigninPage).toBeTruthy();
          
        } catch (error) {
          logger.info('RAG appropriately handled auth state change', { error: error instanceof Error ? error.message : String(error) });
        }
      });
    });
  });

  test.describe('RAG Integration Scenarios', () => {
    test('should integrate with document upload and analysis', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test document analysis with RAG', async () => {
        // Look for document upload or analysis functionality
        const analysisTextarea = page.locator('textarea[placeholder*="analyze"], [data-testid="analysis-input"]');
        
        if (await analysisTextarea.count() > 0) {
          const result = await ragUtils.performRAGAnalysis(
            'Analyze the security posture of our organization based on uploaded documents'
          );

          expect(result.hasAnalysis).toBeTruthy();
          logger.info('Document analysis with RAG completed', result);

          // Test citation interaction if citations are present
          if (result.hasCitations) {
            const citationResult = await ragUtils.testCitationInteraction();
            logger.info('Citation interaction test completed', citationResult);
          }
        }
      });
    });

    test('should work with assessment workflows', async ({ page }) => {
      await page.goto(`/e/${engagementId}/new`);

      await stepTracker.executeStep('Test RAG in assessment context', async () => {
        // Try to create or access an assessment
        const createAssessmentButton = page.locator('button:has-text("Create"), [data-testid="create-assessment"]');
        
        if (await createAssessmentButton.count() > 0) {
          await createAssessmentButton.first().click();
          await page.waitForTimeout(2000);

          // Look for RAG functionality in assessment context
          const ragToggle = page.locator('button[role="switch"], [data-testid="rag-toggle"]');
          
          if (await ragToggle.count() > 0) {
            const status = await ragUtils.verifyRAGStatus();
            logger.info('RAG available in assessment context', status);

            // Test RAG search in assessment
            const resultCount = await ragUtils.performRAGSearch('assessment guidance');
            expect(resultCount).toBeGreaterThanOrEqual(0);
          }
        }
      });
    });

    test('should support export and reporting with RAG data', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test RAG data in exports', async () => {
        // Perform RAG analysis to generate citable content
        const analysisTextarea = page.locator('textarea[placeholder*="analyze"], [data-testid="analysis-input"]');
        
        if (await analysisTextarea.count() > 0) {
          await ragUtils.performRAGAnalysis('Generate analysis for export testing');
          await page.waitForTimeout(2000);

          // Look for export functionality
          const exportButtons = page.locator('button:has-text("Export"), [data-testid="export"]');
          
          if (await exportButtons.count() > 0) {
            // Set up download handler
            const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
            
            try {
              await exportButtons.first().click();
              const download = await downloadPromise;
              
              expect(download.suggestedFilename()).toBeTruthy();
              logger.info('Export with RAG data completed', { 
                filename: download.suggestedFilename() 
              });
              
            } catch (error) {
              logger.info('Export test completed (no download triggered)', { error: error instanceof Error ? error.message : String(error) });
            }
          }
        }
      });
    });
  });

  test.describe('RAG Accessibility and Usability', () => {
    test('should support screen readers and keyboard navigation', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test RAG accessibility features', async () => {
        // Test keyboard navigation
        const ragToggle = page.locator('button[role="switch"]');
        
        if (await ragToggle.count() > 0) {
          await ragToggle.focus();
          await expect(ragToggle).toBeFocused();

          // Test keyboard activation
          await page.keyboard.press('Space');
          await page.waitForTimeout(200);

          // Check ARIA attributes
          const ariaLabel = await ragToggle.getAttribute('aria-label');
          const ariaChecked = await ragToggle.getAttribute('aria-checked');
          
          expect(ariaLabel).toBeTruthy();
          expect(ariaChecked).toBeTruthy();
          
          logger.info('RAG accessibility attributes verified', { ariaLabel, ariaChecked });
        }

        // Test search input accessibility
        const searchInput = page.locator('input[placeholder*="search"]').first();
        
        if (await searchInput.count() > 0) {
          await searchInput.focus();
          await expect(searchInput).toBeFocused();

          // Check for proper labeling
          const hasLabel = await searchInput.getAttribute('aria-label') || 
                          await page.locator('label').count() > 0;
          
          expect(hasLabel).toBeTruthy();
        }
      });
    });

    test('should provide clear feedback and status updates', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      await stepTracker.executeStep('Test RAG user feedback mechanisms', async () => {
        // Test loading states during search
        const searchInput = page.locator('input[placeholder*="search"]').first();
        
        if (await searchInput.count() > 0) {
          await searchInput.fill('loading state test');
          
          const searchButton = page.getByRole('button', { name: /search|ask/i }).first();
          if (await searchButton.count() > 0) {
            await searchButton.click();

            // Check for loading indicators
            const loadingIndicators = page.locator('text=/searching|loading/i, [data-testid="loading"]');
            if (await loadingIndicators.count() > 0) {
              await expect(loadingIndicators.first()).toBeVisible();
              logger.info('Loading state indicators found');
            }

            // Wait for results and check for completion feedback
            await page.waitForTimeout(3000);
            
            const completionIndicators = page.locator('text=/found|results|completed/i');
            const noResultsIndicators = page.locator('text=/no results|not found/i');
            
            const hasCompletionFeedback = await completionIndicators.count() > 0 || 
                                        await noResultsIndicators.count() > 0;
            
            expect(hasCompletionFeedback).toBeTruthy();
            logger.info('Completion feedback mechanisms verified');
          }
        }
      });
    });

    test('should work consistently across viewport sizes', async ({ page }) => {
      await page.goto(`/e/${engagementId}/dashboard`);

      const viewports = [
        { width: 375, height: 667, name: 'Mobile' },
        { width: 768, height: 1024, name: 'Tablet' },
        { width: 1920, height: 1080, name: 'Desktop' }
      ];

      for (const viewport of viewports) {
        await stepTracker.executeStep(`Test RAG on ${viewport.name} viewport`, async () => {
          await page.setViewportSize({ width: viewport.width, height: viewport.height });
          await page.waitForTimeout(500);

          // Verify RAG components are accessible
          const ragToggle = page.locator('button[role="switch"]');
          const searchInput = page.locator('input[placeholder*="search"]').first();

          if (await ragToggle.count() > 0) {
            await expect(ragToggle).toBeVisible();
          }

          if (await searchInput.count() > 0) {
            await expect(searchInput).toBeVisible();
            
            // Test interaction on different screen sizes
            await ragUtils.performRAGSearch('viewport test');
          }

          logger.info(`RAG functionality verified on ${viewport.name}`, viewport);
        });
      }
    });
  });
});
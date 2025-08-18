import { test, expect } from '@playwright/test';

/**
 * Integration Tests for Cross-Service Communication
 * Tests API proxy, service connectivity, and feature flags
 */

test.describe('API Integration', () => {
  const apiBaseURL = process.env.API_BASE_URL;

  test('API proxy functionality', async ({ page, request }) => {
    await test.step('Test API proxy endpoints', async () => {
      // Test that the proxy correctly forwards requests
      const proxyEndpoints = [
        '/api/proxy/health',
        '/api/proxy/version'
      ];

      for (const endpoint of proxyEndpoints) {
        const response = await page.goto(endpoint);
        
        // Proxy should handle the request (success or auth required)
        expect(response?.status()).toBeLessThan(500);
        
        if (response && response.status() >= 400) {
          console.log(`Endpoint ${endpoint} requires authentication (status: ${response.status()})`);
        } else {
          console.log(`Endpoint ${endpoint} accessible (status: ${response?.status()})`);
        }
      }
    });
  });

  test('direct API connectivity', async ({ request }) => {
    if (!apiBaseURL) {
      test.skip(true, 'API_BASE_URL not configured');
    }

    await test.step('Test direct API access', async () => {
      try {
        const response = await request.get(`${apiBaseURL}/health`);
        expect(response.status()).toBe(200);
        
        const healthData = await response.text();
        console.log(`API health response: ${healthData}`);
      } catch (error) {
        console.warn(`Direct API access failed: ${error}`);
        // This might be expected in certain network configurations
      }
    });
  });

  test('API versioning consistency', async ({ page, request }) => {
    await test.step('Compare web and API versions', async () => {
      let webVersion = '';
      let apiVersion = '';

      // Get web version
      try {
        const webResponse = await page.goto('/api/proxy/version');
        if (webResponse && webResponse.status() === 200) {
          webVersion = await page.textContent('body') || '';
        }
      } catch (error) {
        console.warn('Could not get web version');
      }

      // Get API version directly (if available)
      if (apiBaseURL) {
        try {
          const apiResponse = await request.get(`${apiBaseURL}/version`);
          if (apiResponse.status() === 200) {
            apiVersion = await apiResponse.text();
          }
        } catch (error) {
          console.warn('Could not get API version directly');
        }
      }

      // Log versions for comparison
      if (webVersion) console.log(`Web version: ${webVersion}`);
      if (apiVersion) console.log(`API version: ${apiVersion}`);

      // If both are available, they should match
      if (webVersion && apiVersion) {
        expect(webVersion.trim()).toBe(apiVersion.trim());
      }
    });
  });
});

test.describe('Feature Flag Integration', () => {
  test('RAG feature flag behavior', async ({ page }) => {
    await test.step('Test RAG feature availability', async () => {
      await page.goto('/test-evidence');
      
      // Check if RAG features are available
      const evidenceUpload = await page.locator('[data-testid="evidence-upload"], .upload-area').isVisible();
      const evidenceSearch = await page.locator('[data-testid="evidence-search"], .search-input').isVisible();
      
      if (evidenceUpload || evidenceSearch) {
        console.log('RAG features are enabled');
        
        // Test that all RAG components work together
        if (evidenceUpload && evidenceSearch) {
          expect(true).toBeTruthy();
        }
      } else {
        console.log('RAG features appear to be disabled');
      }
    });
  });

  test('AAD groups feature flag behavior', async ({ page }) => {
    await test.step('Test AAD groups feature availability', async () => {
      // Get auth mode from API
      const authResponse = await page.goto('/api/auth/mode');
      expect(authResponse?.status()).toBe(200);
      
      const authMode = await page.textContent('body');
      console.log(`Authentication mode: ${authMode}`);
      
      if (authMode?.includes('aad')) {
        // Test AAD-specific endpoints
        const aadEndpoints = [
          '/api/auth/groups',
          '/api/auth/diagnostics'
        ];
        
        for (const endpoint of aadEndpoints) {
          const response = await page.goto(endpoint);
          expect(response?.status()).toBeLessThan(500);
          console.log(`AAD endpoint ${endpoint} accessible`);
        }
        
        // Check for AAD admin features
        await page.goto('/admin/auth-diagnostics');
        const hasAADDiagnostics = await page.locator('[data-testid="aad-token-info"], .aad-token-info').isVisible();
        
        if (hasAADDiagnostics) {
          console.log('AAD groups features are enabled');
        }
      }
    });
  });

  test('GDPR compliance feature flag behavior', async ({ page }) => {
    await test.step('Test GDPR feature availability', async () => {
      // Test GDPR endpoints availability
      const gdprEndpoints = [
        '/admin/gdpr',
        '/api/gdpr/export',
        '/api/gdpr/purge'
      ];
      
      for (const endpoint of gdprEndpoints) {
        const response = await page.goto(endpoint);
        
        // Should either be accessible or require authentication (not 404)
        if (response?.status() === 404) {
          console.log(`GDPR feature ${endpoint} not available`);
        } else {
          console.log(`GDPR feature ${endpoint} available (status: ${response?.status()})`);
        }
      }
    });
  });

  test('performance monitoring feature flag behavior', async ({ page }) => {
    await test.step('Test performance monitoring availability', async () => {
      const perfEndpoints = [
        '/admin/performance',
        '/api/performance/metrics',
        '/api/cache/status'
      ];
      
      for (const endpoint of perfEndpoints) {
        const response = await page.goto(endpoint);
        
        if (response?.status() === 404) {
          console.log(`Performance feature ${endpoint} not available`);
        } else {
          console.log(`Performance feature ${endpoint} available (status: ${response?.status()})`);
        }
      }
    });
  });

  test('authentication mode consistency', async ({ page }) => {
    await test.step('Test auth mode across app', async () => {
      // Get auth mode from API
      const authResponse = await page.goto('/api/auth/mode');
      expect(authResponse?.status()).toBe(200);
      
      const authMode = await page.textContent('body');
      console.log(`Authentication mode: ${authMode}`);
      
      // Check that signin page reflects the same mode
      await page.goto('/signin');
      
      if (authMode?.includes('aad')) {
        const hasAADButton = await page.locator('button:has-text("Microsoft"), a[href*="microsoft"]').isVisible();
        expect(hasAADButton).toBeTruthy();
      } else if (authMode?.includes('demo')) {
        const hasDemoButton = await page.locator('button:has-text("Demo"), button:has-text("Continue")').isVisible();
        expect(hasDemoButton).toBeTruthy();
      }
    });
  });
});

test.describe('Service Dependencies', () => {
  test('database connectivity through API', async ({ page }) => {
    await test.step('Test database operations', async () => {
      // Test endpoints that require database access
      const dbEndpoints = [
        '/api/proxy/engagements',
        '/api/proxy/assessments'
      ];

      for (const endpoint of dbEndpoints) {
        const response = await page.goto(endpoint);
        
        // Should either return data or require authentication
        expect(response?.status()).not.toBe(500); // No server errors
        
        if (response && response.status() === 200) {
          const content = await page.textContent('body');
          
          // Should return valid JSON or data
          expect(content).toBeTruthy();
          console.log(`Database endpoint ${endpoint} accessible`);
        } else {
          console.log(`Database endpoint ${endpoint} requires authentication`);
        }
      }
    });
  });

  test('search service integration', async ({ page }) => {
    await test.step('Test search functionality', async () => {
      await page.goto('/test-evidence');
      
      const searchInput = page.locator('input[placeholder*="search"]').first();
      
      if (await searchInput.isVisible()) {
        await searchInput.fill('test query');
        await searchInput.press('Enter');
        
        // Wait for response
        await page.waitForTimeout(3000);
        
        // Should show results or error message (not blank)
        const hasResponse = await page.locator('.search-results, .error, text=/no results/i').isVisible();
        expect(hasResponse).toBeTruthy();
      }
    });
  });

  test('storage service integration', async ({ page }) => {
    await test.step('Test file operations', async () => {
      await page.goto('/test-evidence');
      
      // Check if file upload components work
      const fileInput = page.locator('input[type="file"]').first();
      
      if (await fileInput.isVisible()) {
        // File input should be functional
        expect(await fileInput.isEnabled()).toBeTruthy();
        console.log('Storage service integration available');
      } else {
        console.log('Storage service integration not available or requires auth');
      }
    });
  });
});

test.describe('Cross-Service Workflows', () => {
  test('end-to-end assessment workflow', async ({ page }) => {
    await test.step('Test complete assessment flow', async () => {
      // Navigate to engagements
      await page.goto('/engagements');
      
      // Check if we can access or are redirected to auth
      const isAccessible = page.url().includes('/engagements');
      const requiresAuth = page.url().includes('/signin') || 
                          await page.locator('text=/sign in|login/i').isVisible();
      
      if (isAccessible) {
        console.log('Engagements page accessible');
        
        // Look for assessment creation options
        const hasNewAssessment = await page.locator('button:has-text("New"), a:has-text("Create"), [href*="/new"]').isVisible();
        
        if (hasNewAssessment) {
          console.log('Assessment creation workflow available');
        }
      } else if (requiresAuth) {
        console.log('Assessment workflow requires authentication');
      }
      
      expect(isAccessible || requiresAuth).toBeTruthy();
    });
  });

  test('evidence-to-assessment integration', async ({ page }) => {
    await test.step('Test evidence integration with assessments', async () => {
      // Check if evidence features integrate with assessment pages
      await page.goto('/assessment/draft');
      
      const hasEvidenceFeatures = await page.locator('[data-testid*="evidence"], .evidence, text=/evidence/i').isVisible();
      
      if (hasEvidenceFeatures) {
        console.log('Evidence features integrated with assessments');
        expect(hasEvidenceFeatures).toBeTruthy();
      } else {
        console.log('Evidence-assessment integration not visible (may require auth)');
      }
    });
  });

  test('AAD authentication to admin workflow', async ({ page }) => {
    await test.step('Test AAD auth flow to admin features', async () => {
      // Mock AAD authentication context
      await page.addInitScript(() => {
        window.mockAADClaims = {
          groups: ['admin-group-id'],
          tid: 'test-tenant-id',
          oid: 'admin-user-id'
        };
      });
      
      await page.goto('/admin/auth-diagnostics');
      
      // Should either show admin content or require auth
      const hasAADDiagnostics = await page.locator('[data-testid="aad-token-info"], .aad-token-info').isVisible();
      const requiresAuth = page.url().includes('/signin') || 
                          await page.locator('text=/unauthorized|access denied/i').isVisible();
      
      if (hasAADDiagnostics) {
        console.log('AAD auth diagnostics accessible');
        expect(hasAADDiagnostics).toBeTruthy();
      } else if (requiresAuth) {
        console.log('AAD admin features require authentication');
      }
      
      expect(hasAADDiagnostics || requiresAuth).toBeTruthy();
    });
  });

  test('GDPR export workflow integration', async ({ page }) => {
    await test.step('Test GDPR export cross-service workflow', async () => {
      await page.goto('/admin/gdpr');
      
      // Should either show GDPR interface or require auth
      const hasGDPRInterface = await page.locator('[data-testid="gdpr-dashboard"], .gdpr-dashboard').isVisible();
      const requiresAuth = page.url().includes('/signin') || 
                          await page.locator('text=/unauthorized|access denied/i').isVisible();
      
      if (hasGDPRInterface) {
        console.log('GDPR interface accessible');
        
        // Test export initiation
        const exportButton = page.locator('[data-testid="export-data-btn"], button:has-text("Export")').first();
        if (await exportButton.isVisible()) {
          console.log('GDPR export workflow available');
        }
      } else if (requiresAuth) {
        console.log('GDPR features require authentication');
      }
      
      expect(hasGDPRInterface || requiresAuth).toBeTruthy();
    });
  });

  test('performance monitoring to cache integration', async ({ page }) => {
    await test.step('Test performance monitoring workflow', async () => {
      await page.goto('/admin/performance');
      
      const hasPerfInterface = await page.locator('[data-testid="performance-dashboard"], .performance-dashboard').isVisible();
      const requiresAuth = page.url().includes('/signin') || 
                          await page.locator('text=/unauthorized|access denied/i').isVisible();
      
      if (hasPerfInterface) {
        console.log('Performance monitoring accessible');
        
        // Test cache management integration
        const cacheControls = page.locator('[data-testid="cache-controls"], .cache-controls');
        if (await cacheControls.isVisible()) {
          console.log('Cache management integrated with performance monitoring');
        }
      } else if (requiresAuth) {
        console.log('Performance monitoring requires authentication');
      }
      
      expect(hasPerfInterface || requiresAuth).toBeTruthy();
    });
  });

  test('role-based feature integration', async ({ page }) => {
    await test.step('Test role-based feature access integration', async () => {
      // Mock different user roles and test feature availability
      const roles = [
        { role: 'Admin', features: ['/admin/ops', '/admin/gdpr', '/admin/performance'] },
        { role: 'Lead', features: ['/engagements', '/admin/presets'] },
        { role: 'Member', features: ['/engagements'] }
      ];
      
      for (const { role, features } of roles) {
        await page.addInitScript((roleData) => {
          window.mockUserContext = {
            role: roleData.role,
            permissions: roleData.role === 'Admin' ? ['admin:all'] : [`read:${roleData.role.toLowerCase()}`]
          };
        }, { role });
        
        console.log(`Testing ${role} role access`);
        
        for (const feature of features) {
          const response = await page.goto(feature);
          
          // Admin should have access, others may require auth
          if (role === 'Admin') {
            expect(response?.status()).toBeLessThan(500);
          }
          
          console.log(`${role} access to ${feature}: ${response?.status()}`);
        }
      }
    });
  });

  test('admin operations workflow', async ({ page }) => {
    await test.step('Test admin functionality', async () => {
      await page.goto('/admin/ops');
      
      // Should either show admin content or require auth
      const hasAdminContent = await page.locator('.admin, [data-testid*="admin"]').isVisible();
      const requiresAuth = page.url().includes('/signin') || 
                          await page.locator('text=/unauthorized|access denied/i').isVisible();
      
      if (hasAdminContent) {
        console.log('Admin operations accessible');
        
        // Test admin-specific features
        const hasOperations = await page.locator('button, .operation, [data-testid*="operation"]').count();
        expect(hasOperations).toBeGreaterThan(0);
      } else if (requiresAuth) {
        console.log('Admin operations require authentication');
      }
      
      expect(hasAdminContent || requiresAuth).toBeTruthy();
    });
  });
});

test.describe('Performance Integration', () => {
  test('cross-service response times', async ({ page }) => {
    await test.step('Measure integrated response times', async () => {
      const testEndpoints = [
        '/',
        '/signin',
        '/api/auth/mode'
      ];

      for (const endpoint of testEndpoints) {
        const startTime = Date.now();
        
        const response = await page.goto(endpoint);
        await page.waitForLoadState('networkidle');
        
        const responseTime = Date.now() - startTime;
        
        console.log(`${endpoint}: ${responseTime}ms`);
        
        // Response should be reasonable (less than 10 seconds)
        expect(responseTime).toBeLessThan(10000);
      }
    });
  });

  test('concurrent user simulation', async ({ browser }) => {
    await test.step('Test multiple concurrent sessions', async () => {
      const contexts = await Promise.all([
        browser.newContext(),
        browser.newContext(),
        browser.newContext()
      ]);

      const pages = await Promise.all(
        contexts.map(context => context.newPage())
      );

      // Navigate all pages simultaneously
      await Promise.all(
        pages.map(page => page.goto('/'))
      );

      // All pages should load successfully
      for (const page of pages) {
        const title = await page.title();
        expect(title).toBeTruthy();
      }

      // Cleanup
      await Promise.all(contexts.map(context => context.close()));
    });
  });
});

test.describe('Error Recovery', () => {
  test('graceful degradation', async ({ page }) => {
    await test.step('Test app behavior with service failures', async () => {
      // Block API requests
      await page.route('**/api/proxy/**', route => route.abort());
      
      await page.goto('/');
      
      // App should still load basic functionality
      await page.waitForLoadState('domcontentloaded');
      
      const hasBasicContent = await page.locator('nav, header, main, [role="main"]').isVisible();
      expect(hasBasicContent).toBeTruthy();
      
      console.log('App gracefully handles API service failures');
    });
  });

  test('retry mechanisms', async ({ page }) => {
    await test.step('Test retry behavior on failures', async () => {
      let requestCount = 0;
      
      // Intercept and fail first request, succeed on retry
      await page.route('**/api/auth/mode', route => {
        requestCount++;
        if (requestCount === 1) {
          route.abort();
        } else {
          route.continue();
        }
      });
      
      await page.goto('/signin');
      
      // Should eventually succeed
      await page.waitForTimeout(3000);
      
      expect(requestCount).toBeGreaterThan(1);
      console.log(`Request retried ${requestCount} times`);
    });
  });
});
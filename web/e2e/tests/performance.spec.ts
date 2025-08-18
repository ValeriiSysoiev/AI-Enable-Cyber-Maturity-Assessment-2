import { test, expect } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor, withRetry } from '../test-utils';

/**
 * Performance & Caching Tests
 * Tests cache behavior, performance monitoring, response times, and optimization features
 */

test.describe('Cache Performance', () => {
  test('cache hit and miss behavior', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await stepTracker.executeStep('Test API cache miss (first request)', async () => {
        // Clear cache first
        await page.request.post('/api/cache/clear');
        
        // First request should be a cache miss
        const firstRequestTime = await perfMonitor.measureAction('cache_miss_request', async () => {
          await page.goto('/api/engagements');
        });
        
        // Verify response
        const response = await page.waitForResponse(/\/api\/engagements/);
        expect(response.status()).toBe(200);
        
        // Check cache headers
        const cacheStatus = response.headers()['x-cache-status'];
        expect(cacheStatus).toBe('MISS');
        
        logger.info('Cache miss detected and measured', { firstRequestTime, cacheStatus });
      });

      await stepTracker.executeStep('Test API cache hit (subsequent request)', async () => {
        // Second request should be a cache hit
        const secondRequestTime = await perfMonitor.measureAction('cache_hit_request', async () => {
          await page.goto('/api/engagements');
        });
        
        const response = await page.waitForResponse(/\/api\/engagements/);
        const cacheStatus = response.headers()['x-cache-status'];
        expect(cacheStatus).toBe('HIT');
        
        // Cache hit should be significantly faster
        const metrics = perfMonitor.getMetricsSummary();
        const missTime = metrics.metrics['cache_miss_request'][0];
        const hitTime = metrics.metrics['cache_hit_request'][0];
        
        expect(hitTime).toBeLessThan(missTime * 0.5); // At least 50% faster
        
        logger.info('Cache hit performance validated', { missTime, hitTime, improvement: ((missTime - hitTime) / missTime * 100).toFixed(2) + '%' });
      });

      await stepTracker.executeStep('Test cache invalidation', async () => {
        // Force cache invalidation
        await page.request.post('/api/cache/invalidate/engagements');
        
        // Next request should be cache miss again
        const invalidatedRequestTime = await perfMonitor.measureAction('cache_invalidated_request', async () => {
          await page.goto('/api/engagements');
        });
        
        const response = await page.waitForResponse(/\/api\/engagements/);
        const cacheStatus = response.headers()['x-cache-status'];
        expect(cacheStatus).toBe('MISS');
        
        logger.info('Cache invalidation working correctly', { invalidatedRequestTime, cacheStatus });
      });

      await stepTracker.executeStep('Test cache TTL expiration', async () => {
        // Wait for cache TTL to expire (if configured)
        await page.waitForTimeout(5000);
        
        const expiredRequestTime = await perfMonitor.measureAction('cache_expired_request', async () => {
          await page.goto('/api/engagements');
        });
        
        // Should be treated as cache miss due to expiration
        const response = await page.waitForResponse(/\/api\/engagements/);
        const cacheStatus = response.headers()['x-cache-status'];
        
        // May be MISS or EXPIRED depending on implementation
        expect(['MISS', 'EXPIRED']).toContain(cacheStatus);
        
        logger.info('Cache TTL expiration behavior validated', { expiredRequestTime, cacheStatus });
      });

      logger.info('Cache performance test completed', stepTracker.getStepsSummary());
      
    } catch (error) {
      logger.error('Cache performance test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('memory cache vs Redis cache performance', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await test.step('Test memory cache performance', async () => {
        // Configure for memory cache
        await page.request.post('/api/cache/config', {
          data: { cacheType: 'memory' }
        });
        
        // Clear cache and test performance
        await page.request.post('/api/cache/clear');
        
        const memoryMissTime = await perfMonitor.measureAction('memory_cache_miss', async () => {
          await page.goto('/api/presets');
        });
        
        const memoryHitTime = await perfMonitor.measureAction('memory_cache_hit', async () => {
          await page.goto('/api/presets');
        });
        
        logger.info('Memory cache performance measured', { memoryMissTime, memoryHitTime });
      });

      await test.step('Test Redis cache performance', async () => {
        // Configure for Redis cache
        await page.request.post('/api/cache/config', {
          data: { cacheType: 'redis' }
        });
        
        // Clear cache and test performance
        await page.request.post('/api/cache/clear');
        
        const redisMissTime = await perfMonitor.measureAction('redis_cache_miss', async () => {
          await page.goto('/api/presets');
        });
        
        const redisHitTime = await perfMonitor.measureAction('redis_cache_hit', async () => {
          await page.goto('/api/presets');
        });
        
        logger.info('Redis cache performance measured', { redisMissTime, redisHitTime });
      });

      await test.step('Compare cache performance', async () => {
        const metrics = perfMonitor.getMetricsSummary();
        
        const memoryHit = metrics.metrics['memory_cache_hit'][0];
        const redisHit = metrics.metrics['redis_cache_hit'][0];
        
        // Memory cache should generally be faster for hits
        expect(memoryHit).toBeLessThan(redisHit * 2); // Allow some variance
        
        logger.info('Cache performance comparison completed', {
          memoryHitAvg: memoryHit,
          redisHitAvg: redisHit,
          ratio: (redisHit / memoryHit).toFixed(2)
        });
      });

    } catch (error) {
      logger.error('Cache comparison test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Performance Monitoring', () => {
  test('response time validation and monitoring', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await stepTracker.executeStep('Monitor API endpoint response times', async () => {
        const endpoints = [
          '/api/engagements',
          '/api/assessments',
          '/api/presets',
          '/api/documents',
          '/api/auth/session'
        ];
        
        for (const endpoint of endpoints) {
          const responseTime = await perfMonitor.measureAction(`response_time_${endpoint.replace(/\//g, '_')}`, async () => {
            await page.goto(endpoint);
          });
          
          // Response time thresholds
          const thresholds = {
            '/api/auth/session': 500,     // Auth should be fast
            '/api/presets': 1000,         // Presets can be moderate
            '/api/engagements': 2000,     // Engagements may be slower
            '/api/assessments': 2000,     // Assessments may be slower
            '/api/documents': 3000        // Documents may be slowest
          };
          
          const threshold = thresholds[endpoint as keyof typeof thresholds] || 2000;
          expect(responseTime).toBeLessThan(threshold);
          
          logger.info(`Response time validated for ${endpoint}`, { responseTime, threshold });
        }
      });

      await stepTracker.executeStep('Test performance under load', async () => {
        // Simulate concurrent requests
        const concurrentRequests = 5;
        const promises = Array(concurrentRequests).fill(0).map(async (_, index) => {
          return perfMonitor.measureAction(`concurrent_request_${index}`, async () => {
            await page.goto('/api/engagements');
          });
        });
        
        const responseTimes = await Promise.all(promises);
        const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
        
        // Average response time should still be reasonable under load
        expect(avgResponseTime).toBeLessThan(5000);
        
        logger.info('Performance under load validated', {
          concurrentRequests,
          avgResponseTime,
          minTime: Math.min(...responseTimes),
          maxTime: Math.max(...responseTimes)
        });
      });

      await stepTracker.executeStep('Monitor memory usage patterns', async () => {
        // Test memory usage through performance API
        const memoryBefore = await page.evaluate(() => {
          return (performance as any).memory ? {
            usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
            totalJSHeapSize: (performance as any).memory.totalJSHeapSize
          } : null;
        });
        
        // Perform memory-intensive operations
        await page.goto('/api/documents?include=content');
        await page.goto('/api/assessments?include=details');
        
        const memoryAfter = await page.evaluate(() => {
          return (performance as any).memory ? {
            usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
            totalJSHeapSize: (performance as any).memory.totalJSHeapSize
          } : null;
        });
        
        if (memoryBefore && memoryAfter) {
          const memoryIncrease = memoryAfter.usedJSHeapSize - memoryBefore.usedJSHeapSize;
          
          // Memory increase should be reasonable
          expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024); // Less than 50MB increase
          
          logger.info('Memory usage patterns monitored', {
            memoryIncrease: (memoryIncrease / 1024 / 1024).toFixed(2) + ' MB',
            usedHeapBefore: (memoryBefore.usedJSHeapSize / 1024 / 1024).toFixed(2) + ' MB',
            usedHeapAfter: (memoryAfter.usedJSHeapSize / 1024 / 1024).toFixed(2) + ' MB'
          });
        }
      });

      await stepTracker.executeStep('Validate performance thresholds', async () => {
        const performanceThresholds = {
          'response_time__api_auth_session': 500,
          'response_time__api_presets': 1000,
          'response_time__api_engagements': 2000,
          'concurrent_request_0': 5000
        };
        
        const thresholdsMet = perfMonitor.validatePerformance(performanceThresholds);
        expect(thresholdsMet).toBeTruthy();
        
        logger.info('Performance thresholds validation completed', { thresholdsMet });
      });

    } catch (error) {
      logger.error('Performance monitoring test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('slow query detection and alerting', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access performance monitoring dashboard', async () => {
        await page.goto('/admin/performance');
        
        await expect(page.locator('h1:has-text("Performance Monitoring"), [data-testid="performance-dashboard"]')).toBeVisible();
        logger.info('Performance monitoring dashboard loaded');
      });

      await stepTracker.executeStep('View slow query analytics', async () => {
        // Check for slow query section
        await expect(page.locator('[data-testid="slow-queries"], .slow-queries-section')).toBeVisible();
        
        // Check for query performance data
        const queryTable = page.locator('[data-testid="query-performance-table"], .query-table');
        await expect(queryTable).toBeVisible();
        
        // Verify query information display
        const queryRows = page.locator('[data-testid="query-row"], .query-row');
        const queryCount = await queryRows.count();
        
        if (queryCount > 0) {
          const firstQuery = queryRows.first();
          await expect(firstQuery).toContainText(/ms|seconds/); // Should show timing
          await expect(firstQuery).toContainText(/SELECT|UPDATE|INSERT|DELETE/i); // Should show query type
          
          logger.info('Slow query analytics displayed', { queryCount });
        }
      });

      await stepTracker.executeStep('Test performance alert thresholds', async () => {
        // Check for alert configuration
        const alertConfig = page.locator('[data-testid="alert-config"], .alert-configuration');
        await expect(alertConfig).toBeVisible();
        
        // Verify current thresholds
        const responseTimeThreshold = page.locator('[data-testid="response-time-threshold"], input[name="responseTimeThreshold"]');
        const thresholdValue = await responseTimeThreshold.inputValue();
        
        expect(parseInt(thresholdValue)).toBeGreaterThan(0);
        
        // Test threshold update
        await responseTimeThreshold.fill('2000');
        await page.click('[data-testid="save-thresholds"], button:has-text("Save")');
        
        await expect(page.locator('text=Thresholds updated')).toBeVisible();
        
        logger.info('Performance alert thresholds configured', { thresholdValue });
      });

      await stepTracker.executeStep('Generate and detect slow query', async () => {
        // Trigger a potentially slow operation
        await page.goto('/api/reports/comprehensive?include=all');
        
        // Wait for operation to complete
        await page.waitForTimeout(3000);
        
        // Check if slow query was detected
        await page.goto('/admin/performance');
        
        const recentSlowQueries = page.locator('[data-testid="recent-slow-queries"], .recent-slow-queries');
        await expect(recentSlowQueries).toBeVisible();
        
        // Look for the comprehensive report query
        const comprehensiveQuery = page.locator('[data-testid="query-row"]:has-text("comprehensive")');
        
        if (await comprehensiveQuery.isVisible()) {
          logger.info('Slow query detection working correctly');
        } else {
          logger.info('No slow queries detected for this operation');
        }
      });

    } catch (error) {
      logger.error('Slow query detection test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Frontend Performance', () => {
  test('page load performance optimization', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    const perfMonitor = new PerformanceMonitor(logger, page);
    
    try {
      await stepTracker.executeStep('Measure initial page load performance', async () => {
        const loadTime = await perfMonitor.measurePageLoad('/engagements');
        
        // Page should load within reasonable time
        expect(loadTime).toBeLessThan(8000);
        
        logger.info('Initial page load performance measured', { loadTime });
      });

      await stepTracker.executeStep('Test lazy loading and code splitting', async () => {
        const navigationTime = await perfMonitor.measureAction('lazy_navigation', async () => {
          // Navigate to a heavy page that should use code splitting
          await page.goto('/admin/ops');
          await page.waitForSelector('[data-testid="admin-interface"], .admin-content');
        });
        
        // Subsequent navigation should be faster due to caching
        const secondNavigationTime = await perfMonitor.measureAction('cached_navigation', async () => {
          await page.goto('/engagements');
          await page.goto('/admin/ops');
          await page.waitForSelector('[data-testid="admin-interface"], .admin-content');
        });
        
        expect(secondNavigationTime).toBeLessThan(navigationTime);
        
        logger.info('Lazy loading and caching performance validated', {
          firstNavigation: navigationTime,
          cachedNavigation: secondNavigationTime
        });
      });

      await stepTracker.executeStep('Validate Core Web Vitals', async () => {
        await page.goto('/engagements');
        
        // Measure Core Web Vitals
        const webVitals = await page.evaluate(() => {
          return new Promise((resolve) => {
            new PerformanceObserver((list) => {
              const entries = list.getEntries();
              const vitals = {
                lcp: 0, // Largest Contentful Paint
                fid: 0, // First Input Delay
                cls: 0  // Cumulative Layout Shift
              };
              
              entries.forEach((entry) => {
                if (entry.entryType === 'largest-contentful-paint') {
                  vitals.lcp = entry.startTime;
                }
                if (entry.entryType === 'first-input') {
                  vitals.fid = (entry as any).processingStart - entry.startTime;
                }
                if (entry.entryType === 'layout-shift') {
                  vitals.cls += (entry as any).value;
                }
              });
              
              resolve(vitals);
            }).observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
            
            // Fallback timeout
            setTimeout(() => resolve({ lcp: 0, fid: 0, cls: 0 }), 5000);
          });
        });
        
        logger.info('Core Web Vitals measured', webVitals);
        
        // Validate against thresholds (these are generally accepted good values)
        if ((webVitals as any).lcp > 0) {
          expect((webVitals as any).lcp).toBeLessThan(2500); // LCP should be < 2.5s
        }
        if ((webVitals as any).cls > 0) {
          expect((webVitals as any).cls).toBeLessThan(0.1); // CLS should be < 0.1
        }
      });

      await stepTracker.executeStep('Test image optimization and loading', async () => {
        await page.goto('/engagements');
        
        // Wait for images to load
        await page.waitForLoadState('networkidle');
        
        // Check for lazy loaded images
        const images = page.locator('img[loading="lazy"], img[data-src]');
        const imageCount = await images.count();
        
        if (imageCount > 0) {
          logger.info('Lazy loading images detected', { imageCount });
          
          // Verify images load when scrolled into view
          await images.first().scrollIntoViewIfNeeded();
          await page.waitForTimeout(1000);
          
          const firstImageSrc = await images.first().getAttribute('src');
          expect(firstImageSrc).toBeTruthy();
          expect(firstImageSrc).not.toContain('data:image');
          
          logger.info('Lazy loading working correctly');
        }
      });

    } catch (error) {
      logger.error('Frontend performance test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });

  test('bundle size and asset optimization', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    
    try {
      await test.step('Analyze JavaScript bundle sizes', async () => {
        const responses: any[] = [];
        
        page.on('response', response => {
          if (response.url().includes('.js') && response.status() === 200) {
            responses.push({
              url: response.url(),
              size: parseInt(response.headers()['content-length'] || '0'),
              compressed: response.headers()['content-encoding'] === 'gzip'
            });
          }
        });
        
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        const totalBundleSize = responses.reduce((sum, resp) => sum + resp.size, 0);
        const compressedBundles = responses.filter(resp => resp.compressed).length;
        
        // Total JS bundle size should be reasonable
        expect(totalBundleSize).toBeLessThan(2 * 1024 * 1024); // Less than 2MB
        
        // Most bundles should be compressed
        expect(compressedBundles / responses.length).toBeGreaterThan(0.8);
        
        logger.info('Bundle size analysis completed', {
          totalSize: (totalBundleSize / 1024).toFixed(2) + ' KB',
          bundleCount: responses.length,
          compressedRatio: (compressedBundles / responses.length * 100).toFixed(1) + '%'
        });
      });

      await test.step('Verify CSS optimization', async () => {
        const cssResponses: any[] = [];
        
        page.on('response', response => {
          if (response.url().includes('.css') && response.status() === 200) {
            cssResponses.push({
              url: response.url(),
              size: parseInt(response.headers()['content-length'] || '0'),
              compressed: response.headers()['content-encoding'] === 'gzip'
            });
          }
        });
        
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        const totalCSSSize = cssResponses.reduce((sum, resp) => sum + resp.size, 0);
        
        // CSS should be optimized and compressed
        expect(totalCSSSize).toBeLessThan(500 * 1024); // Less than 500KB
        
        logger.info('CSS optimization verified', {
          totalCSSSize: (totalCSSSize / 1024).toFixed(2) + ' KB',
          cssFileCount: cssResponses.length
        });
      });

    } catch (error) {
      logger.error('Bundle optimization test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});

test.describe('Database Performance', () => {
  test('query optimization and indexing', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    const stepTracker = new TestStepTracker(logger);
    
    try {
      await stepTracker.executeStep('Access database performance metrics', async () => {
        await page.goto('/admin/db-performance');
        
        await expect(page.locator('h1:has-text("Database Performance"), [data-testid="db-performance"]')).toBeVisible();
        logger.info('Database performance dashboard loaded');
      });

      await stepTracker.executeStep('Verify query execution plans', async () => {
        // Check for query execution plan display
        const executionPlans = page.locator('[data-testid="execution-plans"], .execution-plans');
        await expect(executionPlans).toBeVisible();
        
        // Look for index usage indicators
        const indexUsage = page.locator('[data-testid="index-usage"], .index-usage');
        const indexUsageCount = await indexUsage.count();
        
        if (indexUsageCount > 0) {
          // Verify index hit ratio
          const indexHitRatio = await page.textContent('[data-testid="index-hit-ratio"], .index-hit-ratio');
          const hitRatioValue = parseFloat(indexHitRatio?.replace('%', '') || '0');
          
          expect(hitRatioValue).toBeGreaterThan(80); // Should have good index usage
          
          logger.info('Query optimization metrics verified', { indexHitRatio: hitRatioValue });
        }
      });

      await stepTracker.executeStep('Test connection pool performance', async () => {
        // Check connection pool status
        const poolStatus = page.locator('[data-testid="connection-pool"], .connection-pool-status');
        await expect(poolStatus).toBeVisible();
        
        // Verify pool metrics
        const activeConnections = await page.textContent('[data-testid="active-connections"], .active-connections');
        const maxConnections = await page.textContent('[data-testid="max-connections"], .max-connections');
        
        const active = parseInt(activeConnections || '0');
        const max = parseInt(maxConnections || '0');
        
        // Pool utilization should be reasonable
        expect(active / max).toBeLessThan(0.8); // Less than 80% utilization
        
        logger.info('Connection pool performance verified', {
          activeConnections: active,
          maxConnections: max,
          utilization: ((active / max) * 100).toFixed(1) + '%'
        });
      });

    } catch (error) {
      logger.error('Database performance test failed', { error: error instanceof Error ? error.message : error });
      throw error;
    }
  });
});
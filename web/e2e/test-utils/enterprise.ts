import { Page, expect } from '@playwright/test';
import { TestLogger } from '../test-utils';

// Extend window interface for testing
declare global {
  interface Window {
    mockAADClaims?: any;
    mockAuthMode?: string;
    mockUserContext?: any;
  }
}

/**
 * Enterprise Test Utilities
 * Specialized utilities for testing enterprise features including AAD, GDPR, and performance features
 */

export interface EnterpriseUserContext {
  userId: string;
  tenantId: string;
  role: 'Admin' | 'Lead' | 'Member' | 'TenantAdmin' | 'GlobalAdmin';
  permissions: string[];
  aadGroups?: string[];
  engagementRoles?: Record<string, string>;
}

export interface AADClaims {
  groups: string[];
  tid: string;
  oid: string;
  preferred_username?: string;
  upn?: string;
  name?: string;
}

export interface GDPRTestScenario {
  userId: string;
  reason: string;
  format: 'json' | 'csv';
  expectedStatus: 'pending' | 'running' | 'completed' | 'failed';
}

export class EnterpriseTestUtils {
  constructor(
    private page: Page,
    private logger: TestLogger
  ) {}

  /**
   * Set up AAD authentication context for testing
   */
  async setupAADContext(claims: AADClaims): Promise<void> {
    await this.page.addInitScript((aadClaims) => {
      window.mockAADClaims = aadClaims;
      window.mockAuthMode = 'aad';
    }, claims);
    
    this.logger.info('AAD context set up', { tenantId: claims.tid, groups: claims.groups });
  }

  /**
   * Set up enterprise user context with role-based permissions
   */
  async setupUserContext(context: EnterpriseUserContext): Promise<void> {
    await this.page.addInitScript((userContext) => {
      window.mockUserContext = userContext;
    }, context);
    
    this.logger.info('User context set up', { 
      role: context.role, 
      tenantId: context.tenantId,
      permissions: context.permissions.length 
    });
  }

  /**
   * Setup combined AAD and user context for comprehensive testing
   */
  async setupEnterpriseAuth(
    aadClaims: AADClaims,
    userContext: EnterpriseUserContext
  ): Promise<void> {
    await this.setupAADContext(aadClaims);
    await this.setupUserContext(userContext);
    
    this.logger.info('Enterprise authentication context established');
  }

  /**
   * Test role-based access to a specific endpoint
   */
  async testRoleBasedAccess(
    endpoint: string,
    expectedStatus: number,
    role: string
  ): Promise<boolean> {
    const response = await this.page.goto(endpoint);
    const actualStatus = response?.status() || 0;
    
    const hasAccess = actualStatus === expectedStatus;
    
    this.logger.info(`Role access test: ${role} to ${endpoint}`, {
      expectedStatus,
      actualStatus,
      hasAccess
    });
    
    return hasAccess;
  }

  /**
   * Test multi-tenant isolation by attempting cross-tenant access
   */
  async testTenantIsolation(
    userTenantId: string,
    crossTenantResourceId: string,
    endpoint: string
  ): Promise<boolean> {
    // Try to access resource from different tenant
    const crossTenantUrl = endpoint.replace('{resourceId}', crossTenantResourceId);
    const response = await this.page.goto(crossTenantUrl);
    
    // Should be denied (403/404)
    const isBlocked = response && response.status() >= 400;
    
    this.logger.info('Tenant isolation test', {
      userTenantId,
      crossTenantResourceId,
      endpoint: crossTenantUrl,
      blocked: isBlocked,
      status: response?.status()
    });
    
    return !!isBlocked;
  }

  /**
   * Initiate and monitor a GDPR export request
   */
  async initiateGDPRExport(scenario: GDPRTestScenario): Promise<string> {
    await this.page.goto('/admin/gdpr');
    
    // Fill export form
    await this.page.click('[data-testid="export-data-btn"]');
    await this.page.fill('[data-testid="export-user-id"]', scenario.userId);
    await this.page.fill('[data-testid="export-reason"]', scenario.reason);
    await this.page.selectOption('[data-testid="export-format"]', scenario.format);
    
    // Submit request
    await this.page.click('[data-testid="submit-export"]');
    
    // Get job ID
    const jobId = await this.page.textContent('[data-testid="export-job-id"]') || '';
    
    this.logger.info('GDPR export initiated', { jobId, scenario });
    
    return jobId;
  }

  /**
   * Monitor GDPR job status until completion or timeout
   */
  async monitorGDPRJob(
    jobId: string,
    expectedStatus: string,
    timeoutMs: number = 60000
  ): Promise<boolean> {
    const startTime = Date.now();
    let currentStatus = '';
    
    while (Date.now() - startTime < timeoutMs) {
      await this.page.reload();
      
      const statusElement = this.page.locator(`[data-testid="job-${jobId}-status"]`);
      if (await statusElement.isVisible()) {
        currentStatus = await statusElement.textContent() || '';
        
        if (currentStatus.toLowerCase().includes(expectedStatus.toLowerCase())) {
          this.logger.info('GDPR job completed', { jobId, status: currentStatus });
          return true;
        }
        
        if (currentStatus.toLowerCase().includes('failed')) {
          this.logger.error('GDPR job failed', { jobId, status: currentStatus });
          return false;
        }
      }
      
      await this.page.waitForTimeout(2000);
    }
    
    this.logger.warn('GDPR job monitoring timeout', { jobId, lastStatus: currentStatus });
    return false;
  }

  /**
   * Initiate GDPR data purge with safety confirmations
   */
  async initiateGDPRPurge(userId: string, reason: string): Promise<string> {
    await this.page.goto('/admin/gdpr/purge');
    
    // Fill purge form
    await this.page.fill('[data-testid="purge-user-id"]', userId);
    await this.page.fill('[data-testid="purge-reason"]', reason);
    
    // First confirmation
    await this.page.check('[data-testid="confirm-irreversible"]');
    await this.page.click('[data-testid="start-purge-btn"]');
    
    // Second confirmation dialog
    await this.page.fill('[data-testid="confirmation-text"]', 'DELETE');
    await this.page.click('[data-testid="confirm-purge-final"]');
    
    // Get purge job ID
    const purgeJobId = await this.page.textContent('[data-testid="purge-job-id"]') || '';
    
    this.logger.info('GDPR purge initiated', { purgeJobId, userId, reason });
    
    return purgeJobId;
  }

  /**
   * Test cache performance with hit/miss scenarios
   */
  async testCachePerformance(endpoint: string): Promise<{
    missTime: number;
    hitTime: number;
    improvement: number;
  }> {
    // Clear cache first
    await this.page.goto('/api/cache/clear', { method: 'POST' });
    
    // Measure cache miss
    const missStart = Date.now();
    await this.page.goto(endpoint);
    const missTime = Date.now() - missStart;
    
    // Measure cache hit
    const hitStart = Date.now();
    await this.page.goto(endpoint);
    const hitTime = Date.now() - hitStart;
    
    const improvement = ((missTime - hitTime) / missTime) * 100;
    
    this.logger.info('Cache performance measured', {
      endpoint,
      missTime,
      hitTime,
      improvement: improvement.toFixed(2) + '%'
    });
    
    return { missTime, hitTime, improvement };
  }

  /**
   * Test performance monitoring thresholds
   */
  async validatePerformanceThresholds(thresholds: Record<string, number>): Promise<boolean> {
    await this.page.goto('/admin/performance');
    
    let allThresholdsMet = true;
    
    for (const [metric, threshold] of Object.entries(thresholds)) {
      const metricElement = this.page.locator(`[data-testid="metric-${metric}"]`);
      
      if (await metricElement.isVisible()) {
        const metricValue = parseFloat(await metricElement.textContent() || '0');
        const thresholdMet = metricValue <= threshold;
        
        if (!thresholdMet) {
          allThresholdsMet = false;
          this.logger.warn('Performance threshold exceeded', {
            metric,
            value: metricValue,
            threshold,
            exceeded: metricValue - threshold
          });
        } else {
          this.logger.info('Performance threshold met', {
            metric,
            value: metricValue,
            threshold
          });
        }
      }
    }
    
    return allThresholdsMet;
  }

  /**
   * Simulate load testing with concurrent requests
   */
  async simulateLoad(
    endpoint: string,
    concurrentUsers: number,
    duration: number
  ): Promise<{
    averageResponseTime: number;
    successRate: number;
    errors: number;
  }> {
    const results: { success: boolean; responseTime: number; error?: string }[] = [];
    const startTime = Date.now();
    
    while (Date.now() - startTime < duration) {
      const promises = Array(concurrentUsers).fill(0).map(async (_, index) => {
        const requestStart = Date.now();
        
        try {
          const response = await this.page.goto(`${endpoint}?user=${index}&time=${Date.now()}`);
          const responseTime = Date.now() - requestStart;
          
          return {
            success: response ? response.status() < 400 : false,
            responseTime,
            error: response && response.status() >= 400 ? `HTTP ${response.status()}` : undefined
          };
        } catch (error) {
          return {
            success: false,
            responseTime: Date.now() - requestStart,
            error: error instanceof Error ? error.message : 'Unknown error'
          };
        }
      });
      
      const batchResults = await Promise.all(promises);
      results.push(...batchResults);
      
      // Brief pause between batches
      await this.page.waitForTimeout(100);
    }
    
    const successfulRequests = results.filter(r => r.success);
    const averageResponseTime = successfulRequests.reduce((sum, r) => sum + r.responseTime, 0) / successfulRequests.length;
    const successRate = (successfulRequests.length / results.length) * 100;
    const errors = results.length - successfulRequests.length;
    
    this.logger.info('Load simulation completed', {
      endpoint,
      totalRequests: results.length,
      successfulRequests: successfulRequests.length,
      averageResponseTime: Math.round(averageResponseTime),
      successRate: successRate.toFixed(1) + '%',
      errors
    });
    
    return { averageResponseTime, successRate, errors };
  }

  /**
   * Test audit trail creation for sensitive operations
   */
  async verifyAuditTrail(
    operation: string,
    userId: string,
    expectedDetails: Record<string, any>
  ): Promise<boolean> {
    await this.page.goto('/admin/audit-log');
    
    // Search for the audit entry
    await this.page.fill('[data-testid="audit-search"]', operation);
    await this.page.click('[data-testid="search-audit"]');
    
    // Look for the specific audit entry
    const auditEntry = this.page.locator(`[data-testid="audit-entry"]:has-text("${operation}")`).first();
    
    if (await auditEntry.isVisible()) {
      await auditEntry.click();
      
      // Verify audit details
      const auditDetails = this.page.locator('[data-testid="audit-details"]');
      const detailsText = await auditDetails.textContent() || '';
      
      // Check for expected details
      let allDetailsFound = true;
      for (const [key, value] of Object.entries(expectedDetails)) {
        if (!detailsText.includes(String(value))) {
          allDetailsFound = false;
          this.logger.warn('Expected audit detail not found', { key, value });
        }
      }
      
      this.logger.info('Audit trail verification', {
        operation,
        found: true,
        allDetailsFound
      });
      
      return allDetailsFound;
    }
    
    this.logger.warn('Audit entry not found', { operation, userId });
    return false;
  }

  /**
   * Test system health monitoring
   */
  async checkSystemHealth(): Promise<{
    healthy: boolean;
    services: Record<string, string>;
    metrics: Record<string, number>;
  }> {
    await this.page.goto('/admin/health');
    
    const services: Record<string, string> = {};
    const metrics: Record<string, number> = {};
    
    // Check service statuses
    const serviceItems = this.page.locator('[data-testid="service-item"]');
    const serviceCount = await serviceItems.count();
    
    for (let i = 0; i < serviceCount; i++) {
      const serviceItem = serviceItems.nth(i);
      const serviceName = await serviceItem.locator('[data-testid="service-name"]').textContent() || '';
      const serviceStatus = await serviceItem.locator('[data-testid="service-status"]').textContent() || '';
      
      services[serviceName] = serviceStatus;
    }
    
    // Check system metrics
    const metricCards = this.page.locator('[data-testid="metric-card"]');
    const metricCount = await metricCards.count();
    
    for (let i = 0; i < metricCount; i++) {
      const metricCard = metricCards.nth(i);
      const metricName = await metricCard.locator('[data-testid="metric-name"]').textContent() || '';
      const metricValueText = await metricCard.locator('[data-testid="metric-value"]').textContent() || '0';
      const metricValue = parseFloat(metricValueText.replace(/[^\d.-]/g, ''));
      
      metrics[metricName] = metricValue;
    }
    
    const healthy = Object.values(services).every(status => 
      status.toLowerCase().includes('healthy') || status.toLowerCase().includes('ok')
    );
    
    this.logger.info('System health check completed', {
      healthy,
      serviceCount: Object.keys(services).length,
      metricCount: Object.keys(metrics).length
    });
    
    return { healthy, services, metrics };
  }

  /**
   * Test background job management
   */
  async manageBackgroundJob(
    jobType: string,
    action: 'cancel' | 'retry' | 'view'
  ): Promise<boolean> {
    await this.page.goto('/admin/jobs');
    
    // Filter by job type
    await this.page.selectOption('[data-testid="job-type-filter"]', jobType);
    await this.page.click('[data-testid="apply-filters"]');
    
    // Find job to manage
    const jobItem = this.page.locator(`[data-testid="job-item"][data-job-type="${jobType}"]`).first();
    
    if (await jobItem.isVisible()) {
      switch (action) {
        case 'cancel':
          await jobItem.locator('[data-testid="cancel-job"]').click();
          await this.page.click('[data-testid="confirm-cancel"]');
          break;
        case 'retry':
          await jobItem.locator('[data-testid="retry-job"]').click();
          break;
        case 'view':
          await jobItem.click();
          break;
      }
      
      this.logger.info('Background job action completed', { jobType, action });
      return true;
    }
    
    this.logger.warn('No job found for action', { jobType, action });
    return false;
  }
}
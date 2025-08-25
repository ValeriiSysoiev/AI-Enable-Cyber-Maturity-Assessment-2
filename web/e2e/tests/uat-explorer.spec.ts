import { test, expect, Page, Request, Response } from '@playwright/test';
import { TestLogger, TestStepTracker, ErrorRecovery, PerformanceMonitor } from '../test-utils';

/**
 * UAT Explorer - Automated Testing and Issue Detection Suite
 * 
 * This comprehensive test suite performs production-safe exploration of the
 * application to detect issues and collect comprehensive telemetry data.
 * 
 * Features:
 * - Handles both AAD and Demo authentication modes
 * - Safe exploration without destructive operations
 * - Comprehensive error collection and reporting
 * - Performance monitoring and screenshots
 * - Custom UAT reporting format
 */

interface UATStepResult {
  name: string;
  url: string;
  httpStatus: number | null;
  timestamp: number;
  duration: number;
  success: boolean;
  error?: string;
  consoleErrors: string[];
  networkErrors: Array<{ url: string; status: number; method: string }>;
  jsExceptions: string[];
  screenshotPath?: string;
  videoPath?: string;
  visibleControls: Array<{ text: string; tag: string; role?: string; href?: string }>;
  interactions: Array<{ type: string; target: string; success: boolean; error?: string }>;
}

interface UATReport {
  testRun: {
    id: string;
    timestamp: number;
    duration: number;
    success: boolean;
    environment: {
      authMode: 'AAD' | 'DEMO';
      baseUrl: string;
      userAgent: string;
      viewport: { width: number; height: number };
    };
  };
  steps: UATStepResult[];
  summary: {
    totalSteps: number;
    successfulSteps: number;
    failedSteps: number;
    totalConsoleErrors: number;
    totalNetworkErrors: number;
    totalJsExceptions: number;
    averageDuration: number;
  };
}

class UATExplorer {
  private page: Page;
  private logger: TestLogger;
  private report: UATReport;
  private consoleErrors: string[] = [];
  private networkErrors: Array<{ url: string; status: number; method: string }> = [];
  private jsExceptions: string[] = [];

  constructor(page: Page, logger: TestLogger) {
    this.page = page;
    this.logger = logger;
    
    // Initialize report structure
    this.report = {
      testRun: {
        id: `uat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
        duration: 0,
        success: true,
        environment: {
          authMode: process.env.DEMO_E2E === '1' ? 'DEMO' : 'AAD',
          baseUrl: process.env.WEB_BASE_URL || 'http://localhost:3000',
          userAgent: '',
          viewport: { width: 0, height: 0 }
        }
      },
      steps: [],
      summary: {
        totalSteps: 0,
        successfulSteps: 0,
        failedSteps: 0,
        totalConsoleErrors: 0,
        totalNetworkErrors: 0,
        totalJsExceptions: 0,
        averageDuration: 0
      }
    };

    this.setupEventListeners();
  }

  private setupEventListeners() {
    // Console error monitoring
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        const error = msg.text();
        this.consoleErrors.push(error);
        this.logger.warn('Console error detected', { error });
      }
    });

    // Network error monitoring
    this.page.on('response', (response: Response) => {
      if (response.status() >= 400) {
        const networkError = {
          url: response.url(),
          status: response.status(),
          method: response.request().method()
        };
        this.networkErrors.push(networkError);
        this.logger.warn('Network error detected', networkError);
      }
    });

    // JavaScript exception monitoring
    this.page.on('pageerror', error => {
      const jsException = error.toString();
      this.jsExceptions.push(jsException);
      this.logger.error('JavaScript exception detected', { error: jsException });
    });
  }

  async initialize(): Promise<void> {
    // Capture environment details
    const viewport = this.page.viewportSize();
    this.report.testRun.environment.userAgent = await this.page.evaluate(() => navigator.userAgent);
    this.report.testRun.environment.viewport = viewport || { width: 1280, height: 720 };

    this.logger.info('UAT Explorer initialized', {
      runId: this.report.testRun.id,
      authMode: this.report.testRun.environment.authMode,
      baseUrl: this.report.testRun.environment.baseUrl
    });
  }

  async exploreStep(
    stepName: string,
    url: string,
    options: {
      expectAuth?: boolean;
      exploreInteractions?: boolean;
      maxInteractions?: number;
    } = {}
  ): Promise<UATStepResult> {
    const startTime = Date.now();
    
    // Reset step-specific error collections
    const stepConsoleErrors: string[] = [];
    const stepNetworkErrors: Array<{ url: string; status: number; method: string }> = [];
    const stepJsExceptions: string[] = [];
    
    // Track errors for this specific step
    const initialConsoleCount = this.consoleErrors.length;
    const initialNetworkCount = this.networkErrors.length;
    const initialJsCount = this.jsExceptions.length;

    const step: UATStepResult = {
      name: stepName,
      url: url,
      httpStatus: null,
      timestamp: startTime,
      duration: 0,
      success: false,
      consoleErrors: [],
      networkErrors: [],
      jsExceptions: [],
      visibleControls: [],
      interactions: []
    };

    try {
      this.logger.info(`Starting UAT step: ${stepName}`, { url });

      // Navigate and capture HTTP status - increased timeout for production
      const isProduction = process.env.NODE_ENV === 'production' || process.env.CI;
      const response = await this.page.goto(url, { 
        waitUntil: 'networkidle',
        timeout: isProduction ? 60000 : 30000 
      });
      
      step.httpStatus = response?.status() || null;

      // Wait for page to settle
      await this.page.waitForTimeout(2000);

      // Capture current URL after any redirects
      step.url = this.page.url();

      // Handle authentication if needed
      if (options.expectAuth) {
        await this.handleAuthentication();
      }

      // Collect visible controls
      step.visibleControls = await this.collectVisibleControls();

      // Perform safe interactions if requested
      if (options.exploreInteractions) {
        step.interactions = await this.performSafeInteractions(options.maxInteractions || 3);
      }

      // Collect step-specific errors
      step.consoleErrors = this.consoleErrors.slice(initialConsoleCount);
      step.networkErrors = this.networkErrors.slice(initialNetworkCount);
      step.jsExceptions = this.jsExceptions.slice(initialJsCount);

      step.success = true;
      this.logger.info(`UAT step completed: ${stepName}`, {
        httpStatus: step.httpStatus,
        finalUrl: step.url,
        controlsFound: step.visibleControls.length,
        interactionsAttempted: step.interactions.length
      });

    } catch (error) {
      step.success = false;
      step.error = error instanceof Error ? error.message : String(error);
      
      // Capture screenshot and video on error
      try {
        const screenshotPath = `artifacts/uat/error-${this.report.testRun.id}-${stepName.replace(/[^a-zA-Z0-9]/g, '_')}-${Date.now()}.png`;
        await this.page.screenshot({ path: screenshotPath, fullPage: true });
        step.screenshotPath = screenshotPath;
      } catch (screenshotError) {
        this.logger.warn('Failed to capture error screenshot', { error: screenshotError });
      }

      this.logger.error(`UAT step failed: ${stepName}`, {
        error: step.error,
        url: step.url,
        sanitizedScreenshotPath: step.screenshotPath ? step.screenshotPath.split('/').slice(-2).join('/') : undefined,
        httpStatus: step.httpStatus
      });

      // Don't throw - continue with other steps
      this.report.testRun.success = false;
    }

    step.duration = Date.now() - startTime;
    this.report.steps.push(step);

    return step;
  }

  private async handleAuthentication(): Promise<void> {
    const isDemoMode = this.report.testRun.environment.authMode === 'DEMO';
    
    if (isDemoMode) {
      // Look for demo signin options
      const demoButton = this.page.locator('button:has-text("Demo"), button:has-text("Continue"), [data-testid="demo-signin"]');
      
      if (await demoButton.first().isVisible()) {
        await demoButton.first().click();
        await this.page.waitForLoadState('networkidle');
        this.logger.info('Demo authentication completed');
      }
    } else {
      // For AAD, check if we're redirected to Microsoft login
      const currentUrl = this.page.url();
      if (currentUrl.includes('login.microsoftonline.com')) {
        this.logger.info('Detected AAD redirect - authentication required');
        // In UAT mode, we don't proceed with actual AAD login
        // This is expected behavior for production systems
      }
    }
  }

  private async collectVisibleControls(): Promise<Array<{ text: string; tag: string; role?: string; href?: string }>> {
    try {
      return await this.page.evaluate(() => {
        const controls: Array<{ text: string; tag: string; role?: string; href?: string }> = [];
        
        // Collect interactive elements
        const interactiveSelectors = [
          'button:not([disabled])',
          'a[href]:not([disabled])',
          'input[type="submit"]:not([disabled])',
          'input[type="button"]:not([disabled])',
          '[role="button"]:not([disabled])',
          '[role="link"]:not([disabled])',
          'select:not([disabled])',
          '[tabindex="0"]'
        ];

        interactiveSelectors.forEach(selector => {
          const elements = document.querySelectorAll(selector);
          elements.forEach(el => {
            if (el instanceof HTMLElement) {
              const rect = el.getBoundingClientRect();
              
              // Only include visible elements
              if (rect.width > 0 && rect.height > 0 && 
                  rect.top >= 0 && rect.left >= 0 && 
                  rect.bottom <= window.innerHeight && 
                  rect.right <= window.innerWidth) {
                
                const text = el.textContent?.trim() || el.getAttribute('aria-label') || el.getAttribute('title') || '';
                const href = el.getAttribute('href');
                const role = el.getAttribute('role');
                
                if (text.length > 0 && text.length < 100) { // Reasonable text length
                  controls.push({
                    text,
                    tag: el.tagName.toLowerCase(),
                    role: role || undefined,
                    href: href || undefined
                  });
                }
              }
            }
          });
        });

        return controls.slice(0, 20); // Limit to prevent overwhelming data
      });
    } catch (error) {
      this.logger.warn('Failed to collect visible controls', { error });
      return [];
    }
  }

  private async performSafeInteractions(maxInteractions: number): Promise<Array<{ type: string; target: string; success: boolean; error?: string }>> {
    const interactions: Array<{ type: string; target: string; success: boolean; error?: string }> = [];
    
    // Only perform safe, non-destructive interactions
    const safeSelectors = [
      { selector: 'button:has-text("View"), button:has-text("Details"), button:has-text("Info")', type: 'click' },
      { selector: 'a[href^="/"][href*="help"], a[href^="/"][href*="docs"]', type: 'hover' },
      { selector: 'select:not([data-dangerous])', type: 'focus' },
      { selector: 'input[type="text"][readonly], input[type="search"]', type: 'focus' }
    ];

    for (const { selector, type } of safeSelectors) {
      if (interactions.length >= maxInteractions) break;

      try {
        const elements = await this.page.locator(selector);
        const count = await elements.count();

        if (count > 0) {
          const element = elements.first();
          const text = await element.textContent() || await element.getAttribute('title') || selector;

          // Ensure the interaction is safe
          const href = await element.getAttribute('href');
          const isPostAction = await element.getAttribute('data-method') === 'post';
          const isDangerous = await element.getAttribute('data-dangerous') === 'true';

          if (!isPostAction && !isDangerous && (!href || !href.includes('delete') && !href.includes('remove'))) {
            switch (type) {
              case 'click':
                await element.click();
                await this.page.waitForTimeout(1000);
                break;
              case 'hover':
                await element.hover();
                await this.page.waitForTimeout(500);
                break;
              case 'focus':
                await element.focus();
                await this.page.waitForTimeout(500);
                break;
            }

            interactions.push({
              type,
              target: text.substring(0, 50),
              success: true
            });

            this.logger.info(`Safe interaction performed: ${type} on "${text.substring(0, 30)}"`);
          }
        }
      } catch (error) {
        interactions.push({
          type,
          target: selector,
          success: false,
          error: error instanceof Error ? error.message : String(error)
        });

        this.logger.warn(`Safe interaction failed: ${type} on ${selector}`, { error });
      }
    }

    return interactions;
  }

  async getFirstEngagementId(): Promise<string | null> {
    try {
      // Navigate to engagements page
      await this.page.goto('/engagements');
      await this.page.waitForLoadState('networkidle');

      // Look for engagement links
      const engagementLink = await this.page.locator('a[href*="/e/"]').first();
      
      if (await engagementLink.count() > 0) {
        const href = await engagementLink.getAttribute('href');
        const match = href?.match(/\/e\/([^\/]+)/);
        return match ? match[1] : null;
      }

      return null;
    } catch (error) {
      this.logger.warn('Failed to get first engagement ID', { error });
      return null;
    }
  }

  finalize(): UATReport {
    this.report.testRun.duration = Date.now() - this.report.testRun.timestamp;
    
    // Calculate summary statistics
    this.report.summary = {
      totalSteps: this.report.steps.length,
      successfulSteps: this.report.steps.filter(s => s.success).length,
      failedSteps: this.report.steps.filter(s => !s.success).length,
      totalConsoleErrors: this.report.steps.reduce((sum, s) => sum + s.consoleErrors.length, 0),
      totalNetworkErrors: this.report.steps.reduce((sum, s) => sum + s.networkErrors.length, 0),
      totalJsExceptions: this.report.steps.reduce((sum, s) => sum + s.jsExceptions.length, 0),
      averageDuration: this.report.steps.length > 0 
        ? this.report.steps.reduce((sum, s) => sum + s.duration, 0) / this.report.steps.length 
        : 0
    };

    this.logger.info('UAT exploration completed', this.report.summary);
    return this.report;
  }
}

test.describe('UAT Explorer - Comprehensive Application Testing', () => {
  let uatExplorer: UATExplorer;

  test.beforeEach(async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);
    uatExplorer = new UATExplorer(page, logger);
    await uatExplorer.initialize();
  });

  test('UAT Explorer - Full Application Suite', async ({ page }, testInfo) => {
    const logger = new TestLogger(testInfo);

    try {
      // Test Step 1: Home page
      await uatExplorer.exploreStep(
        'Home Page Load',
        '/',
        { exploreInteractions: true, maxInteractions: 2 }
      );

      // Test Step 2: Sign-in page
      await uatExplorer.exploreStep(
        'Sign-in Page',
        '/signin',
        { expectAuth: false, exploreInteractions: true, maxInteractions: 2 }
      );

      // Test Step 3: API Auth Providers
      await uatExplorer.exploreStep(
        'Auth Providers API',
        '/api/auth/providers',
        { expectAuth: false }
      );

      // Test Step 4: API Auth Session
      await uatExplorer.exploreStep(
        'Auth Session API',
        '/api/auth/session',
        { expectAuth: false }
      );

      // Test Step 5: Engagements page
      await uatExplorer.exploreStep(
        'Engagements Page',
        '/engagements',
        { expectAuth: true, exploreInteractions: true, maxInteractions: 3 }
      );

      // Test Step 6: First engagement detail (if available)
      const firstEngagementId = await uatExplorer.getFirstEngagementId();
      if (firstEngagementId) {
        await uatExplorer.exploreStep(
          'First Engagement Detail',
          `/e/${firstEngagementId}/dashboard`,
          { expectAuth: true, exploreInteractions: true, maxInteractions: 3 }
        );
      } else {
        logger.info('No engagements found - skipping engagement detail test');
      }

      // Test Step 7: New assessment page
      await uatExplorer.exploreStep(
        'New Assessment Page',
        '/new',
        { expectAuth: true, exploreInteractions: true, maxInteractions: 2 }
      );

      // Test Step 8: Health endpoint
      await uatExplorer.exploreStep(
        'Health Endpoint',
        '/health',
        { expectAuth: false }
      );

      // Test Step 9: Version API
      await uatExplorer.exploreStep(
        'Version API',
        '/api/version',
        { expectAuth: false }
      );

    } catch (error) {
      logger.error('UAT Explorer suite encountered critical error', { error });
      throw error;
    } finally {
      // Generate and save the UAT report
      const report = uatExplorer.finalize();
      
      // Ensure artifacts directory exists
      const fs = require('fs');
      const path = require('path');
      const artifactsDir = path.join(process.cwd(), 'artifacts', 'uat');
      
      if (!fs.existsSync(artifactsDir)) {
        fs.mkdirSync(artifactsDir, { recursive: true });
      }

      // Save the UAT report
      const reportPath = path.join(artifactsDir, 'uat_report.json');
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
      
      logger.info('UAT report saved', { 
        path: reportPath,
        runId: report.testRun.id,
        success: report.testRun.success,
        summary: report.summary
      });

      // Log final summary
      console.log('\n=== UAT Explorer Summary ===');
      console.log(`Run ID: ${report.testRun.id}`);
      console.log(`Success: ${report.testRun.success}`);
      console.log(`Total Steps: ${report.summary.totalSteps}`);
      console.log(`Successful: ${report.summary.successfulSteps}`);
      console.log(`Failed: ${report.summary.failedSteps}`);
      console.log(`Console Errors: ${report.summary.totalConsoleErrors}`);
      console.log(`Network Errors: ${report.summary.totalNetworkErrors}`);
      console.log(`JS Exceptions: ${report.summary.totalJsExceptions}`);
      console.log(`Average Duration: ${Math.round(report.summary.averageDuration)}ms`);
      console.log(`Report saved to: ${reportPath}`);
      console.log('=== End UAT Summary ===\n');
    }
  });
});
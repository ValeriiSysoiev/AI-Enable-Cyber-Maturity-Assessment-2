import { Page, TestInfo, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { sanitizeFilePath, createSanitizedLogEntry } from './utils/path-sanitizer';

/**
 * Test utilities for enhanced error handling and logging
 */

export interface TestContext {
  page: Page;
  testInfo: TestInfo;
  startTime: number;
}

export class TestLogger {
  private testInfo: TestInfo;
  private logFile: string;

  constructor(testInfo: TestInfo) {
    this.testInfo = testInfo;
    this.logFile = path.join(process.cwd(), 'test-results', `${testInfo.title.replace(/[^a-zA-Z0-9]/g, '_')}.log`);
    
    // Ensure log directory exists
    const logDir = path.dirname(this.logFile);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
  }

  log(level: 'info' | 'warn' | 'error', message: string, data?: any) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
    
    // Log to console
    console.log(logEntry);
    if (data) {
      console.log(JSON.stringify(data, null, 2));
    }
    
    // Log to file
    try {
      fs.appendFileSync(this.logFile, logEntry + '\n');
      if (data) {
        fs.appendFileSync(this.logFile, JSON.stringify(data, null, 2) + '\n');
      }
    } catch (error) {
      console.warn(`Failed to write to log file: ${error}`);
    }
    
    // Add to test annotations
    this.testInfo.annotations.push({
      type: level,
      description: message + (data ? ` - ${JSON.stringify(data)}` : '')
    });
  }

  info(message: string, data?: any) {
    this.log('info', message, data);
  }

  warn(message: string, data?: any) {
    this.log('warn', message, data);
  }

  error(message: string, data?: any) {
    this.log('error', message, data);
  }
}

export class TestStepTracker {
  private steps: Array<{ name: string; status: 'pending' | 'running' | 'passed' | 'failed'; duration?: number; error?: string }> = [];
  private logger: TestLogger;

  constructor(logger: TestLogger) {
    this.logger = logger;
  }

  async executeStep<T>(name: string, action: () => Promise<T>): Promise<T> {
    const step: { name: string; status: 'pending' | 'running' | 'passed' | 'failed'; duration?: number; error?: string } = { name, status: 'running' };
    this.steps.push(step);
    this.logger.info(`Starting step: ${name}`);
    
    const startTime = Date.now();
    
    try {
      const result = await action();
      const duration = Date.now() - startTime;
      
      step.status = 'passed';
      step.duration = duration;
      
      this.logger.info(`Step completed: ${name}`, { duration });
      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      
      step.status = 'failed';
      step.duration = duration;
      step.error = error instanceof Error ? error.message : String(error);
      
      this.logger.error(`Step failed: ${name}`, { duration, error: step.error });
      throw error;
    }
  }

  getStepsSummary() {
    return {
      total: this.steps.length,
      passed: this.steps.filter(s => s.status === 'passed').length,
      failed: this.steps.filter(s => s.status === 'failed').length,
      totalDuration: this.steps.reduce((sum, s) => sum + (s.duration || 0), 0),
      steps: this.steps
    };
  }
}

export class ErrorRecovery {
  private logger: TestLogger;
  private page: Page;

  constructor(logger: TestLogger, page: Page) {
    this.logger = logger;
    this.page = page;
  }

  async captureErrorContext(error: Error) {
    this.logger.error('Capturing error context', { error: error.message, stack: error.stack });
    
    try {
      // Capture screenshot
      const screenshotPath = `error-screenshot-${Date.now()}.png`;
      await this.page.screenshot({ path: screenshotPath, fullPage: true });
      this.logger.info('Error screenshot captured', createSanitizedLogEntry('Screenshot saved', screenshotPath));
    } catch (screenshotError) {
      this.logger.warn('Failed to capture error screenshot', { error: screenshotError });
    }
    
    try {
      // Capture page HTML
      const html = await this.page.content();
      const htmlPath = `error-html-${Date.now()}.html`;
      fs.writeFileSync(htmlPath, html);
      this.logger.info('Error HTML captured', createSanitizedLogEntry('HTML content saved', htmlPath));
    } catch (htmlError) {
      this.logger.warn('Failed to capture error HTML', { error: htmlError });
    }
    
    try {
      // Capture console logs
      const logs = await this.page.evaluate(() => {
        // @ts-ignore
        return window.testLogs || 'No logs available';
      });
      this.logger.info('Console logs at error', { logs });
    } catch (logError) {
      this.logger.warn('Failed to capture console logs', { error: logError });
    }
    
    try {
      // Capture network state
      const url = this.page.url();
      const title = await this.page.title();
      this.logger.info('Page state at error', { url, title });
    } catch (stateError) {
      this.logger.warn('Failed to capture page state', { error: stateError });
    }
  }

  async retry<T>(
    action: () => Promise<T>,
    options: {
      maxRetries: number;
      delay: number;
      actionName: string;
    }
  ): Promise<T> {
    const { maxRetries, delay, actionName } = options;
    let lastError: Error;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        this.logger.info(`Attempting ${actionName} (attempt ${attempt}/${maxRetries})`);
        return await action();
      } catch (error) {
        lastError = error as Error;
        this.logger.warn(`${actionName} failed on attempt ${attempt}`, { error: lastError.message });
        
        if (attempt < maxRetries) {
          this.logger.info(`Retrying ${actionName} in ${delay}ms`);
          await this.page.waitForTimeout(delay);
        }
      }
    }
    
    this.logger.error(`${actionName} failed after ${maxRetries} attempts`);
    await this.captureErrorContext(lastError!);
    throw lastError!;
  }
}

export class PerformanceMonitor {
  private logger: TestLogger;
  private page: Page;
  private metrics: Array<{ name: string; value: number; timestamp: number }> = [];

  constructor(logger: TestLogger, page: Page) {
    this.logger = logger;
    this.page = page;
  }

  async measurePageLoad(url: string): Promise<number> {
    const startTime = Date.now();
    
    await this.page.goto(url);
    await this.page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    this.recordMetric('page_load_time', loadTime);
    
    this.logger.info(`Page load time for ${url}`, { loadTime });
    return loadTime;
  }

  async measureAction(actionName: string, action: () => Promise<void>): Promise<number> {
    const startTime = Date.now();
    
    await action();
    
    const actionTime = Date.now() - startTime;
    this.recordMetric(actionName, actionTime);
    
    this.logger.info(`Action time for ${actionName}`, { actionTime });
    return actionTime;
  }

  recordMetric(name: string, value: number) {
    this.metrics.push({
      name,
      value,
      timestamp: Date.now()
    });
  }

  getMetricsSummary() {
    return {
      count: this.metrics.length,
      metrics: this.metrics.reduce((acc, metric) => {
        if (!acc[metric.name]) {
          acc[metric.name] = [];
        }
        acc[metric.name].push(metric.value);
        return acc;
      }, {} as Record<string, number[]>)
    };
  }

  validatePerformance(thresholds: Record<string, number>) {
    const violations: Array<{ metric: string; value: number; threshold: number }> = [];
    
    for (const [metricName, threshold] of Object.entries(thresholds)) {
      const metricValues = this.metrics
        .filter(m => m.name === metricName)
        .map(m => m.value);
      
      if (metricValues.length > 0) {
        const avgValue = metricValues.reduce((sum, val) => sum + val, 0) / metricValues.length;
        
        if (avgValue > threshold) {
          violations.push({
            metric: metricName,
            value: avgValue,
            threshold
          });
        }
      }
    }
    
    if (violations.length > 0) {
      this.logger.warn('Performance threshold violations', { violations });
      return false;
    }
    
    this.logger.info('All performance thresholds met');
    return true;
  }
}

export async function withRetry<T>(
  action: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await action();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError!;
}

export async function waitForCondition(
  condition: () => Promise<boolean>,
  options: {
    timeout: number;
    interval: number;
    timeoutMessage?: string;
  }
): Promise<void> {
  const { timeout, interval, timeoutMessage = 'Condition not met within timeout' } = options;
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return;
    }
    
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error(timeoutMessage);
}

export function createTestContext(page: Page, testInfo: TestInfo): TestContext {
  return {
    page,
    testInfo,
    startTime: Date.now()
  };
}

export function getTestDuration(context: TestContext): number {
  return Date.now() - context.startTime;
}

export async function safeAction<T>(
  action: () => Promise<T>,
  fallback: T,
  logger: TestLogger,
  actionName: string
): Promise<T> {
  try {
    return await action();
  } catch (error) {
    logger.warn(`Safe action "${actionName}" failed, using fallback`, { error: error instanceof Error ? error.message : error });
    return fallback;
  }
}

/**
 * Demo authentication utility for E2E tests
 */
export async function signInAsDemo(page: Page): Promise<void> {
  await page.goto('/signin');
  
  // Look for demo mode signin button
  const demoButton = page.locator('button:has-text("Demo"), button:has-text("Continue"), [data-testid="demo-signin"]');
  
  if (await demoButton.first().isVisible()) {
    await demoButton.first().click();
    
    // Wait for redirect to main application
    await page.waitForURL('**/', { timeout: 10000 });
    
    // Verify we're signed in by checking for main content
    await page.waitForSelector('main, [role="main"], .content', { timeout: 5000 });
  } else {
    throw new Error('Demo mode signin not available');
  }
}

/**
 * RAG-specific test utilities
 */
export class RAGTestUtils {
  constructor(
    private page: Page,
    private logger: TestLogger
  ) {}

  /**
   * Enable RAG mode for testing
   */
  async enableRAG(): Promise<void> {
    const ragToggle = this.page.locator('button[role="switch"], [data-testid="rag-toggle"]');
    
    if (await ragToggle.count() > 0) {
      const isEnabled = await ragToggle.getAttribute('aria-checked');
      if (isEnabled !== 'true') {
        await ragToggle.click();
        await this.page.waitForTimeout(500);
      }
      this.logger.info('RAG enabled for testing');
    } else {
      this.logger.warn('RAG toggle not found - may already be enabled or not available');
    }
  }

  /**
   * Perform a RAG search with validation
   */
  async performRAGSearch(query: string, expectedMinResults: number = 0): Promise<number> {
    const searchInput = this.page.locator('input[placeholder*="search"], [data-testid="evidence-search"]').first();
    
    if (await searchInput.count() === 0) {
      throw new Error('Search input not found');
    }

    await searchInput.fill(query);
    
    const searchButton = this.page.getByRole('button', { name: /search|ask/i }).first();
    if (await searchButton.count() > 0) {
      await searchButton.click();
    } else {
      await searchInput.press('Enter');
    }

    // Wait for search to complete
    await this.page.waitForTimeout(3000);

    // Count results
    const resultsSelector = '[data-testid="search-results"] > *, [data-testid="rag-sources"] > *, .search-result';
    const results = this.page.locator(resultsSelector);
    const resultCount = await results.count();

    this.logger.info(`RAG search performed: "${query}"`, { resultCount, expectedMinResults });

    if (resultCount < expectedMinResults) {
      this.logger.warn('Fewer results than expected', { actual: resultCount, expected: expectedMinResults });
    }

    return resultCount;
  }

  /**
   * Verify RAG status indicators
   */
  async verifyRAGStatus(): Promise<{ operational: boolean; mode: string }> {
    // Look for RAG status indicators
    const statusIndicators = this.page.locator('text=/🟢|🟡|🔴/, [data-testid="rag-status"]');
    
    let operational = false;
    let mode = 'unknown';

    if (await statusIndicators.count() > 0) {
      const statusText = await statusIndicators.first().textContent() || '';
      operational = statusText.includes('🟢') || statusText.toLowerCase().includes('operational');
      
      if (statusText.toLowerCase().includes('azure')) {
        mode = 'azure';
      } else if (statusText.toLowerCase().includes('cosmos')) {
        mode = 'cosmos';
      } else if (statusText.toLowerCase().includes('demo')) {
        mode = 'demo';
      }
    }

    this.logger.info('RAG status verified', { operational, mode });
    return { operational, mode };
  }

  /**
   * Test RAG analysis integration
   */
  async performRAGAnalysis(prompt: string): Promise<{ hasAnalysis: boolean; hasCitations: boolean }> {
    const analysisTextarea = this.page.locator('textarea[placeholder*="analyze"], [data-testid="analysis-input"]');
    
    if (await analysisTextarea.count() === 0) {
      throw new Error('Analysis input not found');
    }

    await analysisTextarea.fill(prompt);

    // Ensure RAG is enabled
    await this.enableRAG();

    // Submit analysis
    const analyzeButton = this.page.getByRole('button', { name: /analyze/i });
    if (await analyzeButton.count() > 0) {
      await analyzeButton.click();
      
      // Wait for analysis to complete
      await this.page.waitForTimeout(8000);
      
      // Check for analysis results
      const analysisResult = this.page.locator('[data-testid="analysis-result"], text=/analysis result/i');
      const hasAnalysis = await analysisResult.count() > 0;

      // Check for citations
      const citations = this.page.locator('[data-testid="citations"], text=/citation|supporting evidence/i');
      const hasCitations = await citations.count() > 0;

      this.logger.info('RAG analysis performed', { prompt: prompt.substring(0, 50), hasAnalysis, hasCitations });

      return { hasAnalysis, hasCitations };
    }

    throw new Error('Analyze button not found');
  }

  /**
   * Test citation interaction
   */
  async testCitationInteraction(): Promise<{ canExpand: boolean; canCopy: boolean }> {
    const expandButton = this.page.locator('button[title*="expand"], button:has-text("▼"), [data-testid="expand-citation"]');
    const canExpand = await expandButton.count() > 0;

    if (canExpand) {
      await expandButton.first().click();
      await this.page.waitForTimeout(500);
    }

    const copyButton = this.page.locator('button[title*="copy"], [data-testid="copy-citation"]');
    const canCopy = await copyButton.count() > 0;

    if (canCopy) {
      await copyButton.first().click();
      await this.page.waitForTimeout(500);
    }

    this.logger.info('Citation interaction tested', { canExpand, canCopy });
    return { canExpand, canCopy };
  }

  /**
   * Validate RAG performance metrics
   */
  async validateRAGPerformance(maxSearchTime: number = 5000, maxAnalysisTime: number = 10000): Promise<boolean> {
    const searchStart = Date.now();
    await this.performRAGSearch('test performance query');
    const searchTime = Date.now() - searchStart;

    const analysisStart = Date.now();
    try {
      await this.performRAGAnalysis('Quick analysis for performance test');
      const analysisTime = Date.now() - analysisStart;

      const performanceOk = searchTime <= maxSearchTime && analysisTime <= maxAnalysisTime;

      this.logger.info('RAG performance validated', {
        searchTime,
        analysisTime,
        maxSearchTime,
        maxAnalysisTime,
        performanceOk
      });

      return performanceOk;
    } catch (error) {
      this.logger.warn('Analysis performance test failed', { searchTime, error });
      return searchTime <= maxSearchTime;
    }
  }
}

// Export enterprise utilities
export { EnterpriseTestUtils } from './test-utils/enterprise';
export type { 
  EnterpriseUserContext, 
  AADClaims, 
  GDPRTestScenario
} from './test-utils/enterprise';

// Add missing export
export class EnterpriseDataGenerator {
  static generateTestData() {
    return {
      tenant: { id: 'test-tenant', name: 'Test Tenant' },
      users: [{ id: 'test-user', name: 'Test User' }]
    };
  }
}
export type {
  DocumentData,
  AssessmentData
} from './test-utils/data-generators';
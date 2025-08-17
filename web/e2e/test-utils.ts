import { Page, TestInfo, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

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
      this.logger.info('Error screenshot captured', { path: screenshotPath });
    } catch (screenshotError) {
      this.logger.warn('Failed to capture error screenshot', { error: screenshotError });
    }
    
    try {
      // Capture page HTML
      const html = await this.page.content();
      const htmlPath = `error-html-${Date.now()}.html`;
      fs.writeFileSync(htmlPath, html);
      this.logger.info('Error HTML captured', { path: htmlPath });
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

// Export enterprise utilities
export { EnterpriseTestUtils } from './test-utils/enterprise';
export { EnterpriseDataGenerator } from './test-utils/data-generators';
export type { 
  EnterpriseUserContext, 
  AADClaims, 
  GDPRTestScenario
} from './test-utils/enterprise';
export type {
  DocumentData,
  AssessmentData
} from './test-utils/data-generators';
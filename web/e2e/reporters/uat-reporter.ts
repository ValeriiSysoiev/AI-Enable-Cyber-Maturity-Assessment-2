import { Reporter, TestCase, TestResult, FullConfig, Suite, FullResult } from '@playwright/test/reporter';
import fs from 'fs';
import path from 'path';
import { GitHubIssueManager, UATIssueData, GitHubIssueConfig } from '../utils/github-issue-manager';

/**
 * Custom UAT Reporter for Playwright
 * 
 * This reporter generates structured JSON reports specifically designed for UAT
 * monitoring and continuous testing in production environments. It focuses on
 * collecting telemetry data, error patterns, and operational insights.
 */

interface UATTestResult {
  testId: string;
  title: string;
  status: 'passed' | 'failed' | 'skipped' | 'timedOut' | 'interrupted';
  duration: number;
  startTime: number;
  endTime: number;
  errors: Array<{
    message: string;
    stack?: string;
    location?: string;
  }>;
  attachments: Array<{
    name: string;
    contentType: string;
    path?: string;
    body?: string;
  }>;
  annotations: Array<{
    type: string;
    description: string;
  }>;
  steps: Array<{
    title: string;
    duration: number;
    error?: string;
    category: string;
  }>;
}

interface UATSuiteResult {
  suiteTitle: string;
  tests: UATTestResult[];
  startTime: number;
  endTime: number;
  duration: number;
  status: 'passed' | 'failed' | 'mixed';
  statistics: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    timedOut: number;
    interrupted: number;
  };
}

interface UATFullReport {
  metadata: {
    reportId: string;
    timestamp: number;
    version: string;
    environment: {
      authMode: string;
      baseUrl: string;
      browser: string;
      os: string;
      ci: boolean;
    };
    configuration: {
      workers: number;
      timeout: number;
      retries: number;
      projects: string[];
    };
  };
  summary: {
    startTime: number;
    endTime: number;
    duration: number;
    totalTests: number;
    passedTests: number;
    failedTests: number;
    skippedTests: number;
    timedOutTests: number;
    successRate: number;
  };
  suites: UATSuiteResult[];
  issues: Array<{
    type: 'error' | 'warning' | 'performance';
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    testId?: string;
    step?: string;
    count: number;
    firstSeen: number;
    lastSeen: number;
    examples: string[];
  }>;
  performance: {
    averageTestDuration: number;
    slowestTest: { testId: string; duration: number };
    fastestTest: { testId: string; duration: number };
    timeouts: number;
    retries: number;
  };
}

export default class UATReporter implements Reporter {
  private config!: FullConfig;
  private suite!: Suite;
  private results: Map<string, UATTestResult> = new Map();
  private suiteResults: Map<string, UATSuiteResult> = new Map();
  private startTime: number = 0;
  private endTime: number = 0;
  private githubIssueManager: GitHubIssueManager | null = null;
  private issuesToCreate: UATIssueData[] = [];

  onBegin(config: FullConfig, suite: Suite) {
    this.config = config;
    this.suite = suite;
    this.startTime = Date.now();
    
    // Initialize GitHub issue manager if configured
    const githubConfig = GitHubIssueManager.validateConfig();
    if (githubConfig) {
      this.githubIssueManager = new GitHubIssueManager(githubConfig);
      console.log(`🐙 GitHub issue integration enabled for ${githubConfig.owner}/${githubConfig.repo}`);
    } else {
      console.log(`⚠️ GitHub issue integration disabled - missing configuration`);
      console.log(`   Set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO environment variables to enable`);
    }
    
    console.log(`\n🔍 UAT Explorer Reporter Starting`);
    console.log(`📊 Running ${this.suite.allTests().length} tests across ${config.projects.length} project(s)`);
    console.log(`🎯 Auth Mode: ${process.env.DEMO_E2E === '1' ? 'DEMO' : 'AAD'}`);
    console.log(`🌐 Base URL: ${process.env.WEB_BASE_URL || 'http://localhost:3000'}`);
  }

  onTestBegin(test: TestCase, result: TestResult) {
    const testId = this.getTestId(test);
    
    const uatResult: UATTestResult = {
      testId,
      title: test.title,
      status: 'skipped',
      duration: 0,
      startTime: Date.now(),
      endTime: 0,
      errors: [],
      attachments: [],
      annotations: [],
      steps: []
    };

    this.results.set(testId, uatResult);
    
    console.log(`🧪 Starting: ${test.title}`);
  }

  onTestEnd(test: TestCase, result: TestResult) {
    const testId = this.getTestId(test);
    const uatResult = this.results.get(testId);

    if (!uatResult) {
      console.warn(`⚠️ No UAT result found for test: ${testId}`);
      return;
    }

    // Update result with final data
    uatResult.status = result.status;
    uatResult.duration = result.duration;
    uatResult.endTime = Date.now();

    // Process errors
    uatResult.errors = result.errors.map(error => ({
      message: GitHubIssueManager.sanitizeContent(error.message || 'Unknown error'),
      stack: error.stack,
      location: error.location ? `${error.location.file}:${error.location.line}:${error.location.column}` : undefined
    }));

    // Process attachments
    uatResult.attachments = result.attachments.map(attachment => ({
      name: attachment.name,
      contentType: attachment.contentType,
      path: attachment.path,
      body: attachment.body?.toString('base64')
    }));

    // Process annotations
    uatResult.annotations = test.annotations.map(annotation => ({
      type: annotation.type,
      description: annotation.description || ''
    }));

    // Process steps
    uatResult.steps = result.steps.map(step => ({
      title: step.title,
      duration: step.duration,
      error: step.error?.message ? GitHubIssueManager.sanitizeContent(step.error.message) : undefined,
      category: this.categorizeStep(step.title)
    }));

    // Log result
    const statusEmoji = this.getStatusEmoji(result.status);
    const durationText = `${Math.round(result.duration)}ms`;
    console.log(`${statusEmoji} ${test.title} (${durationText})`);

    if (result.status === 'failed' && result.errors.length > 0) {
      console.log(`   ❌ Error: ${result.errors[0].message}`);
    }

    // Prepare GitHub issue data for failed tests
    if (result.status === 'failed' && this.githubIssueManager) {
      const issueData = this.createIssueData(test, uatResult, result);
      this.issuesToCreate.push(issueData);
    }

    // Update suite results
    this.updateSuiteResults(test, uatResult);
  }

  async onEnd(result: FullResult): Promise<void> {
    this.endTime = Date.now();
    
    console.log(`\n📈 UAT Explorer Results:`);
    console.log(`   ✅ Passed: ${this.countByStatus('passed')}`);
    console.log(`   ❌ Failed: ${this.countByStatus('failed')}`);
    console.log(`   ⏭️ Skipped: ${this.countByStatus('skipped')}`);
    console.log(`   ⏰ Timed Out: ${this.countByStatus('timedOut')}`);
    console.log(`   ⏱️ Total Duration: ${Math.round((this.endTime - this.startTime) / 1000)}s`);

    // Create GitHub issues for failed tests
    if (this.githubIssueManager && this.issuesToCreate.length > 0) {
      console.log(`\n🐙 Creating GitHub issues for ${this.issuesToCreate.length} failed test(s)...`);
      await this.createGitHubIssues();
    }

    // Generate comprehensive report
    const report = this.generateFullReport(result);

    // Ensure output directory exists
    const outputDir = path.join(process.cwd(), 'artifacts', 'uat');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Write main UAT report
    const reportPath = path.join(outputDir, 'uat_report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Write summary report for quick analysis
    const summaryPath = path.join(outputDir, 'uat_summary.json');
    const summary = {
      reportId: report.metadata.reportId,
      timestamp: report.metadata.timestamp,
      success: result.status === 'passed',
      summary: report.summary,
      criticalIssues: report.issues.filter(i => i.severity === 'critical').length,
      highIssues: report.issues.filter(i => i.severity === 'high').length,
      performanceIssues: report.issues.filter(i => i.type === 'performance').length,
      topIssues: report.issues.slice(0, 5)
    };
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

    // Write human-readable report
    const readableReport = this.generateReadableReport(report);
    const readablePath = path.join(outputDir, 'uat_report.md');
    fs.writeFileSync(readablePath, readableReport);

    console.log(`\n📊 Reports generated:`);
    console.log(`   📄 Full Report: ${reportPath}`);
    console.log(`   📋 Summary: ${summaryPath}`);
    console.log(`   📖 Readable: ${readablePath}`);
    
    if (report.issues.filter(i => i.severity === 'critical').length > 0) {
      console.log(`\n🚨 CRITICAL ISSUES DETECTED: ${report.issues.filter(i => i.severity === 'critical').length}`);
    }
  }

  private getTestId(test: TestCase): string {
    return `${test.parent.title}-${test.title}`.replace(/[^a-zA-Z0-9-_]/g, '_');
  }

  private getStatusEmoji(status: string): string {
    switch (status) {
      case 'passed': return '✅';
      case 'failed': return '❌';
      case 'skipped': return '⏭️';
      case 'timedOut': return '⏰';
      default: return '❓';
    }
  }

  private categorizeStep(stepTitle: string): string {
    if (stepTitle.includes('Navigate') || stepTitle.includes('goto')) return 'navigation';
    if (stepTitle.includes('click') || stepTitle.includes('Click')) return 'interaction';
    if (stepTitle.includes('expect') || stepTitle.includes('assert')) return 'validation';
    if (stepTitle.includes('wait') || stepTitle.includes('Wait')) return 'synchronization';
    if (stepTitle.includes('API') || stepTitle.includes('request')) return 'api';
    if (stepTitle.includes('Auth') || stepTitle.includes('signin')) return 'authentication';
    return 'general';
  }

  private countByStatus(status: string): number {
    return Array.from(this.results.values()).filter(r => r.status === status).length;
  }

  private updateSuiteResults(test: TestCase, testResult: UATTestResult) {
    const suiteTitle = test.parent.title;
    
    if (!this.suiteResults.has(suiteTitle)) {
      this.suiteResults.set(suiteTitle, {
        suiteTitle,
        tests: [],
        startTime: testResult.startTime,
        endTime: testResult.endTime,
        duration: 0,
        status: 'passed',
        statistics: {
          total: 0,
          passed: 0,
          failed: 0,
          skipped: 0,
          timedOut: 0,
          interrupted: 0
        }
      });
    }

    const suite = this.suiteResults.get(suiteTitle)!;
    suite.tests.push(testResult);
    suite.endTime = Math.max(suite.endTime, testResult.endTime);
    suite.duration = suite.endTime - suite.startTime;

    // Update statistics
    suite.statistics.total++;
    suite.statistics[testResult.status]++;

    // Update suite status
    if (testResult.status === 'failed') {
      suite.status = 'failed';
    } else if (suite.status !== 'failed' && testResult.status !== 'passed') {
      suite.status = 'mixed';
    }
  }

  private generateFullReport(result: FullResult): UATFullReport {
    const allResults = Array.from(this.results.values());
    const allSuites = Array.from(this.suiteResults.values());

    // Analyze issues
    const issues = this.analyzeIssues(allResults);

    // Calculate performance metrics
    const durations = allResults.map(r => r.duration);
    const slowest = allResults.reduce((a, b) => a.duration > b.duration ? a : b, allResults[0]);
    const fastest = allResults.reduce((a, b) => a.duration < b.duration ? a : b, allResults[0]);

    return {
      metadata: {
        reportId: `uat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: this.startTime,
        version: '1.0.0',
        environment: {
          authMode: process.env.DEMO_E2E === '1' ? 'DEMO' : 'AAD',
          baseUrl: process.env.WEB_BASE_URL || 'http://localhost:3000',
          browser: this.config.projects[0]?.name || 'unknown',
          os: process.platform,
          ci: !!process.env.CI
        },
        configuration: {
          workers: this.config.workers,
          timeout: this.config.globalTimeout || 30000,
          retries: this.config.projects[0]?.retries || 0,
          projects: this.config.projects.map(p => p.name)
        }
      },
      summary: {
        startTime: this.startTime,
        endTime: this.endTime,
        duration: this.endTime - this.startTime,
        totalTests: allResults.length,
        passedTests: this.countByStatus('passed'),
        failedTests: this.countByStatus('failed'),
        skippedTests: this.countByStatus('skipped'),
        timedOutTests: this.countByStatus('timedOut'),
        successRate: allResults.length > 0 ? (this.countByStatus('passed') / allResults.length) * 100 : 0
      },
      suites: allSuites,
      issues,
      performance: {
        averageTestDuration: durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0,
        slowestTest: { testId: slowest?.testId || '', duration: slowest?.duration || 0 },
        fastestTest: { testId: fastest?.testId || '', duration: fastest?.duration || 0 },
        timeouts: this.countByStatus('timedOut'),
        retries: result.status === 'failed' ? 1 : 0
      }
    };
  }

  private analyzeIssues(results: UATTestResult[]): UATFullReport['issues'] {
    const issueMap = new Map<string, { count: number; examples: string[]; firstSeen: number; lastSeen: number }>();

    results.forEach(result => {
      // Analyze errors
      result.errors.forEach(error => {
        const key = `error:${error.message}`;
        if (!issueMap.has(key)) {
          issueMap.set(key, { count: 0, examples: [], firstSeen: result.startTime, lastSeen: result.startTime });
        }
        const issue = issueMap.get(key)!;
        issue.count++;
        issue.lastSeen = result.endTime;
        issue.examples.push(`${result.title}: ${error.message}`);
      });

      // Analyze performance issues
      if (result.duration > 30000) { // Tests taking longer than 30s
        const key = `performance:slow_test`;
        if (!issueMap.has(key)) {
          issueMap.set(key, { count: 0, examples: [], firstSeen: result.startTime, lastSeen: result.startTime });
        }
        const issue = issueMap.get(key)!;
        issue.count++;
        issue.lastSeen = result.endTime;
        issue.examples.push(`${result.title}: ${result.duration}ms`);
      }

      // Analyze timeouts
      if (result.status === 'timedOut') {
        const key = `error:timeout`;
        if (!issueMap.has(key)) {
          issueMap.set(key, { count: 0, examples: [], firstSeen: result.startTime, lastSeen: result.startTime });
        }
        const issue = issueMap.get(key)!;
        issue.count++;
        issue.lastSeen = result.endTime;
        issue.examples.push(`${result.title}: Test timed out`);
      }
    });

    return Array.from(issueMap.entries()).map(([key, data]) => {
      const [type, message] = key.split(':', 2);
      return {
        type: type as 'error' | 'warning' | 'performance',
        severity: this.determineSeverity(type, message, data.count),
        message: message.replace(/_/g, ' '),
        count: data.count,
        firstSeen: data.firstSeen,
        lastSeen: data.lastSeen,
        examples: data.examples.slice(0, 3) // Limit examples
      };
    }).sort((a, b) => {
      // Sort by severity, then by count
      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const severityDiff = severityOrder[b.severity] - severityOrder[a.severity];
      return severityDiff !== 0 ? severityDiff : b.count - a.count;
    });
  }

  private determineSeverity(type: string, message: string, count: number): 'low' | 'medium' | 'high' | 'critical' {
    if (type === 'error') {
      if (message.includes('timeout') || message.includes('network') || count > 3) {
        return 'critical';
      }
      if (count > 1) {
        return 'high';
      }
      return 'medium';
    }

    if (type === 'performance') {
      if (count > 2) {
        return 'high';
      }
      return 'medium';
    }

    return 'low';
  }

  private generateReadableReport(report: UATFullReport): string {
    const { metadata, summary, issues, performance } = report;
    
    let markdown = `# UAT Explorer Report\n\n`;
    markdown += `**Report ID:** ${metadata.reportId}\n`;
    markdown += `**Generated:** ${new Date(metadata.timestamp).toISOString()}\n`;
    markdown += `**Environment:** ${metadata.environment.authMode} mode on ${metadata.environment.baseUrl}\n`;
    markdown += `**Duration:** ${Math.round(summary.duration / 1000)}s\n\n`;

    markdown += `## Summary\n\n`;
    markdown += `- **Total Tests:** ${summary.totalTests}\n`;
    markdown += `- **Success Rate:** ${summary.successRate.toFixed(1)}%\n`;
    markdown += `- **Passed:** ${summary.passedTests}\n`;
    markdown += `- **Failed:** ${summary.failedTests}\n`;
    markdown += `- **Skipped:** ${summary.skippedTests}\n`;
    markdown += `- **Timed Out:** ${summary.timedOutTests}\n\n`;

    if (issues.length > 0) {
      markdown += `## Issues Detected\n\n`;
      issues.forEach(issue => {
        const severity = issue.severity.toUpperCase();
        markdown += `### ${severity}: ${issue.message} (${issue.count}x)\n\n`;
        markdown += `**Type:** ${issue.type}\n`;
        markdown += `**First Seen:** ${new Date(issue.firstSeen).toISOString()}\n`;
        markdown += `**Last Seen:** ${new Date(issue.lastSeen).toISOString()}\n\n`;
        
        if (issue.examples.length > 0) {
          markdown += `**Examples:**\n`;
          issue.examples.forEach(example => {
            markdown += `- ${example}\n`;
          });
          markdown += `\n`;
        }
      });
    }

    markdown += `## Performance\n\n`;
    markdown += `- **Average Test Duration:** ${Math.round(performance.averageTestDuration)}ms\n`;
    markdown += `- **Slowest Test:** ${performance.slowestTest.testId} (${Math.round(performance.slowestTest.duration)}ms)\n`;
    markdown += `- **Fastest Test:** ${performance.fastestTest.testId} (${Math.round(performance.fastestTest.duration)}ms)\n`;
    markdown += `- **Timeouts:** ${performance.timeouts}\n\n`;

    markdown += `## Test Suites\n\n`;
    report.suites.forEach(suite => {
      markdown += `### ${suite.suiteTitle}\n\n`;
      markdown += `- **Status:** ${suite.status}\n`;
      markdown += `- **Tests:** ${suite.statistics.total}\n`;
      markdown += `- **Duration:** ${Math.round(suite.duration / 1000)}s\n`;
      markdown += `- **Success Rate:** ${suite.statistics.total > 0 ? ((suite.statistics.passed / suite.statistics.total) * 100).toFixed(1) : 0}%\n\n`;
    });

    return markdown;
  }

  /**
   * Create GitHub issue data from test failure
   */
  private createIssueData(test: TestCase, uatResult: UATTestResult, result: TestResult): UATIssueData {
    // Determine environment from base URL or environment variable
    const baseUrl = process.env.WEB_BASE_URL || 'http://localhost:3000';
    let environment: 'staging' | 'production' | 'development' = 'development';
    
    if (baseUrl.includes('staging')) {
      environment = 'staging';
    } else if (baseUrl.includes('prod') || process.env.NODE_ENV === 'production') {
      environment = 'production';
    }

    // Determine severity based on test failure characteristics
    const severity = this.determineTestSeverity(uatResult, environment);

    // Extract screenshots from attachments
    const screenshots = uatResult.attachments
      .filter(att => att.contentType?.startsWith('image/'))
      .map(att => ({
        name: att.name,
        path: att.path || 'attachment-data',
        contentType: att.contentType
      }));

    // Create logs from errors and steps
    const logs: UATIssueData['logs'] = [];
    
    // Add error logs
    uatResult.errors.forEach(error => {
      logs.push({
        type: 'error',
        message: error.message,
        timestamp: uatResult.endTime
      });
    });

    // Add step error logs
    uatResult.steps.forEach(step => {
      if (step.error) {
        logs.push({
          type: 'error',
          message: `Step "${step.title}" failed: ${step.error}`,
          timestamp: uatResult.endTime
        });
      }
    });

    return {
      testName: test.title,
      testId: uatResult.testId,
      failureReason: uatResult.errors.length > 0 ? uatResult.errors[0].message : 'Test failed without specific error',
      environment,
      severity,
      screenshots,
      logs,
      metadata: {
        browser: this.config.projects[0]?.name || 'unknown',
        os: process.platform,
        timestamp: uatResult.startTime,
        reportId: `uat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        baseUrl,
        authMode: process.env.DEMO_E2E === '1' ? 'DEMO' : 'AAD',
        testDuration: uatResult.duration,
        retryCount: result.retry
      },
      steps: uatResult.steps
    };
  }

  /**
   * Determine severity based on test failure characteristics and environment
   */
  private determineTestSeverity(uatResult: UATTestResult, environment: string): 'low' | 'medium' | 'high' | 'critical' {
    // Production failures are always at least high severity
    if (environment === 'production') {
      if (uatResult.status === 'timedOut' || 
          uatResult.errors.some(e => e.message.toLowerCase().includes('network')) ||
          uatResult.errors.some(e => e.message.toLowerCase().includes('500'))) {
        return 'critical';
      }
      return 'high';
    }

    // Staging failures
    if (environment === 'staging') {
      if (uatResult.status === 'timedOut' || 
          uatResult.errors.some(e => e.message.toLowerCase().includes('timeout')) ||
          uatResult.errors.some(e => e.message.toLowerCase().includes('network'))) {
        return 'high';
      }
      return 'medium';
    }

    // Development failures
    if (uatResult.status === 'timedOut') {
      return 'medium';
    }
    
    return 'low';
  }

  /**
   * Create GitHub issues for all failed tests
   */
  private async createGitHubIssues(): Promise<void> {
    if (!this.githubIssueManager) {
      return;
    }

    const createdIssues: Array<{ issueNumber: number; action: 'created' | 'updated'; testName: string }> = [];
    const failedIssues: Array<{ testName: string; error: string }> = [];

    for (const issueData of this.issuesToCreate) {
      try {
        const result = await this.githubIssueManager.createOrUpdateIssue(issueData);
        createdIssues.push({
          issueNumber: result.issueNumber,
          action: result.action,
          testName: issueData.testName
        });
        
        const actionEmoji = result.action === 'created' ? '🆕' : '🔄';
        console.log(`   ${actionEmoji} Issue #${result.issueNumber} ${result.action} for "${issueData.testName}"`);
        
      } catch (error) {
        failedIssues.push({
          testName: issueData.testName,
          error: error instanceof Error ? error.message : String(error)
        });
        console.warn(`   ⚠️ Failed to create issue for "${issueData.testName}": ${error}`);
      }
    }

    // Summary
    if (createdIssues.length > 0) {
      const newIssues = createdIssues.filter(i => i.action === 'created').length;
      const updatedIssues = createdIssues.filter(i => i.action === 'updated').length;
      console.log(`\n✅ GitHub Issues Summary:`);
      if (newIssues > 0) console.log(`   🆕 Created: ${newIssues} new issue(s)`);
      if (updatedIssues > 0) console.log(`   🔄 Updated: ${updatedIssues} existing issue(s)`);
      
      // Show issue links if GitHub config is available
      const githubConfig = GitHubIssueManager.validateConfig();
      if (githubConfig) {
        console.log(`\n🔗 View issues: https://github.com/${githubConfig.owner}/${githubConfig.repo}/issues?q=is:issue+is:open+label:${githubConfig.labelPrefix || 'uat'}`);
      }
    }

    if (failedIssues.length > 0) {
      console.log(`\n❌ Failed to create/update ${failedIssues.length} issue(s):`);
      failedIssues.forEach(failed => {
        console.log(`   - ${failed.testName}: ${failed.error}`);
      });
    }
  }
}
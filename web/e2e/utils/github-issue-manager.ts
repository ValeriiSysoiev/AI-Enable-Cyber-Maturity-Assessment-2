import { Octokit } from '@octokit/rest';
import crypto from 'crypto';
import path from 'path';

/**
 * GitHub Issue Manager for UAT Reporter
 * 
 * Handles creation and updating of GitHub issues for test failures
 * with deduplication based on failure signatures and environment-aware labeling.
 */

export interface UATIssueData {
  testName: string;
  testId: string;
  failureReason: string;
  environment: 'staging' | 'production' | 'development';
  severity: 'low' | 'medium' | 'high' | 'critical';
  screenshots: Array<{
    name: string;
    path: string;
    contentType: string;
  }>;
  logs: Array<{
    type: 'error' | 'warning' | 'info';
    message: string;
    timestamp: number;
  }>;
  metadata: {
    browser: string;
    os: string;
    timestamp: number;
    reportId: string;
    baseUrl: string;
    authMode: string;
    testDuration: number;
    retryCount?: number;
  };
  steps: Array<{
    title: string;
    duration: number;
    error?: string;
    category: string;
  }>;
}

export interface GitHubIssueConfig {
  owner: string;
  repo: string;
  token: string;
  labelPrefix?: string;
  assignees?: string[];
  baseUrl?: string;
}

export class GitHubIssueManager {
  private octokit: Octokit;
  private config: GitHubIssueConfig;
  private issueCache = new Map<string, number>(); // signature -> issue number

  constructor(config: GitHubIssueConfig) {
    this.config = {
      labelPrefix: 'uat',
      ...config
    };

    this.octokit = new Octokit({
      auth: config.token,
      baseUrl: config.baseUrl || 'https://api.github.com'
    });
  }

  /**
   * Generate a unique failure signature for deduplication
   * This signature is based on test name, error type, and key failure patterns
   */
  private generateFailureSignature(issueData: UATIssueData): string {
    const { testName, failureReason, environment } = issueData;
    
    // Extract key error patterns for better deduplication
    const errorPattern = this.extractErrorPattern(failureReason);
    const normalizedTestName = testName.replace(/[^a-zA-Z0-9-_]/g, '_');
    
    const signatureInput = `${normalizedTestName}:${errorPattern}:${environment}`;
    return crypto.createHash('sha256').update(signatureInput).digest('hex').substring(0, 16);
  }

  /**
   * Extract meaningful error patterns from failure reason
   * Helps with better deduplication by focusing on core error types
   */
  private extractErrorPattern(failureReason: string): string {
    // Common error patterns to normalize
    const patterns = [
      { regex: /timeout|timed out/i, replacement: 'TIMEOUT' },
      { regex: /network|connection/i, replacement: 'NETWORK' },
      { regex: /element.*not.*found/i, replacement: 'ELEMENT_NOT_FOUND' },
      { regex: /auth|authentication|unauthorized/i, replacement: 'AUTH_ERROR' },
      { regex: /500|internal server error/i, replacement: 'SERVER_ERROR' },
      { regex: /404|not found/i, replacement: 'NOT_FOUND' },
      { regex: /expect.*received/i, replacement: 'ASSERTION_FAILED' },
      { regex: /page crashed|browser crashed/i, replacement: 'BROWSER_CRASH' }
    ];

    for (const { regex, replacement } of patterns) {
      if (regex.test(failureReason)) {
        return replacement;
      }
    }

    // If no pattern matches, use a hash of the first 100 characters
    const truncated = failureReason.substring(0, 100);
    return crypto.createHash('md5').update(truncated).digest('hex').substring(0, 8);
  }

  /**
   * Generate labels for the GitHub issue
   */
  private generateLabels(issueData: UATIssueData): string[] {
    const labels = [
      this.config.labelPrefix || 'uat',
      issueData.environment,
      `severity:${issueData.severity}`
    ];

    // Add category-based labels
    const errorPattern = this.extractErrorPattern(issueData.failureReason);
    switch (errorPattern) {
      case 'TIMEOUT':
        labels.push('performance');
        break;
      case 'NETWORK':
        labels.push('infrastructure');
        break;
      case 'AUTH_ERROR':
        labels.push('authentication');
        break;
      case 'BROWSER_CRASH':
        labels.push('stability');
        break;
      default:
        labels.push('functional');
    }

    return labels;
  }

  /**
   * Create issue title with environment and failure context
   */
  private createIssueTitle(issueData: UATIssueData): string {
    const { testName, environment, severity } = issueData;
    const errorType = this.extractErrorPattern(issueData.failureReason);
    
    return `[${environment.toUpperCase()}] ${severity.toUpperCase()}: ${testName} - ${errorType}`;
  }

  /**
   * Create comprehensive issue body with all relevant information
   */
  private createIssueBody(issueData: UATIssueData): string {
    const { 
      testName, 
      testId, 
      failureReason, 
      environment, 
      severity,
      metadata,
      steps,
      logs,
      screenshots 
    } = issueData;

    let body = `## Test Failure Report\n\n`;
    body += `**Test:** ${testName}\n`;
    body += `**Test ID:** ${testId}\n`;
    body += `**Environment:** ${environment}\n`;
    body += `**Severity:** ${severity}\n`;
    body += `**Report ID:** ${metadata.reportId}\n`;
    body += `**Timestamp:** ${new Date(metadata.timestamp).toISOString()}\n\n`;

    body += `## Failure Details\n\n`;
    body += `**Error Message:**\n\`\`\`\n${failureReason}\n\`\`\`\n\n`;

    body += `## Environment Information\n\n`;
    body += `- **Base URL:** ${metadata.baseUrl}\n`;
    body += `- **Auth Mode:** ${metadata.authMode}\n`;
    body += `- **Browser:** ${metadata.browser}\n`;
    body += `- **OS:** ${metadata.os}\n`;
    body += `- **Test Duration:** ${Math.round(metadata.testDuration)}ms\n`;
    if (metadata.retryCount !== undefined) {
      body += `- **Retry Count:** ${metadata.retryCount}\n`;
    }
    body += `\n`;

    if (steps.length > 0) {
      body += `## Test Steps\n\n`;
      steps.forEach((step, index) => {
        const stepStatus = step.error ? '❌' : '✅';
        body += `${index + 1}. ${stepStatus} **${step.title}** (${step.duration}ms)\n`;
        if (step.error) {
          body += `   - Error: ${step.error}\n`;
        }
        body += `   - Category: ${step.category}\n\n`;
      });
    }

    if (logs.length > 0) {
      body += `## Logs\n\n`;
      const recentLogs = logs.slice(-10); // Show last 10 logs
      recentLogs.forEach(log => {
        const logEmoji = log.type === 'error' ? '🔴' : log.type === 'warning' ? '🟡' : '🔵';
        const timestamp = new Date(log.timestamp).toISOString();
        body += `${logEmoji} **${log.type.toUpperCase()}** [${timestamp}]: ${log.message}\n`;
      });
      if (logs.length > 10) {
        body += `\n_... and ${logs.length - 10} more log entries_\n`;
      }
      body += `\n`;
    }

    if (screenshots.length > 0) {
      body += `## Screenshots\n\n`;
      screenshots.forEach(screenshot => {
        body += `- **${screenshot.name}**: \`${screenshot.path}\`\n`;
      });
      body += `\n> Note: Screenshots are available in the test artifacts directory.\n\n`;
    }

    body += `## Troubleshooting\n\n`;
    body += this.generateTroubleshootingSteps(issueData);

    body += `\n---\n`;
    body += `*This issue was automatically generated by the UAT Explorer reporter.*\n`;
    body += `*Report ID: ${metadata.reportId}*`;

    return body;
  }

  /**
   * Generate context-aware troubleshooting steps
   */
  private generateTroubleshootingSteps(issueData: UATIssueData): string {
    const errorType = this.extractErrorPattern(issueData.failureReason);
    
    let steps = `### Suggested Actions\n\n`;
    
    switch (errorType) {
      case 'TIMEOUT':
        steps += `- Check network connectivity and server response times\n`;
        steps += `- Verify if the issue is consistent across multiple test runs\n`;
        steps += `- Review server logs for performance bottlenecks\n`;
        steps += `- Consider increasing timeout values if appropriate\n`;
        break;
      case 'NETWORK':
        steps += `- Verify network connectivity to ${issueData.metadata.baseUrl}\n`;
        steps += `- Check firewall and security group configurations\n`;
        steps += `- Review DNS resolution for the target environment\n`;
        steps += `- Validate SSL certificates and TLS configuration\n`;
        break;
      case 'AUTH_ERROR':
        steps += `- Verify authentication credentials and tokens\n`;
        steps += `- Check user permissions and role assignments\n`;
        steps += `- Review AAD/authentication provider configuration\n`;
        steps += `- Validate session management and token expiration\n`;
        break;
      case 'ELEMENT_NOT_FOUND':
        steps += `- Check for recent UI changes or deployments\n`;
        steps += `- Verify element selectors are still valid\n`;
        steps += `- Review page loading and rendering performance\n`;
        steps += `- Consider adding explicit waits for dynamic content\n`;
        break;
      case 'SERVER_ERROR':
        steps += `- Review server logs for detailed error information\n`;
        steps += `- Check database connectivity and queries\n`;
        steps += `- Verify API endpoint availability and configuration\n`;
        steps += `- Monitor system resources and performance metrics\n`;
        break;
      default:
        steps += `- Review the test failure details above\n`;
        steps += `- Check for recent code or infrastructure changes\n`;
        steps += `- Verify the test environment configuration\n`;
        steps += `- Consider running the test in isolation to reproduce the issue\n`;
    }
    
    steps += `\n### Environment-Specific Actions\n\n`;
    switch (issueData.environment) {
      case 'production':
        steps += `- **CRITICAL**: This is a production issue requiring immediate attention\n`;
        steps += `- Monitor user impact and error rates\n`;
        steps += `- Prepare rollback procedures if necessary\n`;
        steps += `- Coordinate with operations team for incident response\n`;
        break;
      case 'staging':
        steps += `- Block promotion to production until resolved\n`;
        steps += `- Verify if the issue exists in other environments\n`;
        steps += `- Coordinate with development team for fix deployment\n`;
        break;
      case 'development':
        steps += `- Verify the issue in local development environment\n`;
        steps += `- Check for configuration differences between environments\n`;
        steps += `- Consider if this is a known development environment limitation\n`;
        break;
    }

    return steps;
  }

  /**
   * Search for existing issues with the same failure signature
   */
  private async findExistingIssue(signature: string): Promise<number | null> {
    // Check cache first
    if (this.issueCache.has(signature)) {
      return this.issueCache.get(signature) || null;
    }

    try {
      const response = await this.octokit.rest.issues.listForRepo({
        owner: this.config.owner,
        repo: this.config.repo,
        labels: [this.config.labelPrefix || 'uat'].join(','),
        state: 'open',
        per_page: 100
      });

      for (const issue of response.data) {
        if (issue.body?.includes(`Signature: ${signature}`)) {
          this.issueCache.set(signature, issue.number);
          return issue.number;
        }
      }

      return null;
    } catch (error) {
      console.warn('Failed to search for existing issues:', error);
      return null;
    }
  }

  /**
   * Create a new GitHub issue for test failure
   */
  private async createIssue(issueData: UATIssueData, signature: string): Promise<number> {
    const title = this.createIssueTitle(issueData);
    const body = this.createIssueBody(issueData) + `\n\n<!-- Signature: ${signature} -->`;
    const labels = this.generateLabels(issueData);

    try {
      const response = await this.octokit.rest.issues.create({
        owner: this.config.owner,
        repo: this.config.repo,
        title,
        body,
        labels,
        assignees: this.config.assignees
      });

      this.issueCache.set(signature, response.data.number);
      return response.data.number;
    } catch (error) {
      throw new Error(`Failed to create GitHub issue: ${error}`);
    }
  }

  /**
   * Update an existing GitHub issue with new failure information
   */
  private async updateIssue(issueNumber: number, issueData: UATIssueData): Promise<void> {
    try {
      // Get current issue to append information
      const currentIssue = await this.octokit.rest.issues.get({
        owner: this.config.owner,
        repo: this.config.repo,
        issue_number: issueNumber
      });

      // Add a comment with the new failure information
      const comment = this.createUpdateComment(issueData);
      
      await this.octokit.rest.issues.createComment({
        owner: this.config.owner,
        repo: this.config.repo,
        issue_number: issueNumber,
        body: comment
      });

      // Update labels to ensure they include current environment and severity
      const currentLabels = currentIssue.data.labels.map(label => 
        typeof label === 'string' ? label : label.name || ''
      );
      const newLabels = this.generateLabels(issueData);
      const updatedLabels = Array.from(new Set([...currentLabels, ...newLabels]));

      await this.octokit.rest.issues.update({
        owner: this.config.owner,
        repo: this.config.repo,
        issue_number: issueNumber,
        labels: updatedLabels
      });

    } catch (error) {
      throw new Error(`Failed to update GitHub issue #${issueNumber}: ${error}`);
    }
  }

  /**
   * Create comment for issue updates
   */
  private createUpdateComment(issueData: UATIssueData): string {
    const { environment, metadata, failureReason } = issueData;
    
    let comment = `## Failure Recurred\n\n`;
    comment += `**New Occurrence:** ${new Date(metadata.timestamp).toISOString()}\n`;
    comment += `**Environment:** ${environment}\n`;
    comment += `**Report ID:** ${metadata.reportId}\n`;
    comment += `**Browser:** ${metadata.browser}\n`;
    comment += `**Test Duration:** ${Math.round(metadata.testDuration)}ms\n\n`;

    comment += `**Error:**\n\`\`\`\n${failureReason}\n\`\`\`\n\n`;

    // Add any new logs
    if (issueData.logs.length > 0) {
      comment += `**Recent Logs:**\n`;
      const recentLogs = issueData.logs.slice(-5); // Show last 5 logs
      recentLogs.forEach(log => {
        const logEmoji = log.type === 'error' ? '🔴' : log.type === 'warning' ? '🟡' : '🔵';
        const timestamp = new Date(log.timestamp).toISOString();
        comment += `${logEmoji} **${log.type.toUpperCase()}** [${timestamp}]: ${log.message}\n`;
      });
      comment += `\n`;
    }

    comment += `---\n*Updated automatically by UAT Explorer*`;
    
    return comment;
  }

  /**
   * Main method to create or update GitHub issue for test failure
   */
  async createOrUpdateIssue(issueData: UATIssueData): Promise<{ issueNumber: number; action: 'created' | 'updated' }> {
    if (!this.config.token) {
      throw new Error('GitHub token not configured. Set GITHUB_TOKEN environment variable.');
    }

    const signature = this.generateFailureSignature(issueData);
    const existingIssue = await this.findExistingIssue(signature);

    if (existingIssue) {
      await this.updateIssue(existingIssue, issueData);
      return { issueNumber: existingIssue, action: 'updated' };
    } else {
      const issueNumber = await this.createIssue(issueData, signature);
      return { issueNumber, action: 'created' };
    }
  }

  /**
   * Validate GitHub configuration
   */
  static validateConfig(): GitHubIssueConfig | null {
    const token = process.env.GITHUB_TOKEN;
    const owner = process.env.GITHUB_OWNER;
    const repo = process.env.GITHUB_REPO;

    if (!token || !owner || !repo) {
      return null;
    }

    return {
      token,
      owner,
      repo,
      labelPrefix: process.env.GITHUB_LABEL_PREFIX || 'uat',
      assignees: process.env.GITHUB_ASSIGNEES?.split(',').map(s => s.trim()) || []
    };
  }

  /**
   * Sanitize sensitive information from error messages and logs
   */
  static sanitizeContent(content: string): string {
    // Remove potential secrets, tokens, passwords, etc.
    const patterns = [
      /token["\s]*[:=]["\s]*[a-zA-Z0-9\-_.]+/gi,
      /password["\s]*[:=]["\s]*[^\s"]+/gi,
      /secret["\s]*[:=]["\s]*[^\s"]+/gi,
      /key["\s]*[:=]["\s]*[a-zA-Z0-9\-_.]+/gi,
      /authorization["\s]*:["\s]*[^\s"]+/gi,
      /bearer\s+[a-zA-Z0-9\-_.]+/gi,
      // Email addresses (partial masking)
      /([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
      // IP addresses (partial masking)
      /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b/g
    ];

    let sanitized = content;
    
    patterns.forEach(pattern => {
      sanitized = sanitized.replace(pattern, (match) => {
        if (match.includes('@')) {
          // Email: show first char and domain
          const parts = match.split('@');
          return `${parts[0][0]}***@${parts[1]}`;
        } else if (match.includes('.') && /\d/.test(match)) {
          // IP: mask last octet
          return match.replace(/\.\d{1,3}$/, '.***');
        } else {
          // Other secrets: replace with placeholder
          return match.substring(0, 10) + '***';
        }
      });
    });

    return sanitized;
  }
}
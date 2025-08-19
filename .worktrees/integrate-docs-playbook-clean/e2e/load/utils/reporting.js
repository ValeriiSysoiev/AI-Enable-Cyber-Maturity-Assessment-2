/**
 * Results aggregation and reporting utilities for k6 load testing
 * 
 * Processes test results, generates reports, and provides analysis.
 */

import { check } from 'k6';

/**
 * Test results aggregator
 */
export class ResultsAggregator {
  constructor() {
    this.metrics = {};
    this.startTime = Date.now();
    this.checkResults = [];
    this.errors = [];
    this.phases = [];
  }
  
  /**
   * Record metric value
   */
  recordMetric(name, value, tags = {}) {
    if (!this.metrics[name]) {
      this.metrics[name] = {
        values: [],
        tags: {},
        summary: {}
      };
    }
    
    this.metrics[name].values.push({
      value: value,
      timestamp: Date.now(),
      tags: tags
    });
  }
  
  /**
   * Record check result
   */
  recordCheck(name, success, details = {}) {
    this.checkResults.push({
      name: name,
      success: success,
      timestamp: Date.now(),
      details: details
    });
  }
  
  /**
   * Record error
   */
  recordError(error, context = {}) {
    this.errors.push({
      message: error.message || error,
      stack: error.stack,
      timestamp: Date.now(),
      context: context
    });
  }
  
  /**
   * Mark test phase
   */
  markPhase(phase, details = {}) {
    this.phases.push({
      phase: phase,
      timestamp: Date.now(),
      details: details
    });
  }
  
  /**
   * Calculate metric statistics
   */
  calculateMetricStats(values) {
    if (values.length === 0) return null;
    
    const sorted = values.map(v => v.value).sort((a, b) => a - b);
    const sum = sorted.reduce((a, b) => a + b, 0);
    
    return {
      count: sorted.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: sum / sorted.length,
      median: sorted[Math.floor(sorted.length / 2)],
      p90: sorted[Math.floor(sorted.length * 0.9)],
      p95: sorted[Math.floor(sorted.length * 0.95)],
      p99: sorted[Math.floor(sorted.length * 0.99)],
      sum: sum
    };
  }
  
  /**
   * Generate test summary
   */
  generateSummary() {
    const endTime = Date.now();
    const duration = (endTime - this.startTime) / 1000;
    
    // Calculate metric summaries
    Object.keys(this.metrics).forEach(name => {
      this.metrics[name].summary = this.calculateMetricStats(this.metrics[name].values);
    });
    
    // Calculate check success rate
    const totalChecks = this.checkResults.length;
    const successfulChecks = this.checkResults.filter(c => c.success).length;
    const checkSuccessRate = totalChecks > 0 ? successfulChecks / totalChecks : 0;
    
    // Group errors by type
    const errorSummary = {};
    this.errors.forEach(error => {
      const key = error.message || 'Unknown error';
      errorSummary[key] = (errorSummary[key] || 0) + 1;
    });
    
    return {
      overview: {
        testDuration: duration,
        startTime: new Date(this.startTime).toISOString(),
        endTime: new Date(endTime).toISOString(),
        totalChecks: totalChecks,
        successfulChecks: successfulChecks,
        checkSuccessRate: checkSuccessRate,
        totalErrors: this.errors.length
      },
      metrics: this.metrics,
      checks: {
        total: totalChecks,
        successful: successfulChecks,
        failed: totalChecks - successfulChecks,
        successRate: checkSuccessRate,
        details: this.checkResults
      },
      errors: {
        total: this.errors.length,
        summary: errorSummary,
        details: this.errors
      },
      phases: this.phases
    };
  }
  
  /**
   * Export summary as JSON
   */
  toJSON() {
    return JSON.stringify(this.generateSummary(), null, 2);
  }
}

/**
 * Performance analyzer
 */
export class PerformanceAnalyzer {
  constructor(results) {
    this.results = results;
  }
  
  /**
   * Analyze response time trends
   */
  analyzeResponseTimes() {
    const responseTimeMetrics = this.results.metrics['http_req_duration'] || 
                               this.results.metrics['response_time'] ||
                               this.results.metrics['custom_response_time'];
    
    if (!responseTimeMetrics || !responseTimeMetrics.summary) {
      return { status: 'no_data', message: 'No response time data available' };
    }
    
    const stats = responseTimeMetrics.summary;
    const analysis = {
      status: 'analyzed',
      performance: 'good',
      issues: [],
      recommendations: []
    };
    
    // Performance assessment
    if (stats.p95 > 5000) {
      analysis.performance = 'poor';
      analysis.issues.push('High P95 response time (> 5s)');
      analysis.recommendations.push('Investigate slow database queries and optimize API endpoints');
    } else if (stats.p95 > 2000) {
      analysis.performance = 'fair';
      analysis.issues.push('Elevated P95 response time (> 2s)');
      analysis.recommendations.push('Consider caching strategies and query optimization');
    }
    
    if (stats.max > 30000) {
      analysis.issues.push('Very high maximum response time (> 30s)');
      analysis.recommendations.push('Implement request timeouts and circuit breakers');
    }
    
    // Consistency assessment
    const variability = (stats.p95 - stats.median) / stats.median;
    if (variability > 2) {
      analysis.issues.push('High response time variability');
      analysis.recommendations.push('Investigate intermittent performance issues');
    }
    
    analysis.stats = stats;
    return analysis;
  }
  
  /**
   * Analyze error patterns
   */
  analyzeErrors() {
    const errorSummary = this.results.errors.summary;
    const totalErrors = this.results.errors.total;
    const totalChecks = this.results.checks.total;
    
    const analysis = {
      status: 'analyzed',
      errorRate: totalChecks > 0 ? totalErrors / totalChecks : 0,
      severity: 'low',
      patterns: [],
      recommendations: []
    };
    
    // Error rate assessment
    if (analysis.errorRate > 0.15) {
      analysis.severity = 'critical';
      analysis.recommendations.push('Immediate investigation required - high error rate');
    } else if (analysis.errorRate > 0.05) {
      analysis.severity = 'high';
      analysis.recommendations.push('Monitor error patterns and investigate root causes');
    } else if (analysis.errorRate > 0.02) {
      analysis.severity = 'medium';
      analysis.recommendations.push('Review error logs for potential issues');
    }
    
    // Pattern analysis
    Object.entries(errorSummary).forEach(([error, count]) => {
      const percentage = (count / totalErrors) * 100;
      
      if (percentage > 50) {
        analysis.patterns.push({
          type: 'dominant_error',
          error: error,
          percentage: percentage,
          impact: 'high'
        });
      } else if (percentage > 20) {
        analysis.patterns.push({
          type: 'frequent_error',
          error: error,
          percentage: percentage,
          impact: 'medium'
        });
      }
    });
    
    analysis.errorSummary = errorSummary;
    return analysis;
  }
  
  /**
   * Analyze throughput and capacity
   */
  analyzeThroughput() {
    const httpReqs = this.results.metrics['http_reqs'];
    const duration = this.results.overview.testDuration;
    
    if (!httpReqs || !httpReqs.summary) {
      return { status: 'no_data', message: 'No throughput data available' };
    }
    
    const totalRequests = httpReqs.summary.sum || httpReqs.summary.count;
    const avgRPS = totalRequests / duration;
    
    const analysis = {
      status: 'analyzed',
      totalRequests: totalRequests,
      duration: duration,
      avgRPS: avgRPS,
      capacity: 'unknown',
      recommendations: []
    };
    
    // Capacity assessment
    if (avgRPS < 10) {
      analysis.capacity = 'low';
      analysis.recommendations.push('System appears to have low throughput capacity');
    } else if (avgRPS < 50) {
      analysis.capacity = 'moderate';
      analysis.recommendations.push('Consider load testing with higher concurrency');
    } else if (avgRPS < 200) {
      analysis.capacity = 'good';
      analysis.recommendations.push('System shows good throughput capacity');
    } else {
      analysis.capacity = 'excellent';
      analysis.recommendations.push('System demonstrates high throughput capacity');
    }
    
    return analysis;
  }
  
  /**
   * Generate comprehensive analysis
   */
  generateAnalysis() {
    return {
      timestamp: new Date().toISOString(),
      overview: this.results.overview,
      responseTime: this.analyzeResponseTimes(),
      errors: this.analyzeErrors(),
      throughput: this.analyzeThroughput(),
      recommendations: this.generateRecommendations()
    };
  }
  
  /**
   * Generate actionable recommendations
   */
  generateRecommendations() {
    const recommendations = [];
    
    const rtAnalysis = this.analyzeResponseTimes();
    const errorAnalysis = this.analyzeErrors();
    const throughputAnalysis = this.analyzeThroughput();
    
    // Priority recommendations based on severity
    if (errorAnalysis.severity === 'critical') {
      recommendations.push({
        priority: 'critical',
        category: 'reliability',
        action: 'Investigate and fix high error rate immediately',
        details: `Error rate: ${(errorAnalysis.errorRate * 100).toFixed(2)}%`
      });
    }
    
    if (rtAnalysis.performance === 'poor') {
      recommendations.push({
        priority: 'high',
        category: 'performance',
        action: 'Optimize response times',
        details: `P95 response time: ${rtAnalysis.stats?.p95 || 'unknown'}ms`
      });
    }
    
    if (throughputAnalysis.capacity === 'low') {
      recommendations.push({
        priority: 'medium',
        category: 'capacity',
        action: 'Investigate low throughput capacity',
        details: `Average RPS: ${throughputAnalysis.avgRPS?.toFixed(2) || 'unknown'}`
      });
    }
    
    // General recommendations
    recommendations.push({
      priority: 'low',
      category: 'monitoring',
      action: 'Continue regular load testing',
      details: 'Establish baseline metrics and monitor trends'
    });
    
    return recommendations;
  }
}

/**
 * Report generator
 */
export class ReportGenerator {
  constructor(results, analysis) {
    this.results = results;
    this.analysis = analysis;
  }
  
  /**
   * Generate markdown report
   */
  generateMarkdownReport(scenario = 'unknown') {
    const report = [];
    
    // Header
    report.push(`# Load Test Report - ${scenario.toUpperCase()}`);
    report.push('');
    report.push(`**Generated**: ${new Date().toISOString()}`);
    report.push(`**Duration**: ${this.results.overview.testDuration.toFixed(2)}s`);
    report.push(`**Environment**: ${process.env.TARGET_ENV || 'unknown'}`);
    report.push('');
    
    // Executive Summary
    report.push('## Executive Summary');
    report.push('');
    
    const overallStatus = this.analysis.errors.severity === 'critical' ? '❌ FAILED' :
                         this.analysis.errors.severity === 'high' ? '⚠️ WARNING' : '✅ PASSED';
    
    report.push(`**Overall Status**: ${overallStatus}`);
    report.push(`**Total Requests**: ${this.results.overview.totalChecks || 'Unknown'}`);
    report.push(`**Success Rate**: ${(this.results.checks.successRate * 100).toFixed(2)}%`);
    report.push(`**Error Rate**: ${(this.analysis.errors.errorRate * 100).toFixed(2)}%`);
    report.push('');
    
    // Performance Metrics
    if (this.analysis.responseTime.stats) {
      report.push('## Performance Metrics');
      report.push('');
      report.push('| Metric | Value |');
      report.push('|--------|-------|');
      report.push(`| Average Response Time | ${this.analysis.responseTime.stats.avg.toFixed(2)}ms |`);
      report.push(`| P95 Response Time | ${this.analysis.responseTime.stats.p95.toFixed(2)}ms |`);
      report.push(`| P99 Response Time | ${this.analysis.responseTime.stats.p99.toFixed(2)}ms |`);
      report.push(`| Max Response Time | ${this.analysis.responseTime.stats.max.toFixed(2)}ms |`);
      report.push('');
    }
    
    // Throughput Analysis
    if (this.analysis.throughput.avgRPS) {
      report.push('## Throughput Analysis');
      report.push('');
      report.push(`**Average RPS**: ${this.analysis.throughput.avgRPS.toFixed(2)}`);
      report.push(`**Total Requests**: ${this.analysis.throughput.totalRequests}`);
      report.push(`**Capacity Assessment**: ${this.analysis.throughput.capacity}`);
      report.push('');
    }
    
    // Error Analysis
    if (this.results.errors.total > 0) {
      report.push('## Error Analysis');
      report.push('');
      report.push(`**Total Errors**: ${this.results.errors.total}`);
      report.push(`**Error Rate**: ${(this.analysis.errors.errorRate * 100).toFixed(2)}%`);
      report.push('');
      
      if (Object.keys(this.results.errors.summary).length > 0) {
        report.push('### Error Breakdown');
        report.push('');
        Object.entries(this.results.errors.summary).forEach(([error, count]) => {
          report.push(`- **${error}**: ${count} occurrences`);
        });
        report.push('');
      }
    }
    
    // Recommendations
    if (this.analysis.recommendations.length > 0) {
      report.push('## Recommendations');
      report.push('');
      
      const priorityOrder = ['critical', 'high', 'medium', 'low'];
      priorityOrder.forEach(priority => {
        const recs = this.analysis.recommendations.filter(r => r.priority === priority);
        if (recs.length > 0) {
          report.push(`### ${priority.toUpperCase()} Priority`);
          report.push('');
          recs.forEach(rec => {
            report.push(`- **${rec.action}** (${rec.category})`);
            if (rec.details) {
              report.push(`  - ${rec.details}`);
            }
          });
          report.push('');
        }
      });
    }
    
    // Test Configuration
    report.push('## Test Configuration');
    report.push('');
    report.push(`- **Scenario**: ${scenario}`);
    report.push(`- **Environment**: ${process.env.TARGET_ENV || 'unknown'}`);
    report.push(`- **Target URL**: ${process.env.DEV_API_URL || 'unknown'}`);
    report.push(`- **Auth Mode**: ${process.env.AUTH_MODE || 'unknown'}`);
    report.push('');
    
    return report.join('\n');
  }
  
  /**
   * Generate JSON report
   */
  generateJSONReport() {
    return JSON.stringify({
      metadata: {
        scenario: process.env.K6_SCENARIO || 'unknown',
        environment: process.env.TARGET_ENV || 'unknown',
        timestamp: new Date().toISOString(),
        generator: 'k6-load-testing'
      },
      results: this.results,
      analysis: this.analysis
    }, null, 2);
  }
  
  /**
   * Generate CSV summary
   */
  generateCSVSummary() {
    const rows = [
      'metric,value,unit',
      `test_duration,${this.results.overview.testDuration.toFixed(2)},seconds`,
      `total_requests,${this.results.overview.totalChecks},count`,
      `success_rate,${(this.results.checks.successRate * 100).toFixed(2)},percent`,
      `error_rate,${(this.analysis.errors.errorRate * 100).toFixed(2)},percent`,
      `total_errors,${this.results.errors.total},count`
    ];
    
    if (this.analysis.responseTime.stats) {
      const stats = this.analysis.responseTime.stats;
      rows.push(`avg_response_time,${stats.avg.toFixed(2)},ms`);
      rows.push(`p95_response_time,${stats.p95.toFixed(2)},ms`);
      rows.push(`p99_response_time,${stats.p99.toFixed(2)},ms`);
      rows.push(`max_response_time,${stats.max.toFixed(2)},ms`);
    }
    
    if (this.analysis.throughput.avgRPS) {
      rows.push(`avg_rps,${this.analysis.throughput.avgRPS.toFixed(2)},requests_per_second`);
    }
    
    return rows.join('\n');
  }
}

/**
 * Real-time monitoring utilities
 */
export class RealtimeMonitor {
  constructor(alertThresholds = {}) {
    this.thresholds = {
      errorRate: alertThresholds.errorRate || 0.10,
      responseTime: alertThresholds.responseTime || 5000,
      ...alertThresholds
    };
    this.alerts = [];
    this.metrics = {};
  }
  
  /**
   * Check thresholds and generate alerts
   */
  checkThresholds(currentMetrics) {
    const alerts = [];
    
    // Error rate check
    if (currentMetrics.errorRate > this.thresholds.errorRate) {
      alerts.push({
        type: 'error_rate',
        severity: 'high',
        message: `Error rate ${(currentMetrics.errorRate * 100).toFixed(2)}% exceeds threshold ${(this.thresholds.errorRate * 100).toFixed(2)}%`,
        timestamp: new Date().toISOString()
      });
    }
    
    // Response time check
    if (currentMetrics.avgResponseTime > this.thresholds.responseTime) {
      alerts.push({
        type: 'response_time',
        severity: 'medium',
        message: `Average response time ${currentMetrics.avgResponseTime.toFixed(2)}ms exceeds threshold ${this.thresholds.responseTime}ms`,
        timestamp: new Date().toISOString()
      });
    }
    
    this.alerts.push(...alerts);
    return alerts;
  }
  
  /**
   * Get current alerts
   */
  getAlerts() {
    return this.alerts;
  }
}

export default {
  ResultsAggregator,
  PerformanceAnalyzer,
  ReportGenerator,
  RealtimeMonitor
};
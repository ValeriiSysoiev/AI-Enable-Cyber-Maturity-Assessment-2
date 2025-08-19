# Security Scanning Runbook

This document provides comprehensive procedures for operating the automated security scanning system.

## 🎯 Overview

The automated security scanning system provides:
- **SAST (Static Application Security Testing)** using Semgrep and Bandit
- **Secret Detection** using Gitleaks
- **Dependency Vulnerability Scanning** using Trivy, pip-audit, and npm audit
- **Infrastructure Security** using tfsec and Checkov
- **Custom Rule Enforcement** for FastAPI, Next.js, and GDPR compliance

## 🚀 Getting Started

### Prerequisites
- GitHub Actions enabled
- Azure Application Insights configured
- Security team access permissions
- Required secrets configured in GitHub

### Required GitHub Secrets
```
GITHUB_TOKEN                    # Automatic (provided by GitHub)
APPLICATIONINSIGHTS_CONNECTION_STRING  # For telemetry
SLACK_WEBHOOK_URL              # For security alerts (optional)
SECURITY_EMAIL_ALERTS          # Comma-separated email list (optional)
```

## 📅 Scheduled Scans

### Daily Automated Scans
- **Time**: 2:00 AM UTC daily
- **Trigger**: GitHub Actions cron schedule
- **Scope**: Full security scan across all components
- **Duration**: 15-30 minutes
- **Artifacts**: Retained for 30 days

### Pull Request Scans
- **Trigger**: PR creation/update to main/develop branches
- **Scope**: Delta scanning (changed files only)
- **Duration**: 5-15 minutes
- **Integration**: PR status checks

### Manual Scans
```bash
# Trigger manual scan via GitHub Actions
gh workflow run security-scan.yml

# Run local security scan
python scripts/security/auto_remediate.py --scan-results=scan-results/ --mode=review_only
```

## 🔍 Scan Components

### 1. SAST (Static Application Security Testing)

#### Semgrep Analysis
```yaml
Tools: Semgrep with custom rules
Coverage: Python (FastAPI), TypeScript/JavaScript (Next.js)
Rules: 
  - security/rules/fastapi-security.yml
  - security/rules/nextjs-security.yml
  - security/rules/gdpr-compliance.yml
Output: semgrep-results.json, semgrep.sarif
```

**Common Findings:**
- Missing authentication dependencies
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure CORS configuration
- Hardcoded secrets
- Missing input validation

#### Bandit Analysis (Python)
```yaml
Tool: Bandit
Coverage: Python codebase (app/)
Severity: High, Medium
Output: bandit-results.json
```

**Common Findings:**
- Use of insecure functions
- Hardcoded passwords
- Shell injection risks
- Insecure random number generation
- SSL/TLS issues

### 2. Secret Detection

#### Gitleaks Scanning
```yaml
Tool: Gitleaks v8.18.0
Coverage: Entire repository including git history
Detection: 
  - API keys
  - Passwords
  - Tokens
  - Certificates
  - Database credentials
Output: gitleaks-results.json
```

**Secret Types Detected:**
- AWS Access Keys
- Azure Storage Keys
- Database passwords
- JWT secrets
- API tokens
- Private keys

### 3. Dependency Vulnerability Scanning

#### Python Dependencies
```yaml
Tool: pip-audit
Coverage: app/requirements.txt
Vulnerability Database: PyPI Advisory Database
Output: pip-audit-results.json
```

#### Node.js Dependencies
```yaml
Tool: npm audit
Coverage: web/package.json, web/package-lock.json
Vulnerability Database: NPM Advisory Database
Output: npm-audit-results.json
```

#### Container Image Scanning
```yaml
Tool: Trivy
Coverage: 
  - API Docker image (app/Dockerfile)
  - Web Docker image (web/Dockerfile)
Vulnerability Types: OS packages, application dependencies
Output: trivy-api-results.json, trivy-web-results.json
```

### 4. Infrastructure Security

#### Terraform Scanning
```yaml
Tool: tfsec
Coverage: infra/*.tf files
Checks: AWS/Azure security misconfigurations
Output: tfsec-results.json
```

#### Multi-Cloud Infrastructure
```yaml
Tool: Checkov
Coverage: Terraform, Dockerfile, Kubernetes manifests
Frameworks: CIS, NIST, GDPR
Output: checkov-results.json
```

## 🎛️ Scan Configuration

### Scan Modes

#### Basic Scan
- Essential security checks only
- Duration: 5-10 minutes
- Use case: PR validation

```yaml
# In workflow dispatch
scan_depth: 'basic'
```

#### Full Scan (Default)
- Comprehensive security analysis
- Duration: 15-30 minutes  
- Use case: Daily automated scans

```yaml
# In workflow dispatch
scan_depth: 'full'
```

#### Comprehensive Scan
- Full analysis + experimental rules
- Duration: 30-45 minutes
- Use case: Release preparation

```yaml
# In workflow dispatch
scan_depth: 'comprehensive'
```

### Auto-Remediation Settings

#### Safe Mode (Default)
```yaml
enable_auto_remediation: true
```
- Applies low-risk fixes automatically
- Creates commits for safe changes
- Requires manual review for high-risk items

#### Review Only Mode
```yaml
enable_auto_remediation: false
```
- No automatic changes
- Generates remediation report only
- Use for compliance audits

## 📊 Understanding Scan Results

### Security Score Calculation
```python
# Weighted scoring system
score = max(0, 100 - (
    critical_issues * 20 +
    high_issues * 10 +
    medium_issues * 5 +
    low_issues * 2
))
```

### Severity Levels
- **CRITICAL (20 pts)**: Immediate action required
- **HIGH (10 pts)**: Fix within 1 week
- **MEDIUM (5 pts)**: Fix within 1 month
- **LOW (2 pts)**: Fix during next maintenance window

### Score Interpretation
- **90-100**: Excellent security posture
- **70-89**: Good security with minor issues
- **50-69**: Moderate security gaps requiring attention
- **Below 50**: Significant security risks requiring immediate action

## 🚨 Alert Management

### Critical Alert Conditions
- Critical vulnerabilities found (score impact ≥ 20)
- Secrets detected in code
- New dependency vulnerabilities (CVSS ≥ 7.0)
- Security scan failures

### Alert Channels
1. **GitHub Security Tab**: SARIF uploads for all findings
2. **Slack Integration**: Critical and high severity alerts
3. **Email Notifications**: Executive summary for critical issues
4. **GitHub Issues**: Automated issue creation for critical findings

### Alert Response Times
- **Critical**: Acknowledge within 1 hour, resolve within 24 hours
- **High**: Acknowledge within 4 hours, resolve within 1 week
- **Medium**: Acknowledge within 1 day, resolve within 1 month

## 🔧 Troubleshooting

### Common Issues

#### Scan Timeouts
```yaml
# Increase timeout in workflow
timeout: 600000  # 10 minutes (max)
```

#### High False Positive Rate
```yaml
# Add exclusions to .semgrepignore
**/test_*.py
**/node_modules/**
```

#### Memory Issues (Large Repositories)
```yaml
# Split scanning by directory
- path: "app/"
- path: "web/"
```

#### Secret Detection False Positives
```yaml
# Add to .gitleaksignore
# Reason: test data
test-api-key-12345
```

### Scan Failure Recovery

#### Failed Semgrep Scan
1. Check .semgrepignore for syntax errors
2. Verify custom rules syntax
3. Check for unsupported file types
4. Review memory and timeout limits

#### Failed Secret Detection
1. Verify Gitleaks installation
2. Check for git repository corruption
3. Review large file exclusions
4. Validate .gitleaksignore syntax

#### Failed Dependency Scan
1. Verify package files exist and are valid
2. Check network connectivity for vulnerability databases
3. Review proxy settings if applicable
4. Validate package manager versions

## 📈 Performance Optimization

### Scan Performance Tips

#### Reduce Scan Scope
```yaml
# Use path filters
paths:
  include:
    - "app/**"
    - "web/src/**"
  exclude:
    - "**/test/**"
    - "**/node_modules/**"
```

#### Parallel Execution
```yaml
# Run scans in parallel
jobs:
  sast-scan:
    runs-on: ubuntu-latest
  secrets-scan:
    runs-on: ubuntu-latest
  vulnerability-scan:
    runs-on: ubuntu-latest
```

#### Cache Dependencies
```yaml
# Cache security tools
- name: Cache Semgrep
  uses: actions/cache@v3
  with:
    path: ~/.cache/semgrep
    key: semgrep-${{ hashFiles('security/rules/**') }}
```

## 📋 Maintenance Procedures

### Weekly Maintenance
- [ ] Review false positive reports
- [ ] Update security rule exclusions
- [ ] Check scan performance metrics
- [ ] Validate alert functionality

### Monthly Maintenance
- [ ] Update security scanning tools
- [ ] Review and update custom rules
- [ ] Audit scan coverage metrics
- [ ] Update threat intelligence feeds

### Quarterly Reviews
- [ ] Comprehensive scan configuration review
- [ ] Security team training on new features
- [ ] Integration testing with new tools
- [ ] Documentation updates

## 🎯 Metrics & KPIs

### Scan Coverage Metrics
- **Code Coverage**: Percentage of codebase scanned
- **Rule Coverage**: Active security rules vs. total available
- **Dependency Coverage**: Percentage of dependencies analyzed

### Performance Metrics
- **Scan Duration**: Average time per scan type
- **Success Rate**: Percentage of successful scans
- **False Positive Rate**: Ratio of false positives to total findings

### Security Metrics
- **Mean Time to Detection (MTTD)**: Average time to identify vulnerabilities
- **Mean Time to Resolution (MTTR)**: Average time to fix security issues
- **Security Debt**: Number of outstanding security findings

## 🔗 Integration Points

### CI/CD Integration
- **Pre-commit hooks**: Optional local scanning
- **PR gates**: Block PRs with critical findings
- **Release gates**: Require security scan passage

### External Tools
- **JIRA**: Automatic ticket creation for findings
- **PagerDuty**: Critical alert escalation
- **ServiceNow**: Compliance tracking integration

### Reporting Integration
- **Application Insights**: Telemetry and dashboards
- **Power BI**: Executive reporting
- **Grafana**: Real-time metrics visualization

---

## 📞 Support & Escalation

### Internal Support
- **Security Team**: security-team@company.com
- **DevSecOps**: devsecops-team@company.com
- **Platform Team**: platform-team@company.com

### External Support
- **Semgrep Support**: https://semgrep.dev/docs/support/
- **GitHub Security**: https://docs.github.com/en/code-security

### Escalation Path
1. **L1**: Team Lead (Response: 1 hour)
2. **L2**: Security Manager (Response: 4 hours)
3. **L3**: CISO (Response: 24 hours)

---

*Last Updated: 2025-08-17*  
*Next Review: 2025-11-17*
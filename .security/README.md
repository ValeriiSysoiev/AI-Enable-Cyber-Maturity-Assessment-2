# Security Configuration

This directory contains security scanning configurations to reduce false positives while maintaining robust security checks.

## SAST Configuration

**File**: `.security/sast-config.json`

- **Excludes**: Build artifacts, node_modules, cache directories, and generated files
- **Fail Threshold**: High severity issues only
- **Ignored Patterns**: Test files and mock directories
- **Focus**: Production code security vulnerabilities
- **Key Rules**: Prevents eval, unsafe HTML, hardcoded secrets, SQL injection, XSS, path traversal, and command injection

## Vulnerability Configuration  

**File**: `.security/vuln-config.json`

- **Fail Threshold**: High severity vulnerabilities only
- **Scope**: Production dependencies only (ignores dev dependencies)
- **Allowed Licenses**: Common open-source licenses (MIT, Apache-2.0, BSD, ISC, etc.)
- **Severity Thresholds**: Zero tolerance for critical/high, flexible for medium/low
- **Performance**: 5-minute timeout, skips unresolved advisories

## Implementation Strategy

Both configurations are tuned to:
1. Focus on production security issues only
2. Exclude build artifacts and test code
3. Fail builds only on high/critical severity findings
4. Reduce noise from false positives
5. Maintain essential security controls

## Usage

These configurations should be referenced in CI/CD pipelines:

```yaml
# Example GitHub Actions usage
- name: SAST Analysis
  run: security-scanner --config .security/sast-config.json

- name: Vulnerability Scan
  run: vuln-scanner --config .security/vuln-config.json
```
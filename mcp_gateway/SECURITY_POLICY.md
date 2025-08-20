# MCP Gateway Security Policy v1.3

## Executive Summary

This document outlines the comprehensive security policies and implementations for the Model Context Protocol (MCP) Gateway version 1.3. The security framework implements defense-in-depth principles with multiple validation layers, fail-secure defaults, and zero-trust architecture between engagements.

## Security Architecture Overview

### Core Security Principles

1. **Defense in Depth**: Multiple layers of security validation
2. **Fail Secure**: Deny by default, explicit allow policies
3. **Zero Trust**: No implicit trust between engagements
4. **Comprehensive Auditing**: All operations logged with secret redaction
5. **Least Privilege**: Minimal permissions and capabilities

### Security Boundaries

- **Engagement Isolation**: Complete data and tool access separation
- **File System Sandbox**: Jailed file operations per engagement
- **Network Boundaries**: Request/response size limits
- **Content Validation**: MIME type and pattern-based filtering

## Security Controls Implementation

### 1. Cross-Tenant Isolation

#### Tool Allowlists per Engagement
- Each engagement has a configurable tool allowlist
- Default allowlist: `fs.read`, `fs.write`, `fs.list`, `search.vector`, `search.semantic`
- Cross-tenant tool access attempts result in `CrossTenantError`
- API endpoints for allowlist management with validation

```python
# Example allowlist configuration
engagement_allowlists = {
    "engagement_alpha": {"fs.read", "fs.write"},
    "engagement_beta": {"fs.read", "search.vector"}
}
```

#### Data Path Isolation
- Engagement-specific data directories under secure root
- Path traversal prevention with pattern matching
- Symbolic link detection and blocking
- Absolute path validation within engagement boundaries

### 2. Secure File Operations

#### Path Security Validation
- Dangerous pattern detection (regex-based)
  - Parent directory traversal (`../`, `..\\`)
  - System directories (`/etc/`, `/proc/`, `/sys/`)
  - Variable expansion (`${VAR}`, `` `command` ``)
  - Null byte injection, URL encoding attacks

#### MIME Type Validation
**Allowed MIME Types:**
- Text: `text/plain`, `text/csv`, `text/markdown`, `text/html`
- Data: `application/json`, `application/xml`
- Documents: `application/pdf`, MS Office formats
- Images: `image/png`, `image/jpeg`, `image/gif`, `image/webp`

**Blocked MIME Types:**
- Executables: `application/x-executable`, `.exe`, `.sh`, `.bat`
- Archives: `application/zip`, `application/x-tar`
- Media: `video/*`, `audio/*` (unless specifically allowed)

#### File Permission Security
- Files written with `0o644` permissions (rw-r--r--)
- No execute permissions set on created files
- Directory permissions: `0o755` (rwxr-xr-x)
- Owner-only write access, group/other read-only

#### Size Limits
- File size limit: 10MB (configurable via `MCP_MAX_FILE_SIZE_MB`)
- Request/response size: 50MB (configurable via `MCP_MAX_REQUEST_SIZE_MB`)
- Content validation before processing

### 3. Secret Redaction and Logging

#### Comprehensive Secret Detection
**Sensitive Field Names (case-insensitive):**
- Credentials: `password`, `token`, `secret`, `key`, `auth`
- Identifiers: `session_id`, `api_key`, `access_token`
- Personal data: `ssn`, `email`, `phone`, `address`

**Pattern-Based Detection:**
- API keys: `[A-Za-z0-9]{20,}`
- JWT tokens: `eyJ[A-Za-z0-9_-]+\..*`
- URLs with credentials: `https://user:pass@host`
- Credit cards: `\b(?:\d{4}[-\s]?){3}\d{4}\b`
- SSH keys: `-----BEGIN.*PRIVATE KEY-----`

#### Redaction Implementation
- Field-level redaction: `[REDACTED]`
- Pattern-based replacement: `[REDACTED_TOKEN_TYPE]`
- Content truncation: `...[TRUNCATED from X chars]`
- Size limits: 500 chars per field, 10KB total

#### Audit Logging
- All MCP calls logged with:
  - Call ID, engagement ID, tool name
  - Execution time, success/failure status
  - Client IP address, timestamp
  - Redacted payload and result previews

### 4. Request/Response Protection

#### Size Validation
- Pre-processing request size validation
- Response size validation before return
- JSON serialization size estimation
- Memory-efficient processing for large data

#### Content Validation
- JSON structure validation
- UTF-8 encoding validation
- Content-Type header verification
- Malicious payload pattern detection

## Attack Vector Mitigation

### Path Traversal Attacks
**Blocked Patterns:**
```
../../../etc/passwd
..\\..\\windows\\system32
${HOME}/../../etc/shadow
`cat /etc/passwd`
%2e%2e%2f (URL encoded)
....//....// (double encoding)
file.txt\x00/etc/passwd (null byte)
```

**Mitigation:**
- Regex pattern matching before processing
- Path component sanitization
- Absolute path resolution and validation
- Symlink detection and rejection

### Cross-Tenant Access
**Attack Scenarios:**
- Engagement A accessing Engagement B's tools
- Data directory traversal between engagements
- Tool allowlist bypass attempts

**Mitigation:**
- Explicit engagement ID validation on every request
- Tool access validation against engagement allowlist
- Path validation within engagement boundaries
- Error logging for attempted violations

### Oversize Payload Attacks
**Attack Vectors:**
- Large file content uploads (DoS)
- Massive JSON payloads (memory exhaustion)
- Recursive data structures (parser attacks)

**Mitigation:**
- Pre-processing size limits (50MB default)
- File content size validation (10MB default)
- Recursive depth limits in data processing
- Memory-efficient streaming where possible

### MIME Type Confusion
**Attack Scenarios:**
- Executable files disguised as documents
- Script injection via file uploads
- Malicious content type spoofing

**Mitigation:**
- File extension and MIME type correlation
- Content-based type detection
- Allowlist-only approach (deny by default)
- Security headers for HTTP responses

### Secret Leakage
**Risk Areas:**
- API keys in request logs
- Database credentials in error messages
- JWT tokens in debug output
- Personal data in audit logs

**Mitigation:**
- Comprehensive pattern-based redaction
- Field name-based sensitive data detection
- Truncation of large content blocks
- Structured logging with automatic redaction

## Security Testing Framework

### Automated Security Tests
1. **Path Traversal Test Suite**: 15+ attack patterns
2. **Cross-Tenant Isolation Tests**: Tool and data access validation
3. **Oversize Payload Tests**: Memory and disk exhaustion prevention
4. **MIME Type Validation Tests**: Allowed and blocked file types
5. **Secret Redaction Tests**: Pattern and field-based detection
6. **Permission Tests**: File system security validation

### Security Gate Integration
- **Bandit**: Static analysis for Python security issues
- **Safety**: Known vulnerability detection in dependencies
- **Semgrep**: Advanced pattern matching for security flaws
- **TruffleHog**: Secret detection in source code
- **Custom Gates**: Application-specific security validations

### Continuous Security Monitoring
- Daily automated security scans
- Dependency vulnerability monitoring
- Log analysis for attack patterns
- Performance impact assessment

## Deployment Security

### Configuration Security
```bash
# Environment variables
MCP_DATA_ROOT=/secure/data/mcp
MCP_MAX_FILE_SIZE_MB=10
MCP_MAX_REQUEST_SIZE_MB=50
MCP_ENABLED=true
```

### Network Security
- TLS 1.3 encryption for all communications
- Request rate limiting and throttling
- IP-based access controls where applicable
- Security headers (CSP, HSTS, etc.)

### Infrastructure Security
- Container security scanning
- Minimal base images (distroless/alpine)
- Non-root container execution
- Resource limits and quotas

## Incident Response

### Security Event Classification
- **Critical**: Data breach, system compromise
- **High**: Authentication bypass, privilege escalation
- **Medium**: DoS attacks, data leakage
- **Low**: Failed login attempts, suspicious patterns

### Response Procedures
1. **Detection**: Automated monitoring and alerting
2. **Assessment**: Severity and impact evaluation
3. **Containment**: Immediate threat isolation
4. **Investigation**: Root cause analysis
5. **Recovery**: System restoration and hardening
6. **Lessons Learned**: Process and control improvements

### Contact Information
- Security Team: security@company.com
- On-call Engineer: +1-XXX-XXX-XXXX
- Incident Response: incident-response@company.com

## Compliance and Governance

### Security Standards Alignment
- OWASP Top 10 mitigation
- NIST Cybersecurity Framework
- ISO 27001 controls implementation
- SOC 2 Type II requirements

### Regular Security Reviews
- Quarterly security architecture review
- Annual penetration testing
- Monthly vulnerability assessments
- Continuous threat modeling updates

### Security Metrics
- Mean Time to Detection (MTTD)
- Mean Time to Response (MTTR)
- Security test coverage percentage
- Vulnerability remediation time
- Security training completion rates

## Maintenance and Updates

### Security Update Cycle
- **Critical**: Immediate (within 24 hours)
- **High**: Weekly maintenance window
- **Medium**: Monthly security updates
- **Low**: Quarterly review cycle

### Version Control and Rollback
- All security configurations version controlled
- Automated rollback procedures for security updates
- Blue/green deployment for zero-downtime updates
- Configuration drift detection and remediation

---

**Document Version**: 1.3.0  
**Last Updated**: 2024-08-20  
**Next Review**: 2024-11-20  
**Classification**: Internal Use
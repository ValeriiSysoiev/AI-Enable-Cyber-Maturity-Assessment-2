# Security

## Identity Model

### Authentication

**Production Environment**: Azure AD (Entra ID) only

- **Protocol**: OAuth 2.0 / OpenID Connect
- **Provider**: Microsoft Identity Platform
- **Token Type**: JWT with refresh tokens
- **Session Management**: Secure cookies with httpOnly flag

### Authorization

**Role-Based Access Control (RBAC)**:

| Role | Permissions | Use Case |
|------|------------|----------|
| **Admin** | Full system access | Platform administrators |
| **Consultant** | Create/edit assessments | Security consultants |
| **Client** | View assessments | Client stakeholders |
| **Guest** | Limited read access | External reviewers |

### User Management

- Users provisioned via Azure AD
- Group-based role assignment
- Multi-factor authentication (MFA) enforced
- Conditional access policies applied

## Secret Management

### Secret Storage Policy

1. **No secrets in code**: All secrets externalized
2. **Azure Key Vault**: Primary secret store
3. **GitHub Secrets**: For CI/CD only
4. **Managed Identities**: Preferred over keys
5. **Rotation Schedule**: Quarterly for all secrets

### Secret Types

| Secret Type | Storage | Rotation | Access |
|-------------|---------|----------|--------|
| API Keys | Key Vault | 90 days | Managed Identity |
| Database Keys | Key Vault | 90 days | Container Apps |
| Client Secrets | Key Vault | 365 days | GitHub Actions |
| Certificates | Key Vault | Annual | Automatic |
| Session Keys | Generated | Per deployment | Application |

### Secret Access Audit

```bash
# View Key Vault access logs
az monitor activity-log list \
  --resource-group rg-cybermat-prd \
  --namespace Microsoft.KeyVault \
  --start-time 2025-08-01T00:00:00Z \
  --query "[?contains(operationName.value, 'SecretGet')]"
```

## Logging & Redaction

### Logging Policy

**What to Log**:
- Authentication events
- Authorization decisions
- Data access patterns
- System errors
- Performance metrics

**What NOT to Log**:
- Passwords or secrets
- Personal identifiable information (PII)
- Session tokens
- Sensitive business data
- Full request/response bodies

### Log Redaction Rules

```python
# Example redaction patterns
REDACTION_PATTERNS = [
    r"password[\"\']?\s*[:=]\s*[\"\']?[^\s\"\']+",  # Passwords
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Emails
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"Bearer\s+[A-Za-z0-9\-._~\+\/]+=*",  # Bearer tokens
]
```

### Audit Logging

All security events logged to:
- Azure Log Analytics workspace
- Retention: 90 days minimum
- Immutable audit trail
- SIEM integration available

## Security Gates

### SAST (Static Application Security Testing)

**Tools**:
- Semgrep for code analysis
- Bandit for Python security
- ESLint security plugin for JavaScript

**CI/CD Integration**:
```yaml
# Runs on every PR
- name: Security Scan
  run: |
    semgrep --config=auto
    bandit -r app/
    npm audit
```

### Vulnerability Scanning

**Container Scanning**:
- Azure Container Registry scanning
- Trivy in CI pipeline
- Weekly vulnerability reports

**Dependency Scanning**:
- Dependabot alerts
- npm audit for Node.js
- pip-audit for Python

### Infrastructure Security

**Network Security**:
- Private endpoints for data services
- Network security groups (NSGs)
- Web Application Firewall (WAF)
- DDoS protection enabled

**Compliance Checks**:
- Azure Policy enforcement
- Security Center recommendations
- Compliance dashboard monitoring

## Security Headers

### Web Application Headers

```typescript
// Security headers configuration
const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'",
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'X-XSS-Protection': '1; mode=block',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'
}
```

### API Security Headers

```python
# FastAPI security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Data Protection

### Encryption

**At Rest**:
- Azure Storage: AES-256 encryption
- Cosmos DB: Transparent data encryption
- Key Vault: HSM-backed keys

**In Transit**:
- TLS 1.2 minimum
- Certificate pinning for critical services
- End-to-end encryption for sensitive data

### Data Classification

| Level | Description | Controls |
|-------|-------------|----------|
| **Public** | Marketing content | Basic protection |
| **Internal** | Business data | Access control |
| **Confidential** | Customer data | Encryption + audit |
| **Secret** | Security keys | HSM + MFA |

## Threat Model

### STRIDE Analysis

| Threat | Mitigation |
|--------|------------|
| **Spoofing** | Azure AD authentication, MFA |
| **Tampering** | Request signing, integrity checks |
| **Repudiation** | Audit logging, non-repudiation |
| **Information Disclosure** | Encryption, access controls |
| **Denial of Service** | Rate limiting, auto-scaling |
| **Elevation of Privilege** | RBAC, least privilege |

### Common Attack Vectors

1. **SQL Injection**: Parameterized queries, input validation
2. **XSS**: Content Security Policy, output encoding
3. **CSRF**: Anti-CSRF tokens, SameSite cookies
4. **SSRF**: URL allowlisting, network isolation
5. **XXE**: Disable XML external entities
6. **Path Traversal**: Input sanitization, chroot

## Incident Response

### Security Incident Process

1. **Detection**: Security alerts, monitoring
2. **Containment**: Isolate affected systems
3. **Investigation**: Log analysis, forensics
4. **Eradication**: Remove threat, patch vulnerability
5. **Recovery**: Restore services, verify integrity
6. **Lessons Learned**: Post-incident review

### Security Contacts

- **Security Team**: security@company.com
- **Incident Response**: incident-response@company.com
- **24/7 Hotline**: +1-XXX-XXX-XXXX
- **Azure Support**: Via Azure Portal

## Compliance

### Standards & Frameworks

- **ISO 27001**: Information security management
- **SOC 2 Type II**: Security controls audit
- **GDPR**: Data privacy compliance
- **NIST CSF**: Cybersecurity framework alignment

### Regular Assessments

| Assessment | Frequency | Scope |
|------------|-----------|-------|
| Penetration Testing | Annual | Full application |
| Vulnerability Assessment | Quarterly | Infrastructure |
| Security Review | Monthly | Code changes |
| Compliance Audit | Annual | Full system |

## Security Best Practices

### Development

1. **Security by Design**: Consider security from inception
2. **Secure Coding**: Follow OWASP guidelines
3. **Code Review**: Security-focused peer reviews
4. **Security Testing**: Include security in test cases
5. **Dependency Management**: Keep dependencies updated

### Operations

1. **Least Privilege**: Minimal necessary permissions
2. **Defense in Depth**: Multiple security layers
3. **Zero Trust**: Verify everything, trust nothing
4. **Monitoring**: Continuous security monitoring
5. **Incident Readiness**: Regular drills and updates

### Access Management

1. **MFA Everywhere**: Enforce for all users
2. **Regular Reviews**: Quarterly access audits
3. **Offboarding**: Immediate revocation on departure
4. **Privileged Access**: Time-bound, justified
5. **Service Accounts**: Managed identities preferred

## Security Tooling

### Monitoring Tools

- **Azure Security Center**: Cloud security posture
- **Azure Sentinel**: SIEM and SOAR
- **Application Insights**: Application monitoring
- **Azure Monitor**: Infrastructure monitoring

### Scanning Tools

- **Trivy**: Container vulnerability scanning
- **OWASP ZAP**: Dynamic application testing
- **Semgrep**: Static code analysis
- **ScoutSuite**: Cloud security auditing

## Security Training

### Required Training

- Security awareness: All staff, annual
- Secure coding: Developers, bi-annual
- Incident response: Operations, quarterly
- Compliance training: As needed

### Resources

- OWASP Top 10 documentation
- Azure Security best practices
- Internal security wiki
- Security champions program
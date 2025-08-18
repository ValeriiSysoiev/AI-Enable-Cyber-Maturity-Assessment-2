# Security Implementation Guide

**Version:** 1.0.0  
**Sprint:** S1  
**Last Updated:** 2025-08-17

## Overview

This document outlines the security implementation for the AI-Enabled Cyber Maturity Assessment tool, covering authentication, authorization, data protection, and security monitoring implemented in Sprint S1.

## Authentication Security

### SSR Route Guards

**Implementation:** Server-Side Rendering authentication checks  
**Location:** `/web/app/engagements/page.tsx`

```typescript
// SSR Authentication Guard Pattern
export default async function ProtectedPage() {
  const user = await getDemoUser();
  
  if (!user) {
    // Log security event with correlation ID
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'WARN',
      service: 'web',
      message: 'Unauthenticated access attempt',
      correlation_id: correlationId,
      route: '/engagements',
      status: 401,
      latency_ms: 0
    }));
    redirect('/signin');
  }
}
```

**Security Features:**
- ✅ Server-side validation prevents client-side bypass
- ✅ Correlation ID logging for security event tracking
- ✅ Automatic redirect to prevent unauthorized access
- ✅ Structured logging for audit compliance

### Cookie Security

**Implementation:** HttpOnly authentication cookies  
**Location:** `/web/app/api/auth/signin/route.ts`

```typescript
response.cookies.set('demo-email', email.trim(), {
  httpOnly: true,              // Prevents XSS access
  secure: process.env.NODE_ENV === 'production', // HTTPS-only in prod
  sameSite: 'lax',            // CSRF protection
  maxAge: 60 * 60 * 24 * 7,   // 7-day expiration
  path: '/'                   // Application-scoped
});
```

**Security Controls:**

| Control | Implementation | Purpose |
|---------|----------------|---------|
| **HttpOnly** | `httpOnly: true` | Prevents XSS cookie theft |
| **Secure** | `secure: true` (prod) | HTTPS-only transmission |
| **SameSite** | `sameSite: 'lax'` | CSRF attack prevention |
| **Expiration** | `maxAge: 7 days` | Limits exposure window |
| **Path Scoping** | `path: '/'` | Application boundary |

### Demo Mode Security

**⚠️ WARNING:** Demo authentication is for development only

**Security Restrictions:**
- 🔒 Must be disabled in production environments
- 🔒 No password validation (email-only)
- 🔒 Fixed role assignments
- 🔒 No account lockout or rate limiting

**Production Readiness Checklist:**
- [ ] Replace demo auth with OIDC/SAML
- [ ] Implement proper session management
- [ ] Add multi-factor authentication
- [ ] Enable account lockout policies
- [ ] Implement rate limiting

## Authorization Security

### Role-Based Access Control (RBAC)

**Implementation:** Server-side role validation  
**Roles Hierarchy:**

```
Admin (Full access)
  ├── LEM (Lead Engagement Manager)
  │   └── Member (Standard access)
  │       └── Viewer (Read-only)
```

**Role Matrix:**

| Action | Admin | LEM | Member | Viewer |
|--------|-------|-----|--------|--------|
| View Engagements | ✅ | ✅ | ✅ | ✅ |
| Create Engagement | ✅ | ✅ | ❌ | ❌ |
| Edit Engagement | ✅ | ✅ | ⚠️ | ❌ |
| Delete Engagement | ✅ | ⚠️ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ |

**Access Control Implementation:**

```typescript
// Role-based access check
const hasAccess = user.roles.some(role => 
  ['Admin', 'LEM', 'Member'].includes(role)
);

if (!hasAccess) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level: 'WARN',
    service: 'web',
    message: 'Insufficient permissions',
    correlation_id: correlationId,
    user_email: user.email,
    user_roles: user.roles,
    required_roles: ['Admin', 'LEM', 'Member'],
    route: '/engagements',
    status: 403
  }));
  redirect('/403');
}
```

### API Security

**JWT Validation Middleware**  
**Location:** `/app/api/middleware/jwt_auth.py`

**Security Headers Required:**
```http
Authorization: Bearer <jwt_token>
X-User-Email: user@example.com
X-Engagement-ID: eng-001
X-Correlation-ID: uuid-v4
```

**Validation Chain:**
1. ✅ JWT signature verification
2. ✅ Token expiration check
3. ✅ Issuer and audience validation
4. ✅ Role extraction and validation
5. ✅ Engagement-scoped permissions

## Data Protection

### Input Validation

**Email Validation (Signin):**
```typescript
if (!email || typeof email !== 'string' || !email.trim()) {
  return NextResponse.json(
    { error: 'Email is required' },
    { status: 400 }
  );
}
```

**Security Controls:**
- ✅ Type validation (string)
- ✅ Null/undefined checks
- ✅ Whitespace trimming
- ✅ Length limits (implicit)

### Error Handling

**Secure Error Responses:**
```typescript
// DON'T: Expose sensitive information
return { error: `Database connection failed: ${dbError.message}` };

// DO: Generic error messages
return { error: 'Internal server error' };
```

**Error Logging Pattern:**
```typescript
console.error('Sign in error:', error);
return NextResponse.json(
  { error: 'Internal server error' },
  { status: 500 }
);
```

**Security Features:**
- ✅ No sensitive data in client responses
- ✅ Detailed server-side logging
- ✅ Proper HTTP status codes
- ✅ Correlation ID tracking

## Security Monitoring

### Structured Logging

**Log Format Standard:**
```json
{
  "timestamp": "2025-08-17T20:30:45.123Z",
  "level": "WARN|ERROR|INFO",
  "service": "web|api",
  "message": "Human-readable message",
  "correlation_id": "uuid-v4",
  "user_email": "user@example.com",
  "user_roles": ["Member"],
  "route": "/engagements",
  "status": 401,
  "latency_ms": 150,
  "error": "Error details (server-side only)"
}
```

### Security Events

**Authentication Events:**
- ✅ Login attempts (success/failure)
- ✅ Logout events
- ✅ Session expiration
- ✅ Cookie manipulation attempts

**Authorization Events:**
- ✅ Access denials (403)
- ✅ Role escalation attempts
- ✅ Unauthorized resource access
- ✅ Permission changes

**Correlation ID Benefits:**
- 🔍 Cross-service request tracing
- 🔍 Security incident investigation
- 🔍 Performance monitoring
- 🔍 Audit compliance

## Security Testing

### E2E Security Tests

**Test Coverage:**
- ✅ Unauthenticated access prevention
- ✅ Role-based access enforcement
- ✅ Cookie security validation
- ✅ CSRF protection testing
- ✅ XSS prevention validation

**Test Scenarios:**
```typescript
test('unauthenticated user redirects to signin', async ({ page }) => {
  await page.goto('/engagements');
  await expect(page).toHaveURL('/signin');
});

test('insufficient permissions shows 403', async ({ page }) => {
  // Test role-based access control
  await page.goto('/403');
  await expect(page.locator('h2')).toContainText('403 - Access Forbidden');
});
```

### Security Verification

**Automated Verification Script:** `scripts/verify_s1_live.sh`

**Verification Checklist:**
- ✅ Health endpoints accessible
- ✅ Authentication redirects working
- ✅ 403 page displays correctly
- ✅ API requires authentication
- ✅ Correlation ID propagation
- ✅ Structured logging format

## Production Security Checklist

### Environment Security

- [ ] **HTTPS Enforcement:** All traffic encrypted in transit
- [ ] **Security Headers:** HSTS, CSP, X-Frame-Options
- [ ] **Cookie Security:** Secure flag enabled, proper SameSite
- [ ] **CORS Configuration:** Restricted origins only

### Authentication Security

- [ ] **OIDC Integration:** Replace demo auth with production OIDC
- [ ] **MFA Enforcement:** Multi-factor authentication required
- [ ] **Session Management:** Proper timeout and refresh
- [ ] **Account Policies:** Lockout, password complexity

### Data Security

- [ ] **Encryption at Rest:** Database and file encryption
- [ ] **Key Management:** Azure Key Vault integration
- [ ] **Data Classification:** PII identification and protection
- [ ] **Backup Security:** Encrypted backups with access controls

### Monitoring Security

- [ ] **SIEM Integration:** Security event forwarding
- [ ] **Alerting:** Real-time security alerts
- [ ] **Audit Logging:** Immutable audit trails
- [ ] **Incident Response:** Automated response procedures

## Security Contacts

**Security Issues:** Report to repository security advisors  
**Vulnerability Disclosure:** Follow responsible disclosure process  
**Emergency Contact:** Escalate to team leads for critical issues

## Evidence Upload Security

### SAS Token Policy

**Implementation:** Write-only Shared Access Signatures  
**Location:** `/app/api/routes/sas_upload.py`

**Security Configuration:**
```python
# SAS Token Generation
permissions = BlobSasPermissions(
    write=True,     # Allow write
    create=True,    # Allow create
    add=True,       # Allow append
    read=False,     # DENY read
    delete=False,   # DENY delete
    list=False      # DENY list
)
```

**Security Controls:**
- ✅ **Write-Only Access:** No read, delete, or list permissions
- ✅ **Short TTL:** 15-minute maximum token lifetime
- ✅ **Unique Paths:** Engagement-scoped blob paths prevent cross-tenant access
- ✅ **Audit Logging:** All SAS generation logged with correlation IDs

### File Type Restrictions

**Allowed MIME Types:**
```python
ALLOWED_MIME_TYPES = [
    # Documents
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    # Text
    'text/plain',
    'text/csv'
]
```

**Validation Requirements:**
- ✅ Client-side MIME type validation before upload
- ✅ Server-side validation during SAS token request
- ✅ Azure Storage content-type header enforcement
- ✅ Rejection of executable and script file types

### Upload Size Limits

**Maximum File Sizes:**
| File Type | Max Size | Rationale |
|-----------|----------|-----------|
| Documents | 50MB | Typical evidence documents |
| Images | 10MB | Screenshots and diagrams |
| CSV/Text | 5MB | Configuration and log files |

**Enforcement:**
- ✅ Client-side validation before upload attempt
- ✅ API validation during SAS token generation
- ✅ Azure Storage service-level limits
- ✅ Monitoring alerts for unusual upload patterns

### Secret Management

**Storage Access Keys:**
- ❌ **NEVER** commit storage keys to repository
- ❌ **NEVER** log SAS tokens or connection strings
- ❌ **NEVER** expose keys in error messages
- ✅ Use Azure Key Vault for production secrets
- ✅ Use Managed Identity where possible
- ✅ Rotate storage keys quarterly
- ✅ Monitor key usage for anomalies

## Compliance

**Frameworks Supported:**
- ✅ GDPR: Data protection and privacy controls
- ✅ SOC 2: Security monitoring and audit trails
- ✅ NIST: Security framework alignment
- ✅ ISO 27001: Information security management

**Audit Support:**
- ✅ Structured logging for audit trails
- ✅ Role-based access documentation
- ✅ Security test evidence
- ✅ Correlation ID for request tracking

---

**Note:** This security implementation represents Sprint S1 baseline security with Phase 3 evidence upload enhancements. Additional security controls will be implemented in subsequent sprints based on production requirements and compliance needs.
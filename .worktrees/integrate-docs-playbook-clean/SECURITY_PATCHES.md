# Critical Security Patches for Immediate Application

## Patch 1: SQL Injection Fix for RAG Service

**File**: `/app/services/rag.py`

```diff
--- a/app/services/rag.py
+++ b/app/services/rag.py
@@ -10,6 +10,7 @@ import uuid
 from typing import List, Dict, Any, Optional, Tuple
 from dataclasses import dataclass, asdict
 from datetime import datetime, timezone
+import re
 
 from azure.search.documents import SearchClient
 from azure.search.documents.indexes import SearchIndexClient
@@ -303,6 +304,20 @@ class RAGService:
                 else:
                     raise
     
+    def _validate_engagement_id(self, engagement_id: str) -> str:
+        """Validate and sanitize engagement ID to prevent injection"""
+        if not engagement_id or not engagement_id.strip():
+            raise ValueError("Engagement ID cannot be empty")
+        
+        # Allow only alphanumeric, hyphens, underscores
+        if not re.match(r'^[a-zA-Z0-9_-]+$', engagement_id):
+            raise ValueError(f"Invalid engagement ID format: {engagement_id}")
+        
+        # Escape single quotes for OData filter
+        safe_id = engagement_id.replace("'", "''")
+        
+        return safe_id
+    
     async def search(
         self, 
         query: str, 
@@ -355,8 +370,11 @@ class RAGService:
                 fields="content_vector"
             )
             
-            # Engagement filter
-            filter_expression = f"engagement_id eq '{engagement_id}'"
+            # Validate and create safe engagement filter
+            try:
+                safe_engagement_id = self._validate_engagement_id(engagement_id)
+                filter_expression = f"engagement_id eq '{safe_engagement_id}'"
+            except ValueError as e:
+                raise ValueError(f"Invalid engagement ID: {str(e)}")
             
             # Execute search
             if config.rag.use_hybrid_search:
@@ -517,7 +535,11 @@ class RAGService:
     async def _delete_engagement_documents(self, engagement_id: str):
         """Delete all documents for an engagement from the search index"""
         try:
-            # Search for all documents in the engagement
-            filter_expr = f"engagement_id eq '{engagement_id}'"
+            # Validate engagement ID first
+            try:
+                safe_engagement_id = self._validate_engagement_id(engagement_id)
+                filter_expr = f"engagement_id eq '{safe_engagement_id}'"
+            except ValueError as e:
+                logger.error(f"Invalid engagement ID for deletion: {e}")
+                return
+                
             results = await asyncio.to_thread(
                 self.search_client.search,
```

## Patch 2: Path Traversal Fix for Document Upload

**File**: `/app/api/routes/documents.py`

```diff
--- a/app/api/routes/documents.py
+++ b/app/api/routes/documents.py
@@ -1,6 +1,7 @@
 from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks
 from fastapi.responses import FileResponse
-import os, uuid, shutil, logging
+import os, uuid, shutil, logging, re
+import pathlib
 from pydantic import BaseModel
 from datetime import datetime
 from typing import Optional, Dict, Any, List
@@ -35,6 +36,29 @@ def _max_bytes():
     mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
     return mb * 1024 * 1024
 
+def _sanitize_filename(filename: str) -> str:
+    """Sanitize filename to prevent path traversal attacks"""
+    if not filename:
+        return f"upload_{uuid.uuid4().hex}"
+    
+    # Remove any directory components
+    filename = os.path.basename(filename)
+    
+    # Remove null bytes and control characters
+    filename = ''.join(char for char in filename if ord(char) >= 32 and char != '\x00')
+    
+    # Limit filename length
+    max_length = 255
+    if len(filename) > max_length:
+        name, ext = os.path.splitext(filename)
+        filename = name[:max_length-len(ext)-10] + ext
+    
+    # Whitelist allowed characters (alphanumeric, dots, hyphens, underscores)
+    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
+    
+    # Ensure filename is not empty after sanitization
+    return filename if filename else f"upload_{uuid.uuid4().hex}"
+
 @router.post("", response_model=list[DocumentPublic])
 async def upload_docs(engagement_id: str,
                       files: list[UploadFile] = File(...),
@@ -47,8 +71,17 @@ async def upload_docs(engagement_id: str,
     os.makedirs(updir, exist_ok=True)
     maxb = _max_bytes()
     for f in files:
-        fname = os.path.basename(f.filename or f"upload-{uuid.uuid4().hex}")
-        dest = safe_join(updir, f"{uuid.uuid4().hex}__{fname}")
+        original_fname = f.filename or f"upload-{uuid.uuid4().hex}"
+        safe_fname = _sanitize_filename(original_fname)
+        
+        # Generate unique filename
+        unique_id = uuid.uuid4().hex[:16]
+        dest_name = f"{unique_id}_{safe_fname}"
+        
+        # Use pathlib for safe path construction and verify it's within upload dir
+        dest_path = pathlib.Path(updir) / dest_name
+        dest = str(dest_path.resolve())
+        if not dest.startswith(os.path.abspath(updir)):
+            raise HTTPException(400, "Invalid file path")
+            
         total = 0
         with open(dest, "wb") as out:
             while True:
@@ -64,7 +97,7 @@ async def upload_docs(engagement_id: str,
                 out.write(chunk)
         d = Document(
             engagement_id=engagement_id,
-            filename=fname,
+            filename=safe_fname,  # Store sanitized filename
             content_type=f.content_type,
             size=total,
             path=os.path.abspath(dest),
```

## Patch 3: Input Validation for Search Queries

**File**: `/app/api/routes/documents.py`

```diff
--- a/app/api/routes/documents.py
+++ b/app/api/routes/documents.py
@@ -1,6 +1,7 @@
 from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks
 from fastapi.responses import FileResponse
 import os, uuid, shutil, logging
+import html
 from pydantic import BaseModel
 from datetime import datetime
 from typing import Optional, Dict, Any, List
@@ -143,7 +144,8 @@ class BulkIngestionStatusResponse(BaseModel):
 class SearchDocumentsRequest(BaseModel):
     """Request model for document search"""
-    query: str
+    query: str = Field(..., min_length=1, max_length=1000)
     top_k: Optional[int] = None
 
@@ -435,6 +437,32 @@ def get_ingestion_status(
         summary=status_counts
     )
 
+def _validate_search_query(query: str) -> str:
+    """Validate and sanitize search query to prevent injection attacks"""
+    if not query or not query.strip():
+        raise ValueError("Search query cannot be empty")
+    
+    # Length validation (already enforced by Pydantic, but double-check)
+    if len(query) > 1000:
+        raise ValueError("Search query exceeds maximum length of 1000 characters")
+    
+    # HTML escape to prevent XSS
+    query = html.escape(query)
+    
+    # Check for common injection patterns
+    dangerous_patterns = [
+        r'<script',
+        r'javascript:',
+        r'on\w+\s*=',  # Event handlers
+        r'\$\{',  # Template injection
+        r'{{',  # Template injection
+        r'exec\s*\(',
+        r'eval\s*\(',
+    ]
+    
+    for pattern in dangerous_patterns:
+        if re.search(pattern, query, re.IGNORECASE):
+            raise ValueError(f"Query contains potentially dangerous content")
+    
+    return query.strip()
 
 @router.post("/search", response_model=SearchDocumentsResponse)
 async def search_documents(
@@ -454,8 +482,13 @@ async def search_documents(
     # Verify permissions
     require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
     
-    if not search_request.query.strip():
-        raise HTTPException(status_code=400, detail="Search query cannot be empty")
+    # Validate and sanitize query
+    try:
+        validated_query = _validate_search_query(search_request.query)
+    except ValueError as e:
+        raise HTTPException(status_code=400, detail=str(e))
+    
+    logger.info(f"Validated search query: {validated_query[:100]}...")  # Log truncated query
     
     correlation_id = get_correlation_id(request)
     
@@ -473,7 +506,7 @@ async def search_documents(
         # Perform search
         rag_service = create_rag_service(correlation_id)
         results = await rag_service.search(
-            query=search_request.query,
+            query=validated_query,
             engagement_id=engagement_id,
             top_k=search_request.top_k
         )
```

## Patch 4: Secure Authentication Headers

**File**: `/web/app/api/proxy/[...path]/route.ts`

```diff
--- a/web/app/api/proxy/[...path]/route.ts
+++ b/web/app/api/proxy/[...path]/route.ts
@@ -1,5 +1,6 @@
 import { NextRequest, NextResponse } from 'next/server';
 import { getAuthHeaders } from '@/components/AuthProvider';
+import crypto from 'crypto';
 
 const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
 
@@ -19,6 +20,38 @@ export async function DELETE(request: NextRequest, { params }: { params: { path
   return handleRequest(request, params.path, 'DELETE');
 }
 
+function validateHeaders(headers: Record<string, string>): Record<string, string> {
+  const validated: Record<string, string> = {};
+  
+  // Validate email header
+  if (headers['X-User-Email']) {
+    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
+    const email = headers['X-User-Email'].toLowerCase().trim();
+    
+    if (!emailRegex.test(email)) {
+      throw new Error('Invalid email format in X-User-Email header');
+    }
+    validated['X-User-Email'] = email;
+  }
+  
+  // Validate engagement ID header
+  if (headers['X-Engagement-ID']) {
+    const idRegex = /^[a-zA-Z0-9_-]+$/;
+    const id = headers['X-Engagement-ID'].trim();
+    
+    if (!idRegex.test(id) || id.length > 100) {
+      throw new Error('Invalid format in X-Engagement-ID header');
+    }
+    validated['X-Engagement-ID'] = id;
+  }
+  
+  // Add request ID for tracing
+  validated['X-Request-ID'] = crypto.randomUUID();
+  validated['X-Request-Timestamp'] = Date.now().toString();
+  
+  return validated;
+}
+
 async function handleRequest(request: NextRequest, path: string[], method: string) {
   try {
     const apiPath = path.join('/');
@@ -31,7 +64,14 @@ async function handleRequest(request: NextRequest, path: string[], method: stri
 
     // Get auth headers (will work for both demo and AAD modes)
-    const authHeaders = getAuthHeaders();
+    let authHeaders: Record<string, string> = {};
+    try {
+      const rawHeaders = getAuthHeaders();
+      authHeaders = validateHeaders(rawHeaders);
+    } catch (error) {
+      console.error('Header validation failed:', error);
+      return NextResponse.json({ detail: 'Invalid authentication headers' }, { status: 400 });
+    }
     
     // Get additional headers from the request
     const requestHeaders: Record<string, string> = {};
```

## Patch 5: Enhanced Email Validation in Security Module

**File**: `/app/api/security.py`

```diff
--- a/app/api/security.py
+++ b/app/api/security.py
@@ -1,8 +1,10 @@
 import os
 import re
 import email.utils
+import hashlib
+import hmac
 from fastapi import Header, HTTPException, Depends
-from typing import Dict
+from typing import Dict, Optional
 from ..domain.repository import Repository
 
 
@@ -23,10 +25,32 @@ def is_admin(user_email: str) -> bool:
     admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
     return canonical_email in admins
 
+def validate_request_signature(
+    email: str,
+    engagement_id: str,
+    timestamp: str,
+    signature: str
+) -> bool:
+    """Validate request signature for integrity"""
+    secret = os.getenv("REQUEST_SIGNING_SECRET", "default-secret")
+    
+    # Check timestamp is recent (within 5 minutes)
+    try:
+        req_time = int(timestamp)
+        current_time = int(time.time() * 1000)
+        if abs(current_time - req_time) > 300000:  # 5 minutes
+            return False
+    except:
+        return False
+    
+    # Verify signature
+    payload = f"{email}:{engagement_id}:{timestamp}"
+    expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
+    
+    return hmac.compare_digest(signature, expected_sig)
 
 async def current_context(
     x_user_email: str = Header(..., alias="X-User-Email"),
-    x_engagement_id: str = Header(..., alias="X-Engagement-ID")
+    x_engagement_id: str = Header(..., alias="X-Engagement-ID"),
+    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
 ) -> Dict[str, str]:
     """Extract current user and engagement context from headers"""
     # Validate and sanitize email
@@ -38,6 +62,10 @@ async def current_context(
         raise HTTPException(422, "X-User-Email header must be a valid email address")
     
     canonical_email = parsed[1].strip().lower()
+    
+    # Additional email validation
+    if len(canonical_email) > 254:  # RFC 5321
+        raise HTTPException(422, "Email address too long")
     
     # Validate and sanitize engagement ID
     if not x_engagement_id or not x_engagement_id.strip():
@@ -45,10 +73,17 @@ async def current_context(
     
     engagement_id_normalized = x_engagement_id.strip()
     # Basic validation - alphanumeric, hyphens, underscores allowed
-    if not re.match(r'^[a-zA-Z0-9_-]+$', engagement_id_normalized):
+    if not re.match(r'^[a-zA-Z0-9_-]{1,100}$', engagement_id_normalized):
         raise HTTPException(422, "X-Engagement-ID header must contain only alphanumeric characters, hyphens, and underscores")
     
-    return {"user_email": canonical_email, "engagement_id": engagement_id_normalized}
+    # Add request ID for tracing
+    request_id = x_request_id or str(uuid.uuid4())
+    
+    return {
+        "user_email": canonical_email,
+        "engagement_id": engagement_id_normalized,
+        "request_id": request_id
+    }
 
 
 def require_member(repo: Repository, ctx: Dict[str, str], min_role: str = "member"):
```

## Applying the Patches

### Step 1: Create backup
```bash
# Backup current files
cp app/services/rag.py app/services/rag.py.bak
cp app/api/routes/documents.py app/api/routes/documents.py.bak
cp web/app/api/proxy/[...path]/route.ts web/app/api/proxy/[...path]/route.ts.bak
cp app/api/security.py app/api/security.py.bak
```

### Step 2: Apply patches
```bash
# Apply each patch file
patch -p1 < patch1_sql_injection.diff
patch -p1 < patch2_path_traversal.diff
patch -p1 < patch3_input_validation.diff
patch -p1 < patch4_auth_headers.diff
patch -p1 < patch5_email_validation.diff
```

### Step 3: Test the patches
```bash
# Run security tests
pytest tests/security/ -v

# Run integration tests
pytest tests/integration/ -v

# Run linting and security checks
bandit -r app/
safety check
```

### Step 4: Deploy with monitoring
```bash
# Deploy to staging first
./scripts/deploy_staging.sh

# Monitor for errors
az monitor app-insights query \
  --app $APP_INSIGHTS_NAME \
  --analytics-query "exceptions | where timestamp > ago(1h)"

# If stable, deploy to production
./scripts/deploy_production.sh
```

## Verification Steps

After applying patches, verify:

1. **SQL Injection**: Test with malicious engagement IDs
2. **Path Traversal**: Attempt to upload files with path components
3. **XSS**: Try injecting scripts in search queries
4. **Authentication**: Test with invalid/missing headers
5. **Rate Limiting**: Verify rate limits are enforced

## Emergency Rollback

If issues occur after patching:

```bash
# Restore from backup
cp app/services/rag.py.bak app/services/rag.py
cp app/api/routes/documents.py.bak app/api/routes/documents.py
cp web/app/api/proxy/[...path]/route.ts.bak web/app/api/proxy/[...path]/route.ts
cp app/api/security.py.bak app/api/security.py

# Redeploy previous version
git checkout HEAD~1
./scripts/deploy_production.sh
```
# UAT Execution Runbook

## Overview

This runbook provides step-by-step procedures for executing User Acceptance Testing (UAT) for the AI-Enabled Cyber Maturity Assessment platform. It includes detailed test scenarios, expected results, and troubleshooting guidance.

## Pre-UAT Setup

### Environment Preparation

#### 1. Verify Staging Environment
```bash
# Check all services are healthy
curl -f https://api-staging.eastus.azurecontainerapps.io/health
curl -f https://web-staging.eastus.azurecontainerapps.io/api/health
curl -f https://mcp-staging.eastus.azurecontainerapps.io/health

# Run comprehensive verification
./scripts/verify_live.sh --staging --governance
```

#### 2. Prepare Test Data
```bash
# Load UAT test dataset
./scripts/load_uat_testdata.sh

# Verify test engagements are created
curl -H "Authorization: Bearer $UAT_TOKEN" \
  https://api-staging.eastus.azurecontainerapps.io/api/engagements
```

#### 3. Create Test Users
```sql
-- UAT test users with different roles
INSERT INTO users (id, email, name, role, engagements) VALUES
  ('uat-admin-001', 'uat.admin@staging.local', 'UAT Admin User', 'admin', '["eng-test-001", "eng-test-002"]'),
  ('uat-analyst-001', 'uat.analyst@staging.local', 'UAT Analyst User', 'analyst', '["eng-test-001"]'),
  ('uat-viewer-001', 'uat.viewer@staging.local', 'UAT Viewer User', 'viewer', '["eng-test-002"]');
```

## Core Functionality Testing

### Authentication and Authorization Testing

#### Test Scenario AC-001: Valid User Login
**Objective**: Verify users can log in with valid credentials

**Prerequisites**: 
- Test user account exists
- Staging environment is accessible

**Test Steps**:
1. Navigate to `https://web-staging.eastus.azurecontainerapps.io`
2. Click "Sign In" button
3. Enter test credentials:
   - Email: `uat.analyst@staging.local`
   - Password: `UAT_Test_Pass123!`
4. Click "Sign In" button

**Expected Result**: 
- User is redirected to dashboard
- Welcome message displays user name
- Navigation menu shows user role-appropriate options

**Verification Commands**:
```bash
# Test login via API
curl -X POST https://api-staging.eastus.azurecontainerapps.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "uat.analyst@staging.local",
    "password": "UAT_Test_Pass123!"
  }'

# Expected: 200 OK with JWT token
```

#### Test Scenario AC-006: Engagement Isolation
**Objective**: Verify users can only access assigned engagements

**Prerequisites**:
- Test users with different engagement assignments
- Test data in multiple engagements

**Test Steps**:
1. Login as `uat.analyst@staging.local` (assigned to eng-test-001)
2. Navigate to Engagements page
3. Verify only eng-test-001 is visible
4. Attempt to access eng-test-002 directly via URL

**Expected Result**:
- Only eng-test-001 appears in engagement list
- Direct access to eng-test-002 returns 403 Forbidden

**Verification Commands**:
```bash
# Test engagement access with analyst token
ANALYST_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Should succeed
curl -H "Authorization: Bearer $ANALYST_TOKEN" \
  https://api-staging.eastus.azurecontainerapps.io/api/engagements/eng-test-001

# Should fail with 403
curl -H "Authorization: Bearer $ANALYST_TOKEN" \
  https://api-staging.eastus.azurecontainerapps.io/api/engagements/eng-test-002
```

### MCP Tools Integration Testing

#### Test Scenario MCP-001: PDF Document Processing
**Objective**: Verify PDF parsing tool extracts content correctly

**Prerequisites**:
- Sample PDF documents in test-files directory
- MCP Gateway is running and healthy

**Test Steps**:
1. Login to staging environment
2. Navigate to Documents → Upload
3. Select test PDF file: `test-files/sample-policy.pdf`
4. Upload document and wait for processing
5. Verify extracted text appears in document preview
6. Search for specific text from the PDF

**Expected Result**:
- Document uploads successfully
- Text extraction completes within 30 seconds
- Extracted content is searchable
- Document metadata is populated correctly

**Manual Verification**:
```bash
# Test MCP PDF tool directly
curl -X POST https://mcp-staging.eastus.azurecontainerapps.io/tools/pdf/parse \
  -H "Content-Type: application/json" \
  -H "X-Engagement-ID: eng-test-001" \
  -d '{
    "document_url": "https://staaemcastaging.blob.core.windows.net/documents/sample-policy.pdf",
    "extract_metadata": true
  }'
```

#### Test Scenario MCP-006: Audio Transcription
**Objective**: Verify audio transcription functionality

**Prerequisites**:
- Sample audio file in supported format (MP3, WAV)
- Transcription service is configured

**Test Steps**:
1. Navigate to Workshops → New Session
2. Upload audio file: `test-files/sample-meeting.mp3`
3. Initiate transcription
4. Wait for transcription completion
5. Review transcript for accuracy
6. Test speaker identification

**Expected Result**:
- Audio uploads successfully
- Transcription completes within processing time limit
- Transcript accuracy is >85% for clear audio
- Speaker identification works for multiple speakers

**API Testing**:
```bash
# Test audio transcription
curl -X POST https://mcp-staging.eastus.azurecontainerapps.io/tools/transcribe \
  -H "Content-Type: multipart/form-data" \
  -H "X-Engagement-ID: eng-test-001" \
  -F "audio_file=@test-files/sample-meeting.mp3" \
  -F "options={\"identify_speakers\":true,\"include_timestamps\":true}"
```

### AI Analysis Testing

#### Test Scenario AI-001: Gap Analysis Generation
**Objective**: Verify AI generates accurate gap analysis

**Prerequisites**:
- Engagement with uploaded documents
- AI analysis service is configured
- Test framework standards are available

**Test Steps**:
1. Navigate to Assessment → New Analysis
2. Select engagement: eng-test-001
3. Choose framework: NIST Cybersecurity Framework
4. Select documents for analysis
5. Initiate gap analysis
6. Review generated findings and recommendations

**Expected Result**:
- Analysis completes within 5 minutes
- Generates specific, actionable findings
- Risk scores are reasonable and justified
- Recommendations are relevant to identified gaps

**Performance Test**:
```bash
# Test gap analysis API
time curl -X POST https://api-staging.eastus.azurecontainerapps.io/api/analysis/gap \
  -H "Authorization: Bearer $UAT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engagement_id": "eng-test-001",
    "framework": "nist-csf",
    "document_ids": ["doc-001", "doc-002"],
    "analysis_depth": "comprehensive"
  }'
```

### Search and RAG Testing

#### Test Scenario RAG-001: Context-Aware Responses
**Objective**: Verify RAG provides accurate, context-aware responses

**Prerequisites**:
- Documents are indexed and searchable
- RAG service is configured with embeddings
- Test queries prepared

**Test Steps**:
1. Navigate to AI Assistant
2. Ask: "What are our current password policy requirements?"
3. Verify response cites relevant documents
4. Ask follow-up: "How does this compare to industry best practices?"
5. Verify response maintains context from previous question

**Expected Result**:
- Initial response cites specific policy documents
- Follow-up response maintains context
- Sources are accurately referenced
- Response quality is helpful and accurate

**RAG API Testing**:
```bash
# Test RAG query
curl -X POST https://api-staging.eastus.azurecontainerapps.io/api/rag/query \
  -H "Authorization: Bearer $UAT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "engagement_id": "eng-test-001",
    "query": "What are our current password policy requirements?",
    "include_sources": true,
    "max_sources": 5
  }'
```

## Security and Governance Testing

### Security Testing Procedures

#### Test Scenario DS-001: Data Encryption Verification
**Objective**: Verify data is encrypted at rest and in transit

**Test Steps**:
1. Monitor network traffic during document upload
2. Verify HTTPS is used for all communications
3. Check database storage for unencrypted sensitive data
4. Test document storage encryption

**Verification Commands**:
```bash
# Check TLS configuration
openssl s_client -connect api-staging.eastus.azurecontainerapps.io:443 -servername api-staging.eastus.azurecontainerapps.io

# Verify no sensitive data in logs
sudo grep -r "password\|secret\|token" /var/log/ | grep -v "sanitized"

# Check database encryption (if accessible)
SELECT encryption_state FROM sys.dm_database_encryption_keys;
```

#### Test Scenario AU-001: Audit Logging
**Objective**: Verify comprehensive audit logging

**Test Steps**:
1. Perform various user actions (login, document upload, analysis)
2. Check audit logs for each action
3. Verify log entries include required fields
4. Test log integrity and tamper protection

**Log Verification**:
```bash
# Check audit logs
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api-staging.eastus.azurecontainerapps.io/api/audit/logs?limit=100

# Verify log structure
jq '.events[] | {timestamp, user_id, action, resource, result}' audit-logs.json
```

### Consent Management Testing

#### Test Scenario CM-001: Recording Consent Collection
**Objective**: Verify explicit consent is collected for recording/transcription

**Test Steps**:
1. Navigate to Workshops → Schedule Session
2. Enable recording option
3. Invite participants via email
4. Verify consent collection in invitation
5. Test consent acceptance/rejection flow
6. Verify recording only starts after consent

**Expected Result**:
- Consent prompt appears before recording starts
- Clear language explaining data usage
- Opt-out mechanism is available
- Consent status is tracked and auditable

```bash
# Check consent records
curl -H "Authorization: Bearer $UAT_TOKEN" \
  https://api-staging.eastus.azurecontainerapps.io/api/workshops/eng-test-001/consents
```

## Performance Testing

### Load Testing Procedures

#### Test Scenario PT-006: Concurrent User Sessions
**Objective**: Verify system handles multiple concurrent users

**Prerequisites**:
- Load testing tools installed (Apache Bench, wrk, or similar)
- Multiple test user accounts

**Test Steps**:
1. Simulate 10 concurrent users logging in
2. Each user uploads a document simultaneously
3. Monitor response times and error rates
4. Verify system stability under load

**Load Test Commands**:
```bash
# Concurrent login test
for i in {1..10}; do
  curl -X POST https://api-staging.eastus.azurecontainerapps.io/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"uat.user$i@staging.local\",\"password\":\"UAT_Test_Pass123!\"}" &
done
wait

# Document upload load test
ab -n 100 -c 10 -T "multipart/form-data" -p upload-data.txt \
  https://api-staging.eastus.azurecontainerapps.io/api/documents/upload
```

#### Test Scenario PT-001: API Response Times
**Objective**: Verify API response times meet performance requirements

**Test Cases**:
- Authentication: < 1 second
- Document upload: < 30 seconds
- Search queries: < 3 seconds
- AI analysis: < 5 minutes

```bash
# Response time monitoring script
#!/bin/bash
echo "Testing API response times..."

# Authentication
start=$(date +%s%N)
curl -s -X POST https://api-staging.eastus.azurecontainerapps.io/api/auth/login \
  -d '{"email":"uat.analyst@staging.local","password":"UAT_Test_Pass123!"}' >/dev/null
end=$(date +%s%N)
auth_time=$((($end - $start) / 1000000))
echo "Authentication: ${auth_time}ms"

# Search query
start=$(date +%s%N)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api-staging.eastus.azurecontainerapps.io/api/search?q=security+policy" >/dev/null
end=$(date +%s%N)
search_time=$((($end - $start) / 1000000))
echo "Search: ${search_time}ms"
```

## End-to-End Workflow Testing

### Complete Assessment Workflow

#### Test Scenario E2E-001: Full Assessment Lifecycle
**Objective**: Test complete assessment from start to finish

**Test Steps**:
1. **Engagement Setup** (5 minutes)
   - Create new engagement
   - Configure settings and participants
   - Verify ABAC permissions

2. **Document Preparation** (10 minutes)
   - Upload policy documents
   - Upload previous assessments
   - Verify document processing and indexing

3. **Workshop Execution** (15 minutes)
   - Schedule workshop session
   - Collect participant consent
   - Record and transcribe session
   - Generate meeting minutes

4. **AI Analysis** (10 minutes)
   - Initiate gap analysis
   - Review AI recommendations
   - Customize and approve findings

5. **Report Generation** (5 minutes)
   - Generate executive summary
   - Create detailed technical report
   - Export in multiple formats

**Success Criteria**:
- Complete workflow completes within 45 minutes
- No data loss or corruption
- All reports contain accurate information
- Audit trail is complete and accurate

### Integration Testing

#### Test Scenario TP-001: SharePoint Integration
**Objective**: Test SharePoint document import functionality

**Prerequisites**:
- SharePoint connector configured
- Test SharePoint site with documents
- Appropriate permissions granted

**Test Steps**:
1. Navigate to Documents → Import → SharePoint
2. Connect to test SharePoint tenant
3. Browse document library
4. Select multiple documents for import
5. Monitor import progress
6. Verify documents are processed correctly

```bash
# Test SharePoint connection
curl -X POST https://mcp-staging.eastus.azurecontainerapps.io/tools/sharepoint/connect \
  -H "Content-Type: application/json" \
  -H "X-Engagement-ID: eng-test-001" \
  -d '{
    "tenant_id": "test-tenant-id",
    "site_url": "https://testorg.sharepoint.com/sites/testsite",
    "mode": "DRY-RUN"
  }'
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Authentication Failures
**Symptoms**: 401 Unauthorized responses, login failures
**Check**:
- Verify user credentials in database
- Check JWT token expiration
- Validate ABAC permissions

```bash
# Debug authentication
curl -v -X POST https://api-staging.eastus.azurecontainerapps.io/api/auth/login \
  -d '{"email":"user@example.com","password":"password"}'

# Decode JWT token
echo "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." | base64 -d
```

#### Document Processing Failures
**Symptoms**: Documents stuck in "Processing" state
**Check**:
- MCP Gateway service health
- Document file format and size
- Storage service connectivity

```bash
# Check MCP Gateway logs
kubectl logs -f deployment/mcp-gateway -n staging

# Test document processing manually
curl -X POST https://mcp-staging.eastus.azurecontainerapps.io/tools/pdf/parse \
  -F "file=@problem-document.pdf"
```

#### Performance Issues
**Symptoms**: Slow response times, timeouts
**Check**:
- Database connection pool
- Memory and CPU usage
- External service dependencies

```bash
# Monitor resource usage
az containerapp logs show -n api-staging -g rg-aecma-staging --tail 100

# Check database performance
az cosmosdb sql database throughput show \
  --account-name cosmos-aecma-staging \
  --name ai_maturity
```

## UAT Execution Schedule

### Daily Testing Schedule

#### Day 1: Core Platform Testing
- **Morning (9:00-12:00)**: Authentication, authorization, basic navigation
- **Afternoon (13:00-17:00)**: Document management, search functionality
- **Evening**: Review findings, log issues

#### Day 2: MCP Tools Testing  
- **Morning (9:00-12:00)**: PDF processing, audio transcription
- **Afternoon (13:00-17:00)**: SharePoint/Jira connectors (if enabled)
- **Evening**: Integration testing review

#### Day 3: AI and Analytics Testing
- **Morning (9:00-12:00)**: Gap analysis, recommendations
- **Afternoon (13:00-17:00)**: RAG functionality, report generation
- **Evening**: AI accuracy review

#### Day 4: Security and Performance Testing
- **Morning (9:00-12:00)**: Security testing, audit verification
- **Afternoon (13:00-17:00)**: Load testing, performance validation
- **Evening**: Security review

#### Day 5: End-to-End and Sign-off
- **Morning (9:00-12:00)**: Complete workflow testing
- **Afternoon (13:00-16:00)**: Final verification, issue triage
- **Late Afternoon (16:00-17:00)**: Stakeholder sign-off meeting

### Stakeholder Responsibilities

#### UAT Team Lead
- Coordinate testing activities
- Track progress against checklist
- Escalate blocking issues
- Prepare sign-off documentation

#### Subject Matter Experts
- Execute domain-specific test scenarios
- Validate AI analysis accuracy
- Review report quality and completeness
- Provide business acceptance criteria

#### Technical Team
- Support testing environment
- Investigate technical issues
- Provide fixes for critical defects
- Maintain test data and configurations

#### Security Team
- Execute security test scenarios
- Review audit logs and compliance
- Validate ABAC enforcement
- Approve security sign-off

## Issue Management

### Issue Classification

**Critical (P0)**:
- Security vulnerabilities
- Data corruption or loss
- System unavailability
- Authentication failures

**High (P1)**:
- Core functionality failures
- Performance below thresholds
- Integration failures
- Significant usability issues

**Medium (P2)**:
- Non-critical feature issues
- Minor performance issues
- Documentation gaps
- UI/UX improvements

**Low (P3)**:
- Cosmetic issues
- Enhancement requests
- Nice-to-have features

### Issue Tracking Template

```markdown
## Issue #UAT-XXX

**Title**: Brief description of the issue

**Priority**: P0/P1/P2/P3

**Test Scenario**: Reference to failed test case

**Steps to Reproduce**:
1. Step one
2. Step two
3. Step three

**Expected Result**: What should happen

**Actual Result**: What actually happened

**Environment**: Staging/Production

**Browser/Client**: Chrome 118, Safari 16, etc.

**Screenshots/Logs**: Attach evidence

**Workaround**: If available

**Assigned To**: Developer name

**Status**: New/In Progress/Fixed/Verified/Closed
```

## Final Sign-off Process

### Sign-off Criteria
- All P0 and P1 issues resolved
- P2 issues have approved workarounds or are scheduled for future release
- Performance benchmarks met
- Security review completed
- All stakeholders have reviewed and approved

### Sign-off Meeting Agenda
1. **Test Results Summary** (15 min)
   - Tests executed vs planned
   - Pass/fail rates by category
   - Key findings and insights

2. **Issue Review** (20 min)
   - Outstanding issues by priority
   - Resolution timeline for remaining issues
   - Risk assessment for unresolved items

3. **Stakeholder Confirmation** (15 min)
   - Business acceptance
   - Technical acceptance
   - Security acceptance
   - Quality acceptance

4. **Production Readiness** (10 min)
   - Deployment plan review
   - Rollback procedures
   - Go-live authorization

---

**Document Version**: 1.0  
**Last Updated**: Sprint v1.7  
**Next Review**: Post-production deployment

*This runbook should be executed in its entirety before production release authorization.*
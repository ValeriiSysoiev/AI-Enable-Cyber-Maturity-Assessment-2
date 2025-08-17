# Data Governance and GDPR Compliance

This document outlines the data governance framework, GDPR compliance capabilities, and data lifecycle management implemented in the AI-Enabled Cyber Maturity Assessment platform.

## Overview

The platform implements comprehensive data governance to ensure:
- GDPR compliance (Articles 15, 17, 30)
- Data minimization and retention policies
- Audit trail and accountability
- Secure data export and purge capabilities

## GDPR Compliance Framework

### Data Subject Rights

#### Right of Access (Article 15)
- **Endpoint**: `POST /gdpr/engagements/{id}/export`
- **Scope**: Complete engagement data export
- **Format**: JSON, PDF (planned)
- **Access Control**: Lead/Admin only

#### Right to Erasure (Article 17)  
- **Endpoint**: `POST /gdpr/engagements/{id}/purge`
- **Process**: Soft delete → Hard delete
- **Retention**: Configurable delay (default: 30 days)
- **Access Control**: Lead/Admin only

#### Records of Processing (Article 30)
- **Endpoint**: `GET /gdpr/admin/audit-logs`
- **Coverage**: All data operations
- **Retention**: 7 years
- **Integrity**: Digital signatures

## Data Classification

### Primary Business Data (No TTL)
- **Engagements**: Core business entities
- **Assessments**: Completed evaluations
- **Answers**: Assessment responses
- **Documents**: Uploaded evidence files

### Operational Data (TTL Applied)
- **Logs**: 90 days retention
- **Temporary Data**: 30 days retention
- **Cache Data**: 24 hours retention
- **Session Data**: 8 hours retention

### Audit Data (Extended Retention)
- **Audit Logs**: 7 years (legal requirement)
- **Access Logs**: 1 year
- **Security Events**: 3 years

## Data Export

### Export Process

1. **Request Initiation**
   ```http
   POST /gdpr/engagements/{engagement_id}/export
   Content-Type: application/json
   
   {
     "engagement_id": "eng-123",
     "include_documents": true,
     "include_embeddings": false,
     "export_format": "json"
   }
   ```

2. **Background Processing**
   - Creates background job for large exports
   - Progress tracking via job status API
   - Automatic cleanup after download

3. **Data Structure**
   ```json
   {
     "export_metadata": {
       "engagement_id": "eng-123",
       "export_date": "2024-01-15T10:30:00Z",
       "export_version": "1.0",
       "data_sources": ["cosmos", "blob", "search"]
     },
     "engagement": {
       "id": "eng-123",
       "name": "ACME Corp Assessment",
       "created_at": "2024-01-01T00:00:00Z"
     },
     "assessments": [...],
     "documents": [...],
     "members": [...],
     "audit_logs": [...]
   }
   ```

### Export Options

- **Full Export**: All engagement data
- **Assessment Only**: Just assessment data
- **Documents Only**: Just uploaded files
- **Metadata Only**: Structure without content

## Data Purge

### Purge Process

1. **Soft Delete Phase**
   ```http
   POST /gdpr/engagements/{engagement_id}/purge
   Content-Type: application/json
   
   {
     "engagement_id": "eng-123",
     "purge_type": "soft_delete",
     "retention_days": 30,
     "reason": "User requested deletion",
     "confirm_purge": true
   }
   ```

2. **Retention Period**
   - Data marked for deletion
   - Access restricted to audit purposes
   - Recovery possible during retention

3. **Hard Delete Phase**
   - Automatic after retention period
   - Permanent data removal
   - Audit log entry created

### Purge Scope

- **Engagement Data**: All related assessments, documents
- **User Data**: Profile, preferences, history
- **Derived Data**: Embeddings, search indexes
- **Audit Preservation**: Audit logs retained per policy

## TTL Policies

### Configuration

TTL policies are configured per container:

```json
{
  "containers": {
    "logs": {
      "defaultTtl": 7776000,  // 90 days
      "enableTtl": true
    },
    "temp_data": {
      "defaultTtl": 2592000,  // 30 days  
      "enableTtl": true
    },
    "audit_logs": {
      "defaultTtl": 220752000, // 7 years
      "enableTtl": true
    }
  }
}
```

### Implementation

Documents include TTL fields:
```json
{
  "id": "doc-123",
  "data": {...},
  "ttl": 7776000,  // Auto-delete after 90 days
  "_ts": 1705401600  // Creation timestamp
}
```

## Background Jobs

### Job Types

1. **Data Export** (`data_export`)
   - Large engagement exports
   - Progress tracking
   - File generation and cleanup

2. **Data Purge** (`data_purge`)
   - Soft delete processing  
   - Hard delete scheduling
   - Cross-service cleanup

3. **TTL Cleanup** (`ttl_cleanup`)
   - Expired document removal
   - Cascade delete handling
   - Cleanup verification

4. **Audit Retention** (`audit_retention`)
   - Long-term audit log management
   - Archive creation
   - Compliance reporting

### Job Processing

```python
# Job creation
job = await job_service.create_job(
    job_type="data_export",
    engagement_id="eng-123",
    parameters={"include_documents": True}
)

# Job monitoring
status = await job_service.get_job_status(job.id)
# Returns: pending, processing, completed, failed

# Job results
result = await job_service.get_job_result(job.id)
```

## Audit Trail

### Audit Events

All GDPR operations generate audit events:

```json
{
  "event_id": "audit-123",
  "event_type": "data_export",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_email": "admin@company.com",
  "engagement_id": "eng-123",
  "details": {
    "export_format": "json",
    "include_documents": true,
    "file_size": 1048576
  },
  "digital_signature": "sha256:abc123...",
  "correlation_id": "req-456"
}
```

### Integrity Verification

Audit logs include HMAC signatures:
```python
# Signature generation
signature = hmac.new(
    key=audit_key,
    msg=json.dumps(event, sort_keys=True),
    digestmod=hashlib.sha256
).hexdigest()

# Verification
is_valid = hmac.compare_digest(
    stored_signature,
    calculated_signature
)
```

## API Reference

### Export Endpoints

```http
# Initiate export
POST /gdpr/engagements/{id}/export
Authorization: Bearer {token}
X-User-Email: {email}
X-Engagement-ID: {id}

# Check export status
GET /gdpr/engagements/{id}/export/{job_id}/status

# Download export
GET /gdpr/engagements/{id}/export/{job_id}/download
```

### Purge Endpoints

```http
# Initiate purge
POST /gdpr/engagements/{id}/purge

# Check purge status  
GET /gdpr/engagements/{id}/purge/{job_id}/status

# Recover during retention
POST /gdpr/engagements/{id}/recover
```

### Admin Endpoints

```http
# GDPR dashboard
GET /gdpr/admin/dashboard

# Background jobs
GET /gdpr/admin/jobs?status=processing&page=1

# Audit logs
GET /gdpr/admin/audit-logs?from=2024-01-01&to=2024-01-31

# TTL policies
GET /gdpr/admin/ttl-policies
PUT /gdpr/admin/ttl-policies
```

## User Interface

### Engagement GDPR Page

Located at `/e/{engagementId}/gdpr`:
- Data export interface
- Purge confirmation dialogs
- Status tracking
- Audit log viewing

### Admin GDPR Interface

Located at `/admin/gdpr`:
- System-wide GDPR dashboard
- Background job monitoring
- Audit trail search
- TTL policy management

## Compliance Monitoring

### Key Metrics

- **Export Response Time**: < 30 seconds for standard exports
- **Purge Completion Rate**: 100% within retention period
- **Audit Integrity**: 100% signature verification pass rate
- **TTL Compliance**: Automatic cleanup within 24 hours of expiry

### Alerting

Configure alerts for:
- Export failures
- Purge job failures
- Audit signature verification failures
- TTL cleanup delays
- GDPR request SLA breaches

### Reporting

Monthly compliance reports include:
- GDPR request volumes and response times
- Data retention compliance rates
- Audit trail integrity status
- Background job performance metrics

## Best Practices

### Data Minimization

1. **Collection Limitation**
   - Only collect necessary data
   - Regular data need assessment
   - Clear purpose specification

2. **Storage Limitation**
   - Implement appropriate TTL policies
   - Regular data cleanup
   - Archive old data

3. **Access Control**
   - Role-based access to GDPR functions
   - Audit all data access
   - Principle of least privilege

### Operational Procedures

1. **Regular Audits**
   - Monthly GDPR compliance review
   - Quarterly audit log verification
   - Annual policy review

2. **Incident Response**
   - Data breach notification procedures
   - GDPR violation escalation
   - Recovery and remediation plans

3. **Training**
   - Staff GDPR awareness training
   - Technical team data handling training
   - Regular compliance updates

## Troubleshooting

### Common Issues

1. **Export Failures**
   ```bash
   # Check job status
   curl -H "Authorization: Bearer $TOKEN" \
        /gdpr/admin/jobs?job_type=data_export&status=failed
   
   # View job logs
   kubectl logs deployment/api-app | grep "export_job"
   ```

2. **Purge Delays**
   ```bash
   # Check background job queue
   curl -H "Authorization: Bearer $TOKEN" \
        /gdpr/admin/jobs?job_type=data_purge
   
   # Manual job trigger
   curl -X POST -H "Authorization: Bearer $TOKEN" \
        /gdpr/admin/jobs/trigger-cleanup
   ```

3. **Audit Integrity Issues**
   ```bash
   # Verify audit signatures
   curl -H "Authorization: Bearer $TOKEN" \
        /gdpr/admin/audit-logs/verify-integrity
   
   # Check signature generation
   kubectl logs deployment/api-app | grep "audit_signature"
   ```

### Performance Optimization

1. **Large Exports**
   - Use streaming for large datasets
   - Implement compression
   - Parallel processing for multiple engagements

2. **Background Jobs**
   - Monitor job queue length
   - Adjust worker pool size
   - Implement job prioritization

3. **Audit Storage**
   - Partition audit logs by date
   - Index on common query fields
   - Archive old audit data

## Compliance Checklist

### GDPR Readiness

- [ ] Data export functionality implemented
- [ ] Data purge capabilities in place
- [ ] Audit trail system operational
- [ ] TTL policies configured
- [ ] Staff training completed
- [ ] Incident response procedures documented
- [ ] Regular compliance monitoring in place
- [ ] Legal review completed

### Technical Implementation

- [ ] All endpoints secured with proper authentication
- [ ] Background job system tested under load
- [ ] Audit log integrity verification working
- [ ] TTL cleanup automation verified
- [ ] Export/purge UI tested by end users
- [ ] API documentation complete
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery procedures tested
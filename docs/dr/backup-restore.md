# Backup and Restore Procedures for AECMA Production

## Overview
This document outlines backup strategies, restore procedures, and disaster recovery testing for the AI-Enabled Cyber Maturity Assessment platform.

## Backup Strategy

### Data Classification
- **Critical**: Assessment data, user profiles, engagement records
- **Important**: Configuration data, framework definitions, uploaded evidence
- **Recoverable**: Logs, temporary files, cached data

### Backup Components

#### 1. Database Backups
- **Azure Cosmos DB**: Automatic continuous backup enabled
- **Backup Retention**: 30 days for point-in-time restore
- **Cross-region**: Geo-redundant backup in paired region

#### 2. Blob Storage Backups
- **Evidence Files**: Geo-redundant storage (GRS) with read access
- **Application Assets**: Backed up with container images
- **Versioning**: Enabled for accidental deletion protection

#### 3. Configuration Backups
- **Container Apps Configuration**: Version controlled in Git
- **Infrastructure as Code**: Terraform/Bicep templates in repository
- **Secrets**: Azure Key Vault with soft-delete and purge protection

#### 4. Container Images
- **GitHub Container Registry**: Multi-region replication
- **Azure Container Registry**: Geo-replication enabled
- **Image Retention**: 90 days for production images

## Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO)

| Component | RTO Target | RPO Target | Backup Frequency |
|-----------|------------|------------|------------------|
| Database | 4 hours | 1 hour | Continuous |
| Blob Storage | 2 hours | 15 minutes | Real-time |
| Application | 1 hour | N/A (stateless) | On deployment |
| Configuration | 30 minutes | N/A | On commit |

## Disaster Recovery Scenarios

### Scenario 1: Database Corruption
**Trigger**: Data corruption, accidental deletion, malicious activity
**Recovery**: Point-in-time restore from Cosmos DB backup

### Scenario 2: Region Outage
**Trigger**: Azure region unavailability
**Recovery**: Failover to secondary region using geo-replicated resources

### Scenario 3: Storage Account Deletion
**Trigger**: Accidental storage account deletion
**Recovery**: Restore from geo-redundant backup in paired region

### Scenario 4: Complete Environment Loss
**Trigger**: Subscription loss, major security incident
**Recovery**: Rebuild from infrastructure code and backups

## Backup Verification Procedures

### Monthly Backup Tests
1. **Database Point-in-Time Restore Test**
   - Select random point within last 30 days
   - Restore to test environment
   - Verify data integrity and completeness

2. **Blob Storage Recovery Test**
   - Simulate file deletion
   - Restore from backup or soft-delete
   - Verify file integrity and accessibility

3. **Configuration Recovery Test**
   - Deploy to test environment from IaC
   - Verify all components are functional
   - Test application connectivity

### Quarterly DR Drills
1. **Simulated Region Failover**
   - Initiate failover procedures
   - Test application availability in secondary region
   - Measure RTO and RPO achievement

2. **Complete Environment Rebuild**
   - Deploy to isolated environment
   - Restore all data from backups
   - Validate end-to-end functionality

## Restore Procedures

### Database Restore
```bash
# Point-in-time restore using Azure CLI
az cosmosdb sql database restore \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --name $DATABASE_NAME \
  --restore-timestamp "2024-01-01T10:00:00Z" \
  --target-database-name "${DATABASE_NAME}-restored"
```

### Blob Storage Restore
```bash
# Restore from geo-redundant backup
az storage account show-backup-policy \
  --account-name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP

# Restore specific container
az storage blob restore \
  --account-name $STORAGE_ACCOUNT \
  --time-to-restore "2024-01-01T10:00:00Z" \
  --blob-range "evidence/*"
```

### Application Restore
```bash
# Redeploy from container images
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $CONTAINER_IMAGE_BACKUP

# Verify deployment
az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.activeRevisionsMode"
```

## Emergency Contacts and Escalation

### Primary Response Team
- **Incident Commander**: incident-commander@company.com
- **Database Admin**: dba@company.com
- **Cloud Engineer**: cloudops@company.com
- **Security Team**: security@company.com

### Escalation Matrix
- **Level 1** (0-2 hours): Technical team response
- **Level 2** (2-4 hours): Management notification
- **Level 3** (4+ hours): Executive escalation and external vendor support

## Recovery Validation Checklist

### Post-Restore Verification
- [ ] Database connectivity and query functionality
- [ ] Blob storage file access and integrity
- [ ] Application health checks passing
- [ ] User authentication and authorization
- [ ] API endpoints responding correctly
- [ ] Evidence upload and download functionality
- [ ] Assessment creation and completion workflows
- [ ] Cross-component integration testing

### Performance Validation
- [ ] Response times within acceptable limits
- [ ] Database query performance normal
- [ ] Storage I/O operations functioning
- [ ] Application scaling working correctly

### Security Validation
- [ ] SSL certificates valid and functioning
- [ ] Authentication mechanisms working
- [ ] Authorization policies enforced
- [ ] Audit logging active
- [ ] Security monitoring enabled

## Backup Monitoring and Alerting

### Azure Monitor Alerts
- Database backup failures
- Storage replication lag
- Container registry sync issues
- Key Vault backup status

### Daily Checks
- Verify backup completion status
- Check geo-replication health
- Validate retention policies
- Monitor storage consumption

## Documentation and Training

### Runbook Maintenance
- Monthly review of procedures
- Quarterly update of contact information
- Annual full documentation review
- Post-incident procedure updates

### Team Training
- New team member DR orientation
- Quarterly hands-on drill exercises
- Annual tabletop exercises
- External DR consultant reviews

## Compliance and Audit

### Regulatory Requirements
- SOC 2 backup and recovery controls
- GDPR data protection requirements
- Industry-specific compliance needs

### Audit Trail
- All backup operations logged
- Restore activities documented
- DR drill results retained
- Compliance evidence maintained

## Continuous Improvement

### Metrics and KPIs
- Backup success rate (target: 99.9%)
- RTO achievement (target: < 4 hours)
- RPO achievement (target: < 1 hour)
- DR drill success rate (target: 100%)

### Lessons Learned
- Post-incident reviews
- DR drill debriefings
- Procedure optimization
- Technology evaluation

---

## Related Documentation
- [AECMA Production Runbook](../go-live-runbook.md)
- [Incident Response Procedures](../incident-response.md)
- [Security Compliance Guide](../security/compliance.md)
- [Monitoring and Alerts](../monitoring-alerts.md)
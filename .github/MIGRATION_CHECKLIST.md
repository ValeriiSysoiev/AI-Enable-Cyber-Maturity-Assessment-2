# GitHub Actions Deployment Migration Checklist

This checklist guides the migration from manual ACR deployment to automated GitHub Actions deployment.

## Pre-Migration Requirements

### ✅ Repository Setup

- [ ] Repository has admin access for configuration
- [ ] Branch protection rules are configured for `main` branch
- [ ] Team members have appropriate GitHub repository permissions

### ✅ Azure Infrastructure Validation

- [ ] Azure Container Apps are deployed and accessible
- [ ] Service principal exists with required permissions
- [ ] Container registry (ACR or GHCR) is configured
- [ ] Managed identities are properly configured
- [ ] Azure resources are properly tagged and organized

### ✅ Current State Backup

- [ ] Document current manual deployment process
- [ ] Export current container app configurations
- [ ] Create backup of working deployment artifacts
- [ ] Document current environment variables and secrets

## Migration Steps

### Step 1: Configure Repository Variables

Set these in **Repository Settings → Secrets and variables → Actions → Variables**:

**Azure Authentication (Required)**
- [ ] `AZURE_SUBSCRIPTION_ID` - Azure subscription ID
- [ ] `AZURE_TENANT_ID` - Azure AD tenant ID  
- [ ] `AZURE_CLIENT_ID` - Service principal client ID

**Azure Resources - Staging (Required)**
- [ ] `ACA_RG` - Container Apps resource group name
- [ ] `ACA_ENV` - Container Apps environment name
- [ ] `ACA_APP_API` - API container app name
- [ ] `ACA_APP_WEB` - Web container app name

**Azure Resources - Production (Optional)**
- [ ] `PROD_ACA_RG` - Production resource group (defaults to ACA_RG)
- [ ] `PROD_ACA_APP_API` - Production API app name (defaults to ACA_APP_API)
- [ ] `PROD_ACA_APP_WEB` - Production Web app name (defaults to ACA_APP_WEB)

**Container Registry (Choose one)**
- [ ] **Option A**: ACR - Set `ACR_LOGIN_SERVER` and `ACR_USERNAME`
- [ ] **Option B**: GHCR - No configuration needed (automatic)

### Step 2: Configure Repository Secrets

Set these in **Repository Settings → Secrets and variables → Actions → Secrets**:

- [ ] `ACR_PASSWORD` - ACR admin password (only if using ACR)

### Step 3: Test Environment Setup

```bash
# Validate configuration
gh workflow run setup-deployment-environment.yml --field environment=staging
```

**Verification checklist:**
- [ ] Workflow runs successfully
- [ ] Azure authentication works
- [ ] Container registry access confirmed
- [ ] Azure resources are accessible
- [ ] Environment is properly configured

### Step 4: First Staging Deployment

```bash
# Manual staging deployment test
gh workflow run build-deploy.yml --field environment=staging
```

**Verification checklist:**
- [ ] Security gates pass
- [ ] Images build successfully  
- [ ] Deployment completes without errors
- [ ] Application is accessible
- [ ] Health checks pass
- [ ] Monitoring integration works

### Step 5: Verify Deployment

```bash
# Run verification script
./scripts/verify_live.sh --staging
```

**Verification checklist:**
- [ ] Web application responds correctly
- [ ] API endpoints are accessible
- [ ] Authentication flows work
- [ ] Database connections are healthy
- [ ] External integrations function
- [ ] Performance meets expectations

### Step 6: Compare with Manual Deployment

**Functional comparison:**
- [ ] Same application version deployed
- [ ] Same environment variables configured
- [ ] Same network connectivity
- [ ] Same security policies applied
- [ ] Same monitoring and logging active

**Performance comparison:**
- [ ] Response times are equivalent
- [ ] Resource utilization is similar
- [ ] Error rates are not increased
- [ ] Availability is maintained

### Step 7: Production Deployment Test

```bash
# Production deployment (requires approval)
gh workflow run build-deploy.yml --field environment=production
```

**Production checklist:**
- [ ] Manual approval process works
- [ ] Production deployment succeeds
- [ ] Production verification passes
- [ ] Rollback procedure tested
- [ ] Production monitoring active

## Post-Migration Activities

### ✅ Team Training

- [ ] Train team on new GitHub Actions workflows
- [ ] Document new deployment procedures
- [ ] Update incident response procedures
- [ ] Create troubleshooting guides

### ✅ Process Updates

- [ ] Update CI/CD documentation
- [ ] Modify development workflow guides
- [ ] Update deployment runbooks
- [ ] Archive manual deployment procedures

### ✅ Monitoring and Alerting

- [ ] Configure deployment failure alerts
- [ ] Set up performance monitoring
- [ ] Enable security scan notifications
- [ ] Configure rollback notifications

### ✅ Security and Compliance

- [ ] Review security scan configurations
- [ ] Validate compliance requirements
- [ ] Test incident response procedures
- [ ] Document audit trails

## Rollback Plan

If issues arise during migration, follow this rollback process:

### Immediate Rollback

```bash
# Emergency rollback to previous version
gh workflow run rollback.yml \
  --field environment=staging \
  --field rollback_target=PREVIOUS_SHA \
  --field component=both \
  --field reason=\"Migration rollback\"
```

### Manual Deployment Restoration

1. **Disable GitHub Actions workflows** (if needed)
2. **Use previous manual deployment process**
3. **Restore previous container versions**
4. **Verify functionality**
5. **Document issues for resolution**

## Validation Criteria

### ✅ Success Criteria

**Technical:**
- [ ] Automated deployments complete successfully
- [ ] Application functionality is identical
- [ ] Performance is maintained or improved
- [ ] Security scans pass consistently
- [ ] Rollback procedures work correctly

**Operational:**
- [ ] Team can deploy without manual ACR steps
- [ ] Deployment time is reduced or maintained
- [ ] Deployment reliability is improved
- [ ] Monitoring and alerting function properly
- [ ] Documentation is complete and accurate

**Security:**
- [ ] No hardcoded secrets in workflows
- [ ] Proper authentication mechanisms used
- [ ] Security gates function correctly
- [ ] Compliance requirements met
- [ ] Audit trails are complete

### ✅ Quality Gates

Before considering migration complete:

- [ ] **Zero Production Issues**: No production incidents related to deployment changes
- [ ] **Performance Maintained**: Application performance metrics unchanged
- [ ] **Security Verified**: All security scans pass with acceptable risk levels
- [ ] **Team Confidence**: Team comfortable with new deployment process
- [ ] **Documentation Complete**: All procedures documented and tested

## Troubleshooting Common Issues

### Authentication Failures

**Symptoms:** Azure login failures, permission denied errors

**Solution:**
1. Verify service principal permissions
2. Check AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
3. Validate OIDC configuration
4. Test authentication manually

### Container Registry Issues

**Symptoms:** Image push/pull failures, registry authentication errors

**Solution:**
1. Verify registry configuration (ACR vs GHCR)
2. Check container registry permissions
3. Validate registry credentials
4. Test manual docker login

### Deployment Failures

**Symptoms:** Container app update failures, deployment timeouts

**Solution:**
1. Check Azure resource availability
2. Verify container app configuration
3. Review deployment logs
4. Test manual Azure CLI deployment

### Security Gate Failures

**Symptoms:** Security scans block deployment, vulnerability alerts

**Solution:**
1. Review security scan results
2. Update dependencies if needed
3. Use force_deploy for urgent fixes (with approval)
4. Adjust security thresholds if appropriate

## Communication Plan

### Stakeholder Notifications

**Before Migration:**
- [ ] Notify development team of migration schedule
- [ ] Inform operations team of new procedures
- [ ] Update incident response contacts
- [ ] Schedule training sessions

**During Migration:**
- [ ] Communicate migration progress
- [ ] Report any issues immediately
- [ ] Coordinate with dependent teams
- [ ] Document lessons learned

**After Migration:**
- [ ] Announce successful completion
- [ ] Share new deployment procedures
- [ ] Collect feedback from team
- [ ] Schedule retrospective meeting

## Success Metrics

Track these metrics to measure migration success:

- **Deployment Frequency**: Increased deployment frequency
- **Deployment Duration**: Reduced deployment time
- **Failure Rate**: Reduced deployment failure rate  
- **Recovery Time**: Faster incident recovery
- **Security Posture**: Improved security scan coverage

## Final Checklist

- [ ] All repository configuration complete
- [ ] All deployment workflows tested
- [ ] Team trained on new procedures
- [ ] Documentation updated
- [ ] Manual processes deprecated
- [ ] Success metrics established
- [ ] Stakeholders notified of completion

**Migration Date**: _______________  
**Migration Lead**: _______________  
**Sign-off**: _______________

---

**Note**: This migration establishes GitHub Actions as the canonical deployment method, providing automated CI/CD with integrated security scanning, deployment tracking, and rollback capabilities. The new system maintains security and reliability standards while improving deployment velocity and operational efficiency.
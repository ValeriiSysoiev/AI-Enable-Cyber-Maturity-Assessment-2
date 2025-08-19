# Production Runbook: v0.1.0 GA Operations Guide

**Version**: v0.1.0 GA  
**Environment**: Production (rg-cybermat-prd)  
**Last Updated**: 2025-08-18  
**Production URL**: https://web-cybermat-prd.azurewebsites.net

---

## 🎯 Quick Reference

### **Production Environment Overview**
- **Web Application**: Azure App Service (web-cybermat-prd)
- **Database**: Cosmos DB (cdb-cybermat-prd)
- **Storage**: Blob Storage (stcybermatprd)
- **Secrets**: Key Vault (kv-cybermat-prd)
- **Monitoring**: Application Insights (ai-cybermat-prd)
- **API Service**: Container Apps (api-cybermat-prd) - **NOT DEPLOYED**¹

¹ *Container Apps deployment was skipped due to provider timeout. Web-only deployment is fully functional.*

### **Emergency Contacts & Escalation**
- **Primary**: GitHub Actions deployment logs and Azure Portal
- **Monitoring**: Application Insights alerts and dashboards
- **Infrastructure**: Azure Resource Health and Service Health
- **Security**: Key Vault access logs and audit trails

---

## 🚀 **Deployment Operations**

### **Successful Deployment Verification**
```bash
# 1. Check production web application
curl -f https://web-cybermat-prd.azurewebsites.net/health
# Expected: HTTP 200 with health status JSON

# 2. Verify authentication endpoint
curl -I https://web-cybermat-prd.azurewebsites.net/signin
# Expected: HTTP 200 or redirect to auth page

# 3. Check static resources
curl -I https://web-cybermat-prd.azurewebsites.net
# Expected: HTTP 200 with proper content-type headers
```

### **Deployment Status Monitoring**
```bash
# GitHub Actions deployment status
gh run list --workflow=deploy_production.yml --limit=5

# View latest deployment details
gh run view <run-id> --log

# Check production environment variables
gh api repos/ValeriiSysoiev/AI-Enable-Cyber-Maturity-Assessment-2/environments/production/variables
```

### **Azure Resource Health Check**
```bash
# App Service status
az webapp show --name web-cybermat-prd --resource-group rg-cybermat-prd --query "state,hostNames"

# Cosmos DB status
az cosmosdb show --name cdb-cybermat-prd --resource-group rg-cybermat-prd --query "documentEndpoint,provisioningState"

# Storage account status
az storage account show --name stcybermatprd --resource-group rg-cybermat-prd --query "primaryEndpoints,provisioningState"

# Key Vault status
az keyvault show --name kv-cybermat-prd --resource-group rg-cybermat-prd --query "properties.vaultUri,properties.provisioningState"
```

---

## 🔄 **Rollback Procedures**

### **Web Application Rollback**

**Option 1: Redeploy Previous Tag**
```bash
# 1. Identify previous successful deployment tag
git tag --sort=-version:refname | grep -E "^v[0-9]" | head -5

# 2. Trigger deployment with previous tag
gh workflow run deploy_production.yml -f ref=<previous-tag>

# 3. Monitor rollback deployment
gh run list --workflow=deploy_production.yml --limit=3
```

**Option 2: Azure App Service Deployment Slots (if configured)**
```bash
# Swap deployment slots (if slots are configured)
az webapp deployment slot swap \
  --name web-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --slot production \
  --target-slot staging
```

**Option 3: Manual App Service Rollback**
```bash
# List recent deployments
az webapp deployment list \
  --name web-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --query "[].{id:id,status:status,start_time:start_time}" \
  --output table

# Rollback to specific deployment (if available)
# Note: Manual intervention may be required for Node.js App Service rollbacks
```

### **Database Rollback (Cosmos DB)**
```bash
# Point-in-time restore (if needed)
# Note: Cosmos DB has built-in backup; restore requires Azure Portal or support ticket
az cosmosdb restorable-database-account list \
  --account-name cdb-cybermat-prd \
  --location westeurope
```

### **Emergency Service Stop**
```bash
# Stop App Service (emergency only)
az webapp stop --name web-cybermat-prd --resource-group rg-cybermat-prd

# Restart App Service
az webapp start --name web-cybermat-prd --resource-group rg-cybermat-prd
```

---

## 📊 **Health Checks & Monitoring**

### **Application Health Validation**
```bash
# Primary health check
curl -f https://web-cybermat-prd.azurewebsites.net/health
# Expected output: {"status":"healthy","timestamp":"..."}

# Web application readiness
curl -f https://web-cybermat-prd.azurewebsites.net/readyz
# Expected: HTTP 200 (if endpoint exists) or 404 (if not implemented)

# Authentication flow check
curl -I https://web-cybermat-prd.azurewebsites.net/signin
# Expected: HTTP 200 or 302 redirect to auth provider
```

### **Infrastructure Health Monitoring**
```bash
# App Service metrics
az monitor metrics list \
  --resource "/subscriptions/<sub-id>/resourceGroups/rg-cybermat-prd/providers/Microsoft.Web/sites/web-cybermat-prd" \
  --metric "Requests,ResponseTime,Http2xx,Http4xx,Http5xx" \
  --interval PT1M

# Cosmos DB metrics  
az monitor metrics list \
  --resource "/subscriptions/<sub-id>/resourceGroups/rg-cybermat-prd/providers/Microsoft.DocumentDB/databaseAccounts/cdb-cybermat-prd" \
  --metric "TotalRequests,ProvisionedThroughput,ConsumedThroughput" \
  --interval PT5M
```

### **Application Insights Queries**

**Request Performance**
```kql
requests
| where timestamp > ago(1h)
| summarize 
    TotalRequests = count(),
    AvgDuration = avg(duration),
    P95Duration = percentile(duration, 95)
by bin(timestamp, 5m)
| render timechart
```

**Error Rate Monitoring**
```kql
requests
| where timestamp > ago(1h)
| summarize 
    TotalRequests = count(),
    FailedRequests = countif(success == false),
    ErrorRate = (countif(success == false) * 100.0) / count()
by bin(timestamp, 5m)
| render timechart
```

**Dependency Health**
```kql
dependencies
| where timestamp > ago(1h)
| summarize 
    TotalCalls = count(),
    FailedCalls = countif(success == false),
    AvgDuration = avg(duration)
by type, name
| order by TotalCalls desc
```

---

## 🔧 **Troubleshooting Guide**

### **Common Issues & Resolutions**

#### **Issue: Web Application Not Responding (HTTP 5xx)**
```bash
# 1. Check App Service status
az webapp show --name web-cybermat-prd --resource-group rg-cybermat-prd --query "state"

# 2. Check App Service logs
az webapp log tail --name web-cybermat-prd --resource-group rg-cybermat-prd

# 3. Restart App Service if needed
az webapp restart --name web-cybermat-prd --resource-group rg-cybermat-prd

# 4. Check Application Insights for errors
# Navigate to ai-cybermat-prd → Failures → Exceptions
```

#### **Issue: Authentication Problems**
```bash
# 1. Verify Key Vault access
az keyvault secret list --vault-name kv-cybermat-prd --query "[].name"

# 2. Check Managed Identity permissions
az webapp identity show --name web-cybermat-prd --resource-group rg-cybermat-prd

# 3. Test authentication endpoint
curl -v https://web-cybermat-prd.azurewebsites.net/api/auth/session

# 4. Check audit logs in Application Insights
# Query: traces | where message contains "auth" | order by timestamp desc
```

#### **Issue: Database Connectivity Problems**
```bash
# 1. Check Cosmos DB status
az cosmosdb show --name cdb-cybermat-prd --resource-group rg-cybermat-prd --query "provisioningState"

# 2. Test connectivity (from App Service or local)
az cosmosdb collection show \
  --db-name appdb \
  --collection-name engagements \
  --name cdb-cybermat-prd \
  --resource-group rg-cybermat-prd

# 3. Check Cosmos DB metrics for throttling
# Navigate to Azure Portal → Cosmos DB → Metrics → Total Request Units
```

#### **Issue: File Upload Problems**
```bash
# 1. Check storage account status
az storage account show --name stcybermatprd --resource-group rg-cybermat-prd --query "provisioningState"

# 2. Verify evidence container exists
az storage container show --name evidence --account-name stcybermatprd

# 3. Check SAS token generation (from application logs)
# Application Insights → Logs → traces | where message contains "SAS"
```

### **Performance Optimization**

#### **Scaling App Service**
```bash
# Check current App Service plan
az appservice plan show --name asp-cybermat-prd --resource-group rg-cybermat-prd

# Scale up (increase VM size)
az appservice plan update \
  --name asp-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --sku S1  # or S2, S3 for more resources

# Scale out (increase instance count)
az appservice plan update \
  --name asp-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --number-of-workers 2
```

#### **Cosmos DB Performance Tuning**
```bash
# Check current RU/s provisioning
az cosmosdb sql database throughput show \
  --account-name cdb-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --name appdb

# Update throughput if needed (example)
az cosmosdb sql database throughput update \
  --account-name cdb-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --name appdb \
  --throughput 800
```

---

## 🔐 **Security Operations**

### **Security Health Checks**
```bash
# 1. HTTPS enforcement check
curl -I http://web-cybermat-prd.azurewebsites.net
# Expected: HTTP 301/302 redirect to HTTPS

# 2. Security headers validation
curl -I https://web-cybermat-prd.azurewebsites.net | grep -E "(Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options)"

# 3. Authentication endpoint security
curl -I https://web-cybermat-prd.azurewebsites.net/api/auth/signin
# Expected: Appropriate CORS and security headers
```

### **Access Control & Audit**
```bash
# Key Vault access audit
az monitor activity-log list \
  --resource-group rg-cybermat-prd \
  --caller "*" \
  --start-time 2025-08-18T00:00:00Z

# App Service authentication logs
# Check Application Insights → Logs
# Query: traces | where message contains "auth" or message contains "sign"
```

### **Secret Rotation (when needed)**
```bash
# List current secrets (names only)
az keyvault secret list --vault-name kv-cybermat-prd --query "[].name" -o table

# Update secret (example)
az keyvault secret set --vault-name kv-cybermat-prd --name "DATABASE_CONNECTION" --value "new-value"

# Restart App Service to pick up new secrets
az webapp restart --name web-cybermat-prd --resource-group rg-cybermat-prd
```

---

## 📈 **Monitoring & Alerting Setup**

### **Recommended Alert Rules**

#### **Application Availability Alert**
```bash
# Create availability alert (example via Azure CLI)
az monitor metric-alert create \
  --name "Web App Down" \
  --resource-group rg-cybermat-prd \
  --scopes "/subscriptions/<sub-id>/resourceGroups/rg-cybermat-prd/providers/Microsoft.Web/sites/web-cybermat-prd" \
  --condition "avg Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 2 \
  --description "Web application returning 5xx errors"
```

#### **Performance Alert**
```bash
# Response time alert
az monitor metric-alert create \
  --name "High Response Time" \
  --resource-group rg-cybermat-prd \
  --scopes "/subscriptions/<sub-id>/resourceGroups/rg-cybermat-prd/providers/Microsoft.Web/sites/web-cybermat-prd" \
  --condition "avg ResponseTime > 5000" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 3 \
  --description "Web application response time > 5 seconds"
```

### **Dashboard Setup**
- **Application Insights**: Create custom dashboard with key metrics
- **Azure Portal**: Pin critical resource health to shared dashboard
- **Log Analytics**: Set up saved queries for common troubleshooting scenarios

---

## 🔄 **Maintenance & Updates**

### **Routine Maintenance Tasks**

#### **Weekly**
- [ ] Review Application Insights for errors and performance trends
- [ ] Check Azure Resource Health for any service advisories
- [ ] Verify backup status for Cosmos DB and blob storage
- [ ] Review security logs and access patterns

#### **Monthly**  
- [ ] Update App Service runtime (if newer versions available)
- [ ] Review and optimize Cosmos DB RU/s based on usage patterns
- [ ] Analyze cost and usage reports
- [ ] Test backup and restore procedures

#### **Quarterly**
- [ ] Security audit and penetration testing
- [ ] Performance load testing
- [ ] Disaster recovery testing
- [ ] Update documentation and runbooks

### **Security Updates**
```bash
# Check for App Service platform updates
az webapp list-runtimes --linux | grep NODE

# Update App Service runtime (if needed)
az webapp config set \
  --name web-cybermat-prd \
  --resource-group rg-cybermat-prd \
  --linux-fx-version "NODE:20-lts"
```

---

## 📞 **Support & Escalation**

### **Level 1: Automated Monitoring**
- Application Insights alerts
- Azure Service Health notifications
- GitHub Actions deployment notifications
- Custom dashboard monitoring

### **Level 2: Operational Response**
- Use this runbook for troubleshooting
- Check Azure Portal for resource health
- Review Application Insights logs and metrics
- Execute standard remediation procedures

### **Level 3: Engineering Escalation**
- Complex performance issues
- Security incidents requiring investigation
- Infrastructure changes or capacity planning
- New feature deployment issues

### **Emergency Procedures**
1. **Immediate**: Stop traffic if security issue detected
2. **Assess**: Use monitoring tools to determine scope and impact
3. **Mitigate**: Apply appropriate remediation from this runbook
4. **Communicate**: Update stakeholders on status and resolution timeline
5. **Document**: Record incident details and lessons learned

---

## 📚 **Reference Links**

### **Production Resources**
- **Web Application**: https://web-cybermat-prd.azurewebsites.net
- **Azure Portal**: [Resource Group rg-cybermat-prd](https://portal.azure.com/#@tenant/resource/subscriptions/sub-id/resourceGroups/rg-cybermat-prd)
- **Application Insights**: [ai-cybermat-prd Dashboard](https://portal.azure.com/#@tenant/resource/subscriptions/sub-id/resourceGroups/rg-cybermat-prd/providers/Microsoft.Insights/components/ai-cybermat-prd)

### **Documentation**
- **Deployment Guide**: `.github/workflows/deploy_production.yml`
- **Environment Variables**: `docs/ENVIRONMENT_SECRETS.md`
- **Release Notes**: `docs/RELEASE_NOTES_0.1.0.md`
- **Security Guide**: `docs/SECURITY.md`

### **Automation**
- **GitHub Actions**: [Production Workflows](https://github.com/ValeriiSysoiev/AI-Enable-Cyber-Maturity-Assessment-2/actions)
- **UAT Validation**: `gh workflow run uat_prod.yml -f deployment_tag=v0.1.0`
- **Health Check Script**: `./scripts/verify_live.sh`

---

**📋 Runbook Version**: v0.1.0 GA  
**🔄 Last Updated**: 2025-08-18  
**👥 Maintained By**: DevOps Engineering Team  
**📞 Emergency Contact**: Monitor GitHub Actions and Azure Portal for real-time status
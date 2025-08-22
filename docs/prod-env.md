# Production Environment Setup Guide

## Overview

This guide outlines the required repository variables and procedures for production deployment of the AI-Enabled Cyber Maturity Assessment platform.

## Required Repository Variables

Navigate to **Settings → Secrets and variables → Actions → Variables** in your GitHub repository and configure the following production variables:

### Core Configuration

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `GHCR_ENABLED` | Enable GitHub Container Registry builds | `1` | ✅ |

### Azure Authentication (Production Service Principal)

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `AZURE_SUBSCRIPTION_ID` | Production Azure subscription ID | `12345678-1234-1234-1234-123456789012` | ✅ |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `87654321-4321-4321-4321-210987654321` | ✅ |
| `AZURE_CLIENT_ID` | Production service principal client ID | `abcdef12-3456-7890-abcd-ef1234567890` | ✅ |

### Azure Container Apps (Production Resources)

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `ACA_RG_PROD` | Production resource group name | `rg-aecma-production` | ✅ |
| `ACA_ENV_PROD` | Production Container Apps environment | `env-aecma-production` | ✅ |
| `ACA_APP_API_PROD` | Production API container app name | `app-aecma-api-prod` | ✅ |
| `ACA_APP_WEB_PROD` | Production web container app name | `app-aecma-web-prod` | ✅ |

### Azure App Service (Production Resources - Alternative to Container Apps)

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `APPSVC_RG_PROD` | Production App Service resource group | `rg-aecma-appservice-prod` | ✅ |
| `APPSVC_WEBAPP_WEB_PROD` | Production web app name | `webapp-aecma-web-prod` | ✅ |
| `APPSVC_WEBAPP_API_PROD` | Production API app name | `webapp-aecma-api-prod` | ✅ |

### Service URLs

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `PROD_URL` | Production web application URL | `https://maturity.yourdomain.com` | ❌ |

**Note**: If `PROD_URL` is not set, the system will compute it as `https://${ACA_APP_WEB_PROD}.${ACA_ENV_PROD}.azurecontainerapps.io`

## How to Run: Deploy Production → Verify

**Quick Checklist:**
1. ✅ Set required repo variables for **App Service** OR **Container Apps** (see tables above)
2. ✅ Configure Azure authentication: `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`
3. ✅ Enable GHCR builds: `GHCR_ENABLED=1`
4. ✅ Run: **Actions → Deploy Production** (manual workflow_dispatch)
5. ✅ Wait for build_and_push_ghcr → deploy_appservice_prod/deploy_aca_prod
6. ✅ Run verification: `./scripts/verify_live.sh --prod`
7. ✅ Check logs in: `artifacts/verify/prod_verify.log`
8. ✅ Auto-fix any issues and re-run verification until ALL GREEN
9. ✅ Monitor production URL for 200-399 HTTP responses
10. ✅ Ready for production traffic!

## Deployment Scenarios

### Scenario A: App Service Production
- Set `GHCR_ENABLED=1` and `PROD_URL` 
- Leave Azure Container Apps variables unset
- Workflow will build/push images but skip Azure deployment

### Scenario B: Container Apps Production  
- Set all Azure authentication and Container Apps variables
- Optionally set `PROD_URL` to override computed URL
- Workflow will build/push images and deploy to Container Apps

## Security Considerations

### Service Principal Setup

Create a dedicated production service principal with minimal required permissions:

```bash
# Create production service principal
az ad sp create-for-rbac --name "aecma-production-deploy" \
  --role "Contributor" \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_PROD_RG"
```

### Required Permissions

The production service principal needs:
- `Contributor` role on the production resource group
- `AcrPush` role if using Azure Container Registry
- **No access** to staging or development resources

### Security Best Practices

1. **Separate Subscriptions**: Use dedicated production subscription when possible
2. **Network Isolation**: Implement network security groups and private endpoints
3. **Resource Tagging**: Tag all production resources for compliance and cost tracking
4. **Access Reviews**: Regular review of service principal permissions
5. **Credential Rotation**: Implement regular credential rotation schedule

## Change Management

### Approval Gates

Production deployments require:
1. **Code Review**: All changes reviewed by at least 2 team members
2. **Security Review**: Security team approval for infrastructure changes
3. **Change Advisory Board**: CAB approval for production deployments
4. **Stakeholder Sign-off**: Business stakeholder approval for releases

### Change Windows

| Change Type | Approved Windows | Notice Period |
|-------------|------------------|---------------|
| **Emergency Fix** | 24/7 with approval | Immediate |
| **Regular Deployment** | Tuesday/Thursday 2-4 PM EST | 48 hours |
| **Major Release** | Saturday 12-6 AM EST | 1 week |
| **Infrastructure** | Saturday 12-6 AM EST | 2 weeks |

### Pre-Production Validation

Before production deployment:
1. ✅ All staging tests pass
2. ✅ Security scans complete with no critical findings
3. ✅ Performance benchmarks meet SLA requirements
4. ✅ Rollback procedures tested and validated
5. ✅ Monitoring and alerting configured

## Environment Protection

### GitHub Environment Settings

Configure the production environment with:
- **Required reviewers**: Security team + Release manager
- **Wait timer**: 5 minutes for final review
- **Deployment branches**: Only `main` branch
- **Environment secrets**: Production-specific secrets if needed

### Monitoring Requirements

Production environment must have:
- **Health checks**: Automated health monitoring every 5 minutes
- **Performance monitoring**: Response time and error rate tracking
- **Security monitoring**: Failed authentication and suspicious activity alerts
- **Business metrics**: Usage analytics and compliance reporting

## Compliance and Auditing

### Audit Trail

All production activities must maintain:
- **Deployment logs**: Complete CI/CD pipeline execution logs
- **Access logs**: All administrative access to production resources
- **Change records**: Documentation of all configuration changes
- **Incident records**: Complete incident response documentation

### Compliance Requirements

Production environment supports:
- **SOC 2 Type II**: Security, availability, and confidentiality controls
- **GDPR**: Data protection and privacy compliance
- **ISO 27001**: Information security management
- **Industry standards**: Sector-specific compliance requirements

## Emergency Procedures

### 503 Service Unavailable Fix

If experiencing 503 errors in production:
1. **Immediate fix**: Run `./scripts/appservice_apply_prod_settings.sh` to restore service configuration
2. **Verify resolution**: Execute `./scripts/verify_live.sh --prod` to confirm service restoration
3. **Monitor**: Check production URL returns 200-399 HTTP responses before considering resolved

### Incident Response

In case of production issues:
1. **Immediate**: Execute rollback procedure if system is degraded
2. **Assessment**: Determine impact and required response level
3. **Communication**: Notify stakeholders per communication plan
4. **Resolution**: Apply fix or maintain rollback until resolution
5. **Post-mortem**: Document lessons learned and process improvements

### Emergency Contacts

| Role | Contact Method | Response Time |
|------|----------------|---------------|
| **On-Call Engineer** | PagerDuty/Phone | 15 minutes |
| **Security Team** | Secure messaging | 30 minutes |
| **Release Manager** | Email/Phone | 1 hour |
| **Business Stakeholder** | Email | 4 hours |

## Validation Checklist

Before enabling production deployment:

- [ ] All required repository variables configured
- [ ] Production service principal created with minimal permissions
- [ ] GitHub environment protection rules configured
- [ ] Monitoring and alerting operational
- [ ] Rollback procedures documented and tested
- [ ] Change management process approved
- [ ] Security review completed
- [ ] Stakeholder training completed
- [ ] Documentation updated and accessible
- [ ] Emergency procedures validated

## Next Steps

After configuration:
1. **Test deployment**: Run production workflow in dry-run mode
2. **Validate monitoring**: Confirm all alerts and dashboards functional
3. **Execute go-live**: Follow go-live runbook procedures
4. **Monitor closely**: Enhanced monitoring for initial 48 hours
5. **Document lessons**: Update procedures based on experience
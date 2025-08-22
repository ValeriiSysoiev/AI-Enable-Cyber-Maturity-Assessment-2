# Deployment Guide

Comprehensive deployment procedures for AI-Enable Cyber Maturity Assessment v2.

## Overview

This guide covers deployment procedures for staging and production environments using Azure Container Apps with GitHub Actions CI/CD.

## Prerequisites

### Azure Resources
- Azure subscription with appropriate permissions
- Resource group created
- Azure Container Apps environment configured
- Azure Key Vault for secrets management
- Azure Cosmos DB for document storage
- Azure AI Search for RAG functionality
- Azure OpenAI for LLM services

### GitHub Configuration
- GitHub repository with actions enabled
- GitHub secrets configured for Azure deployment
- Container registry access (GHCR)
- Environment protection rules configured

## Deployment Environments

### Staging Environment
- **Purpose**: UAT validation and integration testing
- **URL**: `https://web-staging.region.azurecontainerapps.io`
- **Auto-deploy**: Enabled from main branch
- **Monitoring**: Basic monitoring and logging

### Production Environment
- **Purpose**: Live production workloads
- **URL**: `https://aecma.azurecontainerapps.io`
- **Auto-deploy**: Manual approval required
- **Monitoring**: Comprehensive monitoring and alerting

## Deployment Process

### Automated Deployment (Staging)
1. **Trigger**: Push to main branch
2. **Build**: Container images built and pushed to GHCR
3. **Deploy**: Automatic deployment to staging environment
4. **Verify**: Health checks and smoke tests executed

### Manual Deployment (Production)
1. **Preparation**: Release freeze procedures completed
2. **Approval**: Stakeholder sign-offs obtained
3. **Deploy**: Manual trigger of production deployment
4. **Monitor**: Real-time monitoring during deployment
5. **Verify**: Post-deployment validation and testing

## Configuration Management

### Environment Variables
- Managed through Azure Key Vault references
- Environment-specific configuration files
- Secrets never stored in repository
- Configuration validation in CI/CD

### Database Migrations
- Automated schema migrations
- Rollback procedures documented
- Data backup before migrations
- Migration testing in staging

## Monitoring and Alerting

### Health Checks
- Application health endpoints
- Database connectivity checks
- External service dependency validation
- Custom business logic health checks

### Monitoring Stack
- **Application Insights**: Application performance monitoring
- **Azure Monitor**: Infrastructure monitoring
- **Log Analytics**: Centralized logging
- **GitHub Actions**: Deployment pipeline monitoring

## Rollback Procedures

### Automated Rollback Triggers
- Health check failures
- Critical error rate thresholds
- Performance degradation detection
- Manual emergency stop

### Rollback Process
1. **Immediate**: Stop current deployment
2. **Assess**: Evaluate rollback necessity and risk
3. **Execute**: Rollback to previous stable version
4. **Monitor**: Verify system stability after rollback
5. **Investigate**: Root cause analysis and fixes

## Security Considerations

### Deployment Security
- Signed container images
- Secrets management via Key Vault
- Network security groups
- HTTPS enforcement

### Access Control
- Role-based access to deployment environments
- Multi-factor authentication required
- Audit logging for all deployment actions
- Least privilege principle enforcement

## Troubleshooting

### Common Issues
- **Container startup failures**: Check logs and resource limits
- **Database connection issues**: Verify connection strings and network access
- **Authentication failures**: Check Azure AD configuration and tokens
- **Performance issues**: Monitor resource usage and scaling

### Diagnostic Tools
- Azure Container Apps logs
- Application Insights traces
- Health check endpoints
- Performance monitoring dashboards

This deployment guide ensures consistent, secure, and reliable deployments across all environments.
# AI-Enabled Cyber Maturity Assessment

**Overview**: An enterprise-grade platform for conducting AI-powered cybersecurity maturity assessments. The system enables security consultants to analyze organizational evidence, identify gaps against industry frameworks (NIST CSF, ISO 27001), and generate strategic roadmaps through intelligent document analysis and automated recommendations.

## Key Capabilities

- 🔍 **Evidence Analysis**: Automated ingestion and analysis of security documentation
- 📊 **Maturity Assessment**: Gap analysis against NIST CSF, ISO 27001, and custom frameworks
- 🗺️ **Strategic Roadmaps**: AI-generated prioritized recommendations and implementation plans
- 👥 **Workshop Management**: Collaborative assessment sessions with meeting minutes
- 🔐 **Enterprise Security**: Azure AD authentication with role-based access control
- 📈 **Real-time Insights**: Live dashboards and progress tracking

## Current Architecture

### High-Level Components

- **Web Frontend**: Next.js 14 application hosted on Azure Container Apps
  - Production URL: `https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - Built with TypeScript, React 18, and Tailwind CSS
  - Server-side rendering with App Router
  
- **API Backend**: FastAPI service hosted on Azure Container Apps
  - Production URL: `https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - Python 3.11 runtime with async/await support
  - Health endpoint: `/health` | Version endpoint: `/version`
  
- **Proxy Layer**: Web app proxies API calls via `/api/proxy/*`
  - SSRF protection with allowed URL validation
  - Rate limiting and request sanitization
  - Automatic auth token forwarding
  
- **Identity**: Azure AD (Entra ID) authentication in production
  - Sign-in: `/signin` | Sign-out: via user menu
  - Role-based access: Admin, Consultant, Client roles
  - No demo mode in production (AAD-only)

### Data Layer

- **Cosmos DB**: Document store for assessments and evidence
- **Azure Storage**: Blob storage for uploaded files
- **Azure Service Bus**: Async job processing
- **Azure AI Search**: RAG and semantic search capabilities

## Deployments

### GitHub Actions (Canonical)

**Workflow**: `.github/workflows/deploy-container-apps.yml`

- **Staging**: Auto-deploy on push to `main`
- **Production**: Manual dispatch with SHA tagging
  - Builds Docker images tagged with `${{ github.sha }}`
  - Updates Container Apps with new image
  - Sets `BUILD_SHA` environment variable
  - Verification: `/api/version` returns matching SHA

### Deployment Commands

```bash
# Check deployment status
gh run list --workflow=deploy-container-apps.yml

# Trigger production deployment
gh workflow run deploy-container-apps.yml

# Verify deployment
curl https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/version
```

## Environment Configuration

### Key Environment Variables (no secrets)

| Variable | Purpose | Example |
|----------|---------|---------|
| `NODE_ENV` | Environment mode | `production` |
| `AUTH_MODE` | Authentication type | `aad` |
| `NEXTAUTH_URL` | NextAuth callback URL | `https://web-cybermat-prd-aca...` |
| `PROXY_TARGET_API_BASE_URL` | API endpoint for proxy | `https://api-cybermat-prd-aca...` |
| `AZURE_AD_TENANT_ID` | AAD tenant | `{guid}` |
| `AZURE_AD_CLIENT_ID` | AAD app registration | `{guid}` |
| `NEXT_PUBLIC_API_BASE_URL` | Client-side API path | `/api/proxy` |
| `ENVIRONMENT` | Deployment environment | `production` |

## UAT Gate

Every production rollout must pass User Acceptance Testing covering the critical user journey:

**UAT Flow**: Sign-in → View engagements → Create/Open engagement → Navigate to `/new` preset → Complete assessment workflow → Sign-out

This gate ensures core functionality remains intact after each deployment.

## Troubleshooting

### Common Issues

- **503 Service Unavailable**: Check Container Apps health, verify environment variables
- **Module not found**: Check case sensitivity in imports (Linux containers are case-sensitive)
- **AAD callback mismatch**: Verify `NEXTAUTH_URL` matches app registration redirect URI
- **Health check failures**: Ensure `/health` returns 200 for both API and Web

### Quick Checks

```bash
# API health
curl https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/health

# Web health  
curl https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/api/health

# Version verification
curl https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/version
```

## Documentation Index

- [Architecture](./docs/architecture.md) - System design and component details
- [Deployments](./docs/deployments.md) - CI/CD workflows and rollback procedures
- [Configuration](./docs/configuration.md) - Environment variables and settings
- [UAT Guide](./docs/uat.md) - User acceptance testing procedures
- [Operations](./docs/operations.md) - Health checks and monitoring
- [Security](./docs/security.md) - Identity model and security practices
- [Release Notes Template](./docs/release_notes_template.md) - Template for version releases

## Quick Start (Local Development)

```bash
# Clone repository
git clone https://github.com/your-org/cyber-maturity-assessment.git
cd cyber-maturity-assessment

# Install dependencies
cd web && npm install
cd ../app && pip install -r requirements.txt

# Start services (requires Docker)
docker compose up -d

# Access applications
# Web: http://localhost:3000
# API: http://localhost:8000
```

## Repository Management

### Size & Performance
This repository has been optimized for performance and size control:

- **Current Status**: 22KB source code, 1.3GB total (due to git history)
- **Working Tree**: Clean, no build artifacts or dependencies committed
- **Size Monitoring**: Automated CI checks prevent repository bloat
- **Asset Policy**: Large files stored in Azure Blob Storage, not git

### Size Guardrails
Automated checks prevent:
- Individual files >10MB
- Build artifacts (node_modules, .next, __pycache__)
- Test screenshots and temporary files
- Large binary dependencies

### History Cleanup (Scheduled)
⚠️ **Planned History Remediation**: Git history contains 669MB of accidentally committed build artifacts. A history cleanup is planned to reduce total repository size from 1.3GB to ~300-500MB.

See `/docs/repo/` for detailed policies and procedures.

## Support

For issues or questions, please check:
1. [Operations Guide](./docs/operations.md) for troubleshooting
2. GitHub Issues for known problems
3. Contact the platform team via Teams

---
*Last Updated: August 2025*
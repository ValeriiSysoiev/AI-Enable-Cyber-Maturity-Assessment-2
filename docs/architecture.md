# Architecture

## System Overview

The AI-Enabled Cyber Maturity Assessment platform uses a modern microservices architecture deployed on Azure Container Apps.

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────────────┐
│              Web Frontend (Container Apps)                      │
│                   Next.js 14 / React 18                         │
│         web-cybermat-prd-aca.icystone-69c102b0...              │
└────────────────────────┬────────────────────────────────────────┘
                         │ /api/proxy/*
┌────────────────────────▼────────────────────────────────────────┐
│               API Backend (Container Apps)                      │
│                    FastAPI / Python 3.11                        │
│         api-cybermat-prd-aca.icystone-69c102b0...              │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     Azure Services                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │ Cosmos DB │ │  Storage │ │Service   │ │ AI Search    │     │
│  │          │ │   Blobs  │ │  Bus     │ │              │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### Web Frontend (Azure Container Apps)

- **Technology**: Next.js 14 with App Router, React 18, TypeScript
- **Hosting**: Azure Container Apps with auto-scaling
- **Features**:
  - Server-side rendering for performance
  - Client-side interactivity with React
  - Tailwind CSS for styling
  - Responsive design for mobile/desktop

### API Backend (Azure Container Apps)

- **Technology**: FastAPI, Python 3.11, Pydantic
- **Hosting**: Azure Container Apps with health probes
- **Endpoints**:
  - `/health` - Liveness probe
  - `/version` - Build SHA verification
  - `/api/v1/*` - Business endpoints
- **Features**:
  - Async/await for high concurrency
  - OpenAPI documentation
  - Request validation
  - Error handling middleware

### Proxy Layer

The Web frontend proxies all API calls through `/api/proxy/*` for:

- **Security**: SSRF protection with URL allowlist
- **Authentication**: Automatic token forwarding
- **Rate Limiting**: Per-user request throttling
- **Monitoring**: Centralized request logging

Example flow:
```
Browser → /api/proxy/assessments → Web Backend → API Backend
```

### Identity & Authentication

**Production**: Azure AD (Entra ID) only
- OAuth 2.0 / OpenID Connect flow
- Role-based access control (RBAC)
- Groups: Admins, Consultants, Clients
- No demo/local auth in production

**Session Management**:
- NextAuth.js for session handling
- JWT tokens with refresh
- Secure cookie storage
- Auto-logout on inactivity

### Data Layer

**Cosmos DB**:
- Document store for assessments
- Partitioned by engagement ID
- Global replication for HA

**Azure Storage**:
- Blob storage for evidence files
- SAS tokens for secure upload
- Lifecycle policies for retention

**Service Bus**:
- Async job processing
- Document ingestion queue
- Score calculation workers

**AI Search**:
- Semantic search over evidence
- RAG for recommendations
- Vector embeddings

## Deployment Architecture

### Container Registry
- Azure Container Registry (ACR)
- Images tagged with Git SHA
- Vulnerability scanning

### Container Apps Environment
- Managed Kubernetes
- Auto-scaling based on load
- Health probes and restarts
- Ingress with TLS termination

### Networking
- Private endpoints for data services
- Application Gateway for WAF
- Network security groups
- DDoS protection

## Security Architecture

### Defense in Depth
1. **Edge**: Azure Front Door with WAF
2. **Application**: Container Apps with managed identity
3. **Data**: Encryption at rest and in transit
4. **Identity**: Azure AD with MFA
5. **Monitoring**: Security Center and Sentinel

### Secret Management
- Azure Key Vault for secrets
- Managed identities where possible
- Environment variables for config
- No secrets in code or logs

## Scalability

### Horizontal Scaling
- Container Apps auto-scale rules
- Cosmos DB autoscale throughput
- Service Bus competing consumers

### Performance Optimization
- CDN for static assets
- Redis cache for sessions
- Database query optimization
- Async processing for heavy operations

## Monitoring & Observability

### Application Insights
- Request tracking
- Error monitoring
- Performance metrics
- Custom telemetry

### Log Analytics
- Centralized logging
- Query with KQL
- Alert rules
- Dashboards

## Disaster Recovery

### Backup Strategy
- Cosmos DB continuous backup
- Storage account replication
- Container image registry geo-replication

### Recovery Targets
- RTO: 4 hours
- RPO: 1 hour
- Automated failover for critical services
# Development Guidelines

This document defines the non-negotiable principles, architecture baseline, and operational rules for contributing to the AI-Enabled Cyber Maturity Assessment platform.

## Core Principles

1. **Architecture-First**: Every change must align with the documented architecture in README.md and /docs
2. **No Hacks**: Fix root causes only. No workarounds or temporary patches allowed
3. **Tiny PRs**: Maximum 300 LOC per PR (excluding generated files), single concern only
4. **Actions Canonical**: GitHub Actions is the single source of truth for CI/CD
5. **UAT Gate**: Every production deployment must pass the critical user journey validation

## Architecture Baseline

### System Components
- **Web**: Next.js 14 on Azure Container Apps
  - Production: `https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - TypeScript, React 18, Tailwind CSS, App Router
  
- **API**: FastAPI on Azure Container Apps
  - Production: `https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
  - Python 3.11, async/await, Pydantic validation
  
- **Auth**: Azure AD (Entra ID) only in production
  - No demo mode in production
  - Role-based access: Admin, Consultant, Client
  
- **Proxy**: Web proxies API via `/api/proxy/*`
  - SSRF protection, rate limiting, auth forwarding
  
### Invariants
- Health endpoints: `/health` (API), `/api/health` (Web)
- Version endpoint: `/version` returns deployment SHA
- Actions workflow: `.github/workflows/deploy-container-apps.yml`
- UAT Flow: Sign-in → View engagements → Create/Open → Navigate to `/new` → Complete workflow → Sign-out

## Non-Negotiable Rules

### Authentication & Authorization
- Production uses Azure AD exclusively - no demo mode
- Sign-in: `/signin`, Sign-out: via user menu
- All endpoints require authentication except health/version
- Engagement-level authorization enforced at API layer

### Proxy Contract
- Client calls `/api/proxy/*` → Web forwards to API
- Web handles auth token injection
- API never exposed directly to browser
- Request validation and sanitization at proxy layer

### Imports & Case Sensitivity
- Linux containers are case-sensitive
- Always use exact case for imports
- Verify imports work on Linux before PR
- No relative imports beyond `../` (max one level)

### IDs & Storage
- UUIDs for all entity IDs
- Cosmos DB for documents
- Azure Storage for blobs
- No local file storage in containers

### Security Posture
- No secrets in code or logs
- Environment variables for configuration
- Managed Identity for Azure resources
- Input validation on all endpoints
- Rate limiting in production

## Change Discipline

### PR Rules
1. Single concern per PR
2. <300 LOC (excluding generated)
3. Must include tests
4. Must update docs if behavior changes
5. Must pass all CI checks
6. Security review for auth/data changes
7. QA approval for UX changes

### Documentation Updates
- README.md for architecture changes
- /docs for operational changes
- Inline comments only for complex algorithms
- API documentation via OpenAPI/Swagger
- TypeScript types are self-documenting

### Testing Requirements
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user journeys
- Type safety enforced (no `any` without justification)
- Performance tests for data operations

## Testing & Quality Bars

### Unit & Integration Tests
- Python: pytest with >80% coverage
- TypeScript: Jest with >70% coverage
- Mock external dependencies
- Test error paths explicitly
- No test skips without issue reference

### Playwright UAT
- Critical user journey must pass
- Screenshots on failure
- Retry logic for transient issues
- Run against staging before production
- Performance metrics captured

### Type Safety
- TypeScript strict mode enabled
- Pydantic models for all API contracts
- No implicit any
- Exhaustive switch cases
- Null safety enforced

### Performance Standards
- API response <500ms p95
- Page load <3s on 3G
- Bundle size <500KB gzipped
- Memory usage stable over time
- No blocking operations in event loop

## CI/CD & Release Invariants

### Deployment Flow
1. **Staging**: Auto-deploy on push to `main`
2. **Production**: Manual dispatch with SHA tagging
3. **Verification**: `/api/version` returns deployed SHA
4. **UAT Gate**: Critical journey validation required

### GitHub Actions Invariants
- Workflow: `.github/workflows/deploy-container-apps.yml`
- Build Docker images tagged with `${{ github.sha }}`
- Update Container Apps with new image
- Set `BUILD_SHA` environment variable
- Health checks must pass before traffic switch

### Release Criteria
- All CI checks green
- Security scan passed
- Dependencies up to date
- Changelog updated
- Version bumped appropriately
- UAT Gate validated

## Repository Hygiene & Size Policy

### .gitignore Rules
- No build artifacts (node_modules, .next, __pycache__)
- No test artifacts (screenshots, coverage)
- No environment files (.env, .env.local)
- No IDE files (.vscode, .idea)
- No temporary files (*.tmp, *.log)
- No large binaries (>10MB)

### Size Guards
- CI check prevents files >10MB
- Total repo <500MB (working tree)
- Git history periodically cleaned
- Large files in Azure Storage
- Dependencies not committed

### Clean Working Tree
- No uncommitted changes in production
- No stale branches (>30 days)
- No open PRs (>7 days)
- Feature flags for partial work
- Rollback plan documented

## Security Checklist

### Secrets Management
- [ ] No hardcoded secrets
- [ ] Environment variables used
- [ ] Key Vault for production secrets
- [ ] Rotation schedule defined
- [ ] Audit trail enabled

### RBAC Verification
- [ ] Least privilege principle
- [ ] Role assignments reviewed
- [ ] Service principals scoped
- [ ] Admin actions logged
- [ ] Break-glass procedure documented

### Input Validation
- [ ] All inputs sanitized
- [ ] SQL injection prevented
- [ ] XSS protection enabled
- [ ] File upload restrictions
- [ ] Rate limiting configured

### Logging & Monitoring
- [ ] PII redacted from logs
- [ ] Correlation IDs used
- [ ] Error details sanitized
- [ ] Audit events captured
- [ ] Alerts configured

## Pre-Refactor Checklist

Before any refactoring:
1. [ ] Document current behavior
2. [ ] Write characterization tests
3. [ ] Identify breaking changes
4. [ ] Plan incremental migration
5. [ ] Update documentation first
6. [ ] Feature flag if needed
7. [ ] Rollback plan ready

## Pre-Merge Checklist

Before merging any PR:
1. [ ] CI checks all green
2. [ ] Code review approved
3. [ ] Tests added/updated
4. [ ] Documentation updated
5. [ ] Security review if needed
6. [ ] QA approval if UX changed
7. [ ] Deployment plan clear

## Troubleshooting Playbook

### Common Issues
1. **503 Service Unavailable**
   - Check Container Apps health
   - Verify environment variables
   - Review deployment logs
   
2. **Module not found**
   - Check case sensitivity
   - Verify Linux compatibility
   - Confirm dependencies installed
   
3. **Auth failures**
   - Verify AAD configuration
   - Check redirect URIs
   - Confirm token validation
   
4. **Performance degradation**
   - Check memory usage
   - Review database queries
   - Analyze network calls

### Rollback Procedure
1. Identify last known good SHA
2. Trigger deployment with SHA
3. Verify health endpoints
4. Run UAT validation
5. Document incident

## Breaking Change Protocol

For any breaking change:
1. **RFC Required**: Document in `/docs/rfc/`
2. **Migration Guide**: Step-by-step instructions
3. **Deprecation Period**: Minimum 30 days
4. **Feature Flag**: Enable gradual rollout
5. **Rollback Plan**: Tested and documented
6. **Communication**: Email stakeholders
7. **Version Bump**: Major version increment

## Acceptance Criteria for Any Change

Every change must meet ALL criteria:
- [ ] **Alignment**: Matches architecture & vision in README
- [ ] **Tiny PR**: <300 LOC, single concern
- [ ] **Actions Green**: All CI checks passing
- [ ] **UAT Gate**: Critical journey validated
- [ ] **No Workarounds**: Root cause fixed
- [ ] **Repo Hygiene**: .gitignore rules followed, no bloat
- [ ] **Security**: No degradation of security posture
- [ ] **Documentation**: Updated where needed
- [ ] **Tests**: Appropriate coverage added
- [ ] **Performance**: No degradation measured

## References

- [README.md](./README.md) - Architecture and system overview
- [/docs](./docs) - Detailed documentation
- [Team Playbook v2.3](./docs/team-playbook.md) - Operating procedures
- [Security Practices](./docs/security.md) - Security guidelines
- [Operations Guide](./docs/operations.md) - Operational procedures

---
*Last Updated: August 2025*
*Version: 1.0.0*
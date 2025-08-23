# AI-Enabled Cyber Maturity Assessment Workspace

**North-Star**: Secure, agentic assessment end-to-end system delivering evidence-driven cyber maturity assessments, gap analysis, roadmap generation, and compliance exports with enterprise-grade isolation and governance.

This is a **production-deployed** AI-enabled cyber maturity assessment platform that enables consultants to conduct comprehensive cybersecurity assessments through intelligent document analysis, automated gap identification, and strategic roadmap generation.

> **Status:** Production deployment on Azure with staging/production environments.
> Web application (Next.js) + API services (Azure Container Apps) + enterprise data layer.
> Full OIDC authentication, Cosmos DB persistence, and Azure AI integration.

---

## Quickstart (Local)

**Prereqs:** Docker Desktop (or Docker Engine), Make (optional).

```bash
# 1) Unzip the project and cd into it
cd cyber-ai-maturity-tool

# 2) Start everything locally
docker compose up --build -d

# 3) Open UIs
# API gateway docs:
#   http://localhost:8000/docs
# Orchestrator health:
#   http://localhost:8010/health
# Agents (example):
#   Documentation Analyzer: http://localhost:8111/health
#   Gap Analysis Agent:     http://localhost:8121/health
#   Initiative Generator:   http://localhost:8131/health
#   Prioritization Agent:   http://localhost:8141/health
#   Roadmap Planner:        http://localhost:8151/health
#   Report Generator:       http://localhost:8161/health
```

### Happy‑path demo
1. **Create project** (POST `/projects` in API docs) – copy the returned `project_id`.
2. **Upload a doc** (POST `/projects/{project_id}/documents`) – upload a `.txt` file.
3. **Run analysis** (POST `/projects/{project_id}/analyze`) – the orchestrator calls agents.
4. **Get report** (GET `/projects/{project_id}/report`) – returns markdown summary.

You’ll also see artifacts under `./data/projects/<project_id>/` on your host machine.

---

## Services (Ports)

- **API Gateway** (FastAPI): `:8000` – Projects, Documents, Orchestrate, Reports
- **Orchestrator** (FastAPI): `:8010` – Coordinates calls to agents
- **Agents** (FastAPI each):
  - Documentation Analyzer: `:8111`
  - Gap Analysis: `:8121`
  - Initiative Generator: `:8131`
  - Prioritization: `:8141`
  - Roadmap Planner: `:8151`
  - Report Generator: `:8161`

All services provide `/health` endpoints and FastAPI docs at `/docs`.

---

## Architecture (Production)

```mermaid
flowchart TB
    subgraph "Azure Production"
        subgraph "Web Tier"
            WEB[Next.js Web App\nApp Service]
        end
        
        subgraph "API Tier"
            API[FastAPI Backend\nContainer Apps]
            AUTH[OIDC Authentication\nAzure AD]
        end
        
        subgraph "Data Tier"
            COSMOS[(Cosmos DB\nDocument Store)]
            KV[Key Vault\nSecrets & Config]
            SEARCH[Azure AI Search\nRAG & Embeddings)]
        end
        
        subgraph "AI Services"
            OPENAI[Azure OpenAI\nGPT-4 & Embeddings]
            AGENTS[AI Orchestrator\nMulti-Agent System]
        end
    end

    WEB -->|HTTPS| API
    API -->|Managed Identity| COSMOS
    API -->|Managed Identity| KV
    API -->|RAG Queries| SEARCH
    API -->|AI Processing| OPENAI
    AGENTS -->|Document Analysis| SEARCH
    AUTH -->|JWT Tokens| WEB
    AUTH -->|Claims| API
```

**Current Architecture:**
- **Web Frontend**: Next.js on Azure App Service (standalone deployment)
- **API Backend**: FastAPI on Azure Container Apps with auto-scaling
- **Authentication**: OIDC with Azure AD integration
- **Data Persistence**: Cosmos DB with automatic indexing
- **AI Integration**: Azure OpenAI with RAG capabilities via Azure AI Search
- **Security**: Managed identities, Key Vault integration, no exposed secrets

---

## Environments & Deployment

### **Production Environment** 
- **Web**: [web-cybermat-prd.azurewebsites.net](https://web-cybermat-prd.azurewebsites.net) (App Service)
- **API**: [api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io](https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io) (Container Apps)
- **Features**: S4 features OFF, production-hardened configuration

### **Staging Environment**
- **Features**: S4 features ON, full feature testing environment
- **Purpose**: UAT and integration testing before production releases

### **Deployment Workflows**
- **Production Deployment**: `.github/workflows/deploy_production.yml` (OIDC-authenticated)
- **Staging Deployment**: `.github/workflows/deploy_staging.yml` (OIDC-authenticated)
- **Artifact Generation**: Automated web-deploy.zip creation for App Service deployments

### **Infrastructure**
- **Terraform**: `infra/` directory with complete Azure resource definitions
- **Resource Groups**: `rg-cybermat-prd` (production), `rg-cybermat-stg` (staging)
- **Container Registry**: Automated image builds with GitHub Actions integration

---

## Verification & UAT

### **Live System Verification**
```bash
# Verify production deployment
./scripts/verify_live.sh

# Comprehensive UAT workflow
./scripts/uat_s4_workflow.sh  # Staging with S4 features
```

### **Health Checks**
- **API Health**: `GET /health` - Application health and database connectivity
- **Web Health**: Root endpoint with application loading verification
- **Feature Flags**: Dynamic feature toggle verification

---

## Feature Flags & Staged Rollout

The platform implements a **staged rollout strategy** for advanced features:

- **S4 Features**: Advanced AI orchestration and multi-agent workflows
- **Staging**: S4 features enabled for full testing and validation
- **Production**: S4 features disabled for stability (can be toggled)

### **Rollback Procedures**
- **Configuration Rollback**: Toggle `NEXT_PUBLIC_API_BASE_URL` back to App Service if needed
- **Deployment Rollback**: Use prior tagged release with automated rollback scripts
- **Feature Rollback**: Disable S4 features via environment configuration

---

## Governance & Operations

### **Security Model**
- **No Secrets in Repository**: All secrets managed via Azure Key Vault
- **Managed Identities**: Service-to-service authentication without credentials
- **OIDC Authentication**: Enterprise SSO integration with Azure AD
- **Data Isolation**: Tenant-aware data access with proper authorization boundaries

### **Playbook & Agent Mode**
- **Operations Playbook**: [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) - Complete operational procedures
- **Operate with Claude (Claude-First)**: See the [Claude-First Prompt Cheatsheet](docs/team-playbook.md#appendix--claude-first-prompt-cheatsheet-v22)
- **Agent Mode**: [`docs/prompts/agent_mode_header.txt`](docs/prompts/agent_mode_header.txt) - AI assistant integration guide

### **Documentation Structure**
- **UX Roadmap v2**: [`docs/ux-roadmap-v2.md`](docs/ux-roadmap-v2.md) - Comprehensive guide for roadmap UX v2 features
- **Security Documentation**: [`docs/security/README.md`](docs/security/README.md)
- **Load Testing**: [`e2e/load/README.md`](e2e/load/README.md)
- **Production Support**: [`logs/support/appservice-prod/README.md`](logs/support/appservice-prod/README.md)

---

## Security & Compliance

- Secrets via environment variables (local) → **Azure Key Vault** (prod).
- TLS, CORS, RBAC, audit logging stubs.
- Follow‑ups to implement: GDPR deletion workflow, DPA exports, Sentinel alerts.

---

## Roadmap

- [ ] JWT auth against Azure AD (MSAL) on API gateway
- [ ] Async orchestration (Service Bus), idempotent retries
- [ ] Cosmos DB repository for projects/findings
- [ ] Azure OpenAI integration for higher-fidelity analysis
- [ ] Web UI (React + MSAL) for projects, uploads, dashboards
- [ ] Report export to **PowerPoint** and **Word** via templates

## Local development (no Docker)
```bash
make venv
make deps
cp -n .env.example .env 2>/dev/null || true
make dev
# Then open http://localhost:8000/docs
```

---

## Web Frontend Application

The project now includes a **Next.js web application** for the AI Maturity Assessment tool, focusing on cyber security for AI systems.

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+ for the backend API

### Backend API Setup

The backend API provides preset configurations and AI assistance endpoints:

```bash
# Install dependencies
cd app
pip install -r requirements.txt

# Run the API server
uvicorn api.main:app --reload
# API will be available at http://localhost:8000
```

**API Endpoints:**
- `GET /health` - Health check
- `GET /presets/{preset_id}` - Get preset configuration (e.g., "cyber-for-ai")
- `POST /assist/autofill` - AI assistance for question responses (stub)
- `POST /assessments` - Create new assessment
- `GET /assessments/{id}` - Get assessment with answers
- `POST /assessments/{id}/answers` - Save/update answer
- `GET /assessments/{id}/scores` - Compute weighted scores
- `POST /uploads/sas` - Generate SAS token for evidence upload (501 if not configured)

### Frontend Setup

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
# Frontend will be available at http://localhost:3000
```

### Current Features

1. **Preset Management**: Load and display the "Cyber for AI" security assessment preset
2. **Assessment Workspace**: Navigate through assessment pillars and questions
3. **AI Assist**: Stub integration for AI-powered question assistance
4. **Navigation**: Top navigation bar for easy access to Dashboard, New Assessment, and Draft

### Available Pages

- `/` - Dashboard (landing page)
- `/signin` - Demo authentication page for user login
- `/engagements` - Protected page showing user's security assessments (requires authentication)
- `/new` - Create new assessment and load preset
- `/assessment/draft` - Assessment workspace with pillar navigation and questions

### Development Workflow

1. Start the backend API:
   ```bash
   cd app && uvicorn api.main:app --reload
   ```

2. In another terminal, start the frontend:
   ```bash
   cd web && npm run dev
   ```

3. Open http://localhost:3000 in your browser

### Authentication Quickstart (Sprint S1)

The application now includes demo authentication for accessing protected pages:

1. **Access protected page**: Navigate to http://localhost:3000/engagements
2. **Get redirected**: If not signed in, you'll be redirected to `/signin`
3. **Sign in**: Enter any email address (e.g., `demo-user@example.com`) and click "Sign in"
4. **View engagements**: Access the protected engagements page with role-based access control

**Demo Features:**
- Server-Side Rendering (SSR) guards protect routes
- Role-based access: Member, LEM, or Admin roles required for `/engagements`
- Structured logging with correlation IDs for all requests
- Mock engagement data with status badges and role chips
- Comprehensive error handling and loading states

### Phase 2 Features (Implemented)

1. **Assessment Persistence**
   - SQLite database for assessments and answers
   - UUID-based assessment tracking
   - Answer upsert functionality (create or update)

2. **Scoring System**
   - Per-pillar scoring (average of question levels)
   - Weighted overall score calculation
   - Gate enforcement (e.g., governance < 2 caps overall at 3.0)
   - Visual scoring with radar chart
   
   **Scoring Algorithm:**
   - Pillar score = average of answered questions (1-5 scale)
   - Overall score = weighted average of pillar scores
   - Pillars with no answers are excluded from overall calculation
   - Gates can cap the overall score (e.g., if governance < 2, overall is capped at 3)

3. **Evidence Upload**
   - Optional Azure Blob Storage integration
   - SAS token generation with configurable TTL
   - Graceful 501 fallback if not configured
   - Direct browser-to-storage uploads
   - Evidence linked to questions (client-side for now)

### Next Steps

- [x] Implement assessment data persistence (save responses)
- [x] Add file upload capabilities for evidence documents
- [x] Integrate with Azure Storage for document management
- [ ] Implement real AI assistance using Azure OpenAI
- [x] Add assessment scoring and gap analysis
- [ ] Generate downloadable reports (PDF/Word)
- [ ] Add user authentication with Azure AD
- [ ] Create assessment history and dashboard views
- [ ] Persist evidence URLs with assessments in database

### S4 Features (Sprint 4)

Sprint S4 introduces workshop management, NIST CSF 2.0 framework integration, and chat-based assessment assistance:

#### Workshop Management Routes
```
POST /workshops                      # Create workshop session
GET  /workshops/{id}                 # Get workshop details
POST /workshops/{id}/consent         # Grant/revoke participant consent
GET  /workshops/{id}/consent         # Check consent status
POST /workshops/{id}/minutes         # Generate draft meeting minutes
PUT  /workshops/{id}/minutes         # Update draft minutes
POST /workshops/{id}/minutes/publish # Publish immutable minutes
GET  /workshops/{id}/minutes/{version} # Retrieve minutes version
```

#### NIST CSF 2.0 Integration Routes  
```
GET  /csf/functions                  # List 6 CSF functions (Govern, Identify, etc)
GET  /csf/functions/{id}/categories  # Categories for specific function  
GET  /csf/categories/{id}/subcategories # Subcategories with examples
POST /assessments/{id}/csf/grid      # Save grid-based assessment data
GET  /assessments/{id}/csf/gaps      # Generate gap analysis report
GET  /csf/seed                       # Local development CSF test data
```

#### Chat Command Routes
```  
POST /chat/assess                    # AI-assisted assessment questions
POST /chat/evidence                  # Evidence analysis and suggestions
POST /chat/gaps                      # Gap analysis and recommendations
POST /chat/shell                     # Administrative shell commands (Admin only)
```

**Local CSF Seed Data Usage:**
For development and testing, the system provides local CSF 2.0 seed data:
```bash
# Load CSF development data
curl http://localhost:8000/csf/seed

# Example response includes all 6 functions with categories and subcategories
# Supports offline development without external NIST dependencies
```

**Comprehensive E2E Tests:**
Run complete end-to-end tests covering S4 features:
```bash
# Run S4 workshop tests  
cd web && npm run e2e:workshops

# Run CSF grid assessment tests
cd web && npm run e2e:csf

# Run chat command tests (requires Admin role)
cd web && npm run e2e:chat

# Run all S4 features
cd web && npm run e2e:s4
```

**Service Bus Fallback Behavior:**
S4 features implement graceful degradation when Azure Service Bus is unavailable:
- **Workshops:** Direct HTTP calls with async task queuing fallback
- **Minutes:** Synchronous processing with background retry mechanisms  
- **CSF Processing:** Local caching with periodic refresh attempts
- **Chat Commands:** Immediate response mode with best-effort async tasks

### Configuration

#### Frontend Configuration

The web app uses environment variables for configuration:

- `NEXT_PUBLIC_API_BASE_URL` - Backend API URL (default: http://localhost:8000)

Create `web/.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### Backend Configuration

For evidence uploads, create `app/.env`:
```env
# Azure Storage Configuration (optional)
AZURE_STORAGE_ACCOUNT=your-storage-account
AZURE_STORAGE_KEY=your-storage-key
AZURE_STORAGE_CONTAINER=docs
UPLOAD_SAS_TTL_MINUTES=15
```

**Security Guidelines for Azure Storage:**
- **SAS Token Permissions:** Generate write-only SAS tokens with least-privilege permissions. Use only `wca` (write, create, add) for client uploads. Avoid granting list (`l`), read (`r`), or delete (`d`) permissions.
- **Short TTL:** Use a short time-to-live (TTL) for SAS tokens (10-15 minutes recommended) to minimize exposure window.
- **Key Rotation:** Implement periodic rotation of storage account keys to enhance security.
- **Never Log SAS Tokens:** Ensure SAS tokens are never logged in application logs or error messages to prevent unauthorized access.
- **Configure Storage CORS:** Restrict CORS origins to specific domains (e.g., `http://localhost:3000` for development) and always require HTTPS in production.
- **Content Validation:** Implement file type and size validation on both client and server sides to prevent malicious uploads.
- **Size Limits:** Enforce upload size limits to prevent storage abuse and potential denial-of-service attacks.

If Azure Storage is not configured, the `/uploads/sas` endpoint returns HTTP 501.

### Local Development with Azurite

For local evidence upload testing without Azure Storage:

1. **Install and start Azurite:**
   ```bash
   npm install -g azurite
   azurite --silent --location ./azurite-data --blobPort 10000
   ```

2. **Configure local storage in `app/.env`:**
   ```env
   AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"
   AZURE_STORAGE_CONTAINER=evidence
   UPLOAD_SAS_TTL_MINUTES=15
   ```

3. **Create container:**
   ```bash
   az storage container create --name evidence --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"
   ```

### Running Both Services Together

1. **Terminal 1 - Backend:**
   ```bash
   cd app
   pip install -r requirements.txt
   uvicorn api.main:app --reload
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd web
   npm install
   npm run dev
   ```

3. **Terminal 3 - Azurite (optional for uploads):**
   ```bash
   azurite --silent --location ./azurite-data
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Azurite Explorer: Use Azure Storage Explorer to view local blobs

### Workflow Example

1. **Create New Assessment**
   - Navigate to http://localhost:3000/new
   - Click "Load preset" to load the Cyber for AI preset
   - Click "Continue" to create assessment

2. **Answer Questions**
   - Select a pillar from the left sidebar
   - For each question:
     - Select a maturity level (1-5)
     - Click "Save" to persist the answer
     - Optionally upload evidence files

3. **View Scores**
   - Click "Compute Scores" button
   - View pillar scores table
   - See radar chart visualization
   - Check overall weighted score
   - Note any gate warnings (e.g., governance requirements)

### Database

The application uses SQLite for persistence:
- Database location: `app/app.db`
- Auto-created on first run
- Contains assessments and answers tables

---

## Deploy with ACR Admin (Temporary)

This section describes how to deploy the application to Azure Container Apps using ACR admin credentials as a temporary measure.

### Prerequisites

- Azure CLI (`az`) installed and configured
- Docker installed and running
- Access to the Azure subscription

### Deployment Steps

1. **Make scripts executable and run deployment:**
   ```bash
   chmod +x scripts/deploy_admin.sh && ./scripts/deploy_admin.sh
   ```

2. **Get the deployed application URLs:**
   ```bash
   scripts/print_urls.sh
   ```

3. **Run smoke test to verify API health:**
   ```bash
   scripts/smoke.sh
   ```

⚠️ **Important:** Don't re-apply Terraform that touches Container Apps while using admin credentials, as it will wipe the runtime registry credentials.

### Switch to Managed Identity (Recommended)

Once RBAC permissions are granted, switch from ACR admin credentials to Managed Identity:

1. **Grant required roles to the User-Assigned Identities:**
   
   For the API identity:
   - AcrPull (on ACR)
   - Storage Blob Data Contributor (on Storage Account)
   - Storage Blob Data Delegator (on Storage Account)
   - Key Vault Secrets User (on Key Vault)
   
   For the Web identity:
   - AcrPull (on ACR)

2. **Enable Managed Identity for storage in the API:**
   ```bash
   az containerapp update -g rg-aaa-demo -n api-aaa-demo --set-env-vars USE_MANAGED_IDENTITY=true
   ```

3. **Remove admin credentials from Container Apps:**
   ```bash
   az containerapp registry remove -g rg-aaa-demo -n api-aaa-demo --server acraaademo9lyu53.azurecr.io
   az containerapp registry remove -g rg-aaa-demo -n web-aaa-demo --server acraaademo9lyu53.azurecr.io
   ```

4. **Disable ACR admin access:**
   ```bash
   az acr update -n acraaademo9lyu53 --admin-enabled false
   ```

After these steps, the Container Apps will use their Managed Identities to pull images from ACR and the API will use its identity for Azure Storage operations.

---

## Verify Live Environment

After deployment, verify the environment health and configuration:

```bash
# Run comprehensive verification
scripts/verify_live.sh

# Check specific components
scripts/verify_live.sh --api-only
scripts/verify_live.sh --web-only
scripts/verify_live.sh --storage-only
```

**Verification Checks:**
- ✅ API health and authentication
- ✅ Web application accessibility
- ✅ Storage SAS token generation
- ✅ Database connectivity
- ✅ CORS configuration
- ✅ Security headers

**Common Issues:**
- **SAS 501:** Storage not configured - check Azure Storage connection
- **CORS errors:** Verify allowed origins in Container App settings
- **Auth failures:** Ensure JWT configuration matches between services

---

## Production Hardening & Governance

Enterprise-grade security, compliance, and operational excellence:

- **Security Gates**: Secret scanning (TruffleHog), dependency analysis (Trivy), IaC security (Checkov)
- **ABAC Authorization**: Engagement-scoped access control for sensitive resources and MCP tools  
- **Incident Response**: AI-specific playbooks for hallucination, data leakage, prompt injection scenarios
- **Support Bundles**: Automated diagnostic collection with PII anonymization for troubleshooting
- **Access Reviews**: Scheduled compliance reporting and membership auditing by engagement
- **Release Automation**: Auto-generated release notes from conventional commits and PR labels
- **Performance Budgets**: Continuous regression testing with configurable thresholds

**Governance Verification**: Run `./scripts/verify_live.sh --governance` to test security gates, incident response, and support bundle generation.

---

## Staging Deploy

Quick staging deployment using GitHub Actions workflow:

### 1. Set Repository Variables
Go to **Settings → Secrets and variables → Actions → Variables** and configure:

**App Service Option:**
- `GHCR_ENABLED=1`
- `STAGING_URL=https://your-staging-app.azurewebsites.net`

**Container Apps Option:**
- `GHCR_ENABLED=1`
- `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`
- `ACA_RG`, `ACA_ENV`, `ACA_APP_API`, `ACA_APP_WEB`

### 2. Run Deployment
Navigate to **Actions → Deploy Staging → Run workflow**

### 3. Verify Staging
```bash
./scripts/verify_live.sh --staging
```

**Documentation**: See `/docs/staging-env.md` for complete setup guide.

**Helper Tools:**
- Diagnostics: `./scripts/diagnose_staging.sh`
- Set variables: `./scripts/gh_set_repo_vars.sh`

---

## Production Deployment
   # Create resource group
   az group create -n $RESOURCE_GROUP -l eastus2
   
   # Deploy with staging configuration
   scripts/deploy_mvp.sh --env staging
   ```

3. **Configure secrets:**
   ```bash
   # Set required secrets
   az keyvault secret set --vault-name kv-aaa-staging \
     --name storage-key --value "$(az storage account keys list \
     -n staaastaging --query '[0].value' -o tsv)"
   ```

4. **Deploy applications:**
   ```bash
   # Build and deploy
   scripts/build_acr_tasks.sh
   scripts/deploy_containerapps.sh
   ```

5. **Verify deployment:**
   ```bash
   scripts/verify_live.sh --env staging
   ```

**Staging Features:**
- Isolated resource group
- Separate storage account
- Independent Key Vault
- Test data isolation
- Lower SKU tiers for cost optimization

---

## Team Playbook / Cursor

- Read the playbook: [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md)  
- Prepend this header to any Claude Code task to enforce agents and RunCards: [`docs/prompts/agent_mode_header.txt`](docs/prompts/agent_mode_header.txt)
- Cursor uses `scripts/cursor_safe_run.sh` to print STATUS BLOCKS and query PRs (no raw echo with quotes).

---

## Build & Deploy via ACR Tasks (no Docker Desktop)

This section describes how to build container images using Azure Container Registry (ACR) Tasks, eliminating the need for Docker Desktop.

### Build both images:

```bash
scripts/build_acr_tasks.sh
```

This builds the API and Web images directly in Azure using ACR Tasks. The Web image can be built with or without the `API_URL` environment variable.

### Deploy/update Container Apps (prints URLs):

```bash
scripts/deploy_containerapps.sh
```

This script:
- Enables ACR admin credentials temporarily
- Creates or updates both API and Web Container Apps
- Prints the deployed API_URL and WEB_URL

### If web was built before API_URL was known, rebuild web with baked URL:

```bash
scripts/rebuild_web_with_api.sh
```

This rebuilds the Web image with the API URL baked in at build time (for Next.js's `NEXT_PUBLIC_API_BASE_URL`), then updates the Web Container App.

**Note:** This deployment uses temporary ACR admin credentials. Follow the "Switch to Managed Identity" section above to transition to a more secure authentication method using Managed Identities with proper RBAC roles (AcrPull for image access, Storage Blob roles for data, and Key Vault role for secrets).

## Monitoring & Alerts

Production monitoring setup with Log Analytics KQL queries and automated alerting:

- **Health Monitoring**: Application health checks and availability tracking
- **Performance Monitoring**: Response times, error rates, resource utilization
- **Security Monitoring**: Authentication failures and suspicious activity detection
- **Business Metrics**: User engagement and assessment completion rates

**Documentation**: See `/docs/monitoring-alerts.md` for complete setup guide.

**Key Dashboards**:
- Executive: Uptime, performance trends, incident counts
- Technical: System health, resource usage, security events
- Business: User engagement, feature adoption, satisfaction

---

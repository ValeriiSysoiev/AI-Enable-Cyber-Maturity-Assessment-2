# Cyber AI‑Enabled Maturity Assessment Tool (MVP)

This is a **deployable scaffold** for Deloitte’s Cyber AI‑Enabled Maturity Assessment solution.
It includes an **API gateway**, **AI Orchestrator**, and **specialized AI agents** that implement
a simple end‑to‑end flow: upload documents → analyze → identify gaps → propose initiatives →
prioritize → produce a roadmap → generate a report.

> **Status:** MVP skeleton that runs locally with Docker Compose and can be extended/deployed to Azure.
> Uses FastAPI for services and simple HTTP orchestration between agents.
> Azure OpenAI, Cosmos DB, Service Bus, Azure AD, and Sentinel hooks are stubbed with clear TODOs.

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

## Architecture (MVP)

```mermaid
flowchart LR
    UI[Consultant (API Docs / future Web UI)]
    API[API Gateway\n(FastAPI)]
    ORCH[AI Orchestrator\n(FastAPI)]
    DOC[Documentation Analyzer]
    GAP[Gap Analysis Agent]
    INIT[Initiative Generator]
    PRI[Prioritization Agent]
    PLAN[Roadmap Planner]
    REP[Report Generator]
    STORE[(Local Files\n→ future Cosmos DB)]

    UI -->|HTTP| API -->|/analyze| ORCH
    ORCH --> DOC --> GAP --> INIT --> PRI --> PLAN --> REP --> STORE
```

> The MVP uses **HTTP fan‑out/fan‑in** calls for simplicity. In production,
> swap to **Azure Service Bus** for async orchestration (adapter hooks included).

---

## Azure Deployment (Outline)

- **Infra as Code:** see `infra/` (Bicep stubs) and `azure.yaml` (azd skeleton).
- **Images:** GitHub Actions workflow in `.github/workflows/deploy.yml` shows the shape.
- **Identity:** Configure Azure AD app registrations, then enable JWT auth in API gateway.
- **Data:** Replace local file persistence with **Cosmos DB** (DAO placeholders included).
- **AI:** Wire **Azure OpenAI** into agents (endpoints/keys via Key Vault).

> See `docs/DEPLOY-AZURE.md` for step‑by‑step setup (placeholders and TODOs).

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

3. **Access the application:**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs

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

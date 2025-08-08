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
- [ ] Azure OpenAI integration for higher‑fidelity analysis
- [ ] Web UI (React + MSAL) for projects, uploads, dashboards
- [ ] Report export to **PowerPoint** and **Word** via templates
```

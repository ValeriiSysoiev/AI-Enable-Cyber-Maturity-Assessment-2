# Team Playbook — Sprint Execution (Autonomous Mode) v1.1

## 1) Purpose
Unify planning and execution so the Project Conductor (Claude Code) can run a sprint end-to-end in **Autonomous Mode**: understand scope → plan tasks → coordinate sub-agents (backend, frontend, infra, security, QA) → open small PRs → land tests → pass demo.

## 2) Roles & RACI (execution-focused)
- **Product Owner (PO)** — vision/scope/acceptance, secrets/config provisioning. Approves sprint demo.
- **Project Conductor (Claude Code)** — Planner+Executor: discover repo, WBS, create branches, drive small PRs (<300 LOC) with tests, keep CI green, post single summary + RunCard.
- **Frontend** — Next.js/SSR route guards, pages, a11y, Playwright e2e.
- **Backend/Orchestrator** — API/RBAC/integration; unit/integration tests.
- **Infra & AzureOps** — IaC/workflows, OIDC, health/readyz, Verify Live.
- **Security Reviewer** — authN/Z, CORS/CSRF, headers (CSP), secrets; CI gates; SECURITY.md.
- **Test & Release** — CI green, Verify Live wiring, artifacts, release notes.
- **Docs/ADR** — ADRs, runbooks, summaries, rollback notes.
- **QA (CodeRabbit)** — PR quality, a11y/test completeness, <300 LOC enforcement.

## 3) Prompt types & when to use
- **Master Sprint Execution Prompt (primary)** — plan + execute a sprint without step-by-step confirmations (bounded).
- **Role micro-prompts (fallback)** — deep dive for a specific sub-agent (backend/frontend/infra/security/QA).

## 4) Sprint protocol (default)
1) **Preflight** (discovery, env, guardrails)  
2) **Branch & Issues** (WBS, small PRs)  
3) **Obs-first** (health/readyz, logging, correlation IDs)  
4) **Business logic** (backend/frontend)  
5) **Tests & CI** (unit/integration/e2e)  
6) **Verify Live** (bounded, fail-fast)  
7) **Docs** (ADRs/runbooks), **RunCard**, single summary

## 5) Quality gates (non-negotiable)
- PRs **< 300 LOC**, with tests/screenshots/rollback notes  
- Conventional commits; CodeRabbit approval required  
- Security: CORS allowlist, CSRF on callbacks, security headers (CSP), no secrets in code  
- A11y: basic checks on critical screens  
- Observability: every exercised response echoes `X-Correlation-ID`; structured logs

## 6) Secrets & config policy
No plaintext secrets in repo/CI. Use `.env.example` and Key Vault/Managed Identity in cloud. Mocks for CI.

## 7) Blockers & escalation
**Proceed by default.** Pause only for missing cloud IDs/permissions that block runtime auth, repo permission errors, or CI environment limits. Post a short "PO needed" list.

## 8) Sprint deliverables (definition of done)
Working feature increments with tests, CI green, **Verify Live** passing, updated docs, and a concise sprint summary + RunCard.

## 9) Master Sprint Execution Prompt (template)
**SYSTEM ROLE:** Project Conductor (Planner+Executor) for **[Release] / [Sprint]**  
**MODE:** Autonomous. Do **not** ask to proceed at each step; continue until sprint ACs pass or a blocking secret/config is missing.

**CONTEXT**  
- North Star, repo root, sprint scope, working agreements (PR <300 LOC, tests, no secrets, a11y, CI green)

**PHASE 0 — DISCOVERY** (repo tree, stacks)  
**PHASE 1 — BRANCH & ISSUES**  
**PHASE 2+ — IMPLEMENTATION PRs** (obs → backend → frontend → coverage)  
**ACROSS PRs** (tests, screenshots/logs, rollback, conventional commits, CodeRabbit)  
**BLOCKERS POLICY** (list PO items)  
**OUTPUTS** (WBS, PR links, test matrix, Verify output, blockers)

## 10) Agent roster & ops agents
- Project Conductor, Planner, Frontend, Backend/Orchestrator, Infra & AzureOps, Security Reviewer, Test & Release, Docs/ADR, QA (CodeRabbit)
- Ops/Deployment: InfraOps, WebPackager, AppServiceConfigurator, Deployer, LogDoctor, VerifierQA, DocsADR
- API/ACA cutover: GHCR Builder, ACAProvisioner/ACAConfig, CosmosOps, WebOps, SeedOps

## 11) Agent-mode header (quick start)
See: `docs/prompts/agent_mode_header.txt` to enforce agent traces and RunCards on any task.
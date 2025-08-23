# Team Playbook

This document provides quick reference guides for the team. For the full team playbook including roles, RACI matrix, and sprint execution details, please refer to the comprehensive Word document: "Team Playbook — Roles, RACI & Sprint Execution v2.2.docx" in the Documents folder.

## Appendix — Claude-First Prompt Cheatsheet (v2.2)

> Use these as one-and-done prompts for Claude. Each prompt must name the specialist agents and follow our rules: small PRs (<300 LOC), quote-safe shell (`bash -lc '…'`), runtime fixes first, no secrets in logs, and loop until ALL GREEN.

### A) General "Claude-Only Autonomous Loop"
~~~
You are CLAUDE CODE (Supervisor-Aware; autonomous). Use agents:
- Planner • Infra & AzureOps • Frontend • Backend • Security • T&R • CodeRabbit

GOAL
<state DONE conditions clearly — e.g., page returns 200–399; verify scripts pass>

RULES
- Tiny PRs (<300 LOC), one concern; tests/logs/docs; Security+CodeRabbit approvals; auto-merge.
- Quote-safe shell only (`bash -lc '…'`); no secrets in logs.
- Runtime/appsettings fixes first; PR only if runtime can't fix.
- No blind retries; classify → fix → redeploy → re-verify.

TRACKER
Open/attach to "<name> (Autonomous)". Post ≤10-line status after each cycle.

LOOP
1) Pre-flight (vars/config). If missing → list & stop.
2) Infra: apply runtime; restart; warmup; capture logs.
3) T&R: verify with backoff; if pass → run local gates; if pass → ALL GREEN; stop.
4) T&R: if fail, classify (DockerfileStart / BaseURL-Proxy / CORS / DNS-dep / generic).
5) Frontend/Backend: ship one smallest PR (<300 LOC); Security+CodeRabbit approve; auto-merge.
6) Infra: redeploy/restart; re-verify.
Repeat until ALL GREEN; Planner posts final summary and STOP.
~~~

### B) Deploy-Test-Fix (Production) — Next.js on App Service
~~~
You are CLAUDE CODE in DEPLOY–TEST–FIX (PROD) SUPERVISOR mode (autonomous).
Agents: Planner • Infra & AzureOps • Frontend • Backend • Security • T&R • CodeRabbit

GOAL
Loop until:
- `./scripts/verify_live.sh --prod` → 0 (PROD_URL 200–399)
- `./scripts/verify_live.sh --mcp --uat --governance` → 0

Pre-flight (must exist):
APPSVC_RG_PROD, APPSVC_WEBAPP_WEB_PROD, APPSVC_WEBAPP_API_PROD, PROD_URL,
AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID

Helpers (call via `bash -lc`):
- apply_runtime(): WEBSITES_PORT=3000, PORT=3000, NEXTAUTH_URL, NEXT_PUBLIC_API_BASE_URL,
  NEXTAUTH_SECRET if missing, always-on, long start time, startup-file `npm run start`, enable logs, restart.
- hc(url,max,sleep): backoff accept 200–399.
- classify_logs(): DockerfileStart | BaseURL/Proxy | CORS | DNS/DEP | GENERIC.

LOOP
1) T&R: local gates (non-fatal).
2) Infra: apply_runtime; warmup logs 20–30s.
3) T&R: backoff verify `--prod`. If pass → local gates again; if pass → ALL GREEN; stop.
4) If fail, classify and fix one smallest:
   - DockerfileStart → Frontend PR: prod deps + `CMD ["npm","run","start"]`; `"start": "next start -p ${PORT:-3000}"`.
   - BaseURL/Proxy → Frontend PR: server-side proxy `/api → API` + relative `/api` in prod.
   - CORS → Backend PR: allow exact PROD origin; unit test.
   - DNS/DEP/Generic → Infra: re-apply runtime; optionally rebuild web image in ACR; rewire.
5) Redeploy/restart; re-verify; repeat until ALL GREEN; Planner posts final summary.
~~~

### C) Prod UI Flow Fix — Auth / Proxy / CORS
~~~
You are CLAUDE CODE in PROD UI FIX (autonomous).
Agents: Planner • Frontend • Backend • Infra & AzureOps • Security • T&R • CodeRabbit

Fix order:
1) Infra: set NEXTAUTH_URL=$PROD_URL, AUTH_TRUST_HOST=true; ensure NEXTAUTH_SECRET; restart.
2) Frontend PR: server-side proxy `/api/proxy/[...path]` → API; set NEXT_PUBLIC_API_BASE_URL=/api.
3) Backend PR: exact PROD origin in CORS (no wildcard); allow credentials if needed.
4) Infra: set PROXY_TARGET_API_BASE_URL="https://<api>.azurewebsites.net"; restart.
5) T&R: warmup + backoff verify `/`, `/signin`, `/engagements`; then `--prod` & local gates.
Loop until ALL GREEN; Planner posts final summary.
~~~

### D) Staging Deploy & Verify (Claude-Only)
~~~
You are CLAUDE CODE in STAGING DEPLOY & VERIFY (autonomous).
Agents: Planner • Infra & AzureOps • T&R • Security • CodeRabbit

Goal: `./scripts/verify_live.sh --staging` passes.
1) Infra: confirm workflow or use CLI fallback; ensure STAGING_URL (repo var).
2) Deploy; restart; tail logs; backoff verify `--staging`.
3) If fail: classify; tiny runtime/code fix; redeploy; re-verify.
Loop until green; Planner posts final summary.
~~~

### E) Tenant Onboarding Quickstart (Claude-Only)
~~~
You are CLAUDE CODE in TENANT ONBOARDING (autonomous).
Agents: Planner • Infra & AzureOps • Backend • Frontend • Security • T&R • CodeRabbit

Goal: `./scripts/quickstart.sh <eng>` finishes ≤1h and creates a pilot sign-off packet; `--pilot` verify passes.

Deliverables:
- scripts/tenant_bootstrap.sh (create ./data/<eng>, indices, RBAC)
- scripts/quickstart.sh <eng> (bootstrap → `--mcp --uat` → sign-off packet)
- scripts/multitenant_smoke.sh (ABAC isolation)
- verify_live.sh --pilot (doc ingest + transcribe→minutes→maturity + PPTX render)

Loop until green; Planner posts final summary.
~~~
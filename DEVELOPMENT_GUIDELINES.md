# DEVELOPMENT GUIDELINES — AI-Enabled Cyber Maturity Assessment

> **Mandatory reading**  
> Before you start **any** change — and **before every subsequent commit** in an ongoing change — re-read:
> - `README.md` (architecture & intent)  
> - `/docs/*` (operations, security, deployments, UAT)  
> - `/DEVELOPMENT_GUIDELINES.md` (this file)

These guidelines are **non-negotiable**. They encode our long-term architecture, security posture, and delivery discipline so every change improves — not erodes — the system.

## Quick Navigation

[Core Principles](#0-core-principles) | [Architecture](#1-architecture-baseline-do-not-diverge) | [Non-negotiable Rules](#2-non-negotiable-rules-violations-break-prod) | [PR Rules](#3-change-discipline--pr-rules) | [Testing](#4-testing--quality-bars) | [CI/CD](#5-cicd--release-invariants) | [Repo Hygiene](#6-repository-hygiene--size-policy) | [Security](#7-security-checklist-run-for-every-change) | [Checklists](#8-pre-refactor--pre-merge-checklists) | [Troubleshooting](#9-troubleshooting-playbook-what-to-verify) | [Breaking Changes](#10-breaking-change-protocol) | [Acceptance Criteria](#11-acceptance-criteria-for-any-change)

---

## 0) Core Principles

1. **Architecture-first.** The architecture in `README.md` and `/docs` is the source of truth. Align every change to it.
2. **No hacks / no workarounds.** Fix **root causes** only. Temporary band-aids are not allowed.
3. **Tiny PRs.** ≤ **300 LOC**, **single concern**, audited with tests, docs, and logs.
4. **Actions is canonical.** All deploys go through GitHub Actions; green checks are required.
5. **UAT Gate after every rollout.** The critical journey **must** pass:
   - AAD sign-in → engagements list → create/open engagement → `/new` preset → sign-out

---

## 1) Architecture Baseline (do not diverge)

### System Components (Production)

- **Web (Next.js 14)** → **Azure Container Apps**  
  Host (prod): `https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`  
  Stack: TypeScript, React 18, App Router, Tailwind

- **API (FastAPI)** → **Azure Container Apps**  
  Host (prod): `https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`  
  Stack: Python 3.11+, async, Pydantic

- **Auth (NextAuth)** → **Azure AD (Entra ID) only in production**  
  No demo/credentials provider in prod. Role model: Admin / Consultant / Client.

- **Proxy** → Web calls API via **`/api/proxy/*`** (no direct API hostnames in the UI)

### Invariants we prove on every release

- **Health endpoints**  
  Web: `**/health**` • API: `**/health**`

- **Version proof**  
  Web: `**/api/version**` returns the **deployed SHA** and must equal `${{ github.sha }}` post-deploy.

- **Actions behaviors (not file names)**  
  - **Staging**: auto-deploy on **push** to `main`  
  - **Production**: **manual dispatch** builds a web image **tagged with `${{ github.sha }}`**, wires it, sets the build SHA, and **proves** `/api/version == sha`  
  - Deployments view shows the latest green run

- **UAT Gate**  
  Must pass after every production rollout (staging first, then prod-safe).

---

## 2) Non-negotiable Rules (violations break prod)

### 2.1 Authentication & Authorization (Prod = AAD only)

- Only the **Azure AD** provider is active in prod.  
  No demo/credentials fallback. No silent auto-login that bypasses AAD.
- `NEXTAUTH_URL` must equal the **public Container Apps host**.  
  **Never** emit `0.0.0.0:3000` or `localhost` in prod flows (signin/signout/callbacks).
- Reply URLs for the active host must exist in the **AAD app registration**  
  (e.g., `/api/auth/callback/azure-ad` & `/api/auth/callback/aad`).
- **Sign-out** must clear app cookies/session and land on `/signin` at the Container Apps host.

### 2.2 Proxy invariants

- Client → `/api/proxy/*` → Web forwards to API with identity/correlation IDs.  
  No direct API hostnames in browser code.
- Proxy **must not** return success when the API fails; surface real errors; log correlation IDs.

### 2.3 Imports & case-sensitivity

- CI runs on Linux: **imports are case-sensitive**.
- Preferred app-wide alias: **`@/…`** with `baseUrl: "."` in `tsconfig.json`.  
  Keep relative imports **shallow**; avoid deep `../../../…` chains.
- Fix **every** case mismatch before merging.

### 2.4 IDs & storage

- Use **consistent ID conventions** that round-trip between web & API (e.g., `engagement-…`).  
  Do **not** introduce client-only synthetic IDs that the API cannot fetch.
- Cosmos DB for documents; Azure Storage for blobs.  
  No local file storage in containers.

### 2.5 Security posture

- Never log secrets, tokens, PII, or cookies.  
  Secrets live in env/Key Vault; use Managed Identity wherever feasible.
- Tight CORS in prod; no wildcards.  
  Validate inputs; deny path traversal; prevent injection (SQL/NoSQL/command/template).  
  Add CSRF protections where applicable.  
  Enforce server-side RBAC on admin endpoints.  
  Rate-limit and bound payload sizes; redact sensitive values in logs.

---

## 3) Change Discipline & PR Rules

**Every PR must:**

1. Be **single-concern**, ≤ **300 LOC** (generated files excluded).  
2. Include **tests** that would have caught the defect.  
3. Update **docs** (README or `/docs/*`) when behavior/UX/ops change.  
4. Pass all **CI** checks (no bypassing policies or gates).  
5. Undergo **Security review** for auth/data/infra changes; **QA** review for UX changes.  
6. Keep **auditability** intact (clear title, rationale, links to artifacts & runs).

> **Never** merge red checks. **Never** skip tests. **Never** weaken guards to “get it out.”

---

## 4) Testing & Quality Bars

- **Unit & Integration**  
  - Python: pytest, meaningful coverage with error-path tests  
  - TypeScript: Jest/VTU, strict types (no implicit `any`), null-safety upheld

- **Playwright UAT**  
  Critical journey must pass; capture screenshots/videos on failure; run on staging before prod; retry only for demonstrable flake.

- **Performance**  
  Watch bundle size, critical route cost, and API p95; remove N+1; add safe caches where architecturally appropriate.

- **Reliability**  
  Timeouts, retry/backoff, idempotency on creates; consistent error envelopes; graceful degradation; correlation IDs end-to-end.

- **Accessibility (WCAG 2.1 AA)**  
  Semantics, labels, focus order, keyboard nav, contrast; cross-browser smoke set.

---

## 5) CI/CD & Release Invariants

- **Staging**: push to `main` → CI → deploy → UAT Gate (staging).  
- **Production**: dispatch → build web **image tag=`${{ github.sha }}`** → wire → set build SHA → **prove** `/api/version == sha` → UAT Gate (prod-safe).  
- Remove/disable any pipelines targeting deprecated **App Service API**; API target is **Container Apps** only.

---

## 6) Repository Hygiene & Size Policy

- `.gitignore` must block: `.next`, `dist`, `out`, `node_modules`, `__pycache__`, coverage, screenshots/videos, large logs/dumps, IDE/OS files.  
- CI size guard: block files **> 10 MB** (unless LFS/approved).  
- Keep working tree **lean** (< ~500 MB as a guideline).  
- Use external storage (or LFS if architecturally justified) for large versioned assets.  
- Remove legacy/duplicate docs; if you must retain context, move to `/docs/archive/` with a dated rationale.

---

## 7) Security Checklist (run for **every** change)

- [ ] Secrets only in env/Key Vault; never in code, tests, or logs  
- [ ] Server-side RBAC enforced on admin endpoints  
- [ ] Inputs validated; injection & traversal denied; CORS tight  
- [ ] PII redacted; correlation IDs in logs  
- [ ] Rate limits & payload bounds enforced; error envelopes sanitized

---

## 8) Pre-refactor & Pre-merge Checklists

**Pre-refactor (discovery)**  
- [ ] Scan for existing implementations to avoid duplication  
- [ ] Map imports/callers; plan safe moves; fix references  
- [ ] Confirm related docs/env keys; plan migration if contracts shift

**Pre-merge (verification)**  
- [ ] Types & lints pass; no case-sensitivity issues  
- [ ] UAT Gate passes on staging; Actions green  
- [ ] Docs/README updated; impact documented  
- [ ] No workaround remains; **root cause** fixed

---

## 9) Troubleshooting playbook (what to verify)

- **Sign-in**: `/api/auth/providers` shows **azure-ad** only; click AAD triggers Microsoft round-trip; callback lands on our host.  
- **Sign-out**: app cookies cleared; landing on `/signin`; no auto-login without explicit AAD flow.  
- **Presets/Assessments**: API list/get/upload 2xx; create→get 201→200; no 503 via proxy.  
- **Engagements/Admin**: list 2xx; `/api/proxy/admin/status` returns 200 for Admin.

---

## 10) Breaking-change protocol

- **RFC first** (`/docs/rfc/…`) + migration guide  
- Deprecate before removal; feature-flag gradual rollout  
- Extended UAT + tested rollback plan  
- Communicate widely; version bump appropriately

---

## 11) Acceptance criteria for **any** change

A change is acceptable only if **all** are true:

- [ ] **Alignment**: Matches architecture & vision in README + `/docs`  
- [ ] **Tiny PR**: ≤ 300 LOC, **single concern**  
- [ ] **Actions green**: All CI checks pass; no policy bypass  
- [ ] **SHA proof**: `/api/version == HEAD SHA` post-deploy  
- [ ] **UAT Gate**: Critical journey validated (staging → prod-safe)  
- [ ] **No workarounds**: Root cause fixed; maintainability preserved  
- [ ] **Repo hygiene**: `.gitignore` & size guards upheld; no artifacts/data committed  
- [ ] **Security**: Posture unchanged or improved  
- [ ] **Docs**: Updated where needed  
- [ ] **Tests**: Appropriate coverage added; no flakes introduced

---

## References

- [README.md](./README.md) — architecture & system overview  
- [/docs](./docs) — operations, security, deployments, UAT  
- [Team Playbook v2.3](./docs/team-playbook.md) — operating procedures  
- [Security Practices](./docs/security.md) — security guidelines  
- [Operations Guide](./docs/operations.md) — operational procedures  
- [.github/PULL_REQUEST_TEMPLATE.md](./.github/PULL_REQUEST_TEMPLATE.md) — PR gates & checklist

---

*Last Updated: August 2025*  
*Version: 1.1.0*
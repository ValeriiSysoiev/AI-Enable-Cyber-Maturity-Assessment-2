# Product Backlog - AI-Enabled Cyber Maturity Assessment

**Version:** 1.0.0  
**Last Updated:** 2025-08-30  
**Source:** `/product/backlog.yaml`

## Quick Navigation

[Epics](#epics) | [Sprints](#sprints) | [User Stories](#additional-user-stories) | [Metrics](#metrics--governance)

---

## Operating Model

### Sprint Cadence
- **Duration:** 1 week sprints
- **Ceremonies:**
  - Sprint Planning (90m)
  - Daily Standup (15m)
  - Mid-sprint Review (30m)
  - Sprint Review/Demo (45m)
  - Retrospective (30m)

### Definition of Ready
- [ ] User value clearly defined
- [ ] Acceptance criteria in Given/When/Then format
- [ ] Test notes included
- [ ] No external blockers identified

### Definition of Done
- [ ] Code implemented
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] GitHub Actions green
- [ ] SHA proof (/api/version == HEAD SHA)
- [ ] UAT Gate passed in staging & production
- [ ] Demo recorded

### Constraints
- Re-read README, /docs, and /DEVELOPMENT_GUIDELINES.md before every change
- No hacks/workarounds - fix root causes only
- Actions is canonical; post-deploy UAT Gate is mandatory
- PRs must be <300 LOC, single concern

---

## Epics

### Infrastructure & Foundation

#### E1: CI/CD & Environment Baseline
**Goal:** Deterministic Releases  
**Success:** Production workflow builds web image tag=${{ github.sha }}, wires, sets build SHA, and proves /api/version == sha  
**Status:** 🔵 Planned

#### E2: Auth Lifecycle Hardening
**Goal:** AAD-Only Production  
**Success:** AAD round-trip & sign-out are reliable; no auto-login without Microsoft round-trip  
**Status:** 🔵 Planned

#### E3: API Health & Contracts
**Goal:** Reliable API Communication  
**Success:** Presets list/get/upload 2xx; create→get 201→200; engagements list 2xx; /api/proxy/admin/status 200 for Admin  
**Status:** 🔵 Planned

### Core Features

#### E4: Chat Orchestrator v1
**Goal:** Conversation & Tool Routing  
**Success:** Chat can call Doc Analyzer & Transcribe→Minutes tools and persist run logs  
**Status:** 🔵 Planned

#### E5: Evidence Ingestion & Mapping v1
**Goal:** Document Analysis & Control Mapping  
**Success:** Uploaded docs produce control coverage with citations  
**Status:** 🔵 Planned

#### E6: Maturity Scoring v1
**Goal:** Assessment Scoring with Explainability  
**Success:** Domain levels computed with "why" + missing evidence list  
**Status:** 🔵 Planned

#### E7: Roadmap & Exports v1
**Goal:** PPTX/Jira Export Capabilities  
**Success:** PPTX deck + Jira epics/issues generated from roadmap  
**Status:** 🔵 Planned

#### E8: Engagement RAG & Citations
**Goal:** Evidence-based Answers  
**Success:** Answers contain citations to evidence; contradiction prompts  
**Status:** 🔵 Planned

### Administration & Compliance

#### E9: Admin & Presets Management
**Goal:** Preset Curation Tools  
**Success:** Admin-presets CRUD & validation; canonical presets seeded  
**Status:** 🔵 Planned

#### E10: Consent & GDPR
**Goal:** Privacy Compliance  
**Success:** Consent stored & auditable; GDPR Ops dashboards render  
**Status:** 🔵 Planned

### Operations

#### E11: Observability & SLOs
**Goal:** Monitoring & Alerting  
**Success:** Error budgets & alerts configured; support bundle script  
**Status:** 🔵 Planned

#### E12: Security & Compliance
**Goal:** Security Hardening  
**Success:** No high/critical open; scans & policy checks green  
**Status:** 🔵 Planned

#### E13: Repo Hygiene & Docs
**Goal:** Repository Health  
**Success:** Repo lean; docs current; PR template enforced  
**Status:** 🔵 Planned

---

## Sprints

### Sprint 1: Stabilize Releases & Sign-in/out Baseline
**Dates:** Sep 2-8, 2025 | **Points:** 8 | **Epics:** E1, E2

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S1-1 | Production workflow SHA verification | 3 | 🔵 Planned |
| S1-2 | AAD-only providers in production | 1 | 🔵 Planned |
| S1-3 | Sign-out session clearing | 3 | 🔵 Planned |
| S1-4 | Remove App Service API references | 1 | 🔵 Planned |

**UAT:** AAD sign-in/out; evidence no regressions  
**Demo:** Reliable deploy + real sign-out

---

### Sprint 2: Contracts - Presets/Assessments/Engagements
**Dates:** Sep 9-15, 2025 | **Points:** 10 | **Epics:** E3

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S2-1 | Presets list/get endpoints | 3 | 🔵 Planned |
| S2-2 | Preset upload functionality | 3 | 🔵 Planned |
| S2-3 | Assessment create→get flow | 3 | 🔵 Planned |
| S2-4 | Admin status endpoint | 1 | 🔵 Planned |

**UAT:** Create assessment and open it; admin pages render  
**Demo:** Preset catalog & create→read assessment

---

### Sprint 3: Chat Orchestrator v1
**Dates:** Sep 16-22, 2025 | **Points:** 7 | **Epics:** E4

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S3-1 | Conversation store implementation | 3 | 🔵 Planned |
| S3-2 | Intent→tool routing | 3 | 🔵 Planned |
| S3-3 | RBAC & consent guardrails | 1 | 🔵 Planned |

**UAT:** Chat invokes Doc Analyzer with a doc; Transcribe with audio; logs visible  
**Demo:** Hello orchestrator

---

### Sprint 4: Evidence Mapping v1
**Dates:** Sep 23-29, 2025 | **Points:** 8 | **Epics:** E5

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S4-1 | Doc Analyzer control mapping | 5 | 🔵 Planned |
| S4-2 | Evidence overview page | 3 | 🔵 Planned |

**UAT:** Upload doc, chat analyze → mapped controls visible with citations  
**Demo:** Evidence to controls

---

### Sprint 5: Maturity Scoring v1
**Dates:** Sep 30 - Oct 6, 2025 | **Points:** 8 | **Epics:** E6

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S5-1 | Scoring agent implementation | 5 | 🔵 Planned |
| S5-2 | Missing evidence prompts | 3 | 🔵 Planned |

**UAT:** From mapped evidence, score maturity; see gaps & prompts  
**Demo:** Your current maturity, here's why

---

### Sprint 6: Roadmap & Exports v1
**Dates:** Oct 7-13, 2025 | **Points:** 11 | **Epics:** E7

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S6-1 | Roadmap generator | 5 | 🔵 Planned |
| S6-2 | PPTX export | 3 | 🔵 Planned |
| S6-3 | Jira integration | 3 | 🔵 Planned |

**UAT:** Generate roadmap from current scores; export PPTX & Jira  
**Demo:** From gaps to an exec deck & tickets

---

### Sprint 7: RAG Index & Citations
**Dates:** Oct 14-20, 2025 | **Points:** 8 | **Epics:** E8

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S7-1 | Per-engagement RAG index | 5 | 🔵 Planned |
| S7-2 | Contradictions agent | 3 | 🔵 Planned |

**UAT:** Ask 'why level X?' → cited answer; contradictions surfaced  
**Demo:** Show me the evidence

---

### Sprint 8: Admin & Presets Management
**Dates:** Oct 21-27, 2025 | **Points:** 4 | **Epics:** E9

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S8-1 | Admin presets CRUD | 3 | 🔵 Planned |
| S8-2 | Seed canonical presets | 1 | 🔵 Planned |

**UAT:** Admin imports/edits preset; appears in user flow  
**Demo:** Curate your maturity model presets

---

### Sprint 9: Consent & GDPR
**Dates:** Oct 28 - Nov 3, 2025 | **Points:** 6 | **Epics:** E10

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S9-1 | Consent UI implementation | 3 | 🔵 Planned |
| S9-2 | GDPR Ops dashboards | 3 | 🔵 Planned |

**UAT:** Ingest audio with consent; verify GDPR page shows record  
**Demo:** Privacy built in

---

### Sprint 10: Observability, Security, Hygiene
**Dates:** Nov 4-10, 2025 | **Points:** 7 | **Epics:** E11, E12, E13

| Story | Title | Points | Status |
|-------|-------|--------|--------|
| S10-1 | SLO dashboards & alerts | 3 | 🔵 Planned |
| S10-2 | Security findings closure | 3 | 🔵 Planned |
| S10-3 | CI size guard & hygiene | 1 | 🔵 Planned |

**UAT:** Non-functional: alarms tested on staging; size guard blocks test artifact commit  
**Demo:** We can operate & keep it healthy

---

## Sprint Summary

| Sprint | Points | Focus Area |
|--------|--------|------------|
| Sprint 1 | 8 | Foundation - Releases & Auth |
| Sprint 2 | 10 | API Contracts |
| Sprint 3 | 7 | Chat Orchestration |
| Sprint 4 | 8 | Evidence Mapping |
| Sprint 5 | 8 | Maturity Scoring |
| Sprint 6 | 11 | Roadmap & Exports |
| Sprint 7 | 8 | RAG & Citations |
| Sprint 8 | 4 | Admin Tools |
| Sprint 9 | 6 | Privacy & Consent |
| Sprint 10 | 7 | Operations & Security |
| **Total** | **77** | **10 weeks** |

---

## Additional User Stories

### Authentication (E2)
- **US-E2-01:** Sign-out session clearing (3 pts)
- **US-E2-02:** No localhost redirects in production (1 pt)

### API Contracts (E3)
- **US-E3-01:** Presets list functionality (3 pts)
- **US-E3-02:** Assessment create→read flow (3 pts)

### Chat Orchestrator (E4)
- **US-E4-01:** Document analysis routing (3 pts)

---

## Metrics & Governance

### Delivery Metrics
- Sprint burn-up charts
- Lead time for changes
- Change failure rate
- Mean time to restore

### Quality Metrics
- Test coverage trends
- UAT pass rate
- GitHub Actions failure categories

### Security Metrics
- High/Critical findings (count & age)
- Key rotation compliance
- Dependency freshness

### SLOs
- API error rate < 1%
- P95 latency < 500ms
- Uptime > 99.9%
- Alert response time < 15min

---

## UAT Scripts

### Authentication UAT
1. Visit `/signin`
2. Click Azure AD button
3. Complete Microsoft authentication
4. Verify redirect to `/engagements`
5. Click sign-out
6. Verify redirect to `/signin`
7. Repeat sign-in to ensure no auto-login

### Contracts UAT
1. Verify presets table displays data
2. Upload new preset (expect 201)
3. Verify preset appears in list
4. Create new assessment
5. Open assessment detail page
6. Verify engagements list loads
7. Check admin status endpoint (200 for admin users)

### Chat UAT
1. Send "analyze doc" command
2. Verify Doc Analyzer invocation
3. Send "transcribe audio" command
4. Verify Transcribe tool invocation
5. Check conversation logs persisted
6. Verify RBAC blocks unauthorized tools

### Scoring UAT
1. Upload evidence documents
2. Run maturity scoring
3. Verify domain scores displayed
4. Check reasoning explanations
5. Verify missing evidence prompts

### Roadmap UAT
1. Generate roadmap from scores
2. Verify prioritization logic
3. Export to PPTX
4. Export to Jira
5. Verify idempotent Jira updates

---

*This document is generated from `/product/backlog.yaml` - the canonical source of truth for the product backlog.*
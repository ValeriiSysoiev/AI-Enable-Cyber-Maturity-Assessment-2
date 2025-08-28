# Documentation Inventory

## Summary

**Before**: 906 total Markdown files
**After**: ~50 essential files
**Removed**: 850+ legacy/duplicate files
**Kept**: Key operational and compliance documents
**Merged**: Content consolidated into 7 core docs

## Removed Files

### Legacy Release Documents
| File | Reason |
|------|--------|
| `RELEASE_HANDOFF_v0.2.0-rc1.md` | Superseded by release_notes_template.md |
| `RELEASE_HANDOFF_RC1.md` | Old release, no longer relevant |
| `RELEASE_NOTES_RC1.md` | Historical release, archived |
| `RELEASE_NOTES_v0.1.0-rc1.md` | Historical release, archived |
| `R2_MERGE_PLAN.md` | Completed merge, obsolete |

### Phase/Sprint Documents
| File | Reason |
|------|--------|
| `PHASE5_TESTING_IMPLEMENTATION.md` | Completed phase, obsolete |
| `PHASE6_DEPLOYMENT_PLAN.md` | Completed deployment, obsolete |
| `SECURITY_COMPLIANCE_REPORT_PHASE6.md` | Historical compliance report |
| `SECURITY_REVIEW_PHASE5.md` | Historical security review |
| `SPRINT_V1_3_MCP_FRONTEND_IMPLEMENTATION.md` | Completed sprint |
| `SPRINT_V1_7_STAGING_UAT_RELEASE_ISSUE.md` | Resolved issue |

### Production/Staging Legacy
| File | Reason |
|------|--------|
| `PRODUCTION_DEPLOYMENT_REPORT.md` | Superseded by deployments.md |
| `PRODUCTION_READINESS_ASSESSMENT.md` | One-time assessment |
| `PRODUCTION_STATUS.md` | Outdated status |
| `STAGING_ENVIRONMENT_SETUP.md` | Completed setup |
| `STAGING_WORKFLOW_FIX.md` | Resolved fix |
| `STAGING_WORKFLOW_SETUP.md` | Completed setup |
| `DEPLOY_STAGING_WORKFLOW_FIX.md` | Resolved issue |

### App Service References (Removed - Now Container Apps)
| File | Reason |
|------|--------|
| `docs/DEPLOY_STAGING.md` | References App Service API |
| `docs/staging-env.md` | Outdated App Service config |
| `docs/prod-env.md` | Superseded by architecture.md |
| `scripts/PRODUCTION_DEPLOYMENT_GUIDE.md` | Old App Service deployment |

### Duplicate/Redundant Security Docs
| File | Reason |
|------|--------|
| `SECURITY_PATCHES.md` | Merged into security.md |
| `mcp_gateway/SECURITY_PATCH_SUMMARY.md` | Historical patches |
| `mcp_gateway/SECURITY_POLICY.md` | Merged into security.md |
| `mcp_gateway/SECURITY_RISK_ASSESSMENT.md` | One-time assessment |
| `docs/security-implementation.md` | Merged into security.md |

### Old Workflow/CI Documents
| File | Reason |
|------|--------|
| `CI_MCP_INTEGRATION_SUMMARY.md` | Completed integration |
| `UAT_EXPLORER_IMPLEMENTATION_SUMMARY.md` | Merged into uat.md |
| `UAT_EXPLORER_GITHUB_ACTIONS_IMPLEMENTATION.md` | Merged into deployments.md |

### Cleanup/Summary Reports
| File | Reason |
|------|--------|
| `REPO_CLEANUP_SUMMARY.md` | One-time cleanup |
| `artifacts/repo_health/*.md` | Historical reports |
| `artifacts/sprint_v1_2/*.md` | Completed sprints |
| `artifacts/cursor_run/*.md` | Development artifacts |
| `logs/reports/*.md` | Historical logs |

### Web-Specific Legacy
| File | Reason |
|------|--------|
| `web/GDPR_IMPLEMENTATION_SUMMARY.md` | Merged into security.md |
| `web/ACCESSIBILITY_REVIEW.md` | One-time review |
| `web/RAG_IMPLEMENTATION.md` | Merged into architecture.md |
| `web/ENV_SETUP.md` | Superseded by configuration.md |

## Kept Files

### Core Documentation (in /docs/)
| File | Reason |
|------|--------|
| `docs/architecture.md` | Current system architecture |
| `docs/deployments.md` | CI/CD workflows and procedures |
| `docs/configuration.md` | Environment configuration |
| `docs/uat.md` | UAT procedures |
| `docs/operations.md` | Operations guide |
| `docs/security.md` | Security model and practices |
| `docs/release_notes_template.md` | Template for releases |

### Architecture Decision Records
| File | Reason |
|------|--------|
| `docs/ADR-*.md` | Architecture decisions - kept for history |

### Compliance/Legal
| File | Reason |
|------|--------|
| `docs/data-governance.md` | Compliance requirement |
| `docs/uat-consent-privacy.md` | Legal requirement |
| `CHANGELOG.md` | Version history |

### Operational Runbooks
| File | Reason |
|------|--------|
| `docs/go-live-runbook.md` | Still used for major releases |
| `docs/oncall.md` | Active on-call procedures |
| `docs/postmortem-template.md` | Incident response template |

### Infrastructure
| File | Reason |
|------|--------|
| `docs/INFRASTRUCTURE_CLEANUP.md` | Recent migration documentation |
| `docs/cost-guardrails.md` | Cost management policies |
| `docs/monitoring-alerts.md` | Active monitoring configuration |

## Merged Content

### Content Consolidation
| Source Files | Destination | Notes |
|--------------|-------------|-------|
| Multiple security docs | `docs/security.md` | Unified security documentation |
| UAT documents | `docs/uat.md` | Consolidated UAT procedures |
| Deployment guides | `docs/deployments.md` | Single deployment reference |
| Environment docs | `docs/configuration.md` | Centralized config docs |
| Architecture fragments | `docs/architecture.md` | Complete architecture guide |

## File Count Summary

| Category | Before | After | Change |
|----------|--------|-------|--------|
| Root directory | 25 | 2 | -23 |
| /docs | 45 | 20 | -25 |
| /artifacts | 200+ | 0 | -200+ |
| /logs | 300+ | 0 | -300+ |
| /scripts | 30 | 30 | 0 (kept for operations) |
| /web | 10 | 2 | -8 |
| /app | 5 | 1 | -4 |
| **Total** | **906** | **~55** | **-850+** |

## Verification

- ✅ No remaining references to App Service API as production target
- ✅ API target is Container Apps throughout documentation
- ✅ All critical operational docs preserved
- ✅ Compliance and legal documents retained
- ✅ Clean documentation structure in /docs/

## Notes

1. All removed files still exist in Git history if needed
2. Scripts directory preserved as it contains operational tools
3. ADR documents kept for architectural history
4. Template files retained for future use
## Description
<!-- Brief description of changes -->

## Type of Change
<!-- Mark relevant option with "x" -->
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring (no functional changes)

## Checklist
<!-- ALL items must be checked before merge -->

- [ ] I re-read **README** and `/DEVELOPMENT_GUIDELINES.md` and aligned changes with the architecture/vision
- [ ] This PR is **single-concern** and <300 LOC (excluding generated files)
- [ ] Tests added/updated (unit, integration, or UAT as appropriate) and pass locally + CI
- [ ] Docs updated (README or `/docs/*`) if behavior/UX/ops changed
- [ ] Security posture unchanged or improved (no secrets; RBAC verified; inputs validated; logs redacted)
- [ ] CI workflows green; **no** bypass of policy gates
- [ ] For production rollout: `/api/version == HEAD SHA` will be proven by Actions, and the **UAT Gate** is expected to pass
- [ ] No workarounds/hacks; this PR fixes **root cause** and preserves long-term maintainability

## Testing
<!-- Describe tests added/modified -->

## Screenshots
<!-- If applicable, add screenshots -->

## Additional Notes
<!-- Any additional context or notes for reviewers -->
# Release Notes Template

## Version [X.Y.Z] - YYYY-MM-DD

### Overview

Brief description of the release purpose and major themes (1-2 sentences).

### What's New

- **Feature Name**: Brief description of the new capability
- **Enhancement**: Description of improved functionality
- **Integration**: New third-party service or API integration

### Improvements

- **Performance**: Specific optimization and impact
- **User Experience**: UI/UX enhancement details
- **Security**: Security improvement without revealing vulnerabilities
- **Reliability**: Stability or availability improvement

### Bug Fixes

- Fixed issue where [description of problem and resolution]
- Resolved [component] error when [condition]
- Corrected [behavior] in [feature/module]

### Breaking Changes

⚠️ **Action Required**

- **Change**: Description of breaking change
  - **Migration**: Steps to migrate existing functionality
  - **Impact**: Who is affected and how

### Deprecations

- **Deprecated**: [Feature/API] will be removed in version [X.Y.Z]
  - **Replacement**: Use [new feature/API] instead
  - **Timeline**: End of support date

### Known Issues

- **Issue**: Description of known problem
  - **Workaround**: Temporary solution if available
  - **Fix ETA**: Expected resolution version

### Technical Details

#### API Changes

```
GET /api/v1/new-endpoint
POST /api/v1/modified-endpoint (parameter changes)
DELETE /api/v1/deprecated-endpoint (removed)
```

#### Configuration Changes

| Key | Old Value | New Value | Notes |
|-----|-----------|-----------|-------|
| CONFIG_KEY | old | new | Migration required |

#### Database Migrations

- Migration script: `migration_vX.Y.Z.sql`
- Rollback script: `rollback_vX.Y.Z.sql`
- Estimated duration: X minutes

### Deployment Notes

#### Pre-Deployment Steps

1. Backup database
2. Update environment variables
3. Clear cache

#### Deployment Process

```bash
# Standard deployment
gh workflow run deploy-container-apps.yml

# Verify deployment
curl https://api-cybermat-prd-aca.../version
```

#### Post-Deployment Verification

- [ ] Health endpoints return 200
- [ ] Version endpoint shows correct SHA
- [ ] UAT smoke tests pass
- [ ] No error spike in monitoring

### Rollback Procedure

If issues occur:

```bash
# Identify previous version
PREVIOUS_SHA=abc123...

# Deploy previous version
az containerapp update --image service:$PREVIOUS_SHA
```

### Performance Impact

- **Response Time**: +/- X%
- **Memory Usage**: +/- X%
- **CPU Usage**: +/- X%
- **Database Load**: +/- X%

### Security Updates

- Updated dependencies to latest secure versions
- Applied security patches for CVE-YYYY-XXXXX
- Enhanced [security feature] implementation

### Compatibility

#### Supported Environments

- **Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Node.js**: 18.x, 20.x
- **Python**: 3.11+
- **Azure**: Container Apps, Cosmos DB API v2

#### Client Requirements

- Minimum client version: X.Y.Z
- Required permissions: [list any new permissions]

### Documentation Updates

- Updated [Architecture Guide](./docs/architecture.md)
- New section in [Operations Guide](./docs/operations.md)
- API documentation regenerated

### Contributors

- @username1 - Feature development
- @username2 - Bug fixes
- @username3 - Documentation

### Feedback

For issues or questions about this release:
- GitHub Issues: [Create Issue](https://github.com/org/repo/issues)
- Support: support@company.com

---

## Appendix

### Metrics Baseline

Capture pre-release metrics for comparison:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Avg Response Time | Xms | Yms | +/-Z% |
| Error Rate | X% | Y% | +/-Z% |
| Active Users | X | Y | +/-Z% |

### Testing Summary

- Unit Tests: X passed, Y skipped
- Integration Tests: X passed, Y skipped
- UAT: Passed on YYYY-MM-DD
- Security Scan: No critical issues

### Release Checklist

- [ ] Code review completed
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Security scan clean
- [ ] Performance baseline captured
- [ ] Rollback plan documented
- [ ] Stakeholders notified

---

*Template Version: 1.0.0*
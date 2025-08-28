# User Acceptance Testing (UAT) Guide

## Overview

User Acceptance Testing validates that core functionality works correctly after each deployment. UAT must pass before any production release is considered complete.

## UAT Scope

### Critical User Journey

The UAT flow covers the essential path through the application:

1. **Sign-in** → Authenticate via Azure AD
2. **View Engagements** → List existing assessments
3. **Create/Open Engagement** → Start new or continue existing
4. **Navigate to Preset** → Access `/new` preset configuration
5. **Complete Workflow** → Execute assessment steps
6. **Sign-out** → Properly end session

## UAT Execution Steps

### 1. Sign-In Verification

**Test URL**: `https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/signin`

**Steps**:
1. Navigate to application URL
2. Click "Sign in with Azure AD"
3. Enter valid credentials
4. Verify redirect to dashboard

**Expected Result**:
- Successful authentication
- User profile visible in header
- Correct role displayed

**Common Issues**:
- Redirect URI mismatch → Check NEXTAUTH_URL configuration
- Invalid client → Verify AZURE_AD_CLIENT_ID

### 2. Engagements List

**Test URL**: `/engagements`

**Steps**:
1. Navigate to Engagements page
2. Verify list loads within 3 seconds
3. Check pagination if > 10 items
4. Verify search/filter functionality

**Expected Result**:
- Engagements display correctly
- Performance acceptable (< 3s load)
- Filters work as expected

### 3. Create New Engagement

**Test URL**: `/new`

**Steps**:
1. Click "New Engagement" button
2. Fill required fields:
   - Name: "UAT Test [timestamp]"
   - Client: Select from dropdown
   - Framework: Select "NIST CSF"
3. Click "Create"
4. Verify redirect to engagement dashboard

**Expected Result**:
- Engagement created successfully
- Unique ID generated
- Dashboard displays correct information

### 4. Open Existing Engagement

**Steps**:
1. From Engagements list, click on existing item
2. Verify engagement loads
3. Check all tabs are accessible:
   - Assessment
   - Evidence
   - Workshops
   - Chat

**Expected Result**:
- All sections load without errors
- Data displays correctly
- Navigation works between tabs

### 5. Preset Configuration

**Test URL**: `/e/[engagementId]/new`

**Steps**:
1. Navigate to preset configuration
2. Verify preset options load
3. Select a preset template
4. Confirm settings apply

**Expected Result**:
- Preset templates available
- Configuration saves successfully
- Changes reflected in assessment

### 6. Assessment Workflow

**Steps**:
1. Navigate to Assessment tab
2. Complete at least one control:
   - Set maturity level
   - Add evidence
   - Save progress
3. Verify score updates

**Expected Result**:
- Controls interactive
- Progress saves automatically
- Scores calculate correctly

### 7. Sign-Out

**Steps**:
1. Click user menu in header
2. Select "Sign out"
3. Verify redirect to sign-in page
4. Confirm session ended

**Expected Result**:
- Clean sign-out
- Session cleared
- Cannot access protected pages

## UAT Checklist

### Pre-Deployment UAT

- [ ] Test environment accessible
- [ ] Test accounts configured
- [ ] Test data available
- [ ] UAT script reviewed

### Core Functionality

- [ ] Sign-in successful
- [ ] Engagements list loads
- [ ] Create engagement works
- [ ] Open engagement works
- [ ] Assessment functions correctly
- [ ] Evidence upload works
- [ ] Sign-out successful

### Performance Criteria

- [ ] Page load < 3 seconds
- [ ] API responses < 2 seconds
- [ ] No console errors
- [ ] No 500 errors

### Security Validation

- [ ] Authentication required for protected pages
- [ ] Role-based access enforced
- [ ] Session timeout works
- [ ] No sensitive data in URLs

## Automated UAT

### Playwright E2E Tests

Run automated UAT suite:

```bash
# Run UAT tests
npm run test:e2e:uat

# Run specific UAT scenario
npx playwright test tests/uat-flow.spec.ts

# Run with UI mode for debugging
npx playwright test --ui
```

### Test Coverage

Automated tests cover:
- Authentication flow
- Engagement CRUD operations
- Assessment interactions
- Evidence management
- Role-based access

## UAT Reporting

### Pass Criteria

UAT passes when:
- All checklist items complete
- No critical bugs found
- Performance meets SLA
- Security requirements met

### Failure Process

If UAT fails:
1. Document specific failure
2. Create incident ticket
3. Roll back if critical
4. Fix and re-test
5. Update UAT scripts if needed

### UAT Report Template

```markdown
## UAT Report - [Date]

**Build**: [SHA]
**Environment**: Production
**Tester**: [Name]

### Results Summary
- Sign-in: ✅ PASS / ❌ FAIL
- Engagements: ✅ PASS / ❌ FAIL
- Assessment: ✅ PASS / ❌ FAIL
- Evidence: ✅ PASS / ❌ FAIL
- Sign-out: ✅ PASS / ❌ FAIL

### Issues Found
1. [Issue description]
   - Severity: Critical/High/Medium/Low
   - Steps to reproduce
   - Expected vs Actual

### Recommendation
⬜ Ready for production
⬜ Fix issues and re-test
⬜ Roll back deployment
```

## Common UAT Issues

### Authentication Failures

**Issue**: "Invalid redirect URI" error

**Solution**:
- Verify NEXTAUTH_URL matches Azure AD app registration
- Check for trailing slashes in URLs

### Slow Performance

**Issue**: Pages take > 5 seconds to load

**Check**:
- Container App scaling settings
- Database throttling
- Network latency
- Browser dev tools for slow requests

### Missing Data

**Issue**: Engagements list empty

**Check**:
- User has correct permissions
- Database connectivity
- API health endpoint
- Console errors

### Session Issues

**Issue**: User logged out unexpectedly

**Check**:
- Session timeout configuration
- Cookie settings
- NEXTAUTH_SECRET consistency

## UAT Environment

### Access URLs

- **Production**: `https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io`
- **API Health**: `https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io/health`

### Test Accounts

Test accounts should have different roles:
- Admin user - full access
- Consultant - engagement access
- Client - read-only access

### Test Data

Maintain test engagements:
- "UAT Template" - for testing
- "UAT Archive" - historical data
- "UAT Active" - in-progress assessment

## UAT Schedule

### Regular UAT

- **Post-deployment**: Within 30 minutes
- **Weekly**: Every Monday morning
- **Pre-release**: Before major versions

### Emergency UAT

Required after:
- Infrastructure changes
- Security patches
- Database migrations
- Authentication updates

## Contact Information

For UAT issues:
1. Check this guide first
2. Review operations logs
3. Contact platform team
4. Escalate if critical
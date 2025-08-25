# GitHub Issue Integration for UAT Reporter

The UAT Explorer reporter now includes automatic GitHub issue creation for test failures, providing seamless integration between your test suite and issue tracking.

## Features

- **Automatic Issue Creation**: Failed tests automatically generate GitHub issues with comprehensive details
- **Deduplication**: Uses failure signatures to prevent duplicate issues for the same failure type
- **Environment-Aware Labeling**: Issues are labeled with environment (staging/production/development) and severity levels
- **Secret Sanitization**: Sensitive information is automatically removed from issue content
- **Smart Updates**: Existing issues are updated when the same failure occurs again
- **Rich Context**: Issues include test steps, screenshots, logs, and troubleshooting guidance

## Configuration

### Environment Variables

Set the following environment variables to enable GitHub integration:

```bash
# Required - GitHub API token with repo permissions
GITHUB_TOKEN="your_github_token_here"

# Required - Repository owner (organization or username)
GITHUB_OWNER="your_org_or_username"

# Required - Repository name
GITHUB_REPO="your_repo_name"

# Optional - Label prefix (default: "uat")
GITHUB_LABEL_PREFIX="uat"

# Optional - Comma-separated list of GitHub usernames to assign issues to
GITHUB_ASSIGNEES="developer1,developer2"
```

### GitHub Token Setup

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Set expiration and select these scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories - if using public repos)
4. Generate the token and save it securely
5. Add the token to your environment variables

### Example Configuration

```bash
# For production environment
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export GITHUB_OWNER="yourcompany"
export GITHUB_REPO="ai-maturity-assessment"
export GITHUB_LABEL_PREFIX="uat"
export GITHUB_ASSIGNEES="devops-team,qa-lead"

# For CI/CD (GitHub Actions)
# Set these as repository secrets
GITHUB_TOKEN: ${{ secrets.UAT_GITHUB_TOKEN }}
GITHUB_OWNER: "yourcompany"
GITHUB_REPO: "ai-maturity-assessment"
```

## Issue Structure

### Labels
Issues are automatically labeled with:
- `uat` (or custom prefix)
- Environment: `staging`, `production`, `development`
- Severity: `severity:low`, `severity:medium`, `severity:high`, `severity:critical`
- Category: `performance`, `infrastructure`, `authentication`, `stability`, `functional`

### Issue Title Format
```
[ENVIRONMENT] SEVERITY: Test Name - Error Type
```
Example: `[PRODUCTION] HIGH: User Login Flow - TIMEOUT`

### Issue Content
- **Test Details**: Test name, ID, environment, severity
- **Failure Information**: Error messages, stack traces
- **Environment Context**: Browser, OS, authentication mode, base URL
- **Test Steps**: Detailed breakdown of test execution steps
- **Logs**: Recent error and warning logs
- **Screenshots**: Links to test failure screenshots
- **Troubleshooting**: Environment-specific guidance and suggested actions

## Usage

### Automatic Operation
Once configured, the integration works automatically:

1. Run UAT tests: `npm run test:e2e:uat`
2. Failed tests trigger issue creation/updates
3. Console shows GitHub integration status
4. Issues appear in your repository with comprehensive details

### Console Output
```
🐙 GitHub issue integration enabled for yourcompany/ai-maturity-assessment
🧪 Starting: User Authentication Test
❌ User Authentication Test (5432ms)
   ❌ Error: Element not found: [data-testid="login-button"]

🐙 Creating GitHub issues for 1 failed test(s)...
   🆕 Issue #123 created for "User Authentication Test"

✅ GitHub Issues Summary:
   🆕 Created: 1 new issue(s)

🔗 View issues: https://github.com/yourcompany/ai-maturity-assessment/issues?q=is:issue+is:open+label:uat
```

### Manual Control
Disable GitHub integration by removing environment variables:
```bash
unset GITHUB_TOKEN
```

## Security Features

### Secret Sanitization
The integration automatically sanitizes sensitive information:
- API tokens and keys
- Passwords and secrets
- Email addresses (partially masked)
- IP addresses (last octet masked)
- Authorization headers

### Safe Defaults
- Only repository collaborators can view private repository issues
- Sensitive test data is filtered before submission
- GitHub tokens require explicit repository permissions

## Failure Signatures

The system generates unique failure signatures to prevent duplicate issues:
- Based on test name, error pattern, and environment
- Normalizes common error types (timeouts, network errors, etc.)
- Updates existing issues when the same failure recurs
- Maintains issue history and occurrence tracking

## Troubleshooting

### Common Issues

**"GitHub issue integration disabled"**
- Verify environment variables are set correctly
- Check GitHub token permissions
- Ensure repository name and owner are correct

**"Failed to create GitHub issue: Bad credentials"**
- GitHub token may be expired or invalid
- Token may not have required repository permissions
- Repository may not exist or be accessible

**"API rate limit exceeded"**
- GitHub API has rate limits (5000 requests/hour for authenticated requests)
- Consider reducing test frequency or using a GitHub App for higher limits

### Validation
Test your configuration:
```bash
node -e "
const { GitHubIssueManager } = require('./e2e/utils/github-issue-manager');
const config = GitHubIssueManager.validateConfig();
console.log(config ? 'Configuration valid' : 'Configuration missing or invalid');
"
```

## Best Practices

### Token Management
- Use GitHub organization tokens for shared repositories
- Set appropriate token expiration dates
- Store tokens securely in CI/CD secret management
- Rotate tokens regularly

### Issue Management
- Configure appropriate assignees for different environments
- Use milestone and project features for issue organization
- Set up automated workflows for issue triaging
- Monitor issue creation patterns for test stability insights

### Environment Strategy
- Use different labels or repositories for different environments
- Configure stricter severity levels for production issues
- Set up alerts for critical production test failures
- Consider separate tokens for production vs. development

## Advanced Configuration

### Custom Labels
Override default labeling behavior:
```typescript
// In your test setup
process.env.GITHUB_LABEL_PREFIX = 'e2e-tests';
```

### Issue Templates
The integration works with GitHub issue templates. Create `.github/ISSUE_TEMPLATE/uat_failure.yml` to standardize issue format.

### Webhook Integration
Combine with GitHub webhooks to trigger additional automation when issues are created or updated.

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: UAT Tests
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:

jobs:
  uat-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - name: Run UAT Tests
        env:
          GITHUB_TOKEN: ${{ secrets.UAT_GITHUB_TOKEN }}
          GITHUB_OWNER: ${{ github.repository_owner }}
          GITHUB_REPO: ${{ github.event.repository.name }}
          WEB_BASE_URL: https://your-staging-url.com
        run: npm run test:e2e:uat
```

### Azure DevOps Example
```yaml
trigger: none
schedules:
- cron: '0 */4 * * *'
  displayName: 'UAT Tests Every 4 Hours'
  branches:
    include:
    - main

pool:
  vmImage: 'ubuntu-latest'

variables:
- group: 'UAT-GitHub-Config'  # Contains GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO

steps:
- task: NodeTool@0
  inputs:
    versionSpec: '20.x'
- script: npm ci
- script: npm run test:e2e:uat
  env:
    GITHUB_TOKEN: $(GITHUB_TOKEN)
    GITHUB_OWNER: $(GITHUB_OWNER)
    GITHUB_REPO: $(GITHUB_REPO)
    WEB_BASE_URL: https://your-staging-url.com
```

## Monitoring and Metrics

Track the effectiveness of your UAT testing:
- Monitor issue creation patterns over time
- Analyze failure signatures to identify recurring problems
- Track resolution times for different severity levels
- Use GitHub's project management features for sprint planning

The GitHub integration transforms your UAT testing from a simple pass/fail report into an actionable issue tracking system that enhances your development workflow and improves system reliability.
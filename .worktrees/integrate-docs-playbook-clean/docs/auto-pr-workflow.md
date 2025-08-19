# Auto-PR Workflow Setup

This document describes the automated Pull Request workflow for agent commits using GitHub CLI.

## Overview

The auto-PR workflow enables automated creation and merging of pull requests for agent-generated changes. This is useful for:

- Autonomous agent development workflows
- Automated code generation and updates
- Continuous integration improvements
- Background maintenance tasks

## Components

### 1. `scripts/agent_commit.sh`
Main script for creating auto-merging pull requests.

**Features:**
- Automatically detects repository owner/name from git remote
- Creates timestamped branches with agent identification
- Commits all staged changes with provided message
- Creates PR with auto-merge enabled
- Supports customizable agent names and base branches

**Usage:**
```bash
# Basic usage
./scripts/agent_commit.sh "feat: add new feature"

# With custom agent name
AGENT_NAME="feature-bot" ./scripts/agent_commit.sh "feat: implement widget"

# With custom base branch
BASE="develop" ./scripts/agent_commit.sh "fix: resolve issue"
```

**Environment Variables:**
- `OWNER`: Repository owner (auto-detected if not set)
- `REPO`: Repository name (auto-detected if not set)  
- `BASE`: Base branch for PR (default: main)
- `AGENT_NAME`: Agent identifier for branch naming (default: claude)
- `GIT_AUTHOR_NAME`: Git commit author name (default: Claude Agent)
- `GIT_AUTHOR_EMAIL`: Git commit author email (default: claude-bot@local)

### 2. `scripts/setup_auto_pr.sh`
One-time setup script for configuring the auto-PR workflow.

**What it does:**
- Verifies GitHub CLI authentication
- Enables auto-merge for the repository
- Tests the agent_commit.sh script
- Creates a validation PR
- Provides setup verification

## Setup Instructions

### Prerequisites

1. **GitHub CLI Installation:**
   ```bash
   # macOS with Homebrew
   brew install gh
   
   # Or download from https://cli.github.com/
   ```

2. **Repository Access:**
   - Write access to the target repository
   - Admin access to enable auto-merge (if not already enabled)

### Initial Setup

1. **Authenticate GitHub CLI:**
   ```bash
   gh auth login --hostname github.com --web --git-protocol https
   ```
   
   Or use device flow:
   - Visit: https://github.com/login/device
   - Enter the one-time code provided by the command

2. **Run Setup Script:**
   ```bash
   ./scripts/setup_auto_pr.sh
   ```

3. **Verify Setup:**
   The setup script will:
   - Check authentication
   - Enable repository auto-merge
   - Create a test PR
   - Verify auto-merge functionality

## Workflow Details

### Branch Naming Convention
Branches are created with the format: `agent/{AGENT_NAME}/{TIMESTAMP}`

Example: `agent/claude/20240817-143022`

### PR Creation Process

1. **Preparation:**
   - Fetches latest from base branch
   - Creates new branch from base
   - Stages all changes (`git add -A`)

2. **Validation:**
   - Checks for changes to commit
   - Exits gracefully if no changes

3. **Commit & Push:**
   - Commits with provided message
   - Pushes branch to origin

4. **PR Creation:**
   - Creates PR with descriptive title and body
   - Adds labels: `automerge`, `agent`
   - Enables auto-merge with squash strategy

### Auto-Merge Behavior

**When PRs Auto-Merge:**
- All required status checks pass
- No conflicts with base branch
- Auto-merge is enabled on the PR

**When PRs Don't Auto-Merge:**
- Failing status checks (tests, linting, etc.)
- Merge conflicts
- Manual review required (if branch protection configured)

## CI/CD Integration

The workflow integrates with existing CI/CD pipelines:

### Required Status Checks
Configure these in repository settings → Branches → Branch protection rules:

- ✅ `ci` - Main CI pipeline
- ✅ `e2e-tests` - End-to-end testing
- ✅ `security-scan` - Security analysis
- ✅ `lint` - Code linting

### Workflow Files
The following GitHub Actions workflows will run on PRs:

- `.github/workflows/e2e.yml` - E2E testing
- `.github/workflows/release.yml` - Build and validation
- Any other configured workflows

## Security Considerations

### Authentication
- Uses GitHub CLI with standard OAuth authentication
- No secrets stored in repository
- Inherits user permissions from authenticated CLI

### Branch Protection
Consider enabling branch protection rules:

```yaml
Protection Rules:
  - Require status checks to pass
  - Require up-to-date branches
  - Include administrators: false
  - Allow force pushes: false
  - Allow deletions: false
```

### Auto-Merge Safety
- Only auto-merges when ALL required checks pass
- Failed checks block auto-merge
- Manual intervention available if needed

## Troubleshooting

### Common Issues

**"Not authenticated":**
```bash
# Re-authenticate
gh auth login --hostname github.com --web --git-protocol https
```

**"Auto-merge not enabled":**
```bash
# Enable via API
gh api -X PATCH repos/OWNER/REPO --field allow_auto_merge=true
```

**"No changes to commit":**
- Script exits cleanly when no changes detected
- This is normal behavior, not an error

**"PR creation failed":**
- Check GitHub CLI authentication
- Verify repository permissions
- Ensure no conflicts with existing PRs

### Debug Mode
Add debug output to agent_commit.sh:
```bash
# Add at top of script
set -x  # Enable debug mode
```

### Manual PR Management
If auto-merge fails, manage PRs manually:

```bash
# List PRs
gh pr list

# Check PR status
gh pr view PR_NUMBER

# Manually merge
gh pr merge PR_NUMBER --squash
```

## Examples

### Basic Agent Workflow
```bash
# Agent makes changes to files
echo "new feature" > feature.txt

# Stage changes
git add feature.txt

# Create auto-merging PR
./scripts/agent_commit.sh "feat: add new feature implementation"
```

### Custom Agent Workflow
```bash
# Set custom agent name
export AGENT_NAME="code-generator"
export GIT_AUTHOR_NAME="Code Generator Bot"
export GIT_AUTHOR_EMAIL="codegen@company.com"

# Make changes and commit
./scripts/agent_commit.sh "feat: generate new API endpoints

Generated the following endpoints:
- POST /api/users
- GET /api/users/{id}
- PUT /api/users/{id}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Integration with Other Scripts
```bash
# Example: Automated documentation updates
./scripts/generate_docs.sh
./scripts/agent_commit.sh "docs: update API documentation

Auto-generated documentation updates based on latest code changes."
```

## Best Practices

1. **Commit Messages:**
   - Use conventional commit format
   - Include generated tag for traceability
   - Add Co-Authored-By for agent attribution

2. **Change Management:**
   - Test changes locally before committing
   - Use feature flags for major changes
   - Consider staging environments

3. **Monitoring:**
   - Monitor PR success/failure rates
   - Review auto-merged changes regularly
   - Set up notifications for failed auto-merges

4. **Branch Cleanup:**
   - Enable automatic branch deletion after merge
   - Monitor for orphaned branches
   - Regular cleanup of old agent branches

## Configuration Files

### Repository Settings
Enable these settings in GitHub repository configuration:

- ✅ Allow auto-merge
- ✅ Allow squash merging
- ✅ Automatically delete head branches
- ✅ Always suggest updating pull request branches

### Branch Protection (Optional)
```yaml
main:
  required_status_checks:
    strict: true
    contexts:
      - ci
      - e2e-tests
      - security-scan
  enforce_admins: false
  required_pull_request_reviews: null
  restrictions: null
```

## Support

For issues with the auto-PR workflow:

1. Check this documentation
2. Review GitHub CLI documentation
3. Verify repository permissions
4. Check CI/CD pipeline status
5. Contact repository administrators if needed
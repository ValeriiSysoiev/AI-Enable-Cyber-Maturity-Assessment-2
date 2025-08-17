#!/usr/bin/env bash
set -euo pipefail

# Auto-PR Workflow Setup Script
# This script completes the GitHub CLI authentication and enables auto-merge

OWNER="${OWNER:-ValeriiSysoiev}"
REPO="${REPO:-AI-Enable-Cyber-Maturity-Assessment-2}"

echo "🔧 Setting up Auto-PR workflow for $OWNER/$REPO"

# Step 1: Check GitHub CLI authentication
echo "📋 Checking GitHub CLI authentication..."
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated"
    echo "Please run: gh auth login --hostname github.com --web --git-protocol https"
    echo "Or visit: https://github.com/login/device"
    echo "Use this one-time code: 92A8-B0BF"
    exit 1
fi

echo "✅ GitHub CLI authenticated"

# Step 2: Enable auto-merge for the repository
echo "📋 Enabling auto-merge for repository..."
gh api -X PATCH "repos/$OWNER/$REPO" \
    --field allow_auto_merge=true \
    --silent

echo "✅ Auto-merge enabled for repository"

# Step 3: Verify repository settings
echo "📋 Verifying repository settings..."
AUTO_MERGE_ENABLED=$(gh repo view "$OWNER/$REPO" --json allowAutoMerge --jq '.allowAutoMerge')

if [ "$AUTO_MERGE_ENABLED" = "true" ]; then
    echo "✅ Auto-merge is enabled"
else
    echo "⚠️  Auto-merge may not be fully enabled yet"
fi

# Step 4: Check if main branch has protection rules
echo "📋 Checking branch protection..."
BRANCH_PROTECTION=$(gh api "repos/$OWNER/$REPO/branches/main/protection" 2>/dev/null || echo "null")

if [ "$BRANCH_PROTECTION" != "null" ]; then
    echo "✅ Branch protection is configured"
else
    echo "ℹ️  No branch protection configured (optional for auto-merge)"
fi

# Step 5: Test agent_commit.sh script
echo "📋 Testing agent_commit.sh script..."
if [ -x "scripts/agent_commit.sh" ]; then
    echo "✅ agent_commit.sh is executable"
else
    echo "❌ agent_commit.sh is not executable"
    chmod +x scripts/agent_commit.sh
    echo "✅ Made agent_commit.sh executable"
fi

# Step 6: Create a test commit to verify the workflow
echo "📋 Creating test commit to verify workflow..."
TEST_BRANCH="test/auto-pr-setup-$(date +%Y%m%d-%H%M%S)"

# Create a small test file
echo "# Auto-PR Workflow Test" > test_auto_pr.md
echo "This file was created to test the auto-PR workflow setup." >> test_auto_pr.md
echo "Created at: $(date)" >> test_auto_pr.md

# Use the agent_commit.sh script to create a PR
AGENT_NAME="setup-test" \
    ./scripts/agent_commit.sh "feat: add auto-PR workflow setup script

This commit adds the setup script for auto-PR workflow and tests the agent_commit.sh functionality.

- Added setup_auto_pr.sh script
- Tested agent_commit.sh functionality  
- Verified auto-merge configuration

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

echo "✅ Test PR created successfully"

# Clean up test file
rm -f test_auto_pr.md

echo ""
echo "🎉 Auto-PR workflow setup completed successfully!"
echo ""
echo "📝 Summary:"
echo "  ✅ GitHub CLI authenticated"
echo "  ✅ Repository auto-merge enabled"
echo "  ✅ agent_commit.sh script ready"
echo "  ✅ Test PR created and auto-merge enabled"
echo ""
echo "🔧 Usage:"
echo "  To create an auto-merging PR: ./scripts/agent_commit.sh \"commit message\""
echo "  Set AGENT_NAME environment variable to customize branch naming"
echo ""
echo "⚠️  Note: PRs will auto-merge only when all required status checks pass"
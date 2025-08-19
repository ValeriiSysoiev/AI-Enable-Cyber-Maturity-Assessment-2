#!/usr/bin/env bash
set -euo pipefail

# Detect owner/repo from git remote if not provided
get_owner_repo() {
  local url
  url="$(git config --get remote.origin.url || true)"
  # Support https and ssh
  if [[ "$url" =~ github.com[:/](.+)/(.+)\.git$ ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
  else
    echo "" ""
  fi
}

OWNER="${OWNER:-}"
REPO="${REPO:-}"
read -r DET_OWNER DET_REPO < <(get_owner_repo)
OWNER="${OWNER:-${DET_OWNER:-ValeriiSysoiev}}"
REPO="${REPO:-${DET_REPO:-AI-Enable-Cyber-Maturity-Assessment-2}}"
BASE="${BASE:-main}"
AGENT_NAME="${AGENT_NAME:-claude}"
MSG="${1:-chore(agent): automated update}"
TS="$(date +%Y%m%d-%H%M%S)"
BR="agent/${AGENT_NAME}/${TS}"

# Ensure git identity (fallback identity)
git config user.name  "${GIT_AUTHOR_NAME:-Claude Agent}"
git config user.email "${GIT_AUTHOR_EMAIL:-claude-bot@local}"

# Sync base
git fetch origin "$BASE" --prune
git checkout -B "$BR" "origin/$BASE"

# Stage & commit
git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit. Exiting."
  exit 0
fi
git commit -m "$MSG"

# Push branch
git push -u origin "$BR"

# Create PR
TITLE="$MSG"
BODY="Automated change by ${AGENT_NAME}. Auto-merge will occur when required checks (if any) pass."
PR_URL=$(gh pr create \
  --base "$BASE" \
  --head "$BR" \
  --title "$TITLE" \
  --body "$BODY" \
  --label "automerge,agent" \
  --repo "$OWNER/$REPO")
echo "PR created: $PR_URL"

# Enable auto-merge (squash)
gh pr merge --auto --squash "$PR_URL" --repo "$OWNER/$REPO"
echo "Auto-merge enabled. PR will merge once required checks (if any) are green."
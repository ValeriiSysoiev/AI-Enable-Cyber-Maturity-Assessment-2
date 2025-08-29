# Repository History Migration Guide

## Overview
This document provides step-by-step instructions for team members during the git history cleanup process. **All team members must follow these steps** to maintain repository consistency.

## Timeline & Phases

### Phase 1: Pre-Migration (Current)
**Status**: In Progress
- [x] Repository size analysis completed
- [x] Bloat sources identified and classified
- [x] Working tree cleanup completed (2.9GB → 1.3GB)
- [ ] Team notification sent (48 hours notice required)
- [ ] All pending PRs merged or documented

### Phase 2: History Cleanup (Planned)
**Duration**: 2-3 hours
**Impact**: Repository write-locked
- History rewrite execution
- Force push new clean history
- Verification and testing

### Phase 3: Team Migration (Post-cleanup)
**Duration**: 1 week
**Action Required**: All team members must re-clone

## Pre-Migration Checklist

### For All Team Members
**Complete by [DATE]:**

1. **Commit All Work**
   ```bash
   git add .
   git commit -m "Pre-migration checkpoint"
   git push origin your-branch
   ```

2. **List Your Local Branches**
   ```bash
   git branch -a > ~/my-branches-backup.txt
   echo "My important local branches:" >> ~/my-branches-backup.txt
   git branch --no-merged >> ~/my-branches-backup.txt
   ```

3. **Backup Local Changes**
   ```bash
   # If you have uncommitted work
   git stash push -m "Pre-migration stash $(date)"
   git stash list > ~/my-stashes-backup.txt
   
   # Export any important patches
   git format-patch origin/main..HEAD --output-directory ~/git-patches-backup/
   ```

4. **Document Your Environment**
   ```bash
   # Save your current working setup
   echo "# My Development Environment" > ~/dev-environment-backup.md
   echo "Current branch: $(git branch --show-current)" >> ~/dev-environment-backup.md
   echo "Remote URLs:" >> ~/dev-environment-backup.md
   git remote -v >> ~/dev-environment-backup.md
   ```

### For Project Maintainers
1. **Merge or Document PRs**
   - All approved PRs should be merged before migration
   - Document any PRs that cannot be merged
   - Export PR diffs for reconstruction if needed

2. **Archive Release Branches**
   - Ensure all release branches are pushed
   - Tag any important commits that might be lost

## Migration Execution

### What Happens During Migration
1. **History Rewrite**: Large objects removed from all commits
2. **Force Push**: New clean history replaces old history
3. **Size Reduction**: Repository size drops from 1.3GB to ~300-500MB

### Expected Results
- All source code preserved
- Commit messages and authorship maintained
- Large build artifacts and binaries removed
- All SHA hashes will change (history rewrite effect)

## Post-Migration Instructions

### CRITICAL: All Team Members Must Re-clone

**❌ DO NOT:**
- Try to pull/fetch existing clones
- Attempt to rebase existing branches
- Use `git pull --force` or similar commands

**✅ DO THIS:**
```bash
# 1. Backup your current clone (just in case)
mv your-repo-directory your-repo-OLD-$(date +%Y%m%d)

# 2. Fresh clone from cleaned repository
git clone https://github.com/your-org/your-repo.git
cd your-repo

# 3. Verify size reduction
du -sh .git/  # Should be < 200MB

# 4. Restore your development environment
git config --local user.name "Your Name"
git config --local user.email "your.email@company.com"

# 5. Recreate your local branches (use your backup list)
git checkout -b your-feature-branch
```

### Restoring Your Work

#### If You Had Local Branches:
```bash
# From your backup location
cd ~/git-patches-backup
git apply *.patch  # Apply your saved patches

# OR manually recreate branches
git checkout -b recreated-feature
# Copy your code changes from OLD directory
```

#### If You Had Stashed Work:
Your stashes are tied to the old history and cannot be directly restored. Use your OLD directory to manually copy changes:
```bash
# Compare and copy manually
diff -r your-repo-OLD/path/to/file your-repo/path/to/file
```

## Verification Steps

### Individual Verification
After re-cloning, verify:
```bash
# 1. Repository size
du -sh . && du -sh .git/
# Expected: Total < 500MB, .git < 200MB

# 2. Your source code is intact
ls -la  # Check key files exist
git log --oneline -10  # Verify recent commits (different SHAs)

# 3. Development environment works
npm install  # or pip install -r requirements.txt
npm run dev  # or python app/main.py
```

### Team Verification
1. **All workflows pass**: CI/CD pipelines working
2. **API functional**: All endpoints responding
3. **No missing files**: Source code complete
4. **Performance improved**: Faster clone and fetch times

## Troubleshooting

### Common Issues

**Issue**: "Git says remote has diverged"
```
Solution: You're using an old clone. Delete and re-clone fresh.
DO NOT try to merge or rebase.
```

**Issue**: "My branch is missing"
```
Solution: Recreate from your backup patches or copy from OLD directory.
All local branches need to be recreated after history rewrite.
```

**Issue**: "Some commits have different SHAs"
```
Solution: This is expected. History rewrite changes all SHA hashes.
Use commit messages and dates to identify equivalent commits.
```

**Issue**: "Repository clone is still large"
```
Solution: Ensure you're cloning from origin after migration.
Clear any local caches: rm -rf ~/.git* cache directories
```

### Emergency Rollback
If critical issues are discovered:
1. **Notify team immediately** - stop all work
2. **Restore from backup** - maintainers will restore old history
3. **Wait for all-clear** - don't start work until issues resolved

## Timeline & Communication

### Before Migration
- **T-48h**: Team notification sent
- **T-24h**: Final reminder, deadline for preparations
- **T-2h**: Migration starts, repository locked

### During Migration
- **Real-time updates** in team chat
- **Progress notifications** at key milestones
- **Completion notification** when ready for re-clone

### After Migration
- **Day 1-3**: Team re-clones and verifies
- **Day 4-7**: Monitor for issues, performance verification
- **Week 2**: Retrospective and lessons learned

## Support & Help

### During Migration Week
- **Slack channel**: #repo-migration-help
- **Point person**: [DevOps Team Lead]
- **Documentation**: This guide + main migration plan

### Quick Help Commands
```bash
# Check if you need to re-clone (run in your repo)
git log --oneline -5 | head -1
# If the SHA doesn't match the team announcement, re-clone

# Quick verification of clean repository
find . -name "node_modules" -o -name ".next" -o -name ".terraform" -o -name "__pycache__"
# Should return empty (these are now ignored)

# Performance test
time git clone [repo-url] test-clone && du -sh test-clone/
# Should complete in < 30 seconds and be < 500MB
```

---

**Document Status**: Ready for Distribution  
**Last Updated**: 2025-08-29  
**Migration Target Date**: [TO BE SCHEDULED]
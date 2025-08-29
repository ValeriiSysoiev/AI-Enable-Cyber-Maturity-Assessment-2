# Repository Asset Management Policy

## Overview
This policy defines what assets belong in the git repository versus external storage systems, establishing size limits and governance to maintain a lean, performant codebase.

## Core Principles

### Repository Purpose
- **Source Code**: All application source code, configuration, and infrastructure-as-code
- **Essential Assets**: Minimal test data, small documentation images, critical configuration files
- **Documentation**: Markdown docs, architectural diagrams (optimized), setup guides

### External Storage
- **Build Artifacts**: All compiled outputs, dependency caches, generated files
- **Large Media**: Screenshots, videos, large images, demo recordings
- **Runtime Data**: Logs, temporary files, user uploads, data exports
- **Development Dependencies**: node_modules, .venv, .terraform providers

## Size Limits & Guidelines

### Repository Limits
- **File Size**: Individual files > 10MB require justification and review
- **Total Repository**: Target < 100MB for source code, < 500MB total including essential assets
- **History Cleanliness**: No build artifacts, caches, or temporary files in git history

### Asset Categories

#### ✅ ALLOWED IN REPOSITORY
| Category | Max Size | Location | Examples |
|----------|----------|----------|-----------|
| Source Code | No limit | Anywhere | .py, .ts, .tsx, .tf, .yml |
| Configuration | 1MB | Root, /config | .env.example, package.json, terraform files |
| Small Images | 500KB | /docs, /public | Icons, logos, small diagrams |
| Test Data | 1MB total | /data/projects/demo | Minimal sample datasets |
| Documentation | No limit | /docs, README.md | Markdown, small images |

#### ❌ PROHIBITED IN REPOSITORY
| Category | Why Prohibited | Alternative Storage |
|----------|----------------|-------------------|
| Build Outputs | Regenerated on build, large, platform-specific | CI/CD artifacts, container registries |
| Dependencies | Downloadable via package managers | npm install, pip install, terraform init |
| Runtime Logs | Generated during execution, grow indefinitely | Azure Monitor, log aggregation |
| User Uploads | Variable size, user content | Azure Blob Storage |
| Large Media | Performance impact, version irrelevant | Azure Blob Storage, CDN |
| Backup Files | Temporary, point-in-time snapshots | Azure Backup, external backup systems |
| Cache Files | Performance optimization, regenerable | Local machine only |

## Implementation Rules

### .gitignore Requirements
All prohibited categories MUST be in .gitignore:

```gitignore
# Build Outputs
**/node_modules/
**/.next/
**/dist/
**/build/
**/__pycache__/

# Dependencies
.venv/
.terraform/

# Runtime Files
*.log
logs/
temp/
*.tmp

# Platform Specific
.DS_Store
Thumbs.db

# Backup Files
*.bak
backup-*
```

### CI/CD Enforcement
1. **Pre-commit hooks**: Block commits with files > 10MB
2. **GitHub Actions**: Fail builds if prohibited files detected
3. **Branch protection**: Require status checks to pass before merge

### LFS Policy (Use Sparingly)
Git LFS should ONLY be used for:
- **Versioned source assets**: PSD files, AI files that developers modify
- **Essential binary data**: Small datasets required for core functionality
- **Documentation media**: If truly essential and optimized

LFS should NOT be used for:
- Build artifacts (use CI/CD artifact storage)
- User content (use Azure Blob Storage)
- Development dependencies (use package managers)

## Azure Storage Integration

### For Large Assets
- **Container**: `repo-assets`
- **Structure**: `/{env}/{asset-type}/{filename}`
- **Access**: Public read for docs, authenticated for sensitive data

### For Build Artifacts
- **CI/CD Artifacts**: GitHub Actions artifact storage (90-day retention)
- **Container Images**: Azure Container Registry
- **Release Assets**: GitHub Releases (for distribution)

## Remediation Procedures

### Working Tree Cleanup
1. Remove all prohibited files from working directory
2. Update .gitignore to prevent recurrence
3. Commit .gitignore changes
4. Verify clean working tree

### History Cleanup (When Required)
1. **Backup repository** before any history rewriting
2. Use `git filter-repo` to remove large blobs from history
3. Force push to rewrite GitHub history (coordinate with team)
4. All contributors must re-clone repository

### Migration Process
1. **Inventory**: Catalog all assets being moved
2. **Upload**: Move large assets to Azure Storage
3. **Update References**: Change code to reference external URLs
4. **Validate**: Ensure application functionality unchanged
5. **Cleanup**: Remove assets from repository and update .gitignore

## Monitoring & Compliance

### Regular Audits
- **Weekly**: Automated size check in CI/CD
- **Monthly**: Manual review of largest files
- **Quarterly**: Complete repository health assessment

### Metrics to Track
- Total repository size (target: < 500MB)
- Largest individual files (alert if > 10MB)
- Git history growth rate
- .gitignore compliance

### Violation Response
1. **Detection**: Automated alerts for policy violations
2. **Immediate**: Block merge until resolved
3. **Remediation**: Work with contributor to fix violation
4. **Prevention**: Update tooling to prevent recurrence

## Tool Recommendations

### Size Analysis
- `git-sizer`: Analyze repository structure and size
- `du -ah | sort -rh`: Find large directories/files
- `git ls-files --cached`: Check what's tracked

### History Cleanup
- `git filter-repo`: Modern tool for history rewriting
- `git rev-list --objects --all`: Find large objects in history
- `BFG Repo-Cleaner`: Alternative for simpler cases

### Prevention
- `pre-commit`: Git hooks for policy enforcement
- GitHub Actions: Automated size checks
- `gitattributes`: LFS configuration when needed

---

**Policy Version**: 1.0  
**Effective Date**: 2025-08-29  
**Review Schedule**: Quarterly  
**Owner**: DevOps Team
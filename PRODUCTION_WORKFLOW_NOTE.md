# Production Workflow Creation Note

Due to GitHub OAuth scope limitations (workflow scope not available), the production workflow file changes will be committed but may need manual verification.

## Production Workflow Features
- Mirrors staging workflow with production-specific variables  
- Supports both `workflow_dispatch` and `release: published` triggers
- Conditional Azure Container Apps deployment with graceful skip
- Production environment protection with revision suffixes
- Health checks with retry logic and stabilization wait
- Build/push to GHCR with both SHA and latest tags

## Manual Verification Required
If the workflow file doesn't appear correctly in GitHub, manually verify the production deployment workflow is properly configured.
# GitHub Actions Deployment Setup

This document explains how to configure GitHub Actions for Azure deployment.

## Required GitHub Secrets

To enable the deployment workflows, you need to configure the following secrets in your GitHub repository:

### 1. Azure Authentication

**AZURE_CREDENTIALS** - JSON object containing Azure service principal credentials:
```json
{
  "clientId": "your-client-id",
  "clientSecret": "your-client-secret", 
  "subscriptionId": "your-subscription-id",
  "tenantId": "your-tenant-id"
}
```

### 2. Azure Resources

**AZURE_CONTAINER_REGISTRY** - Name of your Azure Container Registry (e.g., `myregistry`)

**AZURE_RESOURCE_GROUP** - Name of your Azure Resource Group (e.g., `rg-myapp-prod`)

**API_CONTAINER_APP** - Name of your API Container App (e.g., `api-myapp-prod`)

**WEB_CONTAINER_APP** - Name of your WEB Container App (e.g., `web-myapp-prod`)

### 3. Verification Endpoints (Optional)

**API_ENDPOINT** - Full URL to your API endpoint (e.g., `https://api-myapp-prod.azurecontainerapps.io`)

**WEB_ENDPOINT** - Full URL to your web endpoint (e.g., `https://web-myapp-prod.azurecontainerapps.io`)

## Setting up Azure Service Principal

1. **Create a Service Principal:**
   ```bash
   az ad sp create-for-rbac --name "github-actions-sp" --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group-name} \
     --sdk-auth
   ```

2. **Copy the JSON output** and use it as the `AZURE_CREDENTIALS` secret.

3. **Grant additional permissions** if needed:
   ```bash
   # For Container Registry access
   az role assignment create --assignee {client-id} \
     --role "AcrPush" \
     --scope /subscriptions/{subscription-id}/resourceGroups/{resource-group-name}/providers/Microsoft.ContainerRegistry/registries/{registry-name}
   ```

## Configuring GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact names listed above

## Workflow Behavior

### Without Secrets Configured
- **CI Workflow** (`ci.yml`) - ✅ Runs basic validation, linting, and build tests
- **Release Workflow** (`release.yml`) - ❌ Fails with helpful error messages
- **Verification Workflow** (`release_verify.yml`) - ⚠️ Skips tests gracefully

### With Secrets Configured
- **CI Workflow** - ✅ Runs full validation
- **Release Workflow** - ✅ Deploys to Azure with rollback capability
- **Verification Workflow** - ✅ Runs comprehensive health checks

## Troubleshooting

### Common Issues

1. **"Login failed with Error: Using auth-type: SERVICE_PRINCIPAL"**
   - Ensure `AZURE_CREDENTIALS` is properly formatted JSON
   - Verify the service principal has correct permissions
   - Check that all required fields are present in the JSON

2. **"Missing required secrets"**
   - Verify all secret names match exactly (case-sensitive)
   - Ensure secrets are set at the repository level, not environment level

3. **Container Registry access denied**
   - Verify the service principal has `AcrPush` role on the registry
   - Ensure the registry name in secrets matches exactly

4. **Container App deployment fails**
   - Verify the service principal has `Contributor` role on the resource group
   - Ensure Container App names in secrets match exactly

### Testing the Setup

1. **Test CI only:** Push to a feature branch - only `ci.yml` should run
2. **Test full deployment:** Push to `main` branch - all workflows should run
3. **Check logs:** Review GitHub Actions logs for detailed error messages

## Security Best Practices

- Use least-privilege access for service principals
- Regularly rotate service principal credentials
- Monitor deployment logs for security issues
- Use environment-specific secrets for different stages (dev/staging/prod)

## Support

If you encounter issues:
1. Check the GitHub Actions logs for detailed error messages
2. Verify all secrets are configured correctly
3. Test Azure CLI commands locally with the same credentials
4. Review Azure resource permissions and access policies

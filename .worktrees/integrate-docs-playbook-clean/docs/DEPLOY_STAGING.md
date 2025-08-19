# Azure Staging Deployment Guide

This guide covers the prerequisites and setup required for deploying the Cyber Maturity Assessment application to Azure staging environments.

## Prerequisites

### Azure Subscription Requirements

Before deploying to Azure, ensure your subscription and environment meet these requirements:

1. **Active Azure Subscription** with sufficient quota
2. **Required Permissions** on the subscription:
   - `Owner` or `Contributor` role for resource management
   - `User Access Administrator` for managed identity role assignments
3. **Azure CLI** installed and authenticated

### Required Azure Resource Providers

The following Azure resource providers must be registered in your subscription:

- `Microsoft.OperationalInsights` - For Log Analytics workspaces and monitoring
- `Microsoft.Insights` - For Application Insights and alert rules
- `Microsoft.ContainerRegistry` - For Azure Container Registry
- `Microsoft.App` - For Container Apps
- `Microsoft.Storage` - For storage accounts
- `Microsoft.DocumentDB` - For Cosmos DB
- `Microsoft.Search` - For Azure Cognitive Search
- `Microsoft.CognitiveServices` - For Azure OpenAI Service
- `Microsoft.KeyVault` - For Azure Key Vault

## Provider Registration

### Automatic Registration

Use the provided script to automatically ensure required providers are registered:

```bash
# Set environment variables
export AZURE_RESOURCE_GROUP="rg-cybermaturity-staging"
export AZURE_LOCATION="East US"

# Run the providers ensure script
./scripts/azure/providers_ensure.sh
```

### Script Features

The `providers_ensure.sh` script provides:

- **Idempotent Operation**: Safe to run multiple times
- **Resource Group Management**: Creates resource group if it doesn't exist
- **Provider Registration**: Registers Microsoft.OperationalInsights and Microsoft.Insights
- **Bounded Execution**: Maximum wait time of 480 seconds (8 minutes) with timeout handling
- **Clear Error Messages**: Detailed error reporting with remediation guidance
- **Permission Validation**: Checks for Azure CLI authentication and subscription access

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_RESOURCE_GROUP` | Target resource group name | None (optional) |
| `AZURE_LOCATION` | Azure region for resource group | "East US" |
| `MAX_WAIT` | Maximum wait time for provider registration (seconds) | 480 |

### Manual Provider Registration

If you prefer to register providers manually:

```bash
# Check current provider status
az provider show --namespace Microsoft.OperationalInsights --query 'registrationState'
az provider show --namespace Microsoft.Insights --query 'registrationState'

# Register providers if needed
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Insights

# Monitor registration progress
az provider show --namespace Microsoft.OperationalInsights --query 'registrationState'
az provider show --namespace Microsoft.Insights --query 'registrationState'
```

## Permission Requirements

### Subscription-Level Permissions

Your account or service principal needs these permissions:

1. **Resource Management**:
   - Create and manage resource groups
   - Deploy Azure resources (Container Apps, Cosmos DB, etc.)
   - Configure networking and security settings

2. **Identity and Access Management**:
   - Create and manage managed identities
   - Assign roles to managed identities
   - Configure RBAC for resources

3. **Monitoring and Logging**:
   - Create Log Analytics workspaces
   - Configure diagnostic settings
   - Set up alert rules

### Required Azure Roles

For deployment, assign one of these roles to your account:

- **Owner** (Recommended for staging): Full access to all resources and role assignments
- **Contributor + User Access Administrator**: Resource management + role assignment capabilities

### Service Principal Setup (CI/CD)

For automated deployments, create a service principal with appropriate permissions:

```bash
# Create service principal
az ad sp create-for-rbac --name "sp-cybermaturity-staging" \
  --role "Contributor" \
  --scopes "/subscriptions/{subscription-id}"

# Add User Access Administrator role for managed identity assignments
az role assignment create \
  --assignee {service-principal-id} \
  --role "User Access Administrator" \
  --scope "/subscriptions/{subscription-id}"
```

## Troubleshooting

### Provider Registration Issues

**Problem**: Provider registration times out or fails

**Solutions**:
1. **Check Permissions**: Ensure you have `Contributor` or `Owner` role
2. **Verify Subscription**: Confirm subscription is active and not disabled
3. **Regional Issues**: Try a different Azure region if registration consistently fails
4. **Service Health**: Check [Azure Service Health](https://status.azure.com/) for known issues
5. **Increase Timeout**: Set `MAX_WAIT=900` for slower regions

**Example**:
```bash
# Increase timeout for slow regions
export MAX_WAIT=900
./scripts/azure/providers_ensure.sh
```

### Common Error Messages

#### "Failed to get subscription information"
- **Cause**: Azure CLI not authenticated or no active subscription
- **Solution**: Run `az login` and `az account set --subscription {id}`

#### "Failed to create resource group"
- **Cause**: Insufficient permissions or invalid location
- **Solution**: Verify `Contributor` role and valid Azure region name

#### "Provider registration timed out"
- **Cause**: Provider registration can take 10-15 minutes in some regions
- **Solution**: Wait and re-run, or increase `MAX_WAIT` value

## Next Steps

After successful provider registration:

1. **Configure Terraform Variables**: Set up `terraform.tfvars` with your environment values
2. **Initialize Terraform**: Run `terraform init` in the `/infra` directory  
3. **Plan Deployment**: Run `terraform plan` to review changes
4. **Deploy Infrastructure**: Run `terraform apply` to create resources
5. **Configure Applications**: Deploy and configure the API and web applications

## Security Considerations

- **Never commit secrets** to version control
- **Use managed identities** for service-to-service authentication
- **Enable audit logging** for all resource changes
- **Apply least privilege** principles for all role assignments
- **Regular access reviews** for service principals and user accounts

For additional security guidance, see [SECURITY.md](./SECURITY.md).
# Staging Environment Auto-Creation Setup

## Overview
This document describes the changes needed to make the 'staging' GitHub environment auto-create on first workflow run.

## Required Changes to `.github/workflows/deploy_staging.yml`

Add the following `environment` block to the `deploy_azure_aca` job (around line 40):

```yaml
environment:
  name: staging
  url: ${{ steps.expose_url.outputs.url }}
```

Add the following step after the "Deploy Web" step (around line 60):

```yaml
- name: Expose staging URL
  id: expose_url
  run: |
    # Get the web app URL from Azure Container App
    WEB_URL=$(az containerapp show \
      --name $ACA_APP_WEB --resource-group $ACA_RG \
      --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    
    if [ -n "$WEB_URL" ]; then
      STAGING_URL="https://$WEB_URL"
      echo "url=$STAGING_URL" >> $GITHUB_OUTPUT
      echo "::notice::Staging deployed at: $STAGING_URL"
    else
      echo "::warning::Could not determine staging URL"
    fi
```

## Implementation Notes
- The environment block will auto-create the 'staging' environment in GitHub on first workflow run
- The URL will be populated with the Azure Container App FQDN when available
- Manual workflow file update required due to OAuth scope limitations

## Testing
After implementing these changes, trigger the staging deployment workflow to automatically create the GitHub environment.
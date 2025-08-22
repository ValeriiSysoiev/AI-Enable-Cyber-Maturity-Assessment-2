# Deploy Staging Workflow Fix - Manual Update Required

## Issue
The staging deployment workflow needs updates to support graceful ACA skipping and improved health checks.

## Required Manual Fix

Edit `.github/workflows/deploy_staging.yml` and apply these changes:

### 1. Replace the duplicate "Compute & print staging URL" steps with:

```yaml
      - name: Compute & print staging URL
        id: staging_url
        shell: bash
        run: |
          if [[ -n "${STAGING_URL}" ]]; then
            echo "STAGING_URL=${STAGING_URL}"
            echo "::notice::Staging URL (configured): ${STAGING_URL}"
          elif [[ -n "${ACA_APP_WEB}" && -n "${ACA_ENV}" ]]; then
            COMPUTED_URL="https://${ACA_APP_WEB}.${ACA_ENV}.azurecontainerapps.io"
            echo "STAGING_URL=${COMPUTED_URL}"
            echo "::notice::Staging URL (computed from ACA): ${COMPUTED_URL}"
          else
            echo "::notice::No staging URL available (set STAGING_URL or ACA_APP_WEB + ACA_ENV)"
          fi
```

### 2. Replace the health check steps with a separate job:

```yaml
  verify_staging:
    needs: build_and_push_ghcr
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Wait for deployment
        shell: bash
        run: |
          echo "::notice::Waiting 30 seconds for deployment to stabilize..."
          sleep 30

      - name: Staging health check
        shell: bash
        run: |
          # Use STAGING_URL if set, otherwise try ACA computed URL
          if [[ -n "${STAGING_URL}" ]]; then
            URL_TO_CHECK="${STAGING_URL}"
            echo "::notice::Using configured STAGING_URL: $URL_TO_CHECK"
          elif [[ -n "${ACA_APP_WEB}" && -n "${ACA_ENV}" ]]; then
            URL_TO_CHECK="https://${ACA_APP_WEB}.${ACA_ENV}.azurecontainerapps.io"
            echo "::notice::Using computed ACA URL: $URL_TO_CHECK"
          else
            echo "::warning::No staging URL available to check"
            echo "::notice::Set STAGING_URL variable or provide ACA_APP_WEB + ACA_ENV"
            exit 0
          fi
          
          # Perform health check with retries
          echo "::notice::Performing health check on: $URL_TO_CHECK"
          for i in {1..5}; do
            if curl -f -s --max-time 10 "$URL_TO_CHECK/" > /dev/null; then
              echo "::notice::✅ Health check passed (attempt $i)"
              exit 0
            else
              echo "::warning::Health check failed (attempt $i/5)"
              if [ $i -eq 5 ]; then
                echo "::error::Health check failed after 5 attempts"
                exit 1
              fi
              sleep 5
            fi
          done
```

## Key Improvements

1. **Graceful ACA Skipping**: The workflow continues even when ACA deployment is skipped
2. **Separate Verification Job**: Health checks run independently with `if: always()`
3. **Better URL Handling**: Support both STAGING_URL and computed ACA URLs
4. **Enhanced Retry Logic**: 5 attempts with 5-second backoff
5. **Clearer Logging**: Better status messages for debugging

## After Manual Fix

1. Commit and push the workflow changes
2. Re-trigger the staging deployment: `gh workflow run deploy_staging.yml`
3. The workflow should complete successfully with either path
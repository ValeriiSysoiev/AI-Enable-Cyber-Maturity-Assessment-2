# Staging Workflow Fix Required

## Issue
The staging deployment workflow `.github/workflows/deploy_staging.yml` is incomplete and causing workflow file errors.

## Required Fix
Add the following steps to complete the workflow (after line 103):

```yaml
      - name: Compute & print staging URL
        id: staging_url
        shell: bash
        run: |
          if [[ -n "${STAGING_URL}" ]]; then
            echo "STAGING_URL=${STAGING_URL}"
            echo "::notice::Staging URL (configured): ${STAGING_URL}"
          else
            COMPUTED_URL="https://${ACA_APP_WEB}.${ACA_ENV}.azurecontainerapps.io"
            echo "STAGING_URL=${COMPUTED_URL}"
            echo "::notice::Staging URL (computed): ${COMPUTED_URL}"
          fi

      - name: Wait for deployment stabilization
        shell: bash
        run: |
          echo "::notice::Waiting 30 seconds for deployment to stabilize..."
          sleep 30

      - name: Basic health check
        shell: bash
        run: |
          STAGING_URL_TO_CHECK="${STAGING_URL:-https://${ACA_APP_WEB}.${ACA_ENV}.azurecontainerapps.io}"
          echo "::notice::Performing basic health check on: $STAGING_URL_TO_CHECK"
          
          # Basic health check with retries
          for i in {1..3}; do
            if curl -f -s --max-time 30 "$STAGING_URL_TO_CHECK/" > /dev/null; then
              echo "::notice::Health check passed (attempt $i)"
              break
            else
              echo "::warning::Health check failed (attempt $i)"
              if [ $i -eq 3 ]; then
                echo "::error::Health check failed after 3 attempts"
                exit 1
              fi
              sleep 10
            fi
          done
```

## Manual Steps
1. Edit `.github/workflows/deploy_staging.yml`
2. Replace the incomplete "Compute & print staging URL" step with the complete version above
3. Commit and push the changes
4. Re-run the staging deployment

This fix adds proper workflow completion, deployment stabilization, and health checking.
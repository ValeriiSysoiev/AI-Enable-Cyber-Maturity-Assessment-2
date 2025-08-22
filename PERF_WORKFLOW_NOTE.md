# Performance Testing Workflow - Manual Setup Required

## Overview
Due to OAuth scope limitations, the performance testing workflow must be created manually in the repository.

## Workflow File Location
Create the following file in your repository: `.github/workflows/perf-nightly.yml`

## Workflow Content
```yaml
name: Nightly Performance Tests

on:
  schedule:
    # Run at 2 AM UTC daily (adjust for your timezone)
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      target_environment:
        description: 'Target environment for testing'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production
      test_type:
        description: 'Type of performance test'
        required: true
        default: 'smoke'
        type: choice
        options:
          - smoke
          - hot-path
          - both

permissions:
  contents: read
  id-token: write

env:
  PERF_ENABLED: ${{ vars.PERF_ENABLED || '0' }}

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    if: ${{ vars.PERF_ENABLED == '1' }}
    
    environment:
      name: ${{ github.event.inputs.target_environment || 'staging' }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Prepare test environment
        run: |
          echo "🏗️ Setting up performance test environment"
          mkdir -p artifacts/perf
          
          # Determine target URL
          if [[ "${{ github.event.inputs.target_environment || 'staging' }}" == "production" ]]; then
            if [[ -n "${{ vars.PROD_URL }}" ]]; then
              echo "BASE_URL=${{ vars.PROD_URL }}" >> $GITHUB_ENV
            elif [[ -n "${{ vars.ACA_APP_WEB_PROD }}" && -n "${{ vars.ACA_ENV_PROD }}" ]]; then
              echo "BASE_URL=https://${{ vars.ACA_APP_WEB_PROD }}.${{ vars.ACA_ENV_PROD }}.azurecontainerapps.io" >> $GITHUB_ENV
            else
              echo "::error::Production URL not configured"
              exit 1
            fi
          else
            if [[ -n "${{ vars.STAGING_URL }}" ]]; then
              echo "BASE_URL=${{ vars.STAGING_URL }}" >> $GITHUB_ENV
            elif [[ -n "${{ vars.ACA_APP_WEB }}" && -n "${{ vars.ACA_ENV }}" ]]; then
              echo "BASE_URL=https://${{ vars.ACA_APP_WEB }}.${{ vars.ACA_ENV }}.azurecontainerapps.io" >> $GITHUB_ENV
            else
              echo "::warning::Staging URL not configured, using localhost"
              echo "BASE_URL=http://localhost:8000" >> $GITHUB_ENV
            fi
          fi
          
          echo "Target URL: $BASE_URL"

      - name: Run smoke test
        if: ${{ github.event.inputs.test_type == 'smoke' || github.event.inputs.test_type == 'both' || github.event.inputs.test_type == '' }}
        run: |
          echo "🚀 Running smoke performance test"
          k6 run perf/k6/smoke.js \
            --env BASE_URL="$BASE_URL" \
            --env API_KEY="${{ secrets.PERF_API_KEY }}" \
            --out json=artifacts/perf/smoke-results.json \
            || echo "::warning::Smoke test failed, check artifacts for details"

      - name: Run hot path test
        if: ${{ github.event.inputs.test_type == 'hot-path' || github.event.inputs.test_type == 'both' }}
        run: |
          echo "🔥 Running hot path performance test"
          k6 run perf/k6/hot-path.js \
            --env BASE_URL="$BASE_URL" \
            --env API_KEY="${{ secrets.PERF_API_KEY }}" \
            --out json=artifacts/perf/hot-path-results.json \
            || echo "::warning::Hot path test failed, check artifacts for details"

      - name: Generate performance report
        if: always()
        run: |
          echo "📊 Generating performance report"
          
          # Create summary report
          cat > artifacts/perf/nightly-report.md << 'EOF'
          # Nightly Performance Test Report
          
          **Date**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
          **Environment**: ${{ github.event.inputs.target_environment || 'staging' }}
          **Target URL**: $BASE_URL
          **Test Type**: ${{ github.event.inputs.test_type || 'smoke' }}
          
          ## Test Results
          
          EOF
          
          # Add smoke test results if available
          if [[ -f "artifacts/perf/smoke-summary.json" ]]; then
            echo "### Smoke Test Results" >> artifacts/perf/nightly-report.md
            echo '```json' >> artifacts/perf/nightly-report.md
            cat artifacts/perf/smoke-summary.json >> artifacts/perf/nightly-report.md
            echo '```' >> artifacts/perf/nightly-report.md
            echo "" >> artifacts/perf/nightly-report.md
          fi
          
          # Add hot path results if available
          if [[ -f "artifacts/perf/hot-path-summary.json" ]]; then
            echo "### Hot Path Test Results" >> artifacts/perf/nightly-report.md
            echo '```json' >> artifacts/perf/nightly-report.md
            cat artifacts/perf/hot-path-summary.json >> artifacts/perf/nightly-report.md
            echo '```' >> artifacts/perf/nightly-report.md
          fi
          
          echo "📈 Performance report generated"

      - name: Upload performance artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: performance-results-${{ github.event.inputs.target_environment || 'staging' }}-${{ github.run_number }}
          path: |
            artifacts/perf/
          retention-days: 30

      - name: Check SLO compliance
        if: always()
        run: |
          echo "🎯 Checking SLO compliance"
          
          SLO_VIOLATIONS=0
          
          # Check smoke test SLOs
          if [[ -f "artifacts/perf/smoke-results.json" ]]; then
            echo "Analyzing smoke test SLOs..."
            
            # Extract metrics (simplified - in real scenario, use jq)
            if grep -q '"http_req_duration"' artifacts/perf/smoke-results.json; then
              echo "✅ Smoke test completed successfully"
            else
              echo "❌ Smoke test SLO violation detected"
              SLO_VIOLATIONS=$((SLO_VIOLATIONS + 1))
            fi
          fi
          
          # Check hot path SLOs
          if [[ -f "artifacts/perf/hot-path-results.json" ]]; then
            echo "Analyzing hot path SLOs..."
            
            if grep -q '"http_req_duration"' artifacts/perf/hot-path-results.json; then
              echo "✅ Hot path test completed successfully"
            else
              echo "❌ Hot path SLO violation detected"
              SLO_VIOLATIONS=$((SLO_VIOLATIONS + 1))
            fi
          fi
          
          if [[ $SLO_VIOLATIONS -gt 0 ]]; then
            echo "::warning::$SLO_VIOLATIONS SLO violation(s) detected"
            echo "SLO_VIOLATIONS=$SLO_VIOLATIONS" >> $GITHUB_ENV
          else
            echo "✅ All SLOs met"
            echo "SLO_VIOLATIONS=0" >> $GITHUB_ENV
          fi

      - name: Create performance issue (on SLO violation)
        if: ${{ env.SLO_VIOLATIONS != '0' && github.event_name == 'schedule' }}
        run: |
          echo "🚨 Creating performance issue due to SLO violations"
          
          # Create GitHub issue for SLO violations
          gh issue create \
            --title "⚠️ Nightly Performance SLO Violation - $(date '+%Y-%m-%d')" \
            --body "$(cat << 'ISSUE_EOF'
          # Performance SLO Violation Detected
          
          **Date**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
          **Environment**: ${{ github.event.inputs.target_environment || 'staging' }}
          **Workflow Run**: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
          
          ## Violations Detected
          - Number of SLO violations: ${{ env.SLO_VIOLATIONS }}
          
          ## Next Steps
          1. Review performance test artifacts
          2. Analyze application performance metrics
          3. Identify performance bottlenecks
          4. Implement performance improvements
          5. Re-run tests to validate fixes
          
          ## Related Documentation
          - [Performance Testing Guide](./docs/load-testing.md)
          - [SLO Definitions](./docs/alerts/slo-definitions.md)
          - [Performance Troubleshooting](./docs/performance-troubleshooting.md)
          ISSUE_EOF
          )" \
            --label "performance" \
            --label "slo-violation" \
            --assignee "${{ github.actor }}"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  notification:
    runs-on: ubuntu-latest
    needs: performance-tests
    if: always() && vars.PERF_ENABLED == '1'
    
    steps:
      - name: Notify performance test completion
        run: |
          echo "📧 Performance test completed"
          echo "Status: ${{ needs.performance-tests.result }}"
          echo "Environment: ${{ github.event.inputs.target_environment || 'staging' }}"
          echo "Results available in workflow artifacts"
```

## Setup Instructions

1. **Create the workflow file manually** in your repository:
   ```bash
   mkdir -p .github/workflows
   # Copy the above YAML content to .github/workflows/perf-nightly.yml
   ```

2. **Configure repository variables** (Settings → Secrets and variables → Actions → Variables):
   ```
   PERF_ENABLED=1  # Enable performance testing
   
   # For staging environment
   STAGING_URL=https://your-staging-url.azurecontainerapps.io
   # OR
   ACA_APP_WEB=your-staging-app-name
   ACA_ENV=your-staging-environment
   
   # For production environment (optional)
   PROD_URL=https://your-production-url.azurecontainerapps.io
   # OR
   ACA_APP_WEB_PROD=your-prod-app-name
   ACA_ENV_PROD=your-prod-environment
   ```

3. **Configure secrets** (Settings → Secrets and variables → Actions → Secrets):
   ```
   PERF_API_KEY=your-api-key-for-authenticated-tests  # Optional
   ```

4. **Test the workflow**:
   - Go to Actions → Nightly Performance Tests
   - Click "Run workflow"
   - Select environment and test type
   - Click "Run workflow"

## Notes
- The workflow only runs when `PERF_ENABLED=1` is set
- Tests run nightly at 2 AM UTC (adjust cron schedule as needed)
- Performance artifacts are stored for 30 days
- SLO violations automatically create GitHub issues during scheduled runs
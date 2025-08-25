# UAT Explorer - Automated Testing and Issue Detection

The UAT Explorer is a comprehensive test suite designed for production-safe automated testing and issue detection. It performs safe exploration of the application while collecting detailed telemetry, error patterns, and performance metrics.

## Features

- **Production-Safe Testing**: Only performs non-destructive operations, no POST requests in production
- **Dual Authentication Support**: Handles both AAD and Demo authentication modes automatically
- **Comprehensive Telemetry**: Collects console errors, network failures, JavaScript exceptions, and performance data
- **Visual Documentation**: Captures screenshots and videos on failures for debugging
- **Safe Interactions**: Explores UI controls safely without destructive operations
- **Custom Reporting**: Generates structured JSON reports and human-readable summaries
- **🆕 GitHub Issue Integration**: Automatically creates/updates GitHub issues for test failures with comprehensive context

## Usage

### Basic UAT Testing

```bash
# Run UAT Explorer with default settings
npm run test:e2e:uat

# Run in demo mode (bypasses AAD authentication)
npm run test:e2e:uat:demo

# Run in production mode (headless, optimized for CI/CD)
npm run test:e2e:uat:production

# Test GitHub integration configuration
npm run test:e2e:uat:github
```

### Environment Variables

- `DEMO_E2E=1`: Forces demo authentication mode
- `UAT_HEADLESS=true`: Runs in headless mode for production environments
- `WEB_BASE_URL`: Base URL for the application (defaults to http://localhost:3000)

#### GitHub Integration (Optional)
- `GITHUB_TOKEN`: GitHub API token with repo permissions
- `GITHUB_OWNER`: Repository owner (organization or username)
- `GITHUB_REPO`: Repository name
- `GITHUB_LABEL_PREFIX`: Label prefix for issues (default: "uat")
- `GITHUB_ASSIGNEES`: Comma-separated list of GitHub usernames to assign issues to

### Manual Configuration

```bash
# Run with custom environment
WEB_BASE_URL=https://your-app.com DEMO_E2E=1 npm run test:e2e:uat

# Run with specific Playwright options
npx playwright test --project=uat-explorer --headed --debug
```

## Test Routes Covered

The UAT Explorer automatically tests these critical application routes:

1. **Home Page** (`/`) - Basic application load and navigation
2. **Sign-in Page** (`/signin`) - Authentication system availability
3. **Auth Providers API** (`/api/auth/providers`) - Authentication configuration
4. **Auth Session API** (`/api/auth/session`) - Session management
5. **Engagements** (`/engagements`) - Main application functionality
6. **First Engagement Detail** (`/e/{id}/dashboard`) - Dynamic content loading
7. **New Assessment** (`/new`) - Assessment creation workflow
8. **Health Endpoint** (`/health`) - System health monitoring
9. **Version API** (`/api/version`) - Application version information

## Authentication Handling

### AAD Mode (Production)
- Detects Microsoft AAD redirects
- Records authentication state without completing login
- Safe for production environments where credentials aren't available

### Demo Mode
- Automatically clicks demo/continue buttons
- Bypasses authentication for testing purposes
- Perfect for development and staging environments

## Output Artifacts

All UAT results are stored in `artifacts/uat/` directory:

### Primary Reports
- **`uat_report.json`**: Complete structured test data with all telemetry
- **`uat_summary.json`**: Quick summary for monitoring systems and dashboards
- **`uat_report.md`**: Human-readable report with issues and recommendations

### Error Artifacts
- **Screenshots**: Captured automatically on test failures
- **Videos**: Recording of failed test sessions (when enabled)
- **Console logs**: JavaScript console output during failures

## Report Structure

### UAT Report Schema

```json
{
  "testRun": {
    "id": "uat-timestamp-random",
    "timestamp": 1640995200000,
    "duration": 45000,
    "success": true,
    "environment": {
      "authMode": "AAD|DEMO",
      "baseUrl": "https://app.com",
      "userAgent": "Mozilla/5.0...",
      "viewport": { "width": 1280, "height": 720 }
    }
  },
  "steps": [
    {
      "name": "Home Page Load",
      "url": "https://app.com/",
      "httpStatus": 200,
      "timestamp": 1640995200000,
      "duration": 1500,
      "success": true,
      "consoleErrors": [],
      "networkErrors": [],
      "jsExceptions": [],
      "visibleControls": [
        {
          "text": "Sign In",
          "tag": "button",
          "role": "button"
        }
      ],
      "interactions": [
        {
          "type": "hover",
          "target": "Help Link",
          "success": true
        }
      ]
    }
  ],
  "summary": {
    "totalSteps": 9,
    "successfulSteps": 8,
    "failedSteps": 1,
    "totalConsoleErrors": 2,
    "totalNetworkErrors": 0,
    "totalJsExceptions": 0,
    "averageDuration": 2500
  }
}
```

## Integration with Monitoring

The UAT Explorer is designed to integrate with monitoring and alerting systems:

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Run UAT Explorer
  run: npm run test:e2e:uat:production
  
- name: Upload UAT Results
  uses: actions/upload-artifact@v3
  with:
    name: uat-results
    path: artifacts/uat/
```

### Monitoring Integration
The `uat_summary.json` file is optimized for monitoring systems:
- Boolean success/failure status
- Issue counts by severity
- Performance metrics
- Trend data for historical analysis

## Troubleshooting

### Common Issues

**Authentication Failures**
- Ensure `DEMO_E2E=1` is set for demo environments
- Check AAD configuration for production environments
- Verify base URL is accessible

**Network Errors**
- Check firewall/proxy settings
- Ensure all API endpoints are accessible
- Verify SSL certificates in production

**Timeout Issues**
- Increase timeout values in playwright.config.ts
- Check for slow network conditions
- Verify application performance

### Debug Mode

Run with debug output for troubleshooting:
```bash
# Enable Playwright debug mode
DEBUG=pw:api npm run test:e2e:uat

# Run in headed mode to see browser
npx playwright test --project=uat-explorer --headed

# Enable verbose logging
npx playwright test --project=uat-explorer --reporter=list,line
```

## Safety Features

The UAT Explorer includes multiple safety mechanisms:

- **Read-Only Operations**: Only performs GET requests and safe UI interactions
- **No Data Modification**: Avoids any operations that could modify application data
- **Production Detection**: Automatically adjusts behavior for production environments
- **Error Recovery**: Continues testing even if individual steps fail
- **Resource Limits**: Limits interactions and screenshot captures to prevent overwhelming systems

## Continuous Testing

For continuous UAT monitoring:

```bash
# Schedule UAT runs every hour
0 * * * * cd /app && npm run test:e2e:uat:production

# Parse results for alerting
cat artifacts/uat/uat_summary.json | jq '.success' # Returns true/false
cat artifacts/uat/uat_summary.json | jq '.criticalIssues' # Returns count
```

## Best Practices

1. **Run Regularly**: Schedule UAT tests to run at regular intervals
2. **Monitor Trends**: Track success rates and performance over time
3. **Alert on Failures**: Set up alerts for critical issues or degraded performance
4. **Review Reports**: Regularly review detailed reports for optimization opportunities
5. **Update Tests**: Keep test scenarios current with application changes

## Contributing

To extend the UAT Explorer:

1. Add new test routes in `uat-explorer.spec.ts`
2. Enhance the reporter in `reporters/uat-reporter.ts`
3. Update safety mechanisms for new interaction types
4. Add new telemetry collection points
5. Improve error analysis and categorization
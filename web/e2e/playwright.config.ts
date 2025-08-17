import { defineConfig, devices } from '@playwright/test';

/**
 * Comprehensive E2E Testing Configuration for AI Maturity Assessment
 * Supports Evidence RAG, AAD authentication, and cross-service testing
 */
export default defineConfig({
  testDir: './tests',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter configuration for CI/CD integration */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['github'], // GitHub Actions integration
    ['list']
  ],
  
  /* Global test timeout */
  timeout: 60_000,
  
  /* Expect timeout for assertions */
  expect: {
    timeout: 10_000,
  },
  
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.WEB_BASE_URL || 'http://localhost:3000',
    
    /* API base URL for direct API testing - handled via environment variables */
    
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Record video on failure */
    video: 'retain-on-failure',
    
    /* Browser context settings */
    viewport: { width: 1280, height: 720 },
    
    /* Ignore HTTPS errors for development */
    ignoreHTTPSErrors: true,
    
    /* Browser settings */
    launchOptions: {
      // Enable slow motion for debugging
      slowMo: process.env.DEBUG_MODE ? 100 : 0,
    },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    
    /* Test against mobile viewports */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    
    /* Run tests in Firefox (for cross-browser compatibility) */
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    
    /* Enterprise Feature Tests */
    {
      name: 'enterprise-aad',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'e2e/auth/aad-session.json',
      },
      testMatch: '**/aad-groups.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    {
      name: 'enterprise-gdpr',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'e2e/auth/admin-session.json',
      },
      testMatch: '**/gdpr.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    {
      name: 'enterprise-performance',
      use: { 
        ...devices['Desktop Chrome'],
      },
      testMatch: '**/performance.spec.ts',
      dependencies: ['setup-enterprise'],
      timeout: 120_000, // Extended timeout for performance tests
    },
    
    {
      name: 'enterprise-rbac',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'e2e/auth/multi-role-session.json',
      },
      testMatch: '**/rbac.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    {
      name: 'enterprise-admin',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'e2e/auth/admin-session.json',
      },
      testMatch: '**/admin-enterprise.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    /* Test AAD authentication flows */
    {
      name: 'aad-auth',
      use: { 
        ...devices['Desktop Chrome'],
        // Use persistent context for AAD sessions
        storageState: 'e2e/auth/aad-session.json',
      },
      testMatch: '**/auth.spec.ts',
      dependencies: ['setup-aad'],
    },
    
    /* Enhanced Integration Tests */
    {
      name: 'integration-enterprise',
      use: { 
        ...devices['Desktop Chrome'],
        // Extended timeout for integration tests
        timeout: 90_000,
      },
      testMatch: '**/integration.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    /* Cross-browser enterprise testing */
    {
      name: 'enterprise-firefox',
      use: { 
        ...devices['Desktop Firefox'],
        timeout: 90_000,
      },
      testMatch: '**/aad-groups.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    /* Load testing project */
    {
      name: 'load-testing',
      use: { 
        ...devices['Desktop Chrome'],
        timeout: 300_000, // 5 minutes for load tests
      },
      testMatch: '**/load/*.spec.ts',
      dependencies: ['setup-enterprise'],
    },
    
    /* Setup project for enterprise features */
    {
      name: 'setup-enterprise',
      testMatch: '**/enterprise-setup.spec.ts',
      teardown: 'cleanup-enterprise',
    },
    
    /* Setup project for AAD authentication */
    {
      name: 'setup-aad',
      testMatch: '**/auth-setup.spec.ts',
      teardown: 'cleanup-aad',
    },
    
    /* Cleanup projects */
    {
      name: 'cleanup-enterprise',
      testMatch: '**/enterprise-cleanup.spec.ts',
    },
    
    {
      name: 'cleanup-aad',
      testMatch: '**/auth-cleanup.spec.ts',
    },
  ],

  /* Output directories */
  outputDir: 'test-results/',
  
  /* Folder for test artifacts such as screenshots, videos, traces, etc. */
  
  /* Global setup and teardown */
  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),
  
  /* Configure test environment */
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
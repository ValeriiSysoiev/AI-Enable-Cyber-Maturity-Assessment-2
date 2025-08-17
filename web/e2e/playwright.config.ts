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
    
    /* API base URL for direct API testing */
    // @ts-ignore - Custom property for API testing
    apiBaseURL: process.env.API_BASE_URL || 'http://localhost:8000',
    
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
    
    /* Setup project for AAD authentication */
    {
      name: 'setup-aad',
      testMatch: '**/auth-setup.spec.ts',
      teardown: 'cleanup-aad',
    },
    
    /* Cleanup project */
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
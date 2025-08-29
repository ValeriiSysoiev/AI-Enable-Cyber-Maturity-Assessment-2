/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['@azure/cosmos'],
  },
  // Only expose non-sensitive runtime variables
  env: {
    // Public variables only - no secrets
    AUTH_MODE: process.env.AUTH_MODE,
    DEMO_E2E: process.env.DEMO_E2E,
    NEXT_PUBLIC_BUILD_SHA: process.env.NEXT_PUBLIC_BUILD_SHA,
    BUILD_SHA: process.env.BUILD_SHA,
    GITHUB_SHA: process.env.GITHUB_SHA,
  },
  // Public runtime config - no sensitive data
  publicRuntimeConfig: {
    AUTH_MODE: process.env.AUTH_MODE,
    DEMO_E2E: process.env.DEMO_E2E,
    BUILD_SHA: process.env.BUILD_SHA || process.env.GITHUB_SHA,
  },
  // Server-side runtime config - removed to prevent exposure
  // Secrets should be accessed directly via process.env in server components
}

module.exports = nextConfig

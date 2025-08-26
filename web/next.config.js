/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['@azure/cosmos'],
  },
  // Enable runtime environment variables
  env: {
    // These will be available at runtime
    AUTH_MODE: process.env.AUTH_MODE,
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID,
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID,
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET,
    DEMO_E2E: process.env.DEMO_E2E,
    NEXTAUTH_URL: process.env.NEXTAUTH_URL,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
    NEXT_PUBLIC_BUILD_SHA: process.env.NEXT_PUBLIC_BUILD_SHA,
    BUILD_SHA: process.env.BUILD_SHA,
    GITHUB_SHA: process.env.GITHUB_SHA,
  },
  // Also expose as public environment variables for client-side access
  publicRuntimeConfig: {
    AUTH_MODE: process.env.AUTH_MODE,
    DEMO_E2E: process.env.DEMO_E2E,
  },
  // Server-side runtime config
  serverRuntimeConfig: {
    AUTH_MODE: process.env.AUTH_MODE,
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID,
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID,
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET,
    DEMO_E2E: process.env.DEMO_E2E,
    NEXTAUTH_URL: process.env.NEXTAUTH_URL,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
  },
}

module.exports = nextConfig

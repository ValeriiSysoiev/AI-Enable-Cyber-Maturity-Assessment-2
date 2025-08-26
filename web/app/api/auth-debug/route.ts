import { NextResponse } from 'next/server';

export async function GET() {
  // Debug endpoint to check auth environment variables at runtime
  return NextResponse.json({
    AUTH_MODE: process.env.AUTH_MODE || 'not set',
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID ? 'set' : 'not set',
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID ? 'set' : 'not set', 
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET ? 'set' : 'not set',
    DEMO_E2E: process.env.DEMO_E2E || 'not set',
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'not set',
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ? 'set' : 'not set',
    // Computed values
    aadEnabled: process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET,
    demoEnabled: process.env.DEMO_E2E === "1"
  });
}

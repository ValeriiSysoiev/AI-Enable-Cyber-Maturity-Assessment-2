import { NextResponse } from 'next/server';

export async function GET() {
  // Check environment variables to determine auth mode - match NextAuth logic exactly
  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;
  
  const demoEnabled = process.env.DEMO_E2E === "1";
  
  // If AAD is enabled and demo is disabled, use AAD
  const authMode = (aadEnabled && !demoEnabled) ? 'aad' : 'demo';
  
  return NextResponse.json({
    mode: authMode,
    enabled: true,
    aadEnabled,
    demoEnabled
  });
}

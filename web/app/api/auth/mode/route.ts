import { NextResponse } from 'next/server';

export async function GET() {
  const isProduction = process.env.NODE_ENV === 'production';
  
  // Check environment variables to determine auth mode
  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;
  
  const demoEnabled = process.env.DEMO_E2E === "1";
  
  // Log auth mode decision for debugging
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level: 'INFO',
    service: 'web',
    message: 'Auth mode check',
    is_production: isProduction,
    auth_mode: process.env.AUTH_MODE,
    aad_configured: aadEnabled,
    demo_flag: process.env.DEMO_E2E,
    demo_enabled: demoEnabled,
    route: '/api/auth/mode'
  }));
  
  // Production MUST use AAD only - no fallback to demo
  if (isProduction) {
    if (!aadEnabled) {
      // In production, if AAD is not configured, return an error state
      return NextResponse.json({
        mode: 'error',
        enabled: false,
        aadEnabled: false,
        demoEnabled: false,
        error: 'Azure AD authentication is required in production'
      }, { status: 500 });
    }
    
    // Production always uses AAD, regardless of demo flag
    return NextResponse.json({
      mode: 'aad',
      enabled: true,
      aadEnabled: true,
      demoEnabled: false
    });
  }
  
  // Non-production environments can use demo if AAD is not configured
  const authMode = (aadEnabled && !demoEnabled) ? 'aad' : 'demo';
  
  return NextResponse.json({
    mode: authMode,
    enabled: true,
    aadEnabled,
    demoEnabled
  });
}

import { NextResponse } from 'next/server';

export async function GET() {
  // Check environment variables to determine auth mode - match NextAuth logic
  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;
  
  const authMode = aadEnabled ? 'aad' : 'demo';
  
  return NextResponse.json({
    mode: authMode,
    enabled: true,
  });
}
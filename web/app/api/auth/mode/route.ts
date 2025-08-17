import { NextResponse } from 'next/server';

export async function GET() {
  // Check environment variables to determine auth mode
  const aadEnabled = process.env.NEXTAUTH_URL && process.env.AZURE_AD_CLIENT_ID;
  const authMode = aadEnabled ? 'aad' : 'demo';
  
  return NextResponse.json({
    mode: authMode,
    enabled: true,
  });
}
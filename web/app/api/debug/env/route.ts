import { NextResponse } from 'next/server';

export async function GET() {
  // Only allow in development environment
  if (process.env.NODE_ENV === 'production') {
    return new NextResponse('Not Found', { status: 404 });
  }

  return NextResponse.json({
    AUTH_MODE: process.env.AUTH_MODE || "NOT_SET",
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID ? "SET" : "NOT_SET",
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID ? "SET" : "NOT_SET", 
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET ? "SET" : "NOT_SET",
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ? "SET" : "NOT_SET",
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || "NOT_SET",
    DEMO_E2E: process.env.DEMO_E2E || "NOT_SET",
    NODE_ENV: process.env.NODE_ENV || "NOT_SET"
    // Never expose any part of secrets, even partially
  });
}

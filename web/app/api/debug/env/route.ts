import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    AUTH_MODE: process.env.AUTH_MODE || "NOT_SET",
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID ? "SET" : "NOT_SET",
    AZURE_AD_TENANT_ID: process.env.AZURE_AD_TENANT_ID ? "SET" : "NOT_SET", 
    AZURE_AD_CLIENT_SECRET: process.env.AZURE_AD_CLIENT_SECRET ? "SET" : "NOT_SET",
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ? "SET" : "NOT_SET",
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || "NOT_SET",
    DEMO_E2E: process.env.DEMO_E2E || "NOT_SET",
    NODE_ENV: process.env.NODE_ENV || "NOT_SET",
    // Check if KeyVault reference is being resolved
    NEXTAUTH_SECRET_VALUE: process.env.NEXTAUTH_SECRET?.substring(0, 10) + "..." || "NOT_SET"
  });
}

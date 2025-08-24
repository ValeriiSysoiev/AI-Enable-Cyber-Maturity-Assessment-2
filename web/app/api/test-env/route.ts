import { NextResponse } from 'next/server';

export async function GET() {
  // Test if environment variables are available at all
  const testEnv = {
    // These should be set by Dockerfile ENV commands
    AUTH_MODE: process.env.AUTH_MODE || "MISSING",
    NODE_ENV: process.env.NODE_ENV || "MISSING", 
    PORT: process.env.PORT || "MISSING",
    AZURE_AD_CLIENT_ID: process.env.AZURE_AD_CLIENT_ID || "MISSING",
    // Test if we can see any environment variables at all
    allEnvKeys: Object.keys(process.env).slice(0, 10),
    totalEnvCount: Object.keys(process.env).length
  };
  
  return NextResponse.json(testEnv);
}

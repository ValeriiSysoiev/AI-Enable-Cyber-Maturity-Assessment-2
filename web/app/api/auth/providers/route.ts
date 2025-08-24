import { NextResponse } from 'next/server';

export async function GET() {
  // Match NextAuth provider logic exactly
  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;
  
  const demoEnabled = process.env.DEMO_E2E === "1";
  
  const providers = [];
  
  if (aadEnabled) {
    providers.push({
      id: "azure-ad",
      name: "Azure Active Directory",
      type: "oauth"
    });
  }
  
  if (demoEnabled) {
    providers.push({
      id: "credentials",
      name: "Demo",
      type: "credentials"
    });
  }
  
  return NextResponse.json(providers);
}

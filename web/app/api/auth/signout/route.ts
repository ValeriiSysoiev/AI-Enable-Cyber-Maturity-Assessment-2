import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const aadEnabled = process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET;
    
    const demoEnabled = process.env.DEMO_E2E === "1";
    
    if (aadEnabled && !demoEnabled) {
      // For AAD mode, redirect to NextAuth signout
      return NextResponse.redirect(new URL('/api/auth/signout', request.url));
    } else {
      // Demo mode - clear cookie
      const response = NextResponse.json({ success: true });
      response.cookies.delete('demo-email');
      return response;
    }
  } catch (error) {
    console.error('Sign out error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
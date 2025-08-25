import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Direct auth mode check without fetch
    const aadEnabled = process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET;
    
    const demoEnabled = process.env.DEMO_E2E === "1";
    
    if (aadEnabled && !demoEnabled) {
      // AAD mode - return admin user session
      return NextResponse.json({
        user: {
          id: 'va.sysoiev@audit3a.com',
          email: 'va.sysoiev@audit3a.com',
          name: 'Valentyn Sysoiev',
          roles: ['Admin'],
          tenant_id: '8354a4cc-cfd8-41e4-9416-ea0304bc62e1'
        }
      });
    } else {
      // Demo mode - check cookie
      const cookieHeader = request.headers.get('cookie');
      if (cookieHeader && cookieHeader.includes('demo-email')) {
        const email = cookieHeader.split('demo-email=')[1]?.split(';')[0];
        if (email) {
          return NextResponse.json({
            user: {
              id: email,
              email: email,
              name: email.split('@')[0],
              roles: ['Member']
            }
          });
        }
      }
    }
    
    return NextResponse.json({ user: null });
    
  } catch (error) {
    console.error('Session API error:', error);
    return NextResponse.json({ user: null });
  }
}

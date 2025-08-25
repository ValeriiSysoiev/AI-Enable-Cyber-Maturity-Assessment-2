import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Check auth mode first
    const authModeResponse = await fetch(new URL('/api/auth/mode', request.url), {
      cache: 'no-store'
    });
    
    if (!authModeResponse.ok) {
      return NextResponse.json({ user: null });
    }
    
    const authMode = await authModeResponse.json();
    
    if (authMode.mode === 'aad' && authMode.aadEnabled) {
      // For AAD mode, return admin user session
      // In full NextAuth implementation, this would check actual JWT/session
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

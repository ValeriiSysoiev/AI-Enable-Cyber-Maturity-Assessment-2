import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '../../../../lib/auth';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    // Check auth mode
    const aadEnabled = process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET;
    
    const demoEnabled = process.env.DEMO_E2E === "1";
    
    if (aadEnabled && !demoEnabled) {
      // AAD mode - get actual session from NextAuth
      const session = await getServerSession(authOptions);
      if (!session || !session.user) {
        return NextResponse.json({ user: null });
      }
      return NextResponse.json({ user: session.user });
    } else {
      // Demo mode - check cookie (not hardcoded)
      const cookieHeader = request.headers.get('cookie');
      if (cookieHeader && cookieHeader.includes('demo-email')) {
        const email = decodeURIComponent(cookieHeader.split('demo-email=')[1]?.split(';')[0] || '');
        if (email && email.trim()) {
          // In demo mode, no users have admin privileges for security
          const isAdmin = false; // Admin roles must come from AAD in production
          
          return NextResponse.json({
            user: {
              id: email,
              email: email,
              name: email.split('@')[0],
              roles: isAdmin ? ['Admin'] : ['Member']
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
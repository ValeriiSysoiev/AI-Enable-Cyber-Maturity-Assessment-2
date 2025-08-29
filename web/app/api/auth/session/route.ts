import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '../../../../lib/auth';
import { validateDemoSession, checkRateLimit } from '../../../../lib/demo-session';

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
    } else if (demoEnabled) {
      // Demo mode - validate secure session token
      const cookieHeader = request.headers.get('cookie');
      const authHeader = request.headers.get('authorization');
      
      // Try to get token from cookie or Authorization header
      let token: string | undefined;
      
      if (cookieHeader && cookieHeader.includes('demo-session-token')) {
        token = cookieHeader.split('demo-session-token=')[1]?.split(';')[0];
      } else if (authHeader && authHeader.startsWith('Bearer ')) {
        token = authHeader.substring(7);
      }
      
      if (token) {
        // Get client info for validation
        const ipAddress = request.headers.get('x-forwarded-for') || 
                         request.headers.get('x-real-ip') || 
                         undefined;
        const userAgent = request.headers.get('user-agent') || undefined;
        
        // Validate the session token
        const validation = validateDemoSession(token, ipAddress, userAgent);
        
        if (validation.valid && validation.email) {
          // Determine admin role based on email from environment variable
          const adminEmails = (process.env.ADMIN_EMAILS || '')
            .split(',')
            .map(e => e.trim().toLowerCase())
            .filter(e => e);
          
          const isAdmin = adminEmails.includes(validation.email.toLowerCase());
          
          return NextResponse.json({
            user: {
              id: validation.email,
              email: validation.email,
              name: validation.email.split('@')[0],
              roles: isAdmin ? ['Admin'] : ['Member']
            }
          });
        }
      }
      
      // Backward compatibility: check old demo-email cookie (will be deprecated)
      if (cookieHeader && cookieHeader.includes('demo-email')) {
        const email = decodeURIComponent(cookieHeader.split('demo-email=')[1]?.split(';')[0] || '');
        if (email && email.trim()) {
          // Log warning about deprecated method
          console.warn(`Deprecated demo authentication method used for ${email}. Please update to use secure tokens.`);
          
          // Still return user but with limited session
          const adminEmails = (process.env.ADMIN_EMAILS || '')
            .split(',')
            .map(e => e.trim().toLowerCase())
            .filter(e => e);
          
          const isAdmin = adminEmails.includes(email.toLowerCase());
          
          return NextResponse.json({
            user: {
              id: email,
              email: email,
              name: email.split('@')[0],
              roles: isAdmin ? ['Admin'] : ['Member'],
              deprecated: true // Flag to indicate deprecated auth method
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
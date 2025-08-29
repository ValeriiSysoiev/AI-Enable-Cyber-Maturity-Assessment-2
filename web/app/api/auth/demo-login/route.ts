import { NextRequest, NextResponse } from 'next/server';
import { createDemoSession, checkRateLimit } from '../../../../lib/demo-session';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    // Only allow in demo mode
    const demoEnabled = process.env.DEMO_E2E === '1';
    if (!demoEnabled) {
      return NextResponse.json(
        { error: 'Demo authentication is disabled' },
        { status: 403 }
      );
    }
    
    // Parse request body
    const body = await request.json();
    const { email } = body;
    
    if (!email || typeof email !== 'string') {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }
    
    // Get client info
    const ipAddress = request.headers.get('x-forwarded-for') || 
                     request.headers.get('x-real-ip') || 
                     undefined;
    const userAgent = request.headers.get('user-agent') || undefined;
    
    // Check rate limit
    const rateLimitKey = ipAddress || email;
    if (!checkRateLimit(rateLimitKey)) {
      return NextResponse.json(
        { error: 'Too many login attempts. Please try again later.' },
        { status: 429 }
      );
    }
    
    // Create secure session
    const { token, session } = createDemoSession(email, ipAddress, userAgent);
    
    // Determine if user is admin
    const adminEmails = (process.env.ADMIN_EMAILS || '')
      .split(',')
      .map(e => e.trim().toLowerCase())
      .filter(e => e);
    
    const isAdmin = adminEmails.includes(email.toLowerCase());
    
    // Create response with secure cookie
    const response = NextResponse.json({
      success: true,
      user: {
        id: email,
        email: email,
        name: email.split('@')[0],
        roles: isAdmin ? ['Admin'] : ['Member']
      },
      token // Include token in response for API clients
    });
    
    // Set secure cookie with token
    response.cookies.set('demo-session-token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 8 * 60 * 60, // 8 hours
      path: '/'
    });
    
    // Remove old demo-email cookie if present
    response.cookies.delete('demo-email');
    
    return response;
    
  } catch (error) {
    console.error('Demo login error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
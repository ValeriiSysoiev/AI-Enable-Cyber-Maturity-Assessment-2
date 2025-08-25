import { NextRequest, NextResponse } from 'next/server';

/**
 * Demo authentication API route
 * Sets a cookie to simulate user authentication for demo mode
 * Only used when DEMO_E2E=1
 */
export async function POST(request: NextRequest) {
  // Only allow demo signin in demo mode
  if (process.env.DEMO_E2E !== '1') {
    return NextResponse.json(
      { error: 'Demo signin is disabled' },
      { status: 403 }
    );
  }

  try {
    const { email } = await request.json();
    
    if (!email || typeof email !== 'string' || !email.trim()) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }
    
    // Create response
    const response = NextResponse.json({ success: true });
    
    // Set authentication cookie
    response.cookies.set('demo-email', email.trim(), {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/'
    });
    
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      service: 'web',
      message: 'Demo user signed in',
      user_email: email.trim(),
      route: '/api/demo/signin',
      status: 200
    }));
    
    return response;
  } catch (error) {
    console.error('Demo sign in error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
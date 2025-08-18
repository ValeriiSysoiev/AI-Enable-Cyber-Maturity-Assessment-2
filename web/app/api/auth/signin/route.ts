import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

/**
 * Demo authentication API route
 * Sets a cookie to simulate user authentication for S1 demo
 */
export async function POST(request: NextRequest) {
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
      route: '/api/auth/signin',
      status: 200
    }));
    
    return response;
  } catch (error) {
    console.error('Sign in error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
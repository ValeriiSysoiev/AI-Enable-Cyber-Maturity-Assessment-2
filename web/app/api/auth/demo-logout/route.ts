import { NextRequest, NextResponse } from 'next/server';
import { revokeDemoSession } from '../../../../lib/demo-session';

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
    
    // Get token from cookie or Authorization header
    const cookieHeader = request.headers.get('cookie');
    const authHeader = request.headers.get('authorization');
    
    let token: string | undefined;
    
    if (cookieHeader && cookieHeader.includes('demo-session-token')) {
      token = cookieHeader.split('demo-session-token=')[1]?.split(';')[0];
    } else if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.substring(7);
    }
    
    // Revoke the session if token exists
    if (token) {
      revokeDemoSession(token);
    }
    
    // Create response that clears the cookie
    const response = NextResponse.json({
      success: true,
      message: 'Logged out successfully'
    });
    
    // Clear session cookie
    response.cookies.delete('demo-session-token');
    
    // Also clear old demo-email cookie if present
    response.cookies.delete('demo-email');
    
    return response;
    
  } catch (error) {
    console.error('Demo logout error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
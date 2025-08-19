import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // For now, return a demo session response
  // In a full AAD implementation, this would check actual session state
  
  const authHeader = request.headers.get('authorization');
  const email = request.headers.get('x-user-email');
  
  if (email) {
    return NextResponse.json({
      user: {
        id: email,
        email: email,
        name: email.split('@')[0],
        roles: ['user'],
      },
    });
  }
  
  return NextResponse.json({ user: null });
}
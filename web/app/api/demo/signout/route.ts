import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Clear the demo-email cookie
    const response = NextResponse.json({ success: true });
    response.cookies.delete('demo-email');
    return response;
  } catch (error) {
    console.error('Demo sign out error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
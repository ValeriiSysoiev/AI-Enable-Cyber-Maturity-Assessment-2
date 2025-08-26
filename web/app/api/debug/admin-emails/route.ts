import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const adminEmails = process.env.ADMIN_EMAILS;
    const userEmail = request.headers.get('X-User-Email');
    
    return NextResponse.json({
      admin_emails_raw: adminEmails,
      admin_emails_array: adminEmails?.split(',').map(e => e.trim()) || [],
      user_email: userEmail,
      is_admin: adminEmails?.split(',').map(e => e.trim().toLowerCase()).includes(userEmail?.toLowerCase().trim() || '') || false
    });
    
  } catch (error) {
    console.error('Debug admin emails error:', error);
    return NextResponse.json(
      { detail: 'Failed to check admin emails' },
      { status: 500 }
    );
  }
}

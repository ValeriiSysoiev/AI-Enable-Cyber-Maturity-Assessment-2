import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Simple admin email check for demo mode
function isAdminEmail(email: string): boolean {
  const adminEmails = process.env.ADMIN_EMAILS?.split(',').map(e => e.trim().toLowerCase()) || [];
  const normalizedEmail = email.toLowerCase().trim();
  return adminEmails.includes(normalizedEmail);
}

export async function GET(request: NextRequest) {
  try {
    const userEmail = request.headers.get('X-User-Email');
    const authMode = process.env.AUTH_MODE?.toLowerCase() || 'demo';
    const adminEmailsRaw = process.env.ADMIN_EMAILS;
    
    return NextResponse.json({
      user_email: userEmail,
      auth_mode: authMode,
      admin_emails_raw: adminEmailsRaw,
      admin_emails_parsed: adminEmailsRaw?.split(',').map(e => e.trim().toLowerCase()) || [],
      is_admin_check: userEmail ? isAdminEmail(userEmail) : null,
      auth_mode_is_demo: authMode === 'demo',
      auth_mode_is_aad: authMode === 'aad'
    });
    
  } catch (error) {
    console.error('Debug auth mode test error:', error);
    return NextResponse.json(
      { detail: 'Failed to test auth mode' },
      { status: 500 }
    );
  }
}

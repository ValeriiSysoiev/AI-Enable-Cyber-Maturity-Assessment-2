import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Simple admin email check for demo mode
function isAdminEmail(email: string): boolean {
  const adminEmails = process.env.ADMIN_EMAILS?.split(',').map(e => e.trim().toLowerCase()) || [];
  const normalizedEmail = email.toLowerCase().trim();
  
  // Debug logging
  console.log('Admin email check:', {
    email: email,
    normalizedEmail: normalizedEmail,
    adminEmails: adminEmails,
    isAdmin: adminEmails.includes(normalizedEmail)
  });
  
  return adminEmails.includes(normalizedEmail);
}

export async function GET(request: NextRequest) {
  try {
    // Get user email for authorization check
    const userEmail = request.headers.get('X-User-Email');
    if (!userEmail) {
      return NextResponse.json(
        { detail: 'Authentication required' },
        { status: 401 }
      );
    }

    const authMode = process.env.AUTH_MODE?.toLowerCase() || 'demo';
    
    // In demo mode, check if user is in demo admin list
    // In AAD mode, check if user is in ADMIN_EMAILS or has proper role
    let isAdmin = false;
    
    if (authMode === 'demo') {
      // For demo mode, we need to check the backend for demo admin status
      try {
        const backendUrl = process.env.PROXY_TARGET_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${backendUrl}/admin/demo-admins`, {
          headers: {
            'X-User-Email': userEmail,
            'X-Correlation-ID': request.headers.get('X-Correlation-ID') || crypto.randomUUID(),
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          isAdmin = data.emails.includes(userEmail);
        }
      } catch (error) {
        console.warn('Failed to check demo admin status:', error);
        // Fallback to checking ADMIN_EMAILS
        isAdmin = isAdminEmail(userEmail);
      }
    } else {
      // For AAD mode, check ADMIN_EMAILS
      isAdmin = isAdminEmail(userEmail);
    }

    if (!isAdmin) {
      return NextResponse.json(
        { detail: 'Admin access required' },
        { status: 403 }
      );
    }

    // Log admin access for security audit
    console.info('Admin access granted', {
      userEmail,
      authMode,
      timestamp: new Date().toISOString()
    });

    return NextResponse.json({
      status: 'authorized',
      user_email: userEmail,
      auth_mode: authMode,
      is_admin: true
    });
    
  } catch (error) {
    console.error('Auth diagnostics error:', error);
    return NextResponse.json(
      { detail: 'Failed to check admin status' },
      { status: 500 }
    );
  }
}
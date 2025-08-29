import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { createLogger } from '@/lib/logger';

const logger = createLogger('auth-signout');

// Custom signout handler that ensures proper Azure AD logout
export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const callbackUrl = url.searchParams.get('callbackUrl') || '/signin';
  
  // Show confirmation page
  return new NextResponse(
    `<!DOCTYPE html>
    <html>
      <head>
        <title>Sign Out</title>
        <style>
          body { 
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f3f4f6;
          }
          .card {
            background: white;
            padding: 2rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 400px;
          }
          h1 { 
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
            color: #111827;
          }
          p { 
            margin: 0 0 1.5rem 0;
            color: #6b7280;
          }
          button {
            background: #4f46e5;
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 0.375rem;
            font-size: 1rem;
            cursor: pointer;
            font-weight: 500;
          }
          button:hover {
            background: #4338ca;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Sign Out</h1>
          <p>Are you sure you want to sign out?</p>
          <form method="POST" action="/api/auth/signout">
            <input type="hidden" name="callbackUrl" value="${callbackUrl.replace(/"/g, '&quot;')}">
            <button type="submit">Sign out</button>
          </form>
        </div>
      </body>
    </html>`,
    {
      status: 200,
      headers: {
        'Content-Type': 'text/html',
      },
    }
  );
}

export async function POST(request: NextRequest) {
  logger.debug('Processing signout initiated');
  
  // Get the form data
  const formData = await request.formData();
  const callbackUrl = formData.get('callbackUrl')?.toString() || '/signin';
  
  // Get the current session to check if it's Azure AD
  const session = await getServerSession(authOptions);
  
  const cookieStore = cookies();
  
  // Clear ALL auth-related cookies first
  const allCookies = cookieStore.getAll();
  const response = NextResponse.redirect(new URL('/signin', request.url));
  
  for (const cookie of allCookies) {
    if (cookie.name.includes('next-auth') || 
        cookie.name.includes('auth') ||
        cookie.name.includes('session') ||
        cookie.name.includes('csrf') ||
        cookie.name === 'demo-email') {
      
      // Delete the cookie
      response.cookies.delete(cookie.name);
      response.cookies.set(cookie.name, '', {
        value: '',
        maxAge: 0,
        expires: new Date(0),
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        sameSite: 'lax'
      });
    }
  }
  
  // Add headers to clear browser cache
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  response.headers.set('Clear-Site-Data', '"cookies", "storage"');
  
  // Check if we need to do Azure AD federated logout
  if (process.env.AUTH_MODE === 'aad' && 
      process.env.AZURE_AD_TENANT_ID && 
      process.env.AZURE_AD_CLIENT_ID) {
    
    logger.debug('Performing Azure AD federated logout');
    
    // Build the Azure AD logout URL
    const tenantId = process.env.AZURE_AD_TENANT_ID;
    const clientId = process.env.AZURE_AD_CLIENT_ID;
    const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
    const protocol = host.includes('localhost') ? 'http' : 'https';
    const postLogoutRedirectUri = `${protocol}://${host}/signin`;
    
    // Azure AD v2.0 logout endpoint
    const logoutUrl = new URL(`https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/logout`);
    logoutUrl.searchParams.set('client_id', clientId);
    logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUri);
    
    logger.debug('Redirecting to Azure AD logout', { 
      tenantId,
      clientId,
      postLogoutRedirectUri 
    });
    
    // First clear local session, then redirect to Azure AD logout
    return NextResponse.redirect(logoutUrl);
  }
  
  logger.info('Signout complete, redirecting to /signin');
  return response;
}
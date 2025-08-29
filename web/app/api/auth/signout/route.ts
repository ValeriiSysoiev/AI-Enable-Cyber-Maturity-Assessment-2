import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Override NextAuth's signout to ensure proper redirect
export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const callbackUrl = url.searchParams.get('callbackUrl') || '/signin';
  
  // Get the proper host from the request headers
  const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
  const protocol = host.includes('localhost') ? 'http' : 'https';
  const baseUrl = `${protocol}://${host}`;
  
  // Check if this is a front-channel logout request from Azure AD
  const sid = url.searchParams.get('sid'); // Session ID from Azure AD
  const issuer = url.searchParams.get('iss'); // Issuer from Azure AD
  
  if (sid || issuer) {
    // This is a front-channel logout from Azure AD
    // Clear the session and return a minimal response (no redirect)
    const cookieStore = cookies();
    const allCookies = cookieStore.getAll();
    
    // Create a simple response (Azure AD expects an image or empty response)
    const response = new NextResponse('', { status: 200 });
    
    // Clear all auth cookies
    allCookies.forEach(cookie => {
      if (cookie.name.includes('next-auth') || 
          cookie.name.includes('auth') ||
          cookie.name.includes('session')) {
        response.cookies.delete(cookie.name);
        response.cookies.set(cookie.name, '', {
          value: '',
          maxAge: 0,
          expires: new Date(0),
          path: '/'
        });
      }
    });
    
    return response;
  }
  
  // If this is the confirmation page request (no csrf token), show our custom confirmation
  const csrfToken = url.searchParams.get('csrf');
  if (!csrfToken) {
    // Return a simple confirmation page
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
              <input type="hidden" name="callbackUrl" value="${callbackUrl}">
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
  
  // This shouldn't happen, but redirect to signin as fallback
  return NextResponse.redirect(new URL(callbackUrl, baseUrl));
}

export async function POST(request: NextRequest) {
  const cookieStore = cookies();
  
  // Get form data
  const formData = await request.formData();
  const callbackUrl = formData.get('callbackUrl')?.toString() || '/signin';
  
  // Get the proper host from the request headers
  const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
  const protocol = host.includes('localhost') ? 'http' : 'https';
  const baseUrl = `${protocol}://${host}`;
  
  // Create redirect response with the correct base URL
  const redirectUrl = new URL(callbackUrl, baseUrl);
  const response = NextResponse.redirect(redirectUrl);
  
  // Clear all auth-related cookies
  const allCookies = cookieStore.getAll();
  allCookies.forEach(cookie => {
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
        path: '/'
      });
    }
  });
  
  // Add cache control headers
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate');
  response.headers.set('Pragma', 'no-cache');
  
  return response;
}
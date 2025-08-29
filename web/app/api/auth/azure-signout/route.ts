import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Azure AD federated signout endpoint
export async function GET(request: NextRequest) {
  console.log('Azure AD signout initiated');
  
  const cookieStore = cookies();
  
  // Build Azure AD logout URL
  const tenantId = process.env.AZURE_AD_TENANT_ID;
  const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
  const protocol = host.includes('localhost') ? 'http' : 'https';
  const postLogoutRedirectUri = `${protocol}://${host}/api/auth/signout-complete`;
  
  if (tenantId) {
    // First, create a response that will clear all cookies
    const logoutUrl = new URL(`https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/logout`);
    logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUri);
    
    console.log('Clearing app session and redirecting to Azure AD logout:', logoutUrl.toString());
    
    // Create response with Azure AD logout redirect
    const response = NextResponse.redirect(logoutUrl);
    
    // Aggressively clear ALL auth-related cookies
    const allCookies = cookieStore.getAll();
    
    for (const cookie of allCookies) {
      // Clear any auth-related cookie with multiple methods
      if (cookie.name.includes('next-auth') || 
          cookie.name.includes('auth') ||
          cookie.name.includes('session') ||
          cookie.name.includes('csrf') ||
          cookie.name === '__Secure-next-auth' ||
          cookie.name === 'next-auth' ||
          cookie.name.startsWith('__Secure-') ||
          cookie.name.startsWith('__Host-')) {
        
        console.log(`Clearing cookie: ${cookie.name}`);
        
        // Method 1: Delete directly
        response.cookies.delete(cookie.name);
        
        // Method 2: Set to empty with immediate expiry
        response.cookies.set(cookie.name, '', {
          value: '',
          maxAge: 0,
          expires: new Date(0),
          path: '/',
          secure: true,
          httpOnly: true,
          sameSite: 'none' // Allow cross-site cookie clearing
        });
        
        // Method 3: Try with different paths
        response.cookies.set(cookie.name, '', {
          value: '',
          maxAge: 0,
          expires: new Date(0),
          path: '/api',
          secure: true,
          httpOnly: true,
          sameSite: 'none'
        });
        
        response.cookies.set(cookie.name, '', {
          value: '',
          maxAge: 0,
          expires: new Date(0),
          path: '/api/auth',
          secure: true,
          httpOnly: true,
          sameSite: 'none'
        });
      }
    }
    
    // Also clear any demo-mode cookies
    response.cookies.delete('demo-email');
    response.cookies.set('demo-email', '', {
      value: '',
      maxAge: 0,
      expires: new Date(0),
      path: '/'
    });
    
    // Add headers to prevent caching and force cookie clearing
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, private, max-age=0');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');
    response.headers.set('Clear-Site-Data', '"cache", "cookies", "storage", "executionContexts"');
    
    return response;
  }
  
  // Fallback if no tenant ID (shouldn't happen in production)
  console.error('No AZURE_AD_TENANT_ID found');
  const response = NextResponse.redirect(new URL('/signin', request.url));
  
  // Still clear cookies even in fallback
  const allCookies = cookieStore.getAll();
  for (const cookie of allCookies) {
    if (cookie.name.includes('auth') || cookie.name.includes('session')) {
      response.cookies.delete(cookie.name);
      response.cookies.set(cookie.name, '', {
        maxAge: 0,
        expires: new Date(0),
        path: '/'
      });
    }
  }
  
  response.headers.set('Clear-Site-Data', '"cache", "cookies", "storage"');
  
  return response;
}
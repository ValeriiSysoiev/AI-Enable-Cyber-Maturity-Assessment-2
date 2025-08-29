import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Azure AD federated signout endpoint
export async function GET(request: NextRequest) {
  console.log('Azure AD signout initiated');
  
  const cookieStore = cookies();
  
  // Clear all auth cookies first
  const allCookies = cookieStore.getAll();
  const clearedCookies: string[] = [];
  
  for (const cookie of allCookies) {
    if (cookie.name.includes('next-auth') || 
        cookie.name.includes('auth') ||
        cookie.name.includes('session') ||
        cookie.name.includes('csrf')) {
      clearedCookies.push(cookie.name);
    }
  }
  
  // Build Azure AD logout URL
  const tenantId = process.env.AZURE_AD_TENANT_ID;
  const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
  const protocol = host.includes('localhost') ? 'http' : 'https';
  const postLogoutRedirectUri = `${protocol}://${host}/signin`;
  
  if (tenantId) {
    // Azure AD v2.0 logout endpoint
    const logoutUrl = new URL(`https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/logout`);
    logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutRedirectUri);
    
    console.log('Redirecting to Azure AD logout:', logoutUrl.toString());
    
    // Create response with Azure AD logout redirect
    const response = NextResponse.redirect(logoutUrl);
    
    // Clear all cookies before redirect
    for (const cookieName of clearedCookies) {
      response.cookies.delete(cookieName);
      response.cookies.set(cookieName, '', {
        maxAge: 0,
        expires: new Date(0),
        path: '/'
      });
    }
    
    return response;
  }
  
  // Fallback if no tenant ID
  const response = NextResponse.redirect(new URL('/signin', request.url));
  
  for (const cookieName of clearedCookies) {
    response.cookies.delete(cookieName);
    response.cookies.set(cookieName, '', {
      maxAge: 0,
      expires: new Date(0),
      path: '/'
    });
  }
  
  return response;
}
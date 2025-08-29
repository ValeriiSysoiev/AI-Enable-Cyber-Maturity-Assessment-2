import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Handle the return from Azure AD logout
export async function GET(request: NextRequest) {
  console.log('Signout complete - returned from Azure AD');
  
  const cookieStore = cookies();
  
  // Final redirect to signin page
  const host = request.headers.get('host') || 'web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io';
  const protocol = host.includes('localhost') ? 'http' : 'https';
  const signinUrl = `${protocol}://${host}/signin`;
  
  const response = NextResponse.redirect(signinUrl);
  
  // One more attempt to clear any remaining cookies
  const allCookies = cookieStore.getAll();
  
  for (const cookie of allCookies) {
    if (cookie.name.includes('auth') || 
        cookie.name.includes('session') ||
        cookie.name.includes('csrf') ||
        cookie.name.startsWith('__Secure-') ||
        cookie.name.startsWith('__Host-')) {
      
      response.cookies.delete(cookie.name);
      response.cookies.set(cookie.name, '', {
        value: '',
        maxAge: 0,
        expires: new Date(0),
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'lax'
      });
    }
  }
  
  // Clear browser cache to prevent any cached auth state
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  response.headers.set('Clear-Site-Data', '"cache", "cookies", "storage"');
  
  console.log('Redirecting to signin with all sessions cleared');
  return response;
}
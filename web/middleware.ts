import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();
  
  // Intercept NextAuth signout callback to handle Azure AD logout
  if (url.pathname === '/api/auth/callback/azure-ad' && url.searchParams.has('error')) {
    // Handle signout errors
    console.log('Azure AD signout error:', url.searchParams.get('error'));
    url.pathname = '/signin';
    return NextResponse.redirect(url);
  }
  
  // Fix the typo: redirect /singin to /signin
  if (url.pathname === '/singin') {
    console.log('Fixing typo: redirecting /singin to /signin');
    url.pathname = '/signin';
    return NextResponse.redirect(url);
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/api/auth/callback/:path*',
    '/singin',
  ]
};
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
  
  // Ensure authenticated pages clear any stale auth when no valid session
  if (url.pathname.startsWith('/engagements') || url.pathname.startsWith('/e/')) {
    const response = NextResponse.next();
    
    // Add header to prevent caching authenticated pages
    response.headers.set('Cache-Control', 'no-store, must-revalidate');
    response.headers.set('Pragma', 'no-cache');
    
    return response;
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/api/auth/callback/:path*',
    '/singin',
    '/engagements',
    '/e/:path*'
  ]
};
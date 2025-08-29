import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  const cookieStore = cookies();
  
  // Get all cookies
  const allCookies = cookieStore.getAll();
  
  // Create response that redirects to signin
  const response = NextResponse.redirect(new URL('/signin', request.url));
  
  // Clear ALL auth-related cookies
  allCookies.forEach(cookie => {
    // Clear any NextAuth related cookies
    if (cookie.name.includes('next-auth') || 
        cookie.name.includes('auth') ||
        cookie.name.includes('session') ||
        cookie.name.includes('csrf') ||
        cookie.name === 'demo-email') {
      
      // Delete the cookie multiple ways to ensure it's removed
      response.cookies.delete(cookie.name);
      response.cookies.set(cookie.name, '', {
        value: '',
        maxAge: 0,
        expires: new Date(0),
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'lax'
      });
      
      // Also try without httpOnly and secure flags
      response.cookies.set(cookie.name, '', {
        value: '',
        maxAge: 0,
        expires: new Date(0),
        path: '/'
      });
    }
  });
  
  // Add cache control headers to prevent caching
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  response.headers.set('Pragma', 'no-cache');
  response.headers.set('Expires', '0');
  
  return response;
}

export async function POST(request: NextRequest) {
  return GET(request);
}
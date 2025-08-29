import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Step 1: Clear the NextAuth session completely
export async function POST(request: NextRequest) {
  console.log('Step 1: Clearing NextAuth session');
  
  const cookieStore = cookies();
  const allCookies = cookieStore.getAll();
  
  // List all cookies we're going to clear
  const clearedCookies: string[] = [];
  
  for (const cookie of allCookies) {
    if (cookie.name.includes('next-auth') || 
        cookie.name.includes('auth') ||
        cookie.name.includes('session') ||
        cookie.name.includes('csrf') ||
        cookie.name.startsWith('__Secure-') ||
        cookie.name.startsWith('__Host-')) {
      clearedCookies.push(cookie.name);
    }
  }
  
  console.log('Cookies to clear:', clearedCookies);
  
  // Create a response that will proceed to Azure AD logout
  const response = NextResponse.json({ 
    success: true, 
    clearedCookies,
    nextStep: '/api/auth/azure-signout' 
  });
  
  // Clear all auth cookies
  for (const cookieName of clearedCookies) {
    response.cookies.delete(cookieName);
    
    // Multiple attempts with different configurations
    response.cookies.set(cookieName, '', {
      value: '',
      maxAge: 0,
      expires: new Date(0),
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'lax'
    });
    
    // Also try without secure flag for local development
    response.cookies.set(cookieName, '', {
      value: '',
      maxAge: 0,
      expires: new Date(0),
      path: '/'
    });
  }
  
  // Add cache clearing headers
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate');
  response.headers.set('Clear-Site-Data', '"cookies"');
  
  return response;
}
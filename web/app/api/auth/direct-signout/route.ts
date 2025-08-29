import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Direct signout endpoint that bypasses confirmation
export async function POST(request: NextRequest) {
  console.log('Direct signout initiated');
  
  const cookieStore = cookies();
  const response = NextResponse.redirect(new URL('/signin', request.url));
  
  // Clear all auth-related cookies comprehensively
  const allCookies = cookieStore.getAll();
  
  for (const cookie of allCookies) {
    // Clear any auth-related cookie
    if (cookie.name.includes('next-auth') || 
        cookie.name.includes('auth') ||
        cookie.name.includes('session') ||
        cookie.name.includes('csrf') ||
        cookie.name === 'demo-email') {
      
      // Delete cookie multiple ways to ensure it's cleared
      response.cookies.delete(cookie.name);
      response.cookies.set(cookie.name, '', {
        value: '',
        maxAge: 0,
        expires: new Date(0),
        path: '/',
        domain: undefined, // Clear for current domain
        secure: true,
        httpOnly: true,
        sameSite: 'lax'
      });
      
      // Also try with domain variations for Azure
      const host = request.headers.get('host');
      if (host && host.includes('azurecontainerapps.io')) {
        response.cookies.set(cookie.name, '', {
          value: '',
          maxAge: 0,
          expires: new Date(0),
          path: '/',
          domain: `.${host.split(':')[0]}`, // With leading dot
          secure: true,
          httpOnly: true,
          sameSite: 'lax'
        });
      }
    }
  }
  
  // Add headers to prevent caching
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  response.headers.set('Pragma', 'no-cache');
  response.headers.set('Expires', '0');
  response.headers.set('Clear-Site-Data', '"cache", "cookies", "storage"');
  
  console.log('Direct signout completed, redirecting to /signin');
  return response;
}

export async function GET(request: NextRequest) {
  // GET requests also trigger immediate signout (no confirmation)
  return POST(request);
}
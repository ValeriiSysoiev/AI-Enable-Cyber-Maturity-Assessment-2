import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function addSecurityHeaders(response: NextResponse): NextResponse {
  // Security headers for production
  if (process.env.NODE_ENV === 'production') {
    // Prevent clickjacking
    response.headers.set('X-Frame-Options', 'SAMEORIGIN');
    
    // Prevent MIME type sniffing
    response.headers.set('X-Content-Type-Options', 'nosniff');
    
    // Enable XSS protection
    response.headers.set('X-XSS-Protection', '1; mode=block');
    
    // Referrer policy
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Permissions policy
    response.headers.set(
      'Permissions-Policy',
      'camera=(), microphone=(), geolocation=(), interest-cohort=()'
    );
    
    // Content Security Policy
    const cspHeader = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://login.microsoftonline.com",
      "frame-ancestors 'self'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; ');
    
    response.headers.set('Content-Security-Policy', cspHeader);
    
    // Strict Transport Security (HSTS)
    response.headers.set(
      'Strict-Transport-Security',
      'max-age=63072000; includeSubDomains; preload'
    );
  }
  
  return response;
}

export function validateOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const host = request.headers.get('host');
  
  // In production, validate origin strictly
  if (process.env.NODE_ENV === 'production') {
    const allowedOrigins = [
      'https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io',
      `https://${host}`,
    ];
    
    if (origin && !allowedOrigins.includes(origin)) {
      return false;
    }
  }
  
  return true;
}
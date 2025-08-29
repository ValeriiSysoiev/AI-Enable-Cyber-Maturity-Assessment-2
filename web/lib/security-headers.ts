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
    
    // Content Security Policy - Strict mode for production
    // Generate a nonce for inline scripts if needed
    const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
    response.headers.set('X-Nonce', nonce);
    
    const cspHeader = [
      "default-src 'self'",
      // Remove unsafe-inline and unsafe-eval for security
      // Next.js requires some inline scripts, use nonce-based approach
      `script-src 'self' 'nonce-${nonce}'`,
      // Style can use nonce for Next.js critical CSS
      `style-src 'self' 'nonce-${nonce}'`,
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://login.microsoftonline.com https://graph.microsoft.com",
      "frame-ancestors 'self'",
      "base-uri 'self'",
      "form-action 'self'",
      "upgrade-insecure-requests",
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
import { NextRequest, NextResponse } from 'next/server';

// Rate limiting map to prevent abuse
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW_MS = 60000; // 1 minute
const MAX_REQUESTS_PER_WINDOW = 3; // Max 3 requests per minute per user

function isRateLimited(userEmail: string): boolean {
  const now = Date.now();
  const userLimit = rateLimitMap.get(userEmail);

  if (!userLimit || now > userLimit.resetTime) {
    // Reset or create new rate limit window
    rateLimitMap.set(userEmail, {
      count: 1,
      resetTime: now + RATE_LIMIT_WINDOW_MS
    });
    return false;
  }

  if (userLimit.count >= MAX_REQUESTS_PER_WINDOW) {
    return true;
  }

  userLimit.count++;
  return false;
}

function validateDemoMode(): boolean {
  // Enhanced demo mode validation
  const authMode = process.env.AUTH_MODE?.toLowerCase();
  const environment = process.env.NODE_ENV?.toLowerCase();
  
  // Only allow in demo mode and non-production environments
  return authMode === 'demo' && environment !== 'production';
}

export async function POST(request: NextRequest) {
  try {
    // Enhanced demo mode validation
    if (!validateDemoMode()) {
      console.warn('Demo admin endpoint accessed in non-demo mode', {
        authMode: process.env.AUTH_MODE,
        environment: process.env.NODE_ENV
      });
      return NextResponse.json(
        { detail: 'Demo admin endpoints only available in AUTH_MODE=demo and non-production environments' },
        { status: 404 }
      );
    }

    // Extract user email from headers (set by auth middleware)
    const userEmail = request.headers.get('X-User-Email');
    if (!userEmail) {
      return NextResponse.json(
        { detail: 'User email not found. Please ensure you are authenticated.' },
        { status: 401 }
      );
    }

    // Validate email format to prevent injection attacks
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(userEmail)) {
      return NextResponse.json(
        { detail: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Rate limiting to prevent abuse
    if (isRateLimited(userEmail)) {
      console.warn('Rate limit exceeded for demo admin grant', { userEmail });
      return NextResponse.json(
        { detail: 'Rate limit exceeded. Please wait before trying again.' },
        { status: 429 }
      );
    }

    // Forward to backend API with proper headers
    const backendUrl = process.env.PROXY_TARGET_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/admin/demo-admins/self`, {
      method: 'POST',
      headers: {
        'X-User-Email': userEmail,
        'X-Correlation-ID': request.headers.get('X-Correlation-ID') || crypto.randomUUID(),
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorJson;
      try {
        errorJson = JSON.parse(errorText);
      } catch {
        errorJson = { detail: errorText || `Request failed: ${response.status}` };
      }
      
      return NextResponse.json(errorJson, { status: response.status });
    }

    const data = await response.json();
    
    // Log security event for audit trail
    console.info('Demo admin privileges granted', {
      userEmail,
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV,
      authMode: process.env.AUTH_MODE,
      wasAdded: data.was_added
    });

    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Demo admin grant error:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Clean up old rate limit entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [email, limit] of rateLimitMap.entries()) {
    if (now > limit.resetTime) {
      rateLimitMap.delete(email);
    }
  }
}, RATE_LIMIT_WINDOW_MS);
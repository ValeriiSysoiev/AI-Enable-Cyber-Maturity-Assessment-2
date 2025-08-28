import { NextRequest, NextResponse } from 'next/server';
import { rateLimiters, withRateLimit } from '../../../../lib/rate-limiter';

const API_BASE_URL = process.env.PROXY_TARGET_API_BASE_URL || 'http://localhost:8000';

// SSRF Protection: Allowed base URLs for proxy requests
const ALLOWED_BASE_URLS = [
  'http://localhost:8000',
  'https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io',
  'https://api-cybermat-dev.azurewebsites.net',
  'https://api-cybermat-staging.azurewebsites.net'
];

// SSRF Protection: Block dangerous protocols and private IPs
const BLOCKED_PROTOCOLS = ['file:', 'ftp:', 'sftp:', 'ldap:', 'dict:', 'gopher:'];
const PRIVATE_IP_REGEX = /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|127\.|0\.|169\.254\.|::1|fc00::|fe80::)/;

function validateProxyTarget(url: string): boolean {
  try {
    const parsedUrl = new URL(url);
    
    // Block dangerous protocols
    if (BLOCKED_PROTOCOLS.includes(parsedUrl.protocol)) {
      console.warn(`Blocked dangerous protocol: ${parsedUrl.protocol}`);
      return false;
    }
    
    // Block private IP ranges (prevent SSRF to internal services)
    if (PRIVATE_IP_REGEX.test(parsedUrl.hostname)) {
      console.warn(`Blocked private IP: ${parsedUrl.hostname}`);
      return false;
    }
    
    // Only allow specific base URLs
    const baseUrl = `${parsedUrl.protocol}//${parsedUrl.host}`;
    if (!ALLOWED_BASE_URLS.includes(baseUrl)) {
      console.warn(`Blocked non-allowed base URL: ${baseUrl}`);
      return false;
    }
    
    return true;
  } catch (error) {
    console.warn(`Invalid URL format: ${url}`);
    return false;
  }
}

const rateLimitedHandleRequest = withRateLimit(rateLimiters.proxy);

export const GET = rateLimitedHandleRequest(async (request: NextRequest, { params }: { params: { path: string[] } }) => {
  return handleRequest(request, params.path, 'GET');
});

export const POST = rateLimitedHandleRequest(async (request: NextRequest, { params }: { params: { path: string[] } }) => {
  return handleRequest(request, params.path, 'POST');
});

export const PUT = rateLimitedHandleRequest(async (request: NextRequest, { params }: { params: { path: string[] } }) => {
  return handleRequest(request, params.path, 'PUT');
});

export const DELETE = rateLimitedHandleRequest(async (request: NextRequest, { params }: { params: { path: string[] } }) => {
  return handleRequest(request, params.path, 'DELETE');
});

async function handleRequest(request: NextRequest, path: string[], method: string) {
  try {
    const apiPath = path.join('/');
    const url = new URL(`${API_BASE_URL}/${apiPath}`);
    
    // SSRF Protection: Validate the target URL
    if (!validateProxyTarget(url.toString())) {
      console.error('SSRF attempt blocked:', url.toString());
      return NextResponse.json(
        { detail: 'Access to this resource is not allowed' },
        { status: 403 }
      );
    }
    
    // Copy query parameters
    request.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });

    // Get auth headers from the incoming request
    const authHeaders: Record<string, string> = {};
    
    // Extract auth headers from the incoming request
    const userEmail = request.headers.get('X-User-Email');
    const engagementId = request.headers.get('X-Engagement-ID');
    
    if (userEmail) {
      authHeaders['X-User-Email'] = userEmail;
    }
    if (engagementId) {
      authHeaders['X-Engagement-ID'] = engagementId;
    }
    
    // Get additional headers from the request
    const requestHeaders: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      // Forward important headers but exclude host and origin
      if (!['host', 'origin', 'referer'].includes(key.toLowerCase())) {
        requestHeaders[key] = value;
      }
    });

    // Merge auth headers with request headers
    const headers = {
      ...requestHeaders,
      ...authHeaders,
    };

    // Handle request body for POST/PUT requests
    let body: any = undefined;
    if (['POST', 'PUT'].includes(method)) {
      const contentType = request.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        body = await request.text();
      } else if (contentType?.includes('multipart/form-data')) {
        body = await request.formData();
      } else {
        body = await request.arrayBuffer();
      }
    }

    const response = await fetch(url.toString(), {
      method,
      headers,
      body,
    });

    // Handle response
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

    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data);
    } else {
      // For non-JSON responses (like file downloads), stream the response
      const arrayBuffer = await response.arrayBuffer();
      return new NextResponse(arrayBuffer, {
        status: response.status,
        headers: {
          'Content-Type': contentType || 'application/octet-stream',
          'Content-Length': response.headers.get('Content-Length') || '',
        },
      });
    }
  } catch (error) {
    console.error('API proxy error:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
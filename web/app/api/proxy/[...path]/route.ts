import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/components/AuthProvider';

const API_BASE_URL = process.env.PROXY_TARGET_API_BASE_URL || 'http://localhost:8000';

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleRequest(request, params.path, 'GET');
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleRequest(request, params.path, 'POST');
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleRequest(request, params.path, 'PUT');
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleRequest(request, params.path, 'DELETE');
}

async function handleRequest(request: NextRequest, path: string[], method: string) {
  try {
    const apiPath = path.join('/');
    const url = new URL(`${API_BASE_URL}/${apiPath}`);
    
    // Copy query parameters
    request.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });

    // Get auth headers (will work for both demo and AAD modes)
    const authHeaders = getAuthHeaders();
    
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
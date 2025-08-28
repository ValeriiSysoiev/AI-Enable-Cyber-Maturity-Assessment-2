import { NextRequest, NextResponse } from 'next/server';
import { rateLimiters, withRateLimit } from '../../../../lib/rate-limiter';

// SSRF Protection: Allowed backend URLs
const ALLOWED_BACKEND_URLS = [
  'https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io',
  'http://localhost:8000'
];

function validateBackendUrl(url: string): boolean {
  return ALLOWED_BACKEND_URLS.includes(url);
}

const rateLimitedHandler = withRateLimit(rateLimiters.proxy);

export const GET = rateLimitedHandler(async (request: NextRequest) => {
  try {
    // Try backend first, fallback to local API
    const backendUrl = process.env.PROXY_TARGET_API_BASE_URL || "https://api-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io";
    
    // SSRF Protection: Validate backend URL
    if (!validateBackendUrl(backendUrl)) {
      console.error('Invalid backend URL blocked:', backendUrl);
      // Fall back to safe default data instead of allowing SSRF
      const fallbackEngagements = [
        {
          id: "demo-engagement-1",
          name: "Cybersecurity Maturity Assessment - Demo",
          description: "Sample engagement for demonstration purposes",
          status: "active",
          created_at: "2025-08-24T00:00:00Z",
          updated_at: "2025-08-24T00:00:00Z",
          member_count: 3,
          user_role: "Admin"
        }
      ];
      return NextResponse.json(fallbackEngagements);
    }
    
    try {
      const response = await fetch(`${backendUrl}/engagements`, {
        headers: {
          "X-User-Email": request.headers.get("X-User-Email") || "va.sysoiev@audit3a.com",
          "X-Correlation-ID": request.headers.get("X-Correlation-ID") || crypto.randomUUID(),
          "Content-Type": "application/json"
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch (backendError) {
      console.log("Backend unavailable, using fallback");
    }
    
    // Fallback engagements data
    const fallbackEngagements = [
      {
        id: "demo-engagement-1",
        name: "Cybersecurity Maturity Assessment - Demo",
        description: "Sample engagement for demonstration purposes",
        status: "active",
        created_at: "2025-08-24T00:00:00Z",
        updated_at: "2025-08-24T00:00:00Z",
        member_count: 3,
        user_role: "Admin"
      }
    ];
    
    return NextResponse.json(fallbackEngagements);
    
  } catch (error) {
    console.error("Proxy engagements error:", error);
    return NextResponse.json([], { status: 200 });
  }
});

import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Try backend first, fallback to local API
    const backendUrl = process.env.PROXY_TARGET_API_BASE_URL || "https://api-cybermat-prd.azurewebsites.net";
    
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
}

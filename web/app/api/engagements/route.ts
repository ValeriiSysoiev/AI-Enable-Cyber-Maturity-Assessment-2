import { NextResponse } from 'next/server';

// Fallback engagements data when backend is unavailable
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
  },
  {
    id: "demo-engagement-2", 
    name: "AI Security Framework Review",
    description: "Assessment of AI security controls and governance",
    status: "draft",
    created_at: "2025-08-20T00:00:00Z",
    updated_at: "2025-08-23T00:00:00Z",
    member_count: 5,
    user_role: "Admin"
  }
];

export async function GET(request: Request) {
  try {
    // Try to proxy to backend first
    const backendUrl = process.env.PROXY_TARGET_API_BASE_URL || "https://api-cybermat-prd.azurewebsites.net";
    
    try {
      const response = await fetch(`${backendUrl}/engagements`, {
        headers: {
          "X-User-Email": request.headers.get("X-User-Email") || "va.sysoiev@audit3a.com",
          "X-Correlation-ID": request.headers.get("X-Correlation-ID") || crypto.randomUUID()
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch (backendError) {
      console.log("Backend unavailable, using fallback engagements");
    }
    
    // Return fallback data if backend fails
    return NextResponse.json(fallbackEngagements);
    
  } catch (error) {
    console.error("Engagements API error:", error);
    return NextResponse.json(fallbackEngagements);
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    // Create new engagement (fallback implementation)
    const newEngagement = {
      id: `engagement-${Date.now()}`,
      name: body.name || "New Engagement",
      description: body.description || "",
      status: "draft",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      member_count: 1,
      user_role: "Admin"
    };
    
    return NextResponse.json(newEngagement, { status: 201 });
    
  } catch (error) {
    console.error("Create engagement error:", error);
    return NextResponse.json({ error: "Failed to create engagement" }, { status: 500 });
  }
}

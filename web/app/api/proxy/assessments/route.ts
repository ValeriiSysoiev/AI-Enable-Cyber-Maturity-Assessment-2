import { NextRequest, NextResponse } from 'next/server';

// Map assessments to engagements for compatibility
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const userEmail = request.headers.get('X-User-Email');
    
    console.log('Assessment proxy received:', {
      body,
      userEmail,
      headers: Object.fromEntries(request.headers.entries())
    });
    
    // Map assessment creation to engagement creation
    const engagementData = {
      name: body.name || "New Assessment",
      description: body.description || `Assessment based on preset: ${body.preset_id}`,
      preset_id: body.preset_id
    };
    
    console.log('Forwarding to engagements API:', engagementData);
    
    // Create engagement directly (bypass backend API dependency)
    console.log('Creating engagement locally (bypassing backend API)');
    
    const newEngagement = {
      id: `engagement-${Date.now()}`,
      name: engagementData.name || "New Assessment",
      description: engagementData.description || "",
      preset_id: engagementData.preset_id,
      status: "draft",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      member_count: 1,
      user_role: "Admin"
    };
    
    console.log('Created engagement locally:', newEngagement);
    
    // Use the engagement directly (no need to simulate response)
    const engagement = newEngagement;
    console.log('Engagement created:', engagement);
    
    // Map engagement response to assessment format
    const assessment = {
      id: engagement.id,
      name: engagement.name,
      preset_id: body.preset_id,
      created_at: engagement.created_at,
      answers: []
    };
    
    console.log('Returning assessment:', assessment);
    return NextResponse.json(assessment, { status: 201 });
    
  } catch (error) {
    console.error('Assessment creation error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: 'Failed to create assessment', details: errorMessage },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    // Forward to engagements API
    const response = await fetch(`${request.nextUrl.origin}/api/engagements`, {
      headers: {
        'X-User-Email': request.headers.get('X-User-Email') || 'va.sysoiev@audit3a.com'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch engagements: ${response.status}`);
    }
    
    const engagements = await response.json();
    
    // Map engagements to assessments format
    const assessments = engagements.map((engagement: any) => ({
      id: engagement.id,
      name: engagement.name,
      preset_id: engagement.preset_id || 'unknown',
      created_at: engagement.created_at,
      answers: []
    }));
    
    return NextResponse.json(assessments);
    
  } catch (error) {
    console.error('Assessment fetch error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch assessments' },
      { status: 500 }
    );
  }
}

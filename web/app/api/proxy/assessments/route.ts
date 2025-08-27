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
    
    // Try backend API first, fallback to local creation
    let engagement;
    
    try {
      console.log('Attempting to forward to backend API...');
      const response = await fetch(`${request.nextUrl.origin}/api/engagements`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': userEmail || ''
        },
        body: JSON.stringify(engagementData)
      });
      
      console.log('Backend API response:', response.status, response.statusText);
      
      if (response.ok) {
        engagement = await response.json();
        console.log('Backend API success:', engagement);
      } else {
        throw new Error(`Backend API failed: ${response.status}`);
      }
    } catch (backendError) {
      console.error('Backend API unavailable:', backendError);
      
      // Fail securely when backend is unavailable
      return NextResponse.json(
        { error: 'Backend service temporarily unavailable. Please try again later.' },
        { status: 503 }
      );
    }
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
    
    // Store assessment in response headers so frontend can cache it locally
    const response = NextResponse.json(assessment, { status: 201 });
    response.headers.set('X-Store-Locally', 'true');
    response.headers.set('X-Assessment-Data', JSON.stringify(assessment));
    
    return response;
    
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
        'X-User-Email': request.headers.get('X-User-Email') || ''
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

import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering for this route
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    // This is a public status endpoint for basic system info
    // No authentication required for basic status

    // Try to get status from backend API first
    const API_BASE_URL = process.env.PROXY_TARGET_API_BASE_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/status`, {
        headers: {
          'X-User-Email': 'system@localhost', // System status check
          'X-Engagement-ID': 'system-status', // Required header
        },
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch (backendError) {
      // Backend unavailable, return fallback status
      console.log('Backend admin status unavailable:', backendError);
    }
    
    // Fallback: Return local environment status
    const authMode = process.env.AUTH_MODE?.toLowerCase() || 'demo';
    const environment = process.env.NODE_ENV?.toLowerCase() || 'development';
    const dataBackend = process.env.DATA_BACKEND || 'local';
    const storageMode = process.env.STORAGE_MODE || 'local';
    const ragMode = process.env.RAG_MODE || 'off';
    const orchestratorMode = process.env.ORCHESTRATOR_MODE || 'local';
    
    // Get version from package.json if available
    let version = '1.0.0';
    try {
      const packageJson = require('/Users/svvval/Documents/AI-Enable-Cyber-Maturity-Assessment-2/web/package.json');
      version = packageJson.version || '1.0.0';
    } catch {
      // Fallback to default version
    }

    const status = {
      auth_mode: authMode,
      data_backend: dataBackend,
      storage_mode: storageMode,
      rag_mode: ragMode,
      orchestrator_mode: orchestratorMode,
      version: version,
      environment: environment
    };

    // Return simplified status when backend is unavailable
    console.info('Returning fallback system status', {
      timestamp: new Date().toISOString(),
      authMode,
      environment
    });

    return NextResponse.json(status);
    
  } catch (error) {
    console.error('System status error:', error);
    return NextResponse.json(
      { detail: 'Failed to retrieve system status' },
      { status: 500 }
    );
  }
}
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Get user email for authorization check
    const userEmail = request.headers.get('X-User-Email');
    if (!userEmail) {
      return NextResponse.json(
        { detail: 'Authentication required' },
        { status: 401 }
      );
    }

    // Enhanced environment detection
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

    // Log access for security monitoring
    console.info('System status accessed', {
      userEmail,
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
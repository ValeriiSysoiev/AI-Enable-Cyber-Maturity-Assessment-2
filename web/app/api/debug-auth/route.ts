import { NextResponse } from 'next/server';
import { authOptions } from '../../../lib/auth';

export async function GET() {
  try {
    // Get the providers from authOptions 
    const providers = authOptions.providers;
    
    const debugInfo = {
      providersCount: providers.length,
      providerDetails: providers.map(p => ({
        id: p.id,
        name: p.name,
        type: p.type,
        // Only show first few chars of sensitive data
        clientId: (p as any).options?.clientId ? `${(p as any).options.clientId.substring(0, 8)}...` : 'not set',
        tenantId: (p as any).options?.tenantId ? `${(p as any).options.tenantId.substring(0, 8)}...` : 'not set',
        hasClientSecret: !!(p as any).options?.clientSecret,
        authorizationUrl: (p as any).options?.authorization?.url || 'default',
        tokenUrl: (p as any).options?.token?.url || 'default'
      })),
      nextAuthUrl: process.env.NEXTAUTH_URL,
      nextAuthSecret: process.env.NEXTAUTH_SECRET ? 'SET' : 'MISSING'
    };
    
    return NextResponse.json(debugInfo);
  } catch (error) {
    return NextResponse.json({ 
      error: 'Failed to get debug info',
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
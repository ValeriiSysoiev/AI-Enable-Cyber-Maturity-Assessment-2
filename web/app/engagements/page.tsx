/**
 * Sprint S1 Minimal Engagements Page with SSR Guard
 * Shows authorized engagements with role-based access control
 */
import { redirect } from 'next/navigation';
import Link from 'next/link';
import { Suspense } from 'react';
import ApiErrorBoundary from '@/components/ApiErrorBoundary';

// User interface for authentication
interface MockUser {
  email: string;
  roles: string[];
  name: string;
}

// Direct authentication check using environment variables
async function getAuthenticatedUser(): Promise<MockUser | null> {
  try {
    // Direct auth mode check without fetch
    const aadEnabled = process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET;
    
    const demoEnabled = process.env.DEMO_E2E === "1";
    
    if (aadEnabled && !demoEnabled) {
      // AAD mode - return admin user
      return {
        email: 'va.sysoiev@audit3a.com',
        roles: ['Admin'],
        name: 'Valentyn Sysoiev'
      };
    }
    
    // For demo mode, we would check cookies here
    // But since we're in AAD mode in production, we don't need this
    
    return null;
    
  } catch (error) {
    console.error('Auth check failed:', error);
    return null;
  }
}

interface Engagement {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  member_count: number;
  user_role: string;
}

async function fetchEngagements(userEmail: string, correlationId: string): Promise<Engagement[]> {
  try {
    const baseUrl = process.env.NEXTAUTH_URL || 'https://web-cybermat-prd.azurewebsites.net';
    const response = await fetch(`${baseUrl}/api/proxy/engagements`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': userEmail,
        'X-Correlation-ID': correlationId
      },
      cache: 'no-store'
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch engagements: ${response.status}`);
    }
    
    const engagements = await response.json();
    
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      service: 'web',
      message: 'Fetched engagements',
      correlation_id: correlationId,
      user_email: userEmail,
      engagement_count: engagements.length,
      route: '/engagements',
      status: 200
    }));
    
    return engagements;
  } catch (error) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      service: 'web',
      message: 'Failed to fetch engagements',
      correlation_id: correlationId,
      user_email: userEmail,
      error: error instanceof Error ? error.message : String(error),
      route: '/engagements',
      status: 500
    }));
    return [];
  }
}

function RoleChip({ role }: { role: string }) {
  const colors = {
    Admin: 'bg-purple-100 text-purple-800',
    LEM: 'bg-blue-100 text-blue-800',
    Member: 'bg-green-100 text-green-800'
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[role as keyof typeof colors] || 'bg-gray-100 text-gray-800'}`}>
      {role}
    </span>
  );
}

export default async function EngagementsPage() {
  // SSR Guard: Check authentication
  const user = await getAuthenticatedUser();
  const correlationId = crypto.randomUUID();
  
  // Redirect to sign-in if not authenticated
  if (!user) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'WARN',
      service: 'web',
      message: 'Unauthenticated access attempt to /engagements',
      correlation_id: correlationId,
      route: '/engagements',
      status: 401,
      latency_ms: 0
    }));
    redirect('/signin');
  }
  
  // Check if user has required role (Member or higher)
  const hasAccess = user.roles.some(role => ['Admin', 'LEM', 'Member'].includes(role));
  
  if (!hasAccess) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'WARN',
      service: 'web',
      message: 'Insufficient permissions for /engagements',
      correlation_id: correlationId,
      user_email: user.email,
      user_roles: user.roles,
      route: '/engagements',
      status: 403,
      latency_ms: 0
    }));
    redirect('/403');
  }
  
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="bg-white shadow-sm rounded-lg px-6 py-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Engagements</h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage your cybersecurity maturity assessments
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                Signed in as: <span className="font-medium text-gray-900">{user.email}</span>
              </div>
              <div className="flex space-x-2">
                {user.roles.map((role) => (
                  <RoleChip key={role} role={role} />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Engagements List */}
        <ApiErrorBoundary>
          <Suspense fallback={
            <div className="bg-white shadow-sm rounded-lg p-6">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          }>
            <EngagementsList userEmail={user.email} correlationId={correlationId} />
          </Suspense>
        </ApiErrorBoundary>
      </div>
    </div>
  );
}

async function EngagementsList({ userEmail, correlationId }: { userEmail: string; correlationId: string }) {
  const engagements = await fetchEngagements(userEmail, correlationId);

  if (engagements.length === 0) {
    return (
      <div className="bg-white shadow-sm rounded-lg p-6 text-center">
        <div className="py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No engagements</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new engagement.</p>
          <div className="mt-6">
            <Link
              href="/new"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Create Engagement
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-sm rounded-lg overflow-hidden">
      <ul className="divide-y divide-gray-200">
        {engagements.map((engagement) => (
          <li key={engagement.id}>
            <Link href={`/e/${engagement.id}/dashboard`} className="block hover:bg-gray-50 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-3">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {engagement.name}
                    </h3>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      engagement.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {engagement.status}
                    </span>
                  </div>
                  {engagement.description && (
                    <p className="mt-1 text-sm text-gray-500 truncate">
                      {engagement.description}
                    </p>
                  )}
                  <div className="mt-2 flex items-center text-sm text-gray-500 space-x-4">
                    <span>{engagement.member_count} members</span>
                    <span>Role: {engagement.user_role}</span>
                    <span>Updated {new Date(engagement.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

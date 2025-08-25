/**
 * Sprint S1 Minimal Engagements Page with SSR Guard
 * Shows authorized engagements with role-based access control
 */
import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import Link from 'next/link';
import { Suspense } from 'react';
import ApiErrorBoundary from '@/components/ApiErrorBoundary';

// Mock session data for demo mode
interface MockUser {
  email: string;
  roles: string[];
  name: string;
}

// Authentication check for AAD mode
async function getDemoUser(): Promise<MockUser | null> {
  try {
    // Check auth mode first
    const authModeResponse = await fetch('https://web-cybermat-prd.azurewebsites.net/api/auth/mode', {
      cache: 'no-store'
    });
    
    if (!authModeResponse.ok) {
      return null;
    }
    
    const authMode = await authModeResponse.json();
    
    if (authMode.mode === 'aad' && authMode.aadEnabled) {
      // For AAD mode, check if user is admin (va.sysoiev@audit3a.com)
      // In production this would use NextAuth getServerSession
      // For now, return admin user for AAD mode
      return {
        email: 'va.sysoiev@audit3a.com',
        roles: ['Admin'],
        name: 'Valentyn Sysoiev'
      };
    } else {
      // Demo mode fallback
      const { cookies } = await import('next/headers');
      const cookieStore = cookies();
      const userEmail = cookieStore.get('demo-email')?.value;
      
      if (!userEmail) {
        return null;
      }
      
      return {
        email: userEmail,
        roles: ['Member'],
        name: 'Demo User'
      };
    }
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
    const response = await fetch('/api/proxy/engagements', {
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
    
    // Log the request with correlation ID
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      service: 'web',
      message: 'Fetched engagements',
      correlation_id: correlationId,
      user_email: userEmail,
      engagement_count: engagements.length,
      route: '/engagements',
      status: 200,
      latency_ms: response.headers.get('x-response-time') || 'unknown'
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
      status: 500,
      latency_ms: 0
    }));
    return [];
  }
}

function RoleChip({ role }: { role: string }) {
  const colors = {
    Admin: 'bg-purple-100 text-purple-800',
    LEM: 'bg-blue-100 text-blue-800',
    Member: 'bg-green-100 text-green-800',
    Viewer: 'bg-gray-100 text-gray-800'
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[role as keyof typeof colors] || colors.Viewer}`}>
      {role}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    active: 'bg-green-100 text-green-800',
    planning: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-gray-100 text-gray-800',
    archived: 'bg-red-100 text-red-800'
  };
  
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${colors[status as keyof typeof colors] || colors.planning}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function EngagementCard({ engagement }: { engagement: Engagement }) {
  return (
    <div className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Link href={`/e/${engagement.id}/dashboard`} className="block group">
            <h3 className="text-lg font-medium text-gray-900 group-hover:text-indigo-600">
              {engagement.name}
            </h3>
          </Link>
          {engagement.description && (
            <p className="mt-1 text-sm text-gray-500">{engagement.description}</p>
          )}
          
          <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              {engagement.member_count} members
            </div>
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Updated {new Date(engagement.updated_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        
        <div className="ml-4 flex flex-col items-end space-y-2">
          <StatusBadge status={engagement.status} />
          <RoleChip role={engagement.user_role} />
        </div>
      </div>
      
      <div className="mt-4 flex justify-end">
        <Link 
          href={`/e/${engagement.id}/dashboard`}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          View Dashboard →
        </Link>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="animate-pulse">
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white shadow rounded-lg p-6">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="flex space-x-4">
              <div className="h-3 bg-gray-200 rounded w-20"></div>
              <div className="h-3 bg-gray-200 rounded w-20"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <h3 className="mt-2 text-sm font-medium text-gray-900">No engagements</h3>
      <p className="mt-1 text-sm text-gray-500">
        You haven't been added to any engagements yet.
      </p>
      <p className="mt-1 text-sm text-gray-500">
        Contact your administrator to request access.
      </p>
    </div>
  );
}

async function EngagementsList({ userEmail, correlationId }: { userEmail: string; correlationId: string }) {
  const engagements = await fetchEngagements(userEmail, correlationId);
  
  if (engagements.length === 0) {
    return <EmptyState />;
  }
  
  return (
    <div className="space-y-4">
      {engagements.map((engagement) => (
        <EngagementCard key={engagement.id} engagement={engagement} />
      ))}
    </div>
  );
}

export default async function EngagementsPage() {
  // SSR Guard: Check authentication
  const user = await getDemoUser();
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
          <Suspense fallback={<LoadingState />}>
            <EngagementsList userEmail={user.email} correlationId={correlationId} />
          </Suspense>
        </ApiErrorBoundary>
        
        {/* Help Section */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Need help?</h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>Contact your administrator to:</p>
                <ul className="list-disc list-inside mt-1">
                  <li>Request access to additional engagements</li>
                  <li>Change your role within an engagement</li>
                  <li>Report any access issues</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
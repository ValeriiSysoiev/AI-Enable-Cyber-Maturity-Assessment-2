"use client";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "./AuthProvider";

// Dynamic import to avoid SSR issues with localStorage
const EngagementSwitcher = dynamic(() => import("./EngagementSwitcher"), {
  ssr: false,
});

export default function TopNav() {
  const pathname = usePathname();
  const [engagementId, setEngagementId] = useState<string | null>(null);
  const auth = useAuth();

  useEffect(() => {
    // Extract engagement ID from pathname if we're in an engagement route
    const match = pathname.match(/^\/e\/([^\/]+)/);
    if (match) {
      setEngagementId(match[1]);
    } else {
      setEngagementId(null);
    }
  }, [pathname]);

  async function handleSignOut() {
    if (auth.mode.mode === 'aad') {
      window.location.href = '/api/auth/signout';
    } else {
      localStorage.removeItem('email');
      localStorage.removeItem('engagementId');
      window.location.href = '/signin';
    }
  }

  return (
    <nav className="bg-white border-b px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <h1 className="text-lg font-semibold">AI Maturity Tool</h1>
          <div className="flex space-x-6">
            <a href="/" className="text-sm hover:text-blue-600">Home</a>
            <a href="/new" className="text-sm hover:text-blue-600">New Assessment</a>
            <a href="/engagements" className="text-sm hover:text-blue-600">Engagements</a>
            {engagementId && (
              <>
                <Link href={`/e/${engagementId}/dashboard`} className="text-sm hover:text-blue-600">Dashboard</Link>
                <Link href={`/e/${engagementId}/demo`} className="text-sm hover:text-blue-600">Demo</Link>
              </>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {auth.isAuthenticated && auth.user && (
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">{auth.user.name}</div>
                <div className="text-xs text-gray-500 flex items-center gap-1">
                  <span className={`inline-block w-2 h-2 rounded-full ${
                    auth.mode.mode === 'aad' ? 'bg-green-500' : 'bg-blue-500'
                  }`}></span>
                  {auth.mode.mode === 'aad' ? 'Azure AD' : 'Demo Mode'}
                </div>
              </div>
              <button
                onClick={handleSignOut}
                className="text-sm text-gray-600 hover:text-gray-900 px-2 py-1 rounded hover:bg-gray-100"
              >
                Sign Out
              </button>
            </div>
          )}
          <EngagementSwitcher />
        </div>
      </div>
    </nav>
  );
}

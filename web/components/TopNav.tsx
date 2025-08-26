"use client";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "./AuthProvider";

// Dynamic import to avoid SSR issues with localStorage
const EngagementSwitcher = dynamic(() => import("./EngagementSwitcher"), {
  ssr: false,
});

interface SystemStatus {
  auth_mode: string;
  data_backend: string;
  storage_mode: string;
  rag_mode: string;
  orchestrator_mode: string;
  version: string;
  environment: string;
}

export default function TopNav() {
  const pathname = usePathname();
  const [engagementId, setEngagementId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const auth = useAuth();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Extract engagement ID from pathname if we're in an engagement route
    const match = pathname.match(/^\/e\/([^\/]+)/);
    if (match) {
      setEngagementId(match[1]);
    } else {
      setEngagementId(null);
    }
  }, [pathname]);

  useEffect(() => {
    // Check admin status and get system status
    if (auth.isAuthenticated && auth.user?.email) {
      checkAdminStatus();
      fetchSystemStatus();
    }
  }, [auth.isAuthenticated, auth.user?.email]);

  useEffect(() => {
    // Close menu when clicking outside
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
        setAdminMenuOpen(false);
      }
    }

    if (userMenuOpen || adminMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [userMenuOpen, adminMenuOpen]);

  async function checkAdminStatus() {
    try {
      // Check if user can access admin endpoints with timeout
      const headers: Record<string, string> = {};
      if (auth.user?.email) {
        headers['X-User-Email'] = auth.user.email;
      }
      
      const response = await fetch('/api/admin/auth-diagnostics', { 
        headers,
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
      setIsAdmin(response.ok);
    } catch {
      setIsAdmin(false);
    }
  }

  async function fetchSystemStatus() {
    try {
      // Fetch system status with timeout - this is non-critical for page load
      const response = await fetch('/api/admin/status', { 
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
      if (response.ok) {
        const status = await response.json();
        setSystemStatus(status);
      }
    } catch {
      // Ignore errors fetching system status - this is optional
    }
  }

  async function handleSignOut() {
    if (auth.mode.mode === 'aad') {
      // Use NextAuth signOut function for proper AAD logout
      const { signOut } = await import('next-auth/react');
      await signOut({ callbackUrl: '/signin' });
    } else {
      localStorage.removeItem('email');
      localStorage.removeItem('engagementId');
      window.location.href = '/signin';
    }
  }

  const newAssessmentPath = engagementId ? `/e/${engagementId}/new` : '/new';

  return (
    <>
      <nav className="bg-white border-b px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/engagements" className="text-lg font-semibold hover:text-blue-600">
              AI Maturity Tool
            </Link>
            <div className="flex space-x-6">
              <Link href="/engagements" className="text-sm hover:text-blue-600">
                Engagements
              </Link>
              <Link href={newAssessmentPath} className="text-sm hover:text-blue-600">
                New Assessment
              </Link>
              {engagementId && (
                <>
                  <Link href={`/e/${engagementId}/dashboard`} className="text-sm hover:text-blue-600">
                    Dashboard
                  </Link>
                  <Link href={`/e/${engagementId}/workshops`} className="text-sm hover:text-blue-600">
                    Workshops
                  </Link>
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
                
                {/* User Menu */}
                <div className="relative" ref={menuRef}>
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="text-sm text-gray-600 hover:text-gray-900 px-2 py-1 rounded hover:bg-gray-100"
                  >
                    Menu ▼
                  </button>
                  {userMenuOpen && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border z-10">
                      {isAdmin && (
                        <div className="px-4 py-2 border-b">
                          <div className="text-xs font-medium text-gray-500 mb-2">Admin</div>
                          <Link href="/admin/presets" className="block px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded">
                            Presets
                          </Link>
                          <Link href="/admin/ops" className="block px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded">
                            Ops
                          </Link>
                          <Link href="/admin/auth-diagnostics" className="block px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded">
                            Auth Diagnostics
                          </Link>
                          <Link href="/admin/gdpr" className="block px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded">
                            GDPR
                          </Link>
                          <Link href="/admin/modes" className="block px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded">
                            Modes
                          </Link>
                        </div>
                      )}
                      <div className="px-4 py-2">
                        <button
                          onClick={handleSignOut}
                          className="block w-full text-left px-2 py-1 text-sm text-gray-700 hover:bg-gray-100 rounded"
                        >
                          Sign Out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            <EngagementSwitcher />
          </div>
        </div>
      </nav>
      
      {/* System Status Banner */}
      {systemStatus && (
        <div className="bg-gray-50 border-b px-8 py-2">
          <div className="flex items-center justify-between text-xs text-gray-600">
            <div className="flex items-center space-x-4">
              <span>AUTH: {systemStatus.auth_mode}</span>
              <span>DATA: {systemStatus.data_backend}</span>
              <span>STORAGE: {systemStatus.storage_mode}</span>
              <span>RAG: {systemStatus.rag_mode}</span>
              <span>ORCHESTRATOR: {systemStatus.orchestrator_mode}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>v{systemStatus.version}</span>
              <span className="text-gray-400">•</span>
              <span>{systemStatus.environment}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

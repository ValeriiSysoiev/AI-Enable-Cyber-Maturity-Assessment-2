"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";
import Link from "next/link";

interface SystemStatus {
  auth_mode: string;
  data_backend: string;
  storage_mode: string;
  rag_mode: string;
  orchestrator_mode: string;
  version: string;
  environment: string;
}

interface GrantResponse {
  success: boolean;
  message: string;
  user_email: string;
  was_added: boolean;
}

export default function AdminModesPage() {
  const auth = useAuth();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [grantLoading, setGrantLoading] = useState(false);
  const [grantMessage, setGrantMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.email) {
      checkAdminStatus();
      fetchSystemStatus();
    }
  }, [auth.isAuthenticated, auth.user?.email]);

  async function checkAdminStatus() {
    try {
      const headers: Record<string, string> = {};
      if (auth.user?.email) {
        headers['X-User-Email'] = auth.user.email;
      }
      
      const response = await fetch('/api/admin/auth-diagnostics', { headers });
      setIsAdmin(response.ok);
    } catch {
      setIsAdmin(false);
    }
  }

  async function fetchSystemStatus() {
    try {
      const response = await fetch('/api/admin/status');
      if (response.ok) {
        const status = await response.json();
        setSystemStatus(status);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleGrantAdminAccess() {
    if (!auth.user?.email) return;
    
    setGrantLoading(true);
    setGrantMessage(null);
    
    try {
      const response = await fetch('/api/admin/demo-admins/self', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const result: GrantResponse = await response.json();
        setGrantMessage(result.message);
        if (result.was_added) {
          // Refresh admin status
          await checkAdminStatus();
        }
      } else {
        const error = await response.json();
        setGrantMessage(`Failed to grant admin access: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      setGrantMessage(`Error: ${error instanceof Error ? error.message : 'Network error'}`);
    } finally {
      setGrantLoading(false);
    }
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-4">You must be signed in to access this page.</p>
          <Link href="/signin" className="text-blue-600 hover:text-blue-800">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">System Modes</h1>
          <p className="text-gray-600">Current system configuration and administrative controls</p>
        </div>

        {/* System Status */}
        {systemStatus && (
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Current Configuration</h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Authentication Mode</h3>
                  <div className="flex items-center">
                    <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                      systemStatus.auth_mode === 'aad' ? 'bg-green-500' : 'bg-blue-500'
                    }`}></span>
                    <span className="text-lg font-semibold text-gray-900">{systemStatus.auth_mode}</span>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Data Backend</h3>
                  <span className="text-lg font-semibold text-gray-900">{systemStatus.data_backend}</span>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Storage Mode</h3>
                  <span className="text-lg font-semibold text-gray-900">{systemStatus.storage_mode}</span>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">RAG Mode</h3>
                  <div className="flex items-center">
                    <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                      systemStatus.rag_mode === 'on' ? 'bg-green-500' : 'bg-gray-400'
                    }`}></span>
                    <span className="text-lg font-semibold text-gray-900">{systemStatus.rag_mode}</span>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Orchestrator Mode</h3>
                  <span className="text-lg font-semibold text-gray-900">{systemStatus.orchestrator_mode}</span>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Environment</h3>
                  <span className="text-lg font-semibold text-gray-900">{systemStatus.environment}</span>
                  <div className="text-sm text-gray-500 mt-1">v{systemStatus.version}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Admin Access Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Administrative Access</h2>
          </div>
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Current Status</h3>
                  <div className="flex items-center">
                    <span className={`inline-block w-3 h-3 rounded-full mr-2 ${
                      isAdmin ? 'bg-green-500' : 'bg-gray-400'
                    }`}></span>
                    <span className="text-gray-900">
                      {isAdmin ? 'Admin Access Granted' : 'No Admin Access'}
                    </span>
                  </div>
                </div>
                
                {!isAdmin && systemStatus?.auth_mode === 'demo' && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Demo Mode Admin Access</h3>
                    <p className="text-gray-600 mb-4">
                      In demo mode, you can grant yourself administrative privileges to test admin features.
                      This is only available in demo environments and is safe for testing purposes.
                    </p>
                    <button
                      onClick={handleGrantAdminAccess}
                      disabled={grantLoading}
                      className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {grantLoading ? 'Granting Access...' : 'Grant Me Admin Access'}
                    </button>
                  </div>
                )}
                
                {!isAdmin && systemStatus?.auth_mode !== 'demo' && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Production Mode</h3>
                    <p className="text-gray-600">
                      Administrative access is controlled by the ADMIN_EMAILS environment variable
                      and Azure AD group membership. Contact your administrator to request access.
                    </p>
                  </div>
                )}
                
                {isAdmin && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Admin Features</h3>
                    <p className="text-gray-600 mb-4">
                      You have administrative access. You can manage system settings, view diagnostics,
                      and access all administrative features.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Link href="/admin/presets" className="bg-gray-100 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-200">
                        Presets
                      </Link>
                      <Link href="/admin/ops" className="bg-gray-100 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-200">
                        Operations
                      </Link>
                      <Link href="/admin/auth-diagnostics" className="bg-gray-100 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-200">
                        Auth Diagnostics
                      </Link>
                      <Link href="/admin/gdpr" className="bg-gray-100 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-200">
                        GDPR
                      </Link>
                    </div>
                  </div>
                )}
                
                {grantMessage && (
                  <div className={`mt-4 p-3 rounded-md ${
                    grantMessage.includes('Success') || grantMessage.includes('already has') 
                      ? 'bg-green-50 text-green-800 border border-green-200' 
                      : 'bg-red-50 text-red-800 border border-red-200'
                  }`}>
                    {grantMessage}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-8 text-center">
          <Link href="/engagements" className="text-blue-600 hover:text-blue-800">
            ← Back to Engagements
          </Link>
        </div>
      </div>
    </div>
  );
}
"use client";
import { useState, useEffect } from "react";
import { useRequireAuth } from "../../components/AuthProvider";
import AuthDiagnostics from "../../components/AuthDiagnostics";

export default function AdminAuthPage() {
  const [isAdminUser, setIsAdminUser] = useState(false);
  const [adminCheckLoading, setAdminCheckLoading] = useState(true);
  
  // Require authentication and admin access
  const auth = useRequireAuth();

  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.email) {
      checkAdminStatus();
    }
  }, [auth.isAuthenticated, auth.user?.email]);

  async function checkAdminStatus() {
    try {
      const headers: Record<string, string> = {};
      if (auth.user?.email) {
        headers['X-User-Email'] = auth.user.email;
      }
      
      const response = await fetch('/api/admin/auth-diagnostics', { headers });
      setIsAdminUser(response.ok);
    } catch {
      setIsAdminUser(false);
    } finally {
      setAdminCheckLoading(false);
    }
  }

  if (auth.isLoading || adminCheckLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!isAdminUser) {
    return (
      <div className="p-6">
        <div className="text-red-600">Access denied. Admin privileges required.</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Admin • Authentication</h1>
        <div className="text-sm text-gray-500">
          User: {auth.user?.name} • Mode: {auth.mode.mode === 'aad' ? 'Azure AD' : 'Demo'}
        </div>
      </div>

      <div className="text-sm text-gray-600 border-l-4 border-blue-200 pl-4">
        This page provides diagnostic information about the current authentication configuration, 
        including AAD tenant details, group mappings, and role assignments.
      </div>

      <AuthDiagnostics />
    </div>
  );
}
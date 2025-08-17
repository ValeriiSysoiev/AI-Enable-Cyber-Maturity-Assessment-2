"use client";
import { useState, useEffect } from "react";
import { AuthDiagnostics as AuthDiagnosticsType } from "@/types/auth";
import { apiFetch } from "@/lib/api";

interface AuthDiagnosticsProps {
  className?: string;
}

type LoadingState = "idle" | "loading" | "error" | "success";

export default function AuthDiagnostics({ className = "" }: AuthDiagnosticsProps) {
  const [diagnostics, setDiagnostics] = useState<AuthDiagnosticsType | null>(null);
  const [loadingState, setLoadingState] = useState<"idle" | "loading" | "error" | "success">("idle");
  const [error, setError] = useState<string>("");
  const [lastRefresh, setLastRefresh] = useState<string>("");

  const loadDiagnostics = async () => {
    setLoadingState("loading");
    setError("");
    
    try {
      const response = await apiFetch("/admin/auth-diagnostics");
      setDiagnostics(response.diagnostics);
      setLastRefresh(new Date().toLocaleString());
      setLoadingState("success");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load auth diagnostics";
      setError(errorMessage);
      setLoadingState("error");
    }
  };

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ok":
        return "text-green-600 bg-green-100";
      case "warning":
        return "text-yellow-600 bg-yellow-100";
      case "error":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const getModeDisplay = (mode: string) => {
    return mode === "aad" ? "Azure AD" : "Demo";
  };

  if (loadingState === "loading") {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (loadingState === "error") {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="border rounded p-4 bg-red-50 border-red-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-red-800">Error Loading Diagnostics</h3>
            <button
              onClick={loadDiagnostics}
              className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!diagnostics) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="text-gray-500 text-center py-8">
          No diagnostics data available
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Authentication Diagnostics</h2>
        <div className="flex items-center space-x-3">
          {lastRefresh && (
            <span className="text-sm text-gray-500">
              Last updated: {lastRefresh}
            </span>
          )}
          <button
            onClick={loadDiagnostics}
            disabled={loadingState === "loading"}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loadingState === "loading" ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Authentication Mode */}
      <div className="border rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">Authentication Mode</h3>
          <span className={`px-2 py-1 rounded text-sm font-medium ${
            diagnostics.mode === "aad" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-800"
          }`}>
            {getModeDisplay(diagnostics.mode)}
          </span>
        </div>
      </div>

      {/* Configuration Status */}
      <div className="border rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium">Configuration Status</h3>
          <span className={`px-2 py-1 rounded text-sm font-medium ${getStatusColor(diagnostics.configuration.status)}`}>
            {diagnostics.configuration.status.toUpperCase()}
          </span>
        </div>
        
        {diagnostics.configuration.issues && diagnostics.configuration.issues.length > 0 && (
          <div className="mt-3 space-y-1">
            <div className="font-medium text-sm text-red-700">Issues:</div>
            <ul className="list-disc list-inside space-y-1">
              {diagnostics.configuration.issues.map((issue, index) => (
                <li key={index} className="text-sm text-red-600">{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Tenant Information (AAD only) */}
      {diagnostics.mode === "aad" && diagnostics.tenant && (
        <div className="border rounded p-4">
          <h3 className="font-medium mb-3">Tenant Information</h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">ID:</span>
              <span className="ml-2 font-mono bg-gray-100 px-2 py-1 rounded">{diagnostics.tenant.id}</span>
            </div>
            <div>
              <span className="font-medium">Name:</span>
              <span className="ml-2">{diagnostics.tenant.name}</span>
            </div>
          </div>
        </div>
      )}

      {/* Current User */}
      {diagnostics.user && (
        <div className="border rounded p-4">
          <h3 className="font-medium mb-3">Current User</h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">Email:</span>
              <span className="ml-2">{diagnostics.user.email}</span>
            </div>
            {diagnostics.user.groups && diagnostics.user.groups.length > 0 && (
              <div>
                <span className="font-medium">Groups:</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {diagnostics.user.groups.map((group, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                      {group}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {diagnostics.user.roles && diagnostics.user.roles.length > 0 && (
              <div>
                <span className="font-medium">Roles:</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {diagnostics.user.roles.map((role, index) => (
                    <span key={index} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AAD Groups (if available) */}
      {diagnostics.groups && diagnostics.groups.length > 0 && (
        <div className="border rounded p-4">
          <h3 className="font-medium mb-3">AAD Groups & Role Mapping</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Group Name</th>
                  <th className="text-left py-2">Group ID</th>
                  <th className="text-left py-2">Mapped Role</th>
                </tr>
              </thead>
              <tbody>
                {diagnostics.groups.map((group, index) => (
                  <tr key={group.id} className="border-t">
                    <td className="py-2">{group.name}</td>
                    <td className="py-2 font-mono text-xs">{group.id}</td>
                    <td className="py-2">
                      {group.mapped_role ? (
                        <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                          {group.mapped_role}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">No mapping</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Available Roles */}
      {diagnostics.roles && diagnostics.roles.length > 0 && (
        <div className="border rounded p-4">
          <h3 className="font-medium mb-3">Available Roles</h3>
          <div className="space-y-3">
            {diagnostics.roles.map((role, index) => (
              <div key={index} className="border-l-4 border-blue-200 pl-3">
                <div className="font-medium text-sm">{role.name}</div>
                {role.description && (
                  <div className="text-sm text-gray-600 mt-1">{role.description}</div>
                )}
                {role.permissions && role.permissions.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-500 mb-1">Permissions:</div>
                    <div className="flex flex-wrap gap-1">
                      {role.permissions.map((permission, permIndex) => (
                        <span key={permIndex} className="px-1 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                          {permission}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
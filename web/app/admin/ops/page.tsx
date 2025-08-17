"use client";
import { useState, useEffect } from "react";
import { API_BASE, authHeaders } from "@/lib/api";
import EvidenceAdminPanel from "@/components/EvidenceAdminPanel";
import { useRequireAuth } from "@/components/AuthProvider";
import { isAdmin } from "@/lib/auth";

type PresetRow = { 
  id: string; 
  name: string; 
  version: string; 
  source: string; 
  counts: { pillars: number; capabilities: number; questions: number } 
};

export default function AdminOpsPage() {
  const [activeTab, setActiveTab] = useState<'presets' | 'evidence'>('presets');
  const [presets, setPresets] = useState<PresetRow[]>([]);
  const [msg, setMsg] = useState<string>("");
  
  // Require authentication and admin access
  const auth = useRequireAuth();

  useEffect(() => {
    if (auth.isAuthenticated && isAdmin()) {
      loadPresets();
    }
  }, [auth.isAuthenticated]);

  async function loadPresets() {
    try {
      const r = await fetch(`${API_BASE}/presets`, { headers: authHeaders() });
      if (!r.ok) {
        setMsg(`Failed to load presets: ${r.status}`);
        return;
      }
      setPresets(await r.json());
    } catch (error) {
      setMsg(`Error loading presets: ${error}`);
    }
  }

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const r = await fetch(`${API_BASE}/presets/upload`, {
        method: "POST",
        headers: { ...authHeaders() }, // do NOT set content-type here
        body: fd
      });
      if (!r.ok) { 
        const errorText = await r.text();
        setMsg(`Upload failed: ${r.status} - ${errorText}`); 
        return; 
      }
      const data = await r.json();
      setMsg(`Uploaded: ${data.name} (${data.id})`);
      await loadPresets();
      e.currentTarget.reset();
    } catch (error) {
      setMsg(`Upload error: ${error}`);
    }
  }

  if (auth.isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!isAdmin()) {
    return (
      <div className="p-6">
        <div className="text-red-600">Access denied. Admin privileges required.</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Admin Operations</h1>
        <div className="text-sm text-gray-500">
          User: {auth.user?.name} • Mode: {auth.mode.mode === 'aad' ? 'Azure AD' : 'Demo'}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'presets', label: 'Presets Management' },
            { id: 'evidence', label: 'Evidence Management' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'presets' && (
        <div className="space-y-6">
          <form onSubmit={onUpload} className="border rounded p-4 space-y-3">
            <div className="text-sm text-gray-600">Upload a preset JSON</div>
            <input name="file" type="file" accept="application/json" className="border rounded p-2" required />
            <button className="px-3 py-1 border rounded bg-blue-500 text-white hover:bg-blue-600" type="submit">Upload</button>
            {msg && <div className="text-sm">{msg}</div>}
          </form>
          
          <div className="border rounded p-4">
            <div className="font-medium mb-2">Available Presets</div>
            <table className="w-full text-sm">
              <thead><tr className="border-b">
                <th className="text-left py-2">Name</th>
                <th className="text-left py-2">ID</th>
                <th className="text-left py-2">Version</th>
                <th className="text-left py-2">Counts (P/C/Q)</th>
                <th className="text-left py-2">Source</th>
                <th className="text-left py-2">Actions</th>
              </tr></thead>
              <tbody>
                {presets.map(it => (
                  <tr key={it.id} className="border-t">
                    <td className="py-2">{it.name}</td>
                    <td className="py-2 font-mono text-xs">{it.id}</td>
                    <td className="py-2">{it.version}</td>
                    <td className="py-2">{it.counts.pillars}/{it.counts.capabilities}/{it.counts.questions}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs ${it.source === 'bundled' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
                        {it.source}
                      </span>
                    </td>
                    <td className="py-2 space-x-2">
                      <a className="underline text-blue-600 hover:text-blue-800" href={`${API_BASE}/presets/${it.id}`} target="_blank" rel="noopener noreferrer">Preview</a>
                      <button 
                        className="underline text-gray-600 hover:text-gray-800"
                        onClick={() => navigator.clipboard.writeText(it.id)}
                      >
                        Copy ID
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {presets.length === 0 && (
              <div className="text-gray-500 text-center py-4">No presets available</div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'evidence' && (
        <EvidenceAdminPanel className="max-w-2xl" />
      )}
    </div>
  );
}
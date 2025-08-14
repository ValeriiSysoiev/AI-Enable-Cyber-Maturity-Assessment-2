"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { requireEmail, getEmail, setEngagementId, isAdmin } from "@/lib/auth";
import { API_BASE } from "@/lib/orchestration";

interface Engagement {
  id: string;
  name: string;
  client_code?: string;
  created_by: string;
  created_at: string;
}

export default function Engagements() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newClientCode, setNewClientCode] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const loadEngagements = useCallback(async () => {
    try {
      const email = getEmail();
      if (!email || !email.trim()) {
        setError("Email is required");
        setLoading(false);
        return;
      }
      
      const res = await fetch(`${API_BASE}/engagements`, {
        headers: {
          "X-User-Email": email,
          "X-Engagement-ID": "bootstrap", // Required by API but not used for listing
        },
      });
      if (res.ok) {
        const data = await res.json();
        setEngagements(data);
      } else {
        setError("Failed to load engagements");
      }
    } catch (err) {
      setError("Error loading engagements");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      const email = await requireEmail(router);
      if (email) {
        loadEngagements();
      }
    };
    initAuth();
  }, [router, loadEngagements]);

  const handleCreate = async () => {
    try {
      const email = getEmail();
      const res = await fetch(`${API_BASE}/engagements`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Email": email,
          "X-Engagement-ID": "bootstrap",
        },
        body: JSON.stringify({ 
          name: newName, 
          client_code: newClientCode || undefined 
        }),
      });
      if (res.ok) {
        setNewName("");
        setNewClientCode("");
        setShowCreate(false);
        loadEngagements();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to create engagement");
      }
    } catch (err) {
      setError("Error creating engagement");
    }
  };

  const selectEngagement = (id: string) => {
    setEngagementId(id);
    router.push(`/e/${id}/demo`);
  };

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold mb-6">My Engagements</h1>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {isAdmin() && (
        <div className="mb-6">
          {!showCreate ? (
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Create New Engagement
            </button>
          ) : (
            <div className="bg-gray-50 p-4 rounded">
              <h3 className="text-lg font-medium mb-3">New Engagement</h3>
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Engagement Name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                />
                <input
                  type="text"
                  placeholder="Client Code (optional)"
                  value={newClientCode}
                  onChange={(e) => setNewClientCode(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleCreate}
                    disabled={!newName.trim()}
                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Create
                  </button>
                  <button
                    onClick={() => {
                      setShowCreate(false);
                      setNewName("");
                      setNewClientCode("");
                    }}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid gap-4">
        {engagements.length === 0 ? (
          <p className="text-gray-500">No engagements found. {isAdmin() && "Create one to get started."}</p>
        ) : (
          engagements.map((eng) => (
            <div
              key={eng.id}
              onClick={() => selectEngagement(eng.id)}
              className="p-4 border rounded hover:bg-gray-50 cursor-pointer"
            >
              <h3 className="font-medium text-lg">{eng.name}</h3>
              {eng.client_code && (
                <p className="text-sm text-gray-600">Client: {eng.client_code}</p>
              )}
              <p className="text-sm text-gray-500">
                Created by {eng.created_by} on {new Date(eng.created_at).toLocaleDateString()}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

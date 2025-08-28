"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getEmail, getEngagementId, setEngagementId } from "../lib/auth";

interface Engagement {
  id: string;
  name: string;
  client_code?: string;
}

export default function EngagementSwitcher() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [currentEngagementId, setCurrentEngagementId] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const email = getEmail();
    const engId = getEngagementId();
    if (email) {
      // Defer engagement loading to not block initial page render
      setTimeout(() => {
        loadEngagements();
      }, 100);
      if (engId) {
        setCurrentEngagementId(engId);
      }
    }
  }, []);

  const loadEngagements = async () => {
    setLoading(true);
    setError(null);
    try {
      const email = getEmail();
      if (!email) {
        setError("No email found");
        return;
      }
      
      // Use server-side proxy route instead of direct external API call
      const res = await fetch('/api/proxy/engagements', {
        headers: {
          "X-User-Email": email,
          "X-Engagement-ID": getEngagementId() || "bootstrap",
        },
        signal: AbortSignal.timeout(8000), // 8 second timeout for engagement loading
      });
      if (res.ok) {
        const data = await res.json();
        setEngagements(data);
      } else {
        try {
          const errorData = await res.json();
          const serverMessage = errorData.message || errorData.error || errorData.detail;
          setError(serverMessage ? `Failed to load engagements: ${serverMessage}` : `Failed to load engagements (${res.status} ${res.statusText})`);
        } catch {
          try {
            const textError = await res.text();
            setError(textError ? `Failed to load engagements: ${textError}` : `Failed to load engagements (${res.status} ${res.statusText})`);
          } catch {
            setError(`Failed to load engagements (${res.status} ${res.statusText})`);
          }
        }
      }
    } catch (err) {
      console.error("Failed to load engagements", err);
      setError("Failed to load engagements");
    } finally {
      setLoading(false);
    }
  };

  const switchEngagement = (id: string) => {
    setEngagementId(id);
    setCurrentEngagementId(id);
    setShowDropdown(false);
    
    // Redirect to engagement-specific route if on a generic page
    if (pathname === "/demo-orchestration") {
      router.push(`/e/${id}/demo`);
    } else if (pathname.startsWith("/e/") && pathname.includes("/demo")) {
      // Replace current engagement ID in path
      const newPath = pathname.replace(/\/e\/[^/]+\//, `/e/${id}/`);
      router.push(newPath);
    }
  };

  const currentEngagement = engagements.find(e => e.id === currentEngagementId);

  if (!getEmail() || engagements.length === 0) {
    return null;
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-2 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
        disabled={loading}
      >
        <span className="font-medium">
          {loading ? "Loading..." : currentEngagement ? currentEngagement.name : "Select Engagement"}
        </span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {showDropdown && (
        <div className="absolute right-0 mt-1 w-64 bg-white border rounded-md shadow-lg z-50">
          {error && (
            <div className="px-4 py-2 text-sm text-red-600 bg-red-50 border-b">
              {error}
              <button 
                onClick={() => {
                  setError(null);
                  loadEngagements();
                }}
                className="ml-2 text-xs underline"
              >
                Retry
              </button>
            </div>
          )}
          <div className="py-1">
            {engagements.map(eng => (
              <button
                key={eng.id}
                onClick={() => switchEngagement(eng.id)}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${
                  eng.id === currentEngagementId ? "bg-gray-50 font-medium" : ""
                }`}
              >
                <div>{eng.name}</div>
                {eng.client_code && (
                  <div className="text-xs text-gray-500">Client: {eng.client_code}</div>
                )}
              </button>
            ))}
          </div>
          <div className="border-t">
            <button
              onClick={() => {
                setShowDropdown(false);
                router.push("/engagements");
              }}
              className="w-full text-left px-4 py-2 text-sm text-indigo-600 hover:bg-gray-100"
            >
              Manage Engagements
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

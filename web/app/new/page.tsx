"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchPreset, authHeaders } from "@/lib/api";
import { createAssessment } from "@/lib/assessments";
import ApiErrorBoundary from "@/components/ApiErrorBoundary";
import { useAuth } from "@/components/AuthProvider";

type PresetOption = { id: string; name: string; version: string; source: string; counts: { pillars: number; capabilities: number; questions: number } };

export default function NewAssessmentPage() {
  const router = useRouter();
  const auth = useAuth();
  const [loading, setLoading] = useState(false);
  const [preset, setPreset] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [presets, setPresets] = useState<PresetOption[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>("");
  
  useEffect(() => {
    loadPresets();
  }, []);

  async function loadPresets() {
    try {
      // Try API proxy first, fallback to direct presets endpoint
      let r = await fetch('/api/proxy/presets', { 
        headers: authHeaders(),
        cache: 'no-store'
      });
      
      if (!r.ok) {
        console.warn('API proxy failed, trying fallback presets endpoint');
        r = await fetch('/api/presets', { 
          cache: 'no-store'
        });
      }
      
      if (!r.ok) {
        throw new Error(`Failed to fetch presets: ${r.status}`);
      }
      const presetList = await r.json();
      setPresets(presetList);
      // Auto-select first preset if available
      if (presetList.length > 0) {
        setSelectedPresetId(presetList[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load presets");
    }
  }
  
  async function load() {
    if (!selectedPresetId) {
      setError("Please select a preset");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setPreset(await fetchPreset(selectedPresetId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preset");
    } finally {
      setLoading(false);
    }
  }

  async function handleContinue() {
    if (!selectedPresetId) {
      setError("Please select a preset");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      // Ensure user email is available for the API call
      if (auth.user?.email && typeof window !== 'undefined') {
        localStorage.setItem('email', auth.user.email);
      }
      
      const assessment = await createAssessment("Demo Assessment", selectedPresetId);
      router.push(`/assessment/${assessment.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create assessment");
      setCreating(false);
    }
  }
  return (
    <ApiErrorBoundary>
      <main className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">New Assessment — Scope</h1>
      <div className="space-y-2">
        <label className="block text-sm font-medium">Profile</label>
        <select 
          className="border rounded px-3 py-2" 
          value={selectedPresetId}
          onChange={(e) => setSelectedPresetId(e.target.value)}
        >
          {presets.length === 0 ? (
            <option value="">Loading presets...</option>
          ) : (
            presets.map(preset => (
              <option key={preset.id} value={preset.id}>
                {preset.name} v{preset.version} ({preset.counts.questions} questions)
              </option>
            ))
          )}
        </select>
      </div>
      <button onClick={load} className="px-4 py-2 bg-black text-white rounded" disabled={loading}>
        {loading ? "Loading…" : "Load preset"}
      </button>
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded">
          Error: {error}
        </div>
      )}
      {preset && (
        <div className="mt-4 border rounded p-4 bg-white">
          <p className="font-medium">{preset.name}</p>
          <p className="text-sm text-gray-600">{preset.description}</p>
          <ul className="mt-2 list-disc list-inside">
            {preset.pillars.map((p: any) => (
              <li key={p.id}>{p.name} — weight {(p.weight*100).toFixed(0)}%</li>
            ))}
          </ul>
          <p className="mt-2 text-sm">Default target level: <b>{preset.default_target_level}</b></p>
          <button 
            onClick={handleContinue} 
            disabled={creating}
            className="inline-block mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {creating ? "Creating..." : "Continue"}
          </button>
        </div>
      )}
      </main>
    </ApiErrorBoundary>
  );
}

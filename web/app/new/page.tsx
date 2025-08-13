"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { fetchPreset } from "@/lib/api";
import { createAssessment } from "@/lib/assessments";

export default function NewAssessmentPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [preset, setPreset] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  
  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPreset(await fetchPreset("cyber-for-ai"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preset");
    } finally {
      setLoading(false);
    }
  }

  async function handleContinue() {
    setCreating(true);
    setError(null);
    try {
      const assessment = await createAssessment("Demo Assessment", "cyber-for-ai");
      router.push(`/assessment/${assessment.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create assessment");
      setCreating(false);
    }
  }
  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">New Assessment — Scope</h1>
      <div className="space-y-2">
        <label className="block text-sm font-medium">Profile</label>
        <select className="border rounded px-3 py-2" defaultValue="cyber-for-ai">
          <option value="cyber-for-ai">Cyber for AI</option>
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
  );
}

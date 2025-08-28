"use client";
import { useEffect, useState } from "react";
import { fetchPreset } from "../../../lib/api";
import QuestionCard from "../../../components/QuestionCard";

export default function DraftAssessment() {
  const [preset, setPreset] = useState<any>(null);
  const [pillarId, setPillarId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { 
    (async () => {
      try {
        const p = await fetchPreset("cyber-for-ai");
        setPreset(p);
        setPillarId(p.pillars[0]?.id ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load preset");
      } finally {
        setLoading(false);
      }
    })(); 
  }, []);

  if (loading) return <main className="p-8">Loading…</main>;
  if (error) return <main className="p-8"><div className="p-4 bg-red-50 text-red-700 rounded">Error: {error}</div></main>;
  if (!preset) return <main className="p-8">No preset loaded</main>;

  const current = pillarId ? preset.questions[pillarId] : [];

  return (
    <div className="grid grid-cols-12 min-h-screen">
      <aside className="col-span-3 bg-gray-100 p-4 space-y-2">
        <h2 className="font-semibold mb-2">Pillars</h2>
        {preset.pillars.map((p: any) => (
          <button key={p.id} onClick={() => setPillarId(p.id)}
            className={`block w-full text-left px-3 py-2 rounded ${pillarId===p.id?'bg-white':'hover:bg-white'}`}>
            {p.name}
          </button>
        ))}
      </aside>
      <main className="col-span-9 p-6 space-y-4">
        <h1 className="text-xl font-semibold">{preset.name}</h1>
        {current?.map((q: any) => (
          <QuestionCard key={q.id} question={q} />
        ))}
      </main>
    </div>
  );
}

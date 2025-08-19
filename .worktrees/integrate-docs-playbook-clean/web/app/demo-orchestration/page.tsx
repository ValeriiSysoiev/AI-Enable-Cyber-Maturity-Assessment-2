"use client";

import { useState } from "react";
import { createAssessment, runAnalyze, runRecommend } from "@/lib/orchestration";

export default function DemoOrchestration() {
  const [aid, setAid] = useState<string>("");
  const [content, setContent] = useState<string>("Sample workshop notes:\n- Admins without MFA\n- No M365 DLP\n- No incident runbooks");
  const [findings, setFindings] = useState<any[]>([]);
  const [recs, setRecs] = useState<any[]>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [msg, setMsg] = useState<string>("");

  async function onCreate() {
    setBusy(true); setMsg("");
    try {
      const a = await createAssessment("Demo Assessment");
      setAid(a.id);
      setMsg(`Created assessment ${a.id}`);
    } catch (e:any) {
      setMsg(e.message);
    } finally { setBusy(false); }
  }

  async function onAnalyze() {
    if (!aid) return setMsg("Create assessment first");
    setBusy(true); setMsg("");
    try {
      const r = await runAnalyze(aid, content);
      setFindings(r.findings || []);
      setMsg(`Analyze ok: ${r.findings?.length || 0} findings`);
    } catch (e:any) {
      setMsg(e.message);
    } finally { setBusy(false); }
  }

  async function onRecommend() {
    if (!aid) return setMsg("Create assessment first");
    setBusy(true); setMsg("");
    try {
      const r = await runRecommend(aid);
      setRecs(r.recommendations || []);
      setMsg(`Recommend ok: ${r.recommendations?.length || 0} items`);
    } catch (e:any) {
      setMsg(e.message);
    } finally { setBusy(false); }
  }

  // Check if engagement is selected
  const hasEngagement = typeof window !== "undefined" && localStorage.getItem("engagementId");

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Demo Orchestration</h1>
      
      {!hasEngagement && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
          <p className="text-yellow-800">
            No engagement selected. 
            <a href="/engagements" className="ml-2 text-yellow-900 underline font-medium">
              Choose an engagement
            </a>
          </p>
        </div>
      )}
      <div className="flex gap-2">
        <button className="px-3 py-2 rounded bg-black text-white" onClick={onCreate} disabled={busy}>Create Assessment</button>
        <button className="px-3 py-2 rounded bg-black text-white" onClick={onAnalyze} disabled={busy}>Run Analyze</button>
        <button className="px-3 py-2 rounded bg-black text-white" onClick={onRecommend} disabled={busy}>Run Recommend</button>
      </div>
      {msg && <div className="text-sm text-gray-600">{msg}</div>}

      <div>
        <label className="block text-sm font-medium mb-1">Workshop / Doc Content</label>
        <textarea value={content} onChange={e=>setContent(e.target.value)} className="w-full border rounded p-2 h-40" />
      </div>

      <div>
        <h2 className="text-xl font-medium">Findings</h2>
        <ul className="list-disc pl-6">
          {(findings || []).map((f:any, index:number)=>(
            <li key={f?.id ?? `finding-${index}`}>
              <strong>[{f?.severity || 'medium'}] {f?.area || "General"}:</strong> {f?.title || 'Untitled finding'}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h2 className="text-xl font-medium">Recommendations</h2>
        <ol className="list-decimal pl-6">
          {(recs || []).map((r:any, index:number)=>(
            <li key={r?.id ?? `result-${index}`}>
              {r?.title || 'Untitled recommendation'} <span className="text-xs text-gray-500">({r?.priority || 'P2'}, {r?.effort || 'M'}, {r?.timeline_weeks ?? "?"}w)</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

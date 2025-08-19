"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { createAssessment, runAnalyze, runRecommend } from "@/lib/orchestration";
import { requireEmail, setEngagementId } from "@/lib/auth";
import EngagementSwitcher from "@/components/EngagementSwitcher";
import { listDocs, uploadDocs, deleteDoc, downloadUrl, analyzeDoc, type Doc } from "@/lib/docs";
import { authHeaders } from "@/lib/api";

interface Finding {
  id: string;
  title: string;
  description?: string;
  severity: string;
  area: string;
  source?: string;
  createdAt?: string;
  updatedAt?: string;
}

interface Recommendation {
  id: string;
  title: string;
  description?: string;
  priority: string;
  effort: string;
  timeline_weeks: number;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

export default function EngagementDemo() {
  const params = useParams();
  const router = useRouter();
  const engagementId = params.engagementId as string;
  
  const [aid, setAid] = useState<string>("");
  const [content, setContent] = useState<string>("Sample workshop notes:\n- Admins without MFA\n- No M365 DLP\n- No incident runbooks");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [msg, setMsg] = useState<string>("");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [docMsg, setDocMsg] = useState<string>("");

  useEffect(() => {
    const initAuth = async () => {
      const email = await requireEmail(router);
      if (email && engagementId) {
        // Set the engagement ID for API calls
        setEngagementId(engagementId);
        refreshDocs();
      }
    };
    initAuth();
  }, [engagementId, router]);

  async function refreshDocs() {
    if (!engagementId) return;
    try { 
      setDocs(await listDocs(engagementId)); 
    } catch (e: any) { 
      setDocMsg(e.message); 
    }
  }

  async function onCreate() {
    setBusy(true); setMsg("");
    try {
      const a = await createAssessment("Demo Assessment");
      setAid(a.id);
      setMsg(`Created assessment ${a.id}`);
    } catch (e: any) {
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
    } catch (e: any) {
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
    } catch (e: any) {
      setMsg(e.message);
    } finally { setBusy(false); }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (!files.length || !engagementId) return;
    setBusy(true);
    try {
      await uploadDocs(engagementId, files);
      await refreshDocs();
      setDocMsg(`Uploaded ${files.length} file(s)`);
    } catch (e: any) { 
      setDocMsg(e.message); 
    } finally { 
      setBusy(false); 
      e.currentTarget.value = ""; 
    }
  }

  async function onAnalyzeDoc(docId: string) {
    setBusy(true);
    try {
      const res = await analyzeDoc(engagementId, docId);
      setDocMsg(res?.note ? `Analyzed (note: ${res.note})` : "Analyzed");
    } catch (e: any) { 
      setDocMsg(e.message); 
    } finally { 
      setBusy(false); 
    }
  }

  async function onDeleteDoc(docId: string) {
    if (!confirm("Delete document?")) return;
    setBusy(true);
    try { 
      await deleteDoc(engagementId, docId); 
      await refreshDocs(); 
    } catch(e: any) { 
      setDocMsg(e.message); 
    } finally { 
      setBusy(false); 
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-xl font-semibold">AI Maturity Assessment</h1>
            <EngagementSwitcher />
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Demo Orchestration</h2>
          
          <div className="flex gap-2 mb-4">
            <button 
              className="px-3 py-2 rounded bg-black text-white disabled:opacity-50" 
              onClick={onCreate} 
              disabled={busy}
            >
              Create Assessment
            </button>
            <button 
              className="px-3 py-2 rounded bg-black text-white disabled:opacity-50" 
              onClick={onAnalyze} 
              disabled={busy}
            >
              Run Analyze
            </button>
            <button 
              className="px-3 py-2 rounded bg-black text-white disabled:opacity-50" 
              onClick={onRecommend} 
              disabled={busy}
            >
              Run Recommend
            </button>
          </div>
          
          {msg && <div className="text-sm text-gray-600 mb-4">{msg}</div>}

          <div className="mb-6">
            <label className="block text-sm font-medium mb-1">Workshop / Doc Content</label>
            <textarea 
              value={content} 
              onChange={e => setContent(e.target.value)} 
              className="w-full border rounded p-2 h-40" 
            />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-xl font-medium mb-3">Findings</h3>
              <ul className="list-disc pl-6 space-y-2">
                {findings.map((f, index) => (
                  <li key={f.id ?? `finding-${index}`}>
                    <strong>[{f.severity || 'medium'}] {f.area || "General"}:</strong> {f.title || 'Untitled finding'}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="text-xl font-medium mb-3">Recommendations</h3>
              <ol className="list-decimal pl-6 space-y-2">
                {recs.map((r, index) => (
                  <li key={r.id ?? `result-${index}`}>
                    {r.title || 'Untitled recommendation'} 
                    <span className="text-xs text-gray-500 ml-2">
                      ({r.priority || 'P2'}, {r.effort || 'M'}, {r.timeline_weeks ?? "?"}w)
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-xl border p-4 space-y-3">
          <h2 className="text-lg font-semibold">Documents</h2>
          <input type="file" multiple onChange={onUpload} disabled={busy} />
          <div className="text-sm text-gray-600">Max {process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? '10'} MB each. PDF, DOCX, TXT recommended.</div>
          <ul className="divide-y">
            {docs.map(d => (
              <li key={d.id} className="py-2 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium truncate">{d.filename}</div>
                  <div className="text-xs text-gray-500">{(d.size/1024).toFixed(1)} KB · {new Date(d.uploaded_at).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button 
                    className="underline" 
                    onClick={async () => {
                      const url = downloadUrl(engagementId as string, d.id);
                      const response = await fetch(url, { headers: authHeaders() });
                      if (response.ok) {
                        const blob = await response.blob();
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = d.filename;
                        a.click();
                      }
                    }} 
                    disabled={busy}
                  >
                    Download
                  </button>
                  <button className="px-2 py-1 border rounded" onClick={()=>onAnalyzeDoc(d.id)} disabled={busy}>Analyze</button>
                  <button className="px-2 py-1 border rounded" onClick={()=>onDeleteDoc(d.id)} disabled={busy}>Delete</button>
                </div>
              </li>
            ))}
            {!docs.length && <li className="text-sm text-gray-500">No documents yet.</li>}
          </ul>
          {docMsg && <div className="text-sm text-blue-700">{docMsg}</div>}
        </div>
      </div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getSummary, reportMdUrl, type EngagementSummary } from "@/lib/summary";
import DocumentsPanel from "@/components/DocumentsPanel";
import EvidenceSearch from "@/components/EvidenceSearch";
import AnalysisWithEvidence from "@/components/AnalysisWithEvidence";
import { useRequireAuth } from "@/components/AuthProvider";
import { isAdmin } from "@/lib/auth";

export default function DashboardPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const router = useRouter();
  const [sum, setSum] = useState<EngagementSummary | null>(null);
  const [err, setErr] = useState<string>("");
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'evidence' | 'analysis' | 'gdpr'>('overview');
  
  // Require authentication
  const auth = useRequireAuth();

  useEffect(() => {
    if (!engagementId) return;
    (async () => {
      try {
        const s = await getSummary(engagementId);
        setSum(s);
      } catch (e: any) {
        setErr(e.message ?? "Failed to load");
      }
    })();
  }, [engagementId]);

  if (auth.isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!engagementId) return <div className="p-6">No engagement selected.</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Engagement Dashboard</h1>
        <div className="flex gap-2">
          <Link className="px-3 py-1 border rounded bg-green-50 text-green-700 hover:bg-green-100" href={`/e/${engagementId}/evidence`}>
            📎 Evidence
          </Link>
          <a className="px-3 py-1 border rounded" href={reportMdUrl(engagementId)} target="_blank">Export Markdown</a>
          <Link className="px-3 py-1 border rounded" href={`/e/${engagementId}/demo`}>Open Demo</Link>
          <Link className="px-3 py-1 border rounded" href={`/e/${engagementId}/demo#docs`}>Docs</Link>
          {isAdmin() && (
            <Link className="px-3 py-1 border rounded bg-blue-50 text-blue-700 hover:bg-blue-100" href={`/e/${engagementId}/gdpr`}>
              GDPR
            </Link>
          )}
        </div>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'documents', label: 'Documents' },
            { id: 'evidence', label: 'Evidence Search' },
            { id: 'analysis', label: 'AI Analysis' },
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
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Card title="Assessments" value={sum?.counts.assessments ?? 0} />
            <Card title="Documents" value={sum?.counts.documents ?? 0} />
            <Card title="Findings" value={sum?.counts.findings ?? 0} />
            <Card title="Recommendations" value={sum?.counts.recommendations ?? 0} />
            <Card title="Run Logs" value={sum?.counts.runlogs ?? 0} />
          </div>

          <div className="rounded-xl border p-4">
            <div className="font-medium mb-2">Recent Activity</div>
            {!sum?.recent_activity?.length && <div className="text-sm text-gray-500">No activity yet.</div>}
            <ul className="divide-y">
              {sum?.recent_activity?.map((a, i) => (
                <li key={i} className="py-2 text-sm flex items-center justify-between gap-3">
                  <div className="truncate">
                    <span className="inline-block min-w-28 text-gray-500">{a.type}</span>
                    <span className="font-medium">{a.title || a.id}</span>
                  </div>
                  <div className="text-gray-500">{a.ts ? new Date(a.ts).toLocaleString() : ""}</div>
                </li>
              ))}
            </ul>
          </div>

          {sum?.recent_runlog_excerpt && (
            <div className="rounded-xl border p-4">
              <div className="font-medium mb-2">Recent Run Log</div>
              <pre className="text-sm whitespace-pre-wrap">{sum.recent_runlog_excerpt}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === 'documents' && <DocumentsPanel />}

      {activeTab === 'evidence' && (
        <EvidenceSearch 
          className="max-w-4xl"
          maxResults={20}
        />
      )}

      {activeTab === 'analysis' && (
        <AnalysisWithEvidence 
          className="max-w-4xl"
        />
      )}
    </div>
  );
}

function Card({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="rounded-xl border p-4">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}

"use client";
import { useState } from "react";

interface QuestionCardProps {
  question: {
    id: string;
    text: string;
    evidence: string[];
    level_hints: {
      [level: string]: string;
    };
  };
}

export default function QuestionCard({ question }: QuestionCardProps) {
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAiAssist() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/assist/autofill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_text: question.text })
      });
      if (res.ok) {
        const data = await res.json();
        setAiResponse(data);
      } else {
        throw new Error("Failed to get AI assistance");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get AI assistance");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border rounded p-4 space-y-3">
      <div className="font-medium">{question.text}</div>
      {question.level_hints && (
        <div className="text-sm text-gray-600">
          {question.level_hints["3"] && <span>L3: {question.level_hints["3"]}</span>}
          {question.level_hints["3"] && question.level_hints["4"] && <span className="mx-2">•</span>}
          {question.level_hints["4"] && <span>L4: {question.level_hints["4"]}</span>}
        </div>
      )}
      <div className="text-sm">
        <span className="font-medium">Evidence:</span> {question.evidence?.join(", ")}
      </div>
      <div className="flex items-center gap-4">
        <div>
          <label className="text-sm">Level:</label>
          <select className="ml-2 border rounded px-2 py-1" defaultValue="3" disabled>
            <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option>
          </select>
          <span className="ml-2 text-xs text-gray-500">read-only (stub)</span>
        </div>
        <button
          onClick={handleAiAssist}
          disabled={loading}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? "Loading..." : "AI Assist → Autofill"}
        </button>
      </div>
      {error && (
        <div className="mt-3 p-3 bg-red-50 rounded text-sm text-red-700">
          Error: {error}
        </div>
      )}
      {aiResponse && (
        <div className="mt-3 p-3 bg-blue-50 rounded text-sm">
          <div className="font-medium text-blue-900">AI Suggestion:</div>
          <div className="mt-1 text-blue-800">Proposed Level: {aiResponse.proposed_level}</div>
          <div className="mt-1 text-blue-700">{aiResponse.justification}</div>
        </div>
      )}
    </div>
  );
}

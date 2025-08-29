"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchPreset } from "../../../lib/api";
import { getAssessment, saveAnswer, getScores, Answer, ScoreData, Assessment } from "../../../lib/assessments";
import ScoreRadar from "../../../components/ScoreRadar";
import EvidenceUploader from "../../../components/EvidenceUploader";

import { AssessmentPreset, QuestionWithAnswer } from "../../../types/presets";

export default function AssessmentPage() {
  const params = useParams();
  const assessmentId = params.id as string;
  
  const [preset, setPreset] = useState<AssessmentPreset | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [pillarId, setPillarId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [savedStates, setSavedStates] = useState<{[key: string]: boolean}>({});
  const [scoreData, setScoreData] = useState<ScoreData | null>(null);
  const [loadingScores, setLoadingScores] = useState(false);
  const [showScores, setShowScores] = useState(false);
  const [evidenceUrls, setEvidenceUrls] = useState<{[key: string]: string[]}>({});

  useEffect(() => {
    loadData();
  }, [assessmentId]);

  async function loadData() {
    try {
      // Load assessment
      const assessmentData = await getAssessment(assessmentId);
      setAssessment(assessmentData);
      
      // Load preset
      const presetData = await fetchPreset(assessmentData.preset_id);
      setPreset(presetData);
      setPillarId(presetData.pillars[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveAnswer(pillarId: string, questionId: string, level: number, notes?: string) {
    const key = `${pillarId}-${questionId}`;
    setSaving(key);
    setSavedStates({ ...savedStates, [key]: false });
    
    try {
      await saveAnswer(assessmentId, {
        pillar_id: pillarId,
        question_id: questionId,
        level,
        notes
      });
      setSavedStates({ ...savedStates, [key]: true });
      setTimeout(() => {
        setSavedStates(prev => ({ ...prev, [key]: false }));
      }, 2000);
      // Reload assessment to get updated answers
      const updatedAssessment = await getAssessment(assessmentId);
      setAssessment(updatedAssessment);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save answer");
    } finally {
      setSaving(null);
    }
  }

  async function handleComputeScores() {
    setLoadingScores(true);
    try {
      const scores = await getScores(assessmentId);
      setScoreData(scores);
      setShowScores(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compute scores");
    } finally {
      setLoadingScores(false);
    }
  }

  function handleEvidenceUpload(questionKey: string, blobUrl: string) {
    setEvidenceUrls(prev => ({
      ...prev,
      [questionKey]: [...(prev[questionKey] || []), blobUrl]
    }));
  }

  if (loading) return <main className="p-8">Loading…</main>;
  if (error) return <main className="p-8"><div className="p-4 bg-red-50 text-red-700 rounded">Error: {error}</div></main>;
  if (!preset || !assessment) return <main className="p-8">No data loaded</main>;

  // Get questions for the current pillar
  const currentQuestions = pillarId 
    ? preset.pillars.find(p => p.id === pillarId)?.capabilities.flatMap(c => c.questions) || []
    : [];
  const answersByKey = assessment.answers.reduce((acc: Record<string, Answer>, ans: Answer) => {
    acc[`${ans.pillar_id}-${ans.question_id}`] = ans;
    return acc;
  }, {});

  return (
    <div className="grid grid-cols-12 min-h-screen">
      <aside className="col-span-3 bg-gray-100 p-4 space-y-2">
        <h2 className="font-semibold mb-2">Assessment: {assessment.name}</h2>
        <div className="text-sm text-gray-600 mb-4">ID: {assessmentId.slice(0, 8)}...</div>
        <h3 className="font-semibold">Pillars</h3>
        {preset.pillars.map((p: any) => (
          <button key={p.id} onClick={() => setPillarId(p.id)}
            className={`block w-full text-left px-3 py-2 rounded ${pillarId===p.id?'bg-white':'hover:bg-white'}`}>
            {p.name}
          </button>
        ))}
      </aside>
      <main className="col-span-9 p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold">{preset.name}</h1>
          <button
            onClick={handleComputeScores}
            disabled={loadingScores}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loadingScores ? "Computing..." : "Compute Scores"}
          </button>
        </div>
        
        {showScores && scoreData && (
          <div className="bg-white border rounded p-6 space-y-6">
            <h2 className="text-lg font-semibold">Assessment Scores</h2>
            
            {/* Pillar Scores Table */}
            <div>
              <h3 className="font-medium mb-2">Pillar Scores</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Pillar</th>
                    <th className="text-center py-2">Score</th>
                    <th className="text-center py-2">Weight</th>
                    <th className="text-center py-2">Questions</th>
                  </tr>
                </thead>
                <tbody>
                  {scoreData.pillar_scores.map((ps) => {
                    const pillar = preset.pillars.find((p: any) => p.id === ps.pillar_id);
                    return (
                      <tr key={ps.pillar_id} className="border-b">
                        <td className="py-2">{pillar?.name || ps.pillar_id}</td>
                        <td className="text-center py-2">
                          {ps.score !== null ? ps.score.toFixed(1) : "N/A"}
                        </td>
                        <td className="text-center py-2">{(ps.weight * 100).toFixed(0)}%</td>
                        <td className="text-center py-2">
                          {ps.questions_answered} / {ps.total_questions}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {/* Radar Chart */}
            <div>
              <h3 className="font-medium mb-2">Radar Visualization</h3>
              <ScoreRadar 
                scores={scoreData.pillar_scores.map(ps => {
                  const pillar = preset.pillars.find((p: any) => p.id === ps.pillar_id);
                  return {
                    pillar_id: ps.pillar_id,
                    pillar_name: pillar?.name || ps.pillar_id,
                    score: ps.score
                  };
                })}
              />
            </div>
            
            {/* Overall Score */}
            <div className="bg-gray-50 p-4 rounded">
              <h3 className="font-medium">Overall Score</h3>
              <div className="text-2xl font-bold mt-1">
                {scoreData.overall_score !== null ? scoreData.overall_score.toFixed(2) : "N/A"} / 5.0
              </div>
              {scoreData.gates_applied.length > 0 && (
                <div className="mt-2 text-sm text-orange-600">
                  {scoreData.gates_applied.map((gate, i) => (
                    <div key={i}>⚠️ {gate}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        {currentQuestions?.map((q: any) => {
          const key = `${pillarId}-${q.id}`;
          const existingAnswer = answersByKey[key];
          const isSaving = saving === key;
          const isSaved = savedStates[key];
          
          return (
            <div key={q.id} className="bg-white border rounded p-4 space-y-3">
              <div className="font-medium">{q.text}</div>
              {q.level_hints && (
                <div className="text-sm text-gray-600">
                  {q.level_hints["3"] && <span>L3: {q.level_hints["3"]}</span>}
                  {q.level_hints["3"] && q.level_hints["4"] && <span className="mx-2">•</span>}
                  {q.level_hints["4"] && <span>L4: {q.level_hints["4"]}</span>}
                </div>
              )}
              <div className="text-sm">
                <span className="font-medium">Evidence:</span> {q.evidence?.join(", ")}
              </div>
              <div className="flex items-center gap-4">
                <div>
                  <label className="text-sm">Level:</label>
                  <select 
                    id={`level-${key}`}
                    className="ml-2 border rounded px-2 py-1" 
                    defaultValue={existingAnswer?.level || "3"}
                    disabled={isSaving}
                  >
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                    <option value="5">5</option>
                  </select>
                </div>
                <button
                  onClick={() => {
                    const select = document.getElementById(`level-${key}`) as HTMLSelectElement;
                    handleSaveAnswer(pillarId!, q.id, parseInt(select.value));
                  }}
                  disabled={isSaving}
                  className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
                >
                  {isSaving ? "Saving..." : "Save"}
                </button>
                {isSaved && <span className="text-sm text-green-600">✓ Saved</span>}
              </div>
              
              {/* Evidence Upload Section */}
              <div className="border-t pt-3 space-y-2">
                <div className="text-sm font-medium">Upload Evidence</div>
                <EvidenceUploader 
                  onUploadComplete={(evidence) => handleEvidenceUpload(key, evidence.blob_path)}
                />
                
                {/* Display linked evidence */}
                {evidenceUrls[key] && evidenceUrls[key].length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="text-sm font-medium text-gray-700">Linked Evidence:</div>
                    {evidenceUrls[key].map((url, idx) => (
                      <div key={idx} className="text-sm text-blue-600 truncate">
                        • {url.split('/').pop()}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </main>
    </div>
  );
}

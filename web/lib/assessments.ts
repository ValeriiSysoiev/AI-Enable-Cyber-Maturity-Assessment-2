const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Assessment {
  id: string;
  name: string;
  preset_id: string;
  created_at: string;
  answers: Answer[];
}

export interface Answer {
  pillar_id: string;
  question_id: string;
  level: number;
  notes?: string;
}

export interface ScoreData {
  assessment_id: string;
  pillar_scores: {
    pillar_id: string;
    score: number | null;
    weight: number;
    questions_answered: number;
    total_questions: number;
  }[];
  overall_score: number | null;
  gates_applied: string[];
}

export async function createAssessment(name: string, presetId: string): Promise<Assessment> {
  const res = await fetch(`${BASE}/assessments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, preset_id: presetId })
  });
  if (!res.ok) {
    throw new Error("Failed to create assessment");
  }
  return res.json();
}

export async function saveAnswer(assessmentId: string, payload: Answer): Promise<void> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error("Failed to save answer");
  }
}

export async function getScores(assessmentId: string): Promise<ScoreData> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}/scores`);
  if (!res.ok) {
    throw new Error("Failed to get scores");
  }
  return res.json();
}

export async function getAssessment(assessmentId: string): Promise<Assessment> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}`);
  if (!res.ok) {
    throw new Error("Failed to get assessment");
  }
  return res.json();
}















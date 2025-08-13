# app/api/assist.py
from fastapi import APIRouter
router = APIRouter(prefix="/assist", tags=["assist"])

@router.post("/autofill")
def autofill(payload: dict):
  """Stub: returns a canned draft justification."""
  qtext = payload.get("question_text", "")
  return {
    "proposed_level": 3,
    "justification": f"Based on available evidence and the question '{qtext[:80]}...', a preliminary level 3 is suggested. Provide documented tests, metrics, and approvals to reach level 4.",
    "citations": []
  }











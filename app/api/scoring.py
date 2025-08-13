from typing import Dict, List, Optional, Tuple
from app.api.models import Answer

def compute_scores(answers_by_pillar: Dict[str, List[Answer]], preset: dict) -> Tuple[Dict[str, Optional[float]], Optional[float], List[str]]:
    """
    Compute pillar scores and overall score based on answers and preset configuration.
    
    Returns:
        - pillar_scores: Dict mapping pillar_id to score (None if no answers)
        - overall_score: Weighted average across pillars (None if no scores)
        - gates_applied: List of gate messages that were applied
    """
    pillar_scores = {}
    gates_applied = []
    
    # Calculate per-pillar scores (average of levels)
    for pillar in preset["pillars"]:
        pillar_id = pillar["id"]
        answers = answers_by_pillar.get(pillar_id, [])
        
        if answers:
            total = sum(answer.level for answer in answers)
            pillar_scores[pillar_id] = total / len(answers)
        else:
            pillar_scores[pillar_id] = None
    
    # Calculate overall score (weighted average)
    weighted_sum = 0
    total_weight = 0
    
    for pillar in preset["pillars"]:
        pillar_id = pillar["id"]
        weight = pillar["weight"]
        score = pillar_scores.get(pillar_id)
        
        if score is not None:
            weighted_sum += score * weight
            total_weight += weight
    
    if total_weight > 0:
        overall_score = weighted_sum / total_weight
    else:
        overall_score = None
    
    # Apply gates
    if overall_score is not None and "scoring" in preset and "gates" in preset["scoring"]:
        for gate in preset["scoring"]["gates"]:
            gate_pillar = gate["pillar"]
            min_level = gate["min_level"]
            reason = gate["reason"]
            
            pillar_score = pillar_scores.get(gate_pillar)
            if pillar_score is not None and pillar_score < min_level:
                # Cap overall score at 3 if gate condition is met
                if overall_score > 3:
                    overall_score = 3.0
                    gates_applied.append(f"Gate applied: {reason}")
    
    return pillar_scores, overall_score, gates_applied











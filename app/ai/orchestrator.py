from __future__ import annotations
import sys
sys.path.append("/app")
import re
import logging
from typing import List, Optional
from pydantic import BaseModel
from domain.models import Finding, Recommendation, RunLog
from ai.llm import LLMClient

# Set up logger
logger = logging.getLogger(__name__)

SYSTEM_ANALYZE = (
    "You are DocAnalyzer. Extract concise cybersecurity maturity findings from the provided content. "
    "Return bullets with [low|medium|high] severity, area (e.g., Identity, Data, SecOps), and evidence."
)
SYSTEM_RECOMMEND = (
    "You are GapRecommender. Using the provided findings, generate prioritized, actionable recommendations. "
    "Each item must include title, short rationale, priority (P1|P2|P3), effort (S|M|L) and suggested timeline in weeks."
)

# Regex patterns for parsing
FINDING_PATTERN = re.compile(
    r'^[-*•]?\s*\[?\s*(low|medium|high|critical|info|informational)\s*\]?\s*'
    r'(?:([^:]+?)\s*:\s*)?(.+)$',
    re.IGNORECASE
)

RECOMMENDATION_PATTERN = re.compile(
    r'^(?:[0-9]+[.)\s]+|[-*•]\s+)?(.+?)(?:\s*\(([^)]+)\))?$'
)

# Severity normalization mapping
SEVERITY_MAP = {
    'informational': 'info',
    'low': 'low',
    'medium': 'medium',
    'high': 'high',
    'critical': 'critical'
}

class Orchestrator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, assessment_id: str, content: str):
        text = self.llm.generate(SYSTEM_ANALYZE, content)
        findings: List[Finding] = []
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            match = FINDING_PATTERN.match(line)
            if match:
                severity_raw = match.group(1)
                area = match.group(2)
                title = match.group(3)
                
                # Normalize severity
                severity = SEVERITY_MAP.get(severity_raw.lower(), 'medium')
                
                # Clean up captured groups
                if area:
                    area = area.strip().strip('"\'')
                title = title.strip().strip('"\'')
                
                # Only create finding if we have a title
                if title:
                    findings.append(Finding(
                        assessment_id=assessment_id,
                        title=title,
                        severity=severity,
                        area=area
                    ))
                    logger.debug(f"Parsed finding: severity={severity}, area={area}, title={title[:50]}...")
                else:
                    logger.warning(f"Skipped finding with empty title from line: {line}")
            else:
                # Log lines that look like findings but didn't match
                if any(marker in line.lower() for marker in ['low', 'medium', 'high', 'critical']):
                    logger.debug(f"Line might contain finding but didn't match pattern: {line}")
        
        # Safely limit output preview
        preview_lines = text.splitlines()[:8]
        preview = "\n".join(preview_lines)[:500]  # Limit to 500 chars
        
        log = RunLog(
            assessment_id=assessment_id,
            agent="DocAnalyzer",
            input_preview=content[:200],
            output_preview=preview
        )
        return findings, log

    def recommend(self, assessment_id: str, findings_for_prompt: str):
        text = self.llm.generate(SYSTEM_RECOMMEND, findings_for_prompt)
        recs: List[Recommendation] = []
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Try to match recommendation pattern
            match = RECOMMENDATION_PATTERN.match(line)
            if match:
                title_part = match.group(1)
                metadata_part = match.group(2)
                
                # Skip if title is too short or looks like just a number
                if not title_part or len(title_part) < 5 or title_part.isdigit():
                    continue
                
                # Default values
                priority = "P2"
                effort = "M"
                weeks: Optional[int] = None
                
                # Parse metadata if present
                if metadata_part:
                    # Normalize metadata to lowercase for matching
                    meta_lower = metadata_part.lower()
                    tokens = re.split(r'[,;\s]+', metadata_part)
                    
                    # Extract priority
                    if 'p1' in meta_lower:
                        priority = "P1"
                    elif 'p3' in meta_lower:
                        priority = "P3"
                    elif 'p2' in meta_lower:
                        priority = "P2"
                    
                    # Extract effort
                    for token in tokens:
                        token_clean = token.strip().upper()
                        if token_clean == 'S' or 'small' in token.lower():
                            effort = "S"
                        elif token_clean == 'L' or 'large' in token.lower():
                            effort = "L"
                        elif token_clean == 'M' or 'medium' in token.lower():
                            effort = "M"
                    
                    # Extract weeks
                    for token in tokens:
                        # Look for patterns like "6 weeks", "6w", or just "6"
                        week_match = re.search(r'(\d+)\s*(?:weeks?|w)?', token)
                        if week_match:
                            try:
                                weeks = int(week_match.group(1))
                                break
                            except ValueError:
                                pass
                    
                    # Clean title by removing metadata
                    title_clean = title_part.strip()
                else:
                    title_clean = line.strip()
                
                # Remove list markers from title
                title_clean = re.sub(r'^[0-9]+[.)\s]+|^[-*•]\s+', '', title_clean).strip()
                
                # Limit title length
                if len(title_clean) > 200:
                    title_clean = title_clean[:197] + "..."
                
                recs.append(Recommendation(
                    assessment_id=assessment_id,
                    title=title_clean,
                    priority=priority,
                    effort=effort,
                    timeline_weeks=weeks
                ))
                logger.debug(f"Parsed recommendation: priority={priority}, effort={effort}, weeks={weeks}, title={title_clean[:50]}...")
        
        # Safely limit output preview
        preview_lines = text.splitlines()[:8]
        preview = "\n".join(preview_lines)[:500]  # Limit to 500 chars
        
        log = RunLog(
            assessment_id=assessment_id,
            agent="GapRecommender",
            input_preview=findings_for_prompt[:200],
            output_preview=preview
        )
        return recs, log

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PresetQuestion(BaseModel):
    id: str
    text: str
    weight: float = 1.0
    scale: str = "0-5"

class PresetCapability(BaseModel):
    id: str
    name: str
    questions: List[PresetQuestion]

class PresetPillar(BaseModel):
    id: str
    name: str
    capabilities: List[PresetCapability]

class AssessmentPreset(BaseModel):
    id: str
    name: str
    version: str = "1.0"
    pillars: List[PresetPillar]
    # optional metadata
    generated_at: Optional[str] = None
    source_file: Optional[str] = None
    columns_mapping: Optional[Dict[str, str]] = None

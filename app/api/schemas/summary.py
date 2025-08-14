from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CountSummary(BaseModel):
    assessments: int
    documents: int
    findings: int
    recommendations: int
    runlogs: int


class ActivityItem(BaseModel):
    type: str
    id: str
    ts: Optional[datetime] = None
    title: Optional[str] = None
    extra: Optional[dict] = None


class EngagementSummary(BaseModel):
    engagement_id: str
    counts: CountSummary
    last_activity: Optional[datetime] = None
    recent_activity: List[ActivityItem] = None
    recent_runlog_excerpt: Optional[str] = None

    def __init__(self, **data):
        if data.get('recent_activity') is None:
            data['recent_activity'] = []
        super().__init__(**data)

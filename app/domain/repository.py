from __future__ import annotations
import threading
import logging
from typing import Dict, List, Optional
from .models import Assessment, Question, Response, Finding, Recommendation, RunLog, Engagement, Membership, Document, Workshop, ConsentRecord

logger = logging.getLogger(__name__)

class Repository:
    # Engagements & Memberships
    def create_engagement(self, e: Engagement) -> Engagement: ...
    def list_engagements_for_user(self, user_email: str, admin: bool) -> List[Engagement]: ...
    def add_membership(self, m: Membership) -> Membership: ...
    def get_membership(self, engagement_id: str, user_email: str) -> Optional[Membership]: ...
    
    # Existing domain (must be scoped by engagement_id)
    def create_assessment(self, a: Assessment) -> Assessment: ...
    def get_assessment(self, assessment_id: str) -> Optional[Assessment]: ...
    def list_assessments(self, engagement_id: str) -> List[Assessment]: ...
    def add_question(self, q: Question) -> Question: ...
    def save_response(self, r: Response) -> Response: ...
    def add_findings(self, assessment_id: str, items: List[Finding]) -> List[Finding]: ...
    def add_recommendations(self, assessment_id: str, items: List[Recommendation]) -> List[Recommendation]: ...
    def add_runlog(self, log: RunLog) -> RunLog: ...
    def get_findings(self, engagement_id: str) -> List[Finding]: ...
    def get_recommendations(self, engagement_id: str) -> List[Recommendation]: ...
    def get_runlogs(self, engagement_id: str) -> List[RunLog]: ...
    
    # Documents
    def add_document(self, d: Document) -> Document: ...
    def list_documents(self, engagement_id: str) -> List[Document]: ...
    def get_document(self, engagement_id: str, doc_id: str) -> Optional[Document]: ...
    def delete_document(self, engagement_id: str, doc_id: str) -> bool: ...
    
    # Workshops
    async def create_workshop(self, workshop: Workshop) -> Workshop: ...
    async def get_workshop(self, workshop_id: str, engagement_id: str) -> Optional[Workshop]: ...
    async def list_workshops(self, engagement_id: str, page: int = 1, page_size: int = 50) -> tuple[List[Workshop], int]: ...
    async def update_workshop_consent(self, workshop_id: str, engagement_id: str, attendee_id: str, consent: ConsentRecord) -> Workshop: ...
    async def start_workshop(self, workshop_id: str, engagement_id: str) -> Workshop: ...

class InMemoryRepository(Repository):
    def __init__(self):
        self.assessments: Dict[str, Assessment] = {}
        self.questions: Dict[str, Question] = {}
        self.responses: Dict[str, Response] = {}
        self.findings: Dict[str, Finding] = {}
        self.recommendations: Dict[str, Recommendation] = {}
        self.runlogs: Dict[str, RunLog] = {}
        self.engagements: Dict[str, Engagement] = {}
        self.memberships: Dict[str, Membership] = {}
        self.documents: Dict[str, Document] = {}
        # Thread safety lock
        self._lock = threading.RLock()

    # Engagement & Membership methods
    def create_engagement(self, e: Engagement) -> Engagement:
        with self._lock:
            if e.id in self.engagements:
                raise ValueError(f"Engagement with ID {e.id} already exists")
            self.engagements[e.id] = e
            return e

    def list_engagements_for_user(self, user_email: str, admin: bool) -> List[Engagement]:
        with self._lock:
            if admin:
                return list(self.engagements.values())
            else:
                # Get engagements where user is a member
                user_engagement_ids = {m.engagement_id for m in self.memberships.values() 
                                       if m.user_email.lower() == user_email.lower()}
                return [e for e in self.engagements.values() if e.id in user_engagement_ids]

    def add_membership(self, m: Membership) -> Membership:
        with self._lock:
            # Check if membership already exists
            existing = [mem for mem in self.memberships.values() 
                        if mem.engagement_id == m.engagement_id and mem.user_email.lower() == m.user_email.lower()]
            if existing:
                raise ValueError(f"User {m.user_email} is already a member of engagement {m.engagement_id}")
            self.memberships[m.id] = m
            return m

    def get_membership(self, engagement_id: str, user_email: str) -> Optional[Membership]:
        with self._lock:
            for m in self.memberships.values():
                if m.engagement_id == engagement_id and m.user_email.lower() == user_email.lower():
                    return m
            return None

    def create_assessment(self, a: Assessment) -> Assessment:
        with self._lock:
            # Check if assessment already exists
            if a.id in self.assessments:
                raise ValueError(f"Assessment with ID {a.id} already exists")
            self.assessments[a.id] = a
            return a

    def get_assessment(self, assessment_id: str) -> Optional[Assessment]:
        with self._lock:
            return self.assessments.get(assessment_id)

    def list_assessments(self, engagement_id: str) -> List[Assessment]:
        with self._lock:
            return [a for a in self.assessments.values() if a.engagement_id == engagement_id]

    def add_question(self, q: Question) -> Question:
        with self._lock:
            self.questions[q.id] = q
            return q

    def save_response(self, r: Response) -> Response:
        with self._lock:
            self.responses[r.id] = r
            return r

    def add_findings(self, engagement_id: str, items: List[Finding]) -> List[Finding]:
        with self._lock:
            result = []
            for f in items:
                # Validate engagement_id consistency
                if f.engagement_id and f.engagement_id != engagement_id:
                    raise ValueError(f"Finding {f.id} has mismatched engagement_id: {f.engagement_id} != {engagement_id}")
                # Create a copy to avoid mutating the original
                f_copy = f.model_copy()
                f_copy.engagement_id = engagement_id
                self.findings[f_copy.id] = f_copy
                result.append(f_copy)
            return result

    def add_recommendations(self, assessment_id: str, items: List[Recommendation]) -> List[Recommendation]:
        with self._lock:
            result = []
            for rec in items:
                # Validate required fields
                if not rec.id:
                    raise ValueError("Recommendation must have an ID")
                if not rec.title:
                    raise ValueError(f"Recommendation {rec.id} must have a title")
                # Validate assessment_id consistency
                if rec.assessment_id and rec.assessment_id != assessment_id:
                    raise ValueError(f"Recommendation {rec.id} has mismatched assessment_id: {rec.assessment_id} != {assessment_id}")
                # Create a copy to avoid mutating the original
                rec_copy = rec.model_copy()
                rec_copy.assessment_id = assessment_id
                self.recommendations[rec_copy.id] = rec_copy
                result.append(rec_copy)
            return result

    def add_runlog(self, log: RunLog) -> RunLog:
        with self._lock:
            # Validate required fields
            if not log.assessment_id:
                raise ValueError("RunLog must have an assessment_id")
            self.runlogs[log.id] = log
            return log

    def get_findings(self, engagement_id: str) -> List[Finding]:
        with self._lock:
            # Get all findings for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self.assessments.values() if a.engagement_id == engagement_id}
            return [f for f in self.findings.values() if f.assessment_id in engagement_assessment_ids]

    def get_recommendations(self, engagement_id: str) -> List[Recommendation]:
        with self._lock:
            # Get all recommendations for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self.assessments.values() if a.engagement_id == engagement_id}
            return [r for r in self.recommendations.values() if r.assessment_id in engagement_assessment_ids]

    def get_runlogs(self, engagement_id: str) -> List[RunLog]:
        with self._lock:
            # Get all runlogs for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self.assessments.values() if a.engagement_id == engagement_id}
            return [log for log in self.runlogs.values() if log.assessment_id in engagement_assessment_ids]
    
    # Document methods
    def add_document(self, d: Document) -> Document:
        with self._lock:
            if d.id in self.documents:
                raise ValueError(f"Document with ID {d.id} already exists")
            self.documents[d.id] = d
            return d
    
    def list_documents(self, engagement_id: str) -> List[Document]:
        with self._lock:
            return [d for d in self.documents.values() if d.engagement_id == engagement_id]
    
    def get_document(self, engagement_id: str, doc_id: str) -> Optional[Document]:
        with self._lock:
            doc = self.documents.get(doc_id)
            if not doc or doc.engagement_id != engagement_id:
                return None
            return doc
    
    def delete_document(self, engagement_id: str, doc_id: str) -> bool:
        with self._lock:
            doc = self.documents.get(doc_id)
            if not doc or doc.engagement_id != engagement_id:
                return False
            # Attempt to remove file from disk
            import os
            if os.path.exists(doc.path):
                try:
                    os.remove(doc.path)
                except OSError as e:
                    logger.warning(f"Failed to delete file {doc.path} for document {doc_id} in engagement {engagement_id}: {e}")
            # Always remove document from memory even if file deletion failed
            del self.documents[doc_id]
            return True

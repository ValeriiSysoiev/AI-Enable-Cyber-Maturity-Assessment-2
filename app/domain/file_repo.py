import json
import os
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import threading
from .models import Assessment, Question, Response, Finding, Recommendation, RunLog, Engagement, Membership, Document
from .repository import Repository

logger = logging.getLogger(__name__)


class FileRepository(Repository):
    def __init__(self, base_path: str = "data/engagements"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db_file = self.base_path / "db.json"
        self._load_db()

    def _load_db(self):
        """Load the database from file or create empty structure"""
        if self._db_file.exists():
            try:
                with open(self._db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._db = {
                        "engagements": {k: Engagement(**v) for k, v in data.get("engagements", {}).items()},
                        "memberships": {k: Membership(**v) for k, v in data.get("memberships", {}).items()},
                        "assessments": {k: Assessment(**v) for k, v in data.get("assessments", {}).items()},
                        "questions": {k: Question(**v) for k, v in data.get("questions", {}).items()},
                        "responses": {k: Response(**v) for k, v in data.get("responses", {}).items()},
                        "findings": {k: Finding(**v) for k, v in data.get("findings", {}).items()},
                        "recommendations": {k: Recommendation(**v) for k, v in data.get("recommendations", {}).items()},
                        "runlogs": {k: RunLog(**v) for k, v in data.get("runlogs", {}).items()},
                        "documents": {k: Document(**v) for k, v in data.get("documents", {}).items()}
                    }
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load database from {self._db_file}: {e}")
                # Create a backup of the corrupted file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self._db_file.with_suffix(f".backup_{timestamp}.json")
                try:
                    if self._db_file.exists():
                        self._db_file.rename(backup_path)
                        logger.info(f"Corrupted database backed up to {backup_path}")
                except Exception as backup_error:
                    logger.error(f"Failed to create backup: {backup_error}")
                
                # Initialize with empty structure
                self._init_empty_db()
            except Exception as e:
                logger.exception(f"Unexpected error loading database: {e}")
                self._init_empty_db()
        else:
            self._init_empty_db()
    
    def _init_empty_db(self):
        """Initialize an empty database structure"""
        self._db = {
            "engagements": {},
            "memberships": {},
            "assessments": {},
            "questions": {},
            "responses": {},
            "findings": {},
            "recommendations": {},
            "runlogs": {},
            "documents": {}
        }
        self._save_db()

    def _save_db(self):
        """Save the database to file atomically"""
        data = {
            collection: {k: v.model_dump(mode='json') for k, v in items.items()}
            for collection, items in self._db.items()
        }
        
        # Use atomic write to prevent corruption
        temp_file = None
        try:
            # Create temporary file in the same directory
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=self._db_file.parent, 
                prefix=f".{self._db_file.name}_tmp_",
                suffix='.json',
                delete=False,
                encoding='utf-8'
            ) as f:
                temp_file = f.name
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomically replace the target file
            os.replace(temp_file, self._db_file)
            temp_file = None  # Successfully moved, don't clean up
            
            # Optionally fsync the directory (for maximum durability)
            try:
                dir_fd = os.open(self._db_file.parent, os.O_RDONLY)
                os.fsync(dir_fd)
                os.close(dir_fd)
            except (OSError, AttributeError):
                # Directory fsync not supported on all platforms
                pass
                
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
            # Clean up temp file on error
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
            raise

    # Engagement & Membership methods
    def create_engagement(self, e: Engagement) -> Engagement:
        with self._lock:
            if e.id in self._db["engagements"]:
                raise ValueError(f"Engagement with ID {e.id} already exists")
            self._db["engagements"][e.id] = e
            self._save_db()
            return e

    def list_engagements_for_user(self, user_email: str, admin: bool) -> List[Engagement]:
        with self._lock:
            if admin:
                return list(self._db["engagements"].values())
            else:
                # Get engagements where user is a member
                user_engagement_ids = {m.engagement_id for m in self._db["memberships"].values() 
                                       if m.user_email.lower() == user_email.lower()}
                return [e for e in self._db["engagements"].values() if e.id in user_engagement_ids]

    def add_membership(self, m: Membership) -> Membership:
        with self._lock:
            # Check if membership already exists
            existing = [mem for mem in self._db["memberships"].values() 
                        if mem.engagement_id == m.engagement_id and mem.user_email.lower() == m.user_email.lower()]
            if existing:
                raise ValueError(f"User {m.user_email} is already a member of engagement {m.engagement_id}")
            self._db["memberships"][m.id] = m
            self._save_db()
            return m

    def get_membership(self, engagement_id: str, user_email: str) -> Optional[Membership]:
        with self._lock:
            for m in self._db["memberships"].values():
                if m.engagement_id == engagement_id and m.user_email.lower() == user_email.lower():
                    return m
            return None

    # Assessment methods
    def create_assessment(self, a: Assessment) -> Assessment:
        with self._lock:
            if a.id in self._db["assessments"]:
                raise ValueError(f"Assessment with ID {a.id} already exists")
            if not hasattr(a, 'engagement_id') or not a.engagement_id:
                raise ValueError("Assessment must have an engagement_id")
            self._db["assessments"][a.id] = a
            self._save_db()
            return a

    def get_assessment(self, assessment_id: str) -> Optional[Assessment]:
        with self._lock:
            return self._db["assessments"].get(assessment_id)

    def list_assessments(self, engagement_id: str) -> List[Assessment]:
        with self._lock:
            return [a for a in self._db["assessments"].values() if a.engagement_id == engagement_id]

    # Question and Response methods
    def add_question(self, q: Question) -> Question:
        with self._lock:
            self._db["questions"][q.id] = q
            self._save_db()
            return q

    def save_response(self, r: Response) -> Response:
        with self._lock:
            self._db["responses"][r.id] = r
            self._save_db()
            return r

    # Finding methods
    def add_findings(self, assessment_id: str, items: List[Finding]) -> List[Finding]:
        with self._lock:
            result = []
            for f in items:
                # Validate assessment_id consistency
                if f.assessment_id and f.assessment_id != assessment_id:
                    raise ValueError(f"Finding {f.id} has mismatched assessment_id: {f.assessment_id} != {assessment_id}")
                # Create a copy to avoid mutating the original
                f_copy = f.model_copy()
                f_copy.assessment_id = assessment_id
                self._db["findings"][f_copy.id] = f_copy
                result.append(f_copy)
            self._save_db()
            return result

    def get_findings(self, engagement_id: str) -> List[Finding]:
        with self._lock:
            # Get all findings for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self._db["assessments"].values() if a.engagement_id == engagement_id}
            return [f for f in self._db["findings"].values() if f.assessment_id in engagement_assessment_ids]

    # Recommendation methods
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
                self._db["recommendations"][rec_copy.id] = rec_copy
                result.append(rec_copy)
            self._save_db()
            return result

    def get_recommendations(self, engagement_id: str) -> List[Recommendation]:
        with self._lock:
            # Get all recommendations for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self._db["assessments"].values() if a.engagement_id == engagement_id}
            return [r for r in self._db["recommendations"].values() if r.assessment_id in engagement_assessment_ids]

    # RunLog methods
    def add_runlog(self, log: RunLog) -> RunLog:
        with self._lock:
            # Validate required fields
            if not log.assessment_id:
                raise ValueError("RunLog must have an assessment_id")
            self._db["runlogs"][log.id] = log
            self._save_db()
            return log

    def get_runlogs(self, engagement_id: str) -> List[RunLog]:
        with self._lock:
            # Get all runlogs for assessments in this engagement
            engagement_assessment_ids = {a.id for a in self._db["assessments"].values() if a.engagement_id == engagement_id}
            return [log for log in self._db["runlogs"].values() if log.assessment_id in engagement_assessment_ids]
    
    # Document methods
    def add_document(self, d: Document) -> Document:
        with self._lock:
            self._db["documents"][d.id] = d
            self._save_db()
            return d
    
    def list_documents(self, engagement_id: str) -> List[Document]:
        with self._lock:
            return [d for d in self._db["documents"].values() if d.engagement_id == engagement_id]
    
    def get_document(self, engagement_id: str, doc_id: str) -> Optional[Document]:
        with self._lock:
            doc = self._db["documents"].get(doc_id)
            if not doc or doc.engagement_id != engagement_id:
                return None
            return doc
    
    def delete_document(self, engagement_id: str, doc_id: str) -> bool:
        with self._lock:
            doc = self._db["documents"].get(doc_id)
            if not doc or doc.engagement_id != engagement_id:
                return False
            # Attempt to remove file from disk
            import os
            if os.path.exists(doc.path):
                try:
                    os.remove(doc.path)
                    logger.info(f"Successfully deleted file: {doc.path}")
                except FileNotFoundError:
                    # File was already deleted, this is not fatal
                    logger.info(f"File already deleted: {doc.path}")
                except OSError as e:
                    # Log the error but continue with DB record deletion
                    logger.warning(f"Failed to delete file {doc.path} for document {doc_id} in engagement {engagement_id}: {e}")
            else:
                logger.info(f"File does not exist, skipping deletion: {doc.path}")
            
            # Always remove from database even if file deletion failed
            self._db["documents"].pop(doc_id, None)
            self._save_db()
            return True

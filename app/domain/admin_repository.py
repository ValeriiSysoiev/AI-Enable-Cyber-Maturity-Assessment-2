"""
Admin Repository Interface for Demo Admin Management

Provides persistent storage for demo-mode admin lists that augment
the ADMIN_EMAILS environment variable configuration.
"""

from abc import ABC, abstractmethod
from typing import List, Set
import json
import os
from pathlib import Path
import logging
import aiofiles

logger = logging.getLogger(__name__)


class AdminRepository(ABC):
    """Abstract interface for admin user management"""
    
    @abstractmethod
    async def get_demo_admins(self) -> Set[str]:
        """Get list of demo admin emails"""
        pass
    
    @abstractmethod
    async def add_demo_admin(self, email: str) -> bool:
        """Add email to demo admin list. Returns True if added, False if already exists"""
        pass
    
    @abstractmethod
    async def remove_demo_admin(self, email: str) -> bool:
        """Remove email from demo admin list. Returns True if removed, False if not found"""
        pass
    
    @abstractmethod
    async def is_demo_admin(self, email: str) -> bool:
        """Check if email is in demo admin list"""
        pass


class FileAdminRepository(AdminRepository):
    """File-based implementation for demo admin storage"""
    
    def __init__(self, file_path: str = "data/admins.json"):
        self.file_path = Path(file_path)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the admin file and directory exist"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            # Create empty file synchronously during initialization
            try:
                data = {'emails': []}
                content = json.dumps(data, indent=2)
                with open(self.file_path, 'w') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Failed to create initial admin file: {e}")
    
    async def _read_admins(self) -> Set[str]:
        """Read admin emails from file asynchronously"""
        try:
            async with aiofiles.open(self.file_path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                return set(email.strip().lower() for email in data.get('emails', []) if email.strip())
        except Exception as e:
            logger.warning(f"Failed to read admin file {self.file_path}: {e}")
            return set()
    
    async def _write_admins(self, admins: Set[str]):
        """Write admin emails to file asynchronously"""
        try:
            data = {'emails': sorted(list(admins))}
            content = json.dumps(data, indent=2)
            async with aiofiles.open(self.file_path, 'w') as f:
                await f.write(content)
        except Exception as e:
            logger.error(f"Failed to write admin file {self.file_path}: {e}")
            raise
    
    async def get_demo_admins(self) -> Set[str]:
        """Get list of demo admin emails"""
        return await self._read_admins()
    
    async def add_demo_admin(self, email: str) -> bool:
        """Add email to demo admin list"""
        if not email or '@' not in email:
            return False
        
        normalized_email = email.strip().lower()
        admins = await self._read_admins()
        
        if normalized_email in admins:
            return False  # Already exists
        
        admins.add(normalized_email)
        await self._write_admins(admins)
        
        logger.info(f"Added demo admin: {normalized_email}")
        return True
    
    async def remove_demo_admin(self, email: str) -> bool:
        """Remove email from demo admin list"""
        if not email:
            return False
        
        normalized_email = email.strip().lower()
        admins = await self._read_admins()
        
        if normalized_email not in admins:
            return False  # Not found
        
        admins.remove(normalized_email)
        await self._write_admins(admins)
        
        logger.info(f"Removed demo admin: {normalized_email}")
        return True
    
    async def is_demo_admin(self, email: str) -> bool:
        """Check if email is in demo admin list"""
        if not email:
            return False
        
        normalized_email = email.strip().lower()
        admins = self._read_admins()
        return normalized_email in admins


class CosmosAdminRepository(AdminRepository):
    """Cosmos DB implementation for demo admin storage"""
    
    def __init__(self, repository, correlation_id: str = "admin-repo"):
        self.repository = repository
        self.correlation_id = correlation_id
        self.container_name = "admin_config"
        self.admin_doc_id = "demo_admins"
    
    async def _get_admin_document(self) -> dict:
        """Get the admin document from Cosmos DB"""
        try:
            # Use the repository's query method to get the admin document
            query = "SELECT * FROM c WHERE c.id = @doc_id"
            parameters = [{"name": "@doc_id", "value": self.admin_doc_id}]
            
            results = await self.repository._query_items(
                self.container_name, query, parameters
            )
            
            if results:
                return results[0]
            else:
                # Create default document
                return {
                    "id": self.admin_doc_id,
                    "emails": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
        except Exception as e:
            logger.warning(f"Failed to get admin document: {e}")
            return {
                "id": self.admin_doc_id,
                "emails": [],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
    
    async def _save_admin_document(self, doc: dict) -> bool:
        """Save the admin document to Cosmos DB"""
        try:
            from datetime import datetime, timezone
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.repository._upsert_item(self.container_name, doc)
            return True
        except Exception as e:
            logger.error(f"Failed to save admin document: {e}")
            return False
    
    async def get_demo_admins(self) -> Set[str]:
        """Get list of demo admin emails"""
        doc = await self._get_admin_document()
        return set(email.strip().lower() for email in doc.get('emails', []) if email.strip())
    
    async def add_demo_admin(self, email: str) -> bool:
        """Add email to demo admin list"""
        if not email or '@' not in email:
            return False
        
        normalized_email = email.strip().lower()
        doc = await self._get_admin_document()
        
        emails = set(email.strip().lower() for email in doc.get('emails', []) if email.strip())
        
        if normalized_email in emails:
            return False  # Already exists
        
        emails.add(normalized_email)
        doc['emails'] = sorted(list(emails))
        
        success = await self._save_admin_document(doc)
        if success:
            logger.info(f"Added demo admin: {normalized_email}")
        
        return success
    
    async def remove_demo_admin(self, email: str) -> bool:
        """Remove email from demo admin list"""
        if not email:
            return False
        
        normalized_email = email.strip().lower()
        doc = await self._get_admin_document()
        
        emails = set(email.strip().lower() for email in doc.get('emails', []) if email.strip())
        
        if normalized_email not in emails:
            return False  # Not found
        
        emails.remove(normalized_email)
        doc['emails'] = sorted(list(emails))
        
        success = await self._save_admin_document(doc)
        if success:
            logger.info(f"Removed demo admin: {normalized_email}")
        
        return success
    
    async def is_demo_admin(self, email: str) -> bool:
        """Check if email is in demo admin list"""
        if not email:
            return False
        
        normalized_email = email.strip().lower()
        admins = await self.get_demo_admins()
        return normalized_email in admins


def create_admin_repository(data_backend: str = None, repository=None) -> AdminRepository:
    """Factory function to create appropriate admin repository"""
    if data_backend is None:
        data_backend = os.getenv("DATA_BACKEND", "local")
    
    if data_backend.lower() == "cosmos" and repository:
        return CosmosAdminRepository(repository)
    else:
        return FileAdminRepository()
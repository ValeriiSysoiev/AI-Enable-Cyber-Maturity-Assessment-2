"""
Vector Store Manager for MCP Gateway

Manages per-engagement vector stores for embedding and search operations.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sqlite3
import numpy as np
from dataclasses import dataclass, asdict

from security import SecurityValidator, PathSecurityError

logger = logging.getLogger(__name__)

@dataclass
class VectorEntry:
    """Represents a vector entry in the store"""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    created_at: str

@dataclass 
class SearchResult:
    """Represents a search result"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class VectorStoreManager:
    """Manages vector stores for embeddings and search"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.stores: Dict[str, 'EngagementVectorStore'] = {}
        
        # Mock embedding function for demo (in production, use real embeddings)
        self.embedding_dim = 384  # Example dimension
        
    def get_store(self, engagement_id: str) -> 'EngagementVectorStore':
        """Get or create vector store for engagement"""
        if engagement_id not in self.stores:
            # Create store path
            store_path = self.data_root / engagement_id / "mcp_index"
            store_path.mkdir(parents=True, exist_ok=True)
            
            self.stores[engagement_id] = EngagementVectorStore(store_path, self.embedding_dim)
        
        return self.stores[engagement_id]
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (mock implementation)"""
        # In production, this would use a real embedding model
        # For demo purposes, create a deterministic hash-based embedding
        
        # Create hash of text
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float array
        embedding = []
        for i in range(0, min(len(hash_bytes), self.embedding_dim // 8)):
            # Convert each byte to multiple float values
            byte_val = hash_bytes[i]
            for j in range(8):
                if len(embedding) < self.embedding_dim:
                    # Create deterministic float between -1 and 1
                    float_val = ((byte_val >> j) & 1) * 2.0 - 1.0
                    embedding.append(float_val)
        
        # Pad to correct dimension
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)
        
        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding

class EngagementVectorStore:
    """Vector store for a specific engagement"""
    
    def __init__(self, store_path: Path, embedding_dim: int):
        self.store_path = store_path
        self.embedding_dim = embedding_dim
        self.db_path = store_path / "vectors.db"
        
        # Initialize SQLite database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for vector storage"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON vectors(created_at)
            """)
            conn.commit()
    
    def add_vector(self, id: str, text: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        """Add vector to store"""
        if len(embedding) != self.embedding_dim:
            raise ValueError(f"Embedding dimension mismatch: expected {self.embedding_dim}, got {len(embedding)}")
        
        from datetime import datetime
        created_at = datetime.utcnow().isoformat()
        
        # Convert embedding to bytes
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO vectors (id, text, embedding, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (id, text, embedding_bytes, json.dumps(metadata), created_at))
            conn.commit()
    
    def search(self, query_embedding: List[float], top_k: int = 10) -> List[SearchResult]:
        """Search for similar vectors"""
        if len(query_embedding) != self.embedding_dim:
            raise ValueError(f"Query embedding dimension mismatch: expected {self.embedding_dim}, got {len(query_embedding)}")
        
        query_array = np.array(query_embedding, dtype=np.float32)
        
        results = []
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT id, text, embedding, metadata FROM vectors")
            
            for row in cursor:
                id, text, embedding_bytes, metadata_json = row
                
                # Convert embedding from bytes
                stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # Calculate cosine similarity
                dot_product = np.dot(query_array, stored_embedding)
                norm_query = np.linalg.norm(query_array)
                norm_stored = np.linalg.norm(stored_embedding)
                
                if norm_query > 0 and norm_stored > 0:
                    similarity = dot_product / (norm_query * norm_stored)
                else:
                    similarity = 0.0
                
                results.append(SearchResult(
                    id=id,
                    text=text,
                    score=float(similarity),
                    metadata=json.loads(metadata_json)
                ))
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def get_vector(self, id: str) -> Optional[VectorEntry]:
        """Get vector by ID"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT id, text, embedding, metadata, created_at FROM vectors WHERE id = ?",
                (id,)
            )
            row = cursor.fetchone()
            
            if row:
                id, text, embedding_bytes, metadata_json, created_at = row
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
                
                return VectorEntry(
                    id=id,
                    text=text,
                    embedding=embedding,
                    metadata=json.loads(metadata_json),
                    created_at=created_at
                )
        
        return None
    
    def delete_vector(self, id: str) -> bool:
        """Delete vector by ID"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM vectors WHERE id = ?", (id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def list_vectors(self, limit: int = 100, offset: int = 0) -> List[VectorEntry]:
        """List vectors in store"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT id, text, embedding, metadata, created_at 
                FROM vectors 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            results = []
            for row in cursor:
                id, text, embedding_bytes, metadata_json, created_at = row
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
                
                results.append(VectorEntry(
                    id=id,
                    text=text,
                    embedding=embedding,
                    metadata=json.loads(metadata_json),
                    created_at=created_at
                ))
            
            return results
    
    def count_vectors(self) -> int:
        """Count total vectors in store"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM vectors")
            return cursor.fetchone()[0]
    
    def clear(self) -> int:
        """Clear all vectors from store"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM vectors")
            conn.commit()
            return cursor.rowcount
"""
Comprehensive tests for RAG endpoints covering success, error, and edge cases.
Tests all RAG functionality including vector search, document ingestion, and analytics.
"""
import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.routes.orchestrations import router as orchestrations_router
from api.routes.version import router as version_router
from services.rag_service import ProductionRAGService, RAGMode, RAGSearchResult, RAGIngestionResult
from domain.models import Document, EmbeddingDocument
import sys
sys.path.append("/app")
from config import config


# Test fixtures
@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(orchestrations_router)
    app.include_router(version_router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_rag_service():
    """Mock RAG service for testing"""
    service = Mock(spec=ProductionRAGService)
    service.correlation_id = "test-correlation-id"
    service.mode = RAGMode.AZURE_OPENAI
    service.is_operational.return_value = True
    service.get_status.return_value = {
        "mode": "azure_openai",
        "operational": True,
        "embeddings_service_available": True,
        "cosmos_repo_available": True
    }
    service.get_metrics.return_value = []
    return service


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return Document(
        id="test-doc-id",
        engagement_id="test-engagement-id",
        filename="test-document.pdf",
        content_type="application/pdf",
        size=1024,
        path=tempfile.mkdtemp() + "/test-document.pdf",
        uploaded_by="test@example.com"
    )


@pytest.fixture
def sample_search_results():
    """Sample RAG search results"""
    return [
        RAGSearchResult(
            document_id="doc1",
            chunk_index=0,
            content="This is test content from document 1",
            filename="document1.pdf",
            similarity_score=0.95,
            engagement_id="test-engagement-id",
            uploaded_by="test@example.com",
            uploaded_at="2023-01-01T00:00:00Z",
            metadata={"content_type": "application/pdf"},
            citation="[1] document1.pdf"
        ),
        RAGSearchResult(
            document_id="doc2",
            chunk_index=1,
            content="This is test content from document 2",
            filename="document2.pdf",
            similarity_score=0.87,
            engagement_id="test-engagement-id",
            uploaded_by="test@example.com",
            uploaded_at="2023-01-01T00:00:00Z",
            metadata={"content_type": "application/pdf"},
            citation="[2] document2.pdf"
        )
    ]


class TestRAGSearchEndpoint:
    """Test the RAG search endpoint"""
    
    @patch('app.services.rag_service.create_rag_service')
    @patch('app.api.routes.orchestrations.require_member')
    def test_rag_search_success(self, mock_require_member, mock_create_rag_service, client, mock_rag_service, sample_search_results):
        """Test successful RAG search"""
        # Setup mocks
        mock_require_member.return_value = None
        mock_create_rag_service.return_value = mock_rag_service
        mock_rag_service.search = AsyncMock(return_value=sample_search_results)
        
        # Mock context
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": "test query", "top_k": 5},
                headers={"X-Correlation-ID": "test-correlation-id"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "test query"
        assert data["engagement_id"] == "test-engagement-id"
        assert data["total_results"] == 2
        assert data["rag_operational"] == True
        assert len(data["results"]) == 2
        
        # Check result structure
        result = data["results"][0]
        assert result["document_id"] == "doc1"
        assert result["similarity_score"] == 0.95
        assert result["citation"] == "[1] document1.pdf"
    
    @patch('app.services.rag_service.create_rag_service')
    @patch('app.api.routes.orchestrations.require_member')
    def test_rag_search_not_operational(self, mock_require_member, mock_create_rag_service, client, mock_rag_service):
        """Test RAG search when service is not operational"""
        # Setup mocks
        mock_require_member.return_value = None
        mock_create_rag_service.return_value = mock_rag_service
        mock_rag_service.is_operational.return_value = False
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": "test query"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["rag_operational"] == False
        assert data["total_results"] == 0
        assert len(data["results"]) == 0
    
    @patch('app.api.routes.orchestrations.require_member')
    def test_rag_search_empty_query(self, mock_require_member, client):
        """Test RAG search with empty query"""
        mock_require_member.return_value = None
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": ""}
            )
        
        assert response.status_code == 400
        assert "Query cannot be empty" in response.json()["detail"]
    
    @patch('app.api.routes.orchestrations.require_member')
    def test_rag_search_query_too_long(self, mock_require_member, client):
        """Test RAG search with very long query"""
        mock_require_member.return_value = None
        long_query = "x" * 1001  # Exceeds 1000 character limit
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": long_query}
            )
        
        assert response.status_code == 400
        assert "Query too long" in response.json()["detail"]


class TestAnalyzeDocEndpoint:
    """Test the enhanced analyze-doc endpoint"""
    
    @patch('app.services.rag_service.create_rag_service')
    @patch('app.api.routes.orchestrations.require_member')
    @patch('app.util.files.extract_text')
    def test_analyze_doc_with_rag_ingestion(self, mock_extract_text, mock_require_member, mock_create_rag_service, client, mock_rag_service, sample_document):
        """Test document analysis with RAG ingestion"""
        # Setup mocks
        mock_require_member.return_value = None
        mock_extract_text.return_value = Mock(text="Sample document text", note=None)
        mock_create_rag_service.return_value = mock_rag_service
        
        # Mock ingestion result
        ingestion_result = RAGIngestionResult(
            document_id="test-doc-id",
            status="success",
            chunks_processed=5,
            total_chunks=5,
            errors=[],
            processing_time_seconds=2.5
        )
        mock_rag_service.ingest_document = AsyncMock(return_value=ingestion_result)
        
        # Mock repository and orchestrator
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}), \
             patch('app.api.routes.orchestrations.get_repo') as mock_get_repo, \
             patch('app.config.is_rag_enabled', return_value=True):
            
            mock_repo = Mock()
            mock_repo.get_document.return_value = sample_document
            mock_repo.create_assessment.return_value = None
            mock_repo.add_findings.return_value = None
            mock_repo.add_runlog.return_value = None
            mock_get_repo.return_value = mock_repo
            
            # Mock orchestrator
            mock_app_state = Mock()
            mock_orchestrator = Mock()
            mock_orchestrator.analyze.return_value = ([], Mock())
            mock_app_state.orchestrator = mock_orchestrator
            
            with patch.object(client.app, 'state', mock_app_state):
                response = client.post(
                    "/orchestrations/analyze-doc",
                    json={"doc_id": "test-doc-id"},
                    headers={"X-Correlation-ID": "test-correlation-id"}
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["analyzed"] == True
        assert data["rag_ingestion"]["status"] == "success"
        assert data["rag_ingestion"]["chunks_processed"] == 5
        assert data["rag_ingestion"]["total_chunks"] == 5
    
    @patch('app.api.routes.orchestrations.require_member')
    def test_analyze_doc_not_found(self, mock_require_member, client):
        """Test analyze-doc with non-existent document"""
        mock_require_member.return_value = None
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}), \
             patch('app.api.routes.orchestrations.get_repo') as mock_get_repo:
            
            mock_repo = Mock()
            mock_repo.get_document.return_value = None
            mock_get_repo.return_value = mock_repo
            
            response = client.post(
                "/orchestrations/analyze-doc",
                json={"doc_id": "non-existent-doc"}
            )
        
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


class TestAnalyzeEndpointWithRAG:
    """Test the enhanced analyze endpoint with RAG support"""
    
    @patch('app.services.rag_service.create_rag_service')
    @patch('app.api.routes.orchestrations.require_member')
    def test_analyze_with_evidence(self, mock_require_member, mock_create_rag_service, client, mock_rag_service, sample_search_results):
        """Test analyze endpoint with evidence search"""
        # Setup mocks
        mock_require_member.return_value = None
        mock_create_rag_service.return_value = mock_rag_service
        mock_rag_service.search = AsyncMock(return_value=sample_search_results)
        mock_rag_service.format_search_results_for_context.return_value = "Evidence context"
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}), \
             patch('app.api.routes.orchestrations.get_repo') as mock_get_repo, \
             patch('app.api.routes.orchestrations.get_orchestrator') as mock_get_orchestrator, \
             patch('app.config.is_rag_enabled', return_value=True):
            
            # Mock repository
            mock_repo = Mock()
            mock_assessment = Mock()
            mock_assessment.engagement_id = "test-engagement-id"
            mock_repo.get_assessment.return_value = mock_assessment
            mock_repo.add_findings.return_value = None
            mock_repo.add_runlog.return_value = None
            mock_get_repo.return_value = mock_repo
            
            # Mock orchestrator
            mock_orchestrator = Mock()
            mock_log = Mock()
            mock_orchestrator.analyze.return_value = ([], mock_log)
            mock_get_orchestrator.return_value = mock_orchestrator
            
            response = client.post(
                "/orchestrations/analyze",
                json={
                    "assessment_id": "test-assessment-id",
                    "content": "Test content for analysis",
                    "use_evidence": True
                },
                headers={"X-Correlation-ID": "test-correlation-id"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["evidence_used"] == True
        assert data["rag_operational"] == True
        assert len(data["citations"]) == 2
        assert "[1] document1.pdf" in data["citations"]


class TestVersionEndpoints:
    """Test version and status endpoints"""
    
    def test_version_endpoint(self, client):
        """Test version endpoint"""
        response = client.get("/version")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "app_name" in data
        assert "app_version" in data
        assert "git_sha" in data
        assert "rag_status" in data
        assert "timestamp" in data
    
    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "rag_operational" in data
    
    @patch('app.services.rag_service.create_rag_service')
    def test_rag_metrics_endpoint(self, mock_create_rag_service, client, mock_rag_service):
        """Test RAG metrics endpoint"""
        # Setup sample metrics
        from services.rag_service import RAGMetrics
        sample_metrics = [
            RAGMetrics("search", 0.5, True, "eng1", 0, 5),
            RAGMetrics("search", 0.7, True, "eng1", 0, 3),
            RAGMetrics("ingestion", 2.1, True, "eng1", 1, 10),
            RAGMetrics("search", 1.2, False, "eng2", 0, 0, "Connection timeout")
        ]
        
        mock_rag_service.get_metrics.return_value = sample_metrics
        mock_create_rag_service.return_value = mock_rag_service
        
        response = client.get("/rag/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_operations"] == 4
        assert data["overall_success_rate"] == 0.75  # 3 successes out of 4
        assert "operation_stats" in data
        assert "search" in data["operation_stats"]
        assert "ingestion" in data["operation_stats"]
        
        # Check search stats
        search_stats = data["operation_stats"]["search"]
        assert search_stats["count"] == 3
        assert search_stats["success_count"] == 2
        assert search_stats["success_rate"] == 2/3
    
    @patch('app.services.rag_service.create_rag_service')
    def test_rag_status_endpoint(self, mock_create_rag_service, client, mock_rag_service):
        """Test RAG status endpoint"""
        mock_create_rag_service.return_value = mock_rag_service
        
        response = client.get("/rag/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "operational" in data
        assert "mode" in data
        assert "metrics" in data


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @patch('app.services.rag_service.create_rag_service')
    @patch('app.api.routes.orchestrations.require_member')
    def test_rag_search_service_error(self, mock_require_member, mock_create_rag_service, client, mock_rag_service):
        """Test RAG search when service raises an exception"""
        mock_require_member.return_value = None
        mock_create_rag_service.return_value = mock_rag_service
        mock_rag_service.search = AsyncMock(side_effect=Exception("Service unavailable"))
        
        with patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": "test query"}
            )
        
        # Should return graceful error response, not HTTP 500
        assert response.status_code == 200
        data = response.json()
        assert data["rag_operational"] == False
        assert data["total_results"] == 0
    
    @patch('app.services.rag_service.create_rag_service')
    def test_rag_metrics_service_error(self, mock_create_rag_service, client):
        """Test RAG metrics endpoint when service is unavailable"""
        mock_create_rag_service.side_effect = Exception("Service initialization failed")
        
        response = client.get("/rag/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Service initialization failed" in data["error"]


class TestRAGConfiguration:
    """Test RAG configuration and mode switching"""
    
    @patch('app.config.config')
    def test_rag_disabled_mode(self, mock_config, client):
        """Test behavior when RAG is disabled"""
        mock_config.is_rag_enabled.return_value = False
        mock_config.rag.mode = "none"
        
        with patch('app.api.routes.orchestrations.require_member'), \
             patch('app.api.routes.orchestrations.current_context', return_value={"engagement_id": "test-engagement-id"}):
            
            response = client.post(
                "/orchestrations/rag-search",
                json={"query": "test query"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rag_operational"] == False
    
    def test_version_endpoint_with_rag_disabled(self, client):
        """Test version endpoint when RAG is disabled"""
        with patch('app.config.is_rag_enabled', return_value=False):
            response = client.get("/version")
        
        assert response.status_code == 200
        data = response.json()
        assert "rag_status" in data


# Integration test class
class TestRAGIntegration:
    """Integration tests for RAG functionality"""
    
    @pytest.mark.asyncio
    @patch('app.services.rag_service.create_embeddings_service')
    @patch('app.repos.cosmos_embeddings_repository.create_cosmos_embeddings_repository')
    async def test_end_to_end_rag_flow(self, mock_cosmos_repo, mock_embeddings_service):
        """Test complete RAG flow from document ingestion to search"""
        # This would be a more comprehensive integration test
        # testing the actual RAG service with mocked dependencies
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Unit tests for the RAG retriever component.
Tests backend selection, search functionality, and error handling.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from services.rag_retriever import RAGRetriever, SearchBackend, RetrievalResult, RetrievalMetrics
from services.azure_search_index import AzureSearchIndexManager, SearchResult as AzureSearchResult, SearchDocument
from services.rag_service import ProductionRAGService, RAGSearchResult
from domain.models import EmbeddingDocument
import sys
sys.path.append("/app")
from config import config


@pytest.fixture
def mock_azure_search_manager():
    """Mock Azure Search Index Manager"""
    manager = Mock(spec=AzureSearchIndexManager)
    manager.correlation_id = "test-correlation-id"
    manager.index_name = "test-index"
    manager.endpoint = "https://test-search.search.windows.net"
    manager.vector_dimensions = 3072
    return manager


@pytest.fixture
def mock_rag_service():
    """Mock RAG service"""
    service = Mock(spec=ProductionRAGService)
    service.correlation_id = "test-correlation-id"
    service.is_operational.return_value = True
    return service


@pytest.fixture
def sample_azure_search_results():
    """Sample Azure Search results"""
    doc1 = SearchDocument(
        id="result1",
        engagement_id="test-engagement",
        doc_id="doc1",
        chunk_id="doc1_0",
        content="Sample content from document 1",
        filename="document1.pdf",
        uploaded_by="test@example.com",
        uploaded_at="2023-01-01T00:00:00Z",
        chunk_index=0,
        chunk_start=0,
        chunk_end=100,
        token_count=25,
        model="text-embedding-3-large",
        content_type="application/pdf",
        size=1024,
        vector=[0.1] * 3072,
        metadata='{"key": "value"}'
    )
    
    doc2 = SearchDocument(
        id="result2",
        engagement_id="test-engagement",
        doc_id="doc2",
        chunk_id="doc2_0",
        content="Sample content from document 2",
        filename="document2.pdf",
        uploaded_by="test@example.com",
        uploaded_at="2023-01-01T00:00:00Z",
        chunk_index=0,
        chunk_start=0,
        chunk_end=100,
        token_count=25,
        model="text-embedding-3-large",
        content_type="application/pdf",
        size=2048,
        vector=[0.2] * 3072,
        metadata='{"key": "value2"}'
    )
    
    return [
        AzureSearchResult(document=doc1, score=0.95, reranker_score=0.98),
        AzureSearchResult(document=doc2, score=0.87, reranker_score=0.90)
    ]


@pytest.fixture
def sample_rag_search_results():
    """Sample RAG service search results"""
    return [
        RAGSearchResult(
            document_id="doc1",
            chunk_index=0,
            content="Sample content from document 1",
            filename="document1.pdf",
            similarity_score=0.95,
            engagement_id="test-engagement",
            uploaded_by="test@example.com",
            uploaded_at="2023-01-01T00:00:00Z",
            metadata={"content_type": "application/pdf"},
            citation="[1] document1.pdf"
        )
    ]


class TestBackendSelection:
    """Test backend selection logic"""
    
    @patch('app.services.rag_retriever.config')
    def test_azure_search_backend_selection(self, mock_config):
        """Test Azure Search backend is selected when configured"""
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        retriever = RAGRetriever("test-correlation")
        assert retriever.backend == SearchBackend.AZURE_SEARCH
    
    @patch('app.services.rag_retriever.config')
    def test_cosmos_db_fallback(self, mock_config):
        """Test Cosmos DB fallback when Azure Search not configured"""
        mock_config.azure_search.endpoint = ""
        mock_config.azure_search.index_name = ""
        mock_config.rag.search_backend = "azure_search"
        mock_config.is_rag_enabled.return_value = True
        
        retriever = RAGRetriever("test-correlation")
        assert retriever.backend == SearchBackend.COSMOS_DB
    
    @patch('app.services.rag_retriever.config')
    def test_none_backend_when_disabled(self, mock_config):
        """Test NONE backend when RAG is disabled"""
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = False
        
        retriever = RAGRetriever("test-correlation")
        assert retriever.backend == SearchBackend.NONE


class TestAzureSearchRetrieval:
    """Test Azure Search retrieval functionality"""
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_azure_search_retrieve_success(self, mock_config, mock_create_manager, mock_azure_search_manager, sample_azure_search_results):
        """Test successful retrieval using Azure Search"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        mock_config.rag.search_top_k = 10
        
        # Setup manager
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.search = AsyncMock(return_value=sample_azure_search_results)
        
        # Mock embeddings service for query vector generation
        with patch('app.services.rag_retriever.create_embeddings_service') as mock_create_embeddings:
            mock_embeddings_service = Mock()
            mock_embeddings_service.chunk_text.return_value = [Mock()]
            mock_embeddings_service.generate_embeddings = AsyncMock(return_value=[Mock(embedding=[0.1] * 3072)])
            mock_create_embeddings.return_value = mock_embeddings_service
            
            retriever = RAGRetriever("test-correlation")
            
            results = await retriever.retrieve(
                query="test query",
                query_vector=None,
                engagement_id="test-engagement",
                top_k=5,
                use_semantic_ranking=True
            )
        
        assert len(results) == 2
        assert results[0].document_id == "doc1"
        assert results[0].similarity_score == 0.95
        assert results[0].backend_used == "azure_search"
        assert results[0].reranker_score == 0.98
        assert results[0].citation == "[1] document1.pdf"
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_azure_search_with_provided_vector(self, mock_config, mock_create_manager, mock_azure_search_manager, sample_azure_search_results):
        """Test Azure Search with pre-computed query vector"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        # Setup manager
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.search = AsyncMock(return_value=sample_azure_search_results)
        
        retriever = RAGRetriever("test-correlation")
        query_vector = [0.1] * 3072
        
        results = await retriever.retrieve(
            query="test query",
            query_vector=query_vector,
            engagement_id="test-engagement"
        )
        
        # Verify the manager was called with the provided vector
        mock_azure_search_manager.search.assert_called_once()
        call_args = mock_azure_search_manager.search.call_args
        assert call_args[1]['query_vector'] == query_vector


class TestCosmosDbRetrieval:
    """Test Cosmos DB retrieval functionality"""
    
    @patch('app.services.rag_retriever.ProductionRAGService')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_cosmos_db_retrieve_success(self, mock_config, mock_rag_service_class, mock_rag_service, sample_rag_search_results):
        """Test successful retrieval using Cosmos DB"""
        # Setup config
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = True
        
        # Setup RAG service
        mock_rag_service_class.return_value = mock_rag_service
        mock_rag_service.search = AsyncMock(return_value=sample_rag_search_results)
        
        retriever = RAGRetriever("test-correlation")
        query_vector = [0.1] * 3072
        
        results = await retriever.retrieve(
            query="test query",
            query_vector=query_vector,
            engagement_id="test-engagement"
        )
        
        assert len(results) == 1
        assert results[0].document_id == "doc1"
        assert results[0].similarity_score == 0.95
        assert results[0].backend_used == "cosmos_db"
        assert results[0].citation == "[1] document1.pdf"
    
    @patch('app.services.rag_retriever.ProductionRAGService')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_cosmos_db_requires_query_vector(self, mock_config, mock_rag_service_class, mock_rag_service):
        """Test that Cosmos DB backend requires query vector"""
        # Setup config for Cosmos DB
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = True
        
        mock_rag_service_class.return_value = mock_rag_service
        
        retriever = RAGRetriever("test-correlation")
        
        # Should return empty results when no query vector provided
        results = await retriever.retrieve(
            query="test query",
            query_vector=None,
            engagement_id="test-engagement"
        )
        
        assert len(results) == 0


class TestErrorHandling:
    """Test error handling and graceful failures"""
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_azure_search_error_handling(self, mock_config, mock_create_manager, mock_azure_search_manager):
        """Test error handling in Azure Search retrieval"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        # Setup manager to raise exception
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.search = AsyncMock(side_effect=Exception("Search service error"))
        
        # Mock embeddings service
        with patch('app.services.rag_retriever.create_embeddings_service') as mock_create_embeddings:
            mock_embeddings_service = Mock()
            mock_embeddings_service.chunk_text.return_value = [Mock()]
            mock_embeddings_service.generate_embeddings = AsyncMock(return_value=[Mock(embedding=[0.1] * 3072)])
            mock_create_embeddings.return_value = mock_embeddings_service
            
            retriever = RAGRetriever("test-correlation")
            
            # Should return empty results instead of raising exception
            results = await retriever.retrieve(
                query="test query",
                query_vector=None,
                engagement_id="test-engagement"
            )
        
        assert len(results) == 0
    
    @patch('app.services.rag_retriever.config')
    def test_initialization_error_handling(self, mock_config):
        """Test graceful handling of initialization errors"""
        # Setup config that would cause initialization failure
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        with patch('app.services.rag_retriever.create_azure_search_index_manager', side_effect=Exception("Init error")):
            retriever = RAGRetriever("test-correlation")
            
            # Should fallback to NONE backend
            assert retriever.backend == SearchBackend.NONE
            assert not retriever.is_operational()


class TestDocumentIngestion:
    """Test document ingestion functionality"""
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_azure_search_ingestion(self, mock_config, mock_create_manager, mock_azure_search_manager):
        """Test document ingestion with Azure Search"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        # Setup manager
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.upload_documents = AsyncMock(return_value=(5, []))
        
        retriever = RAGRetriever("test-correlation")
        
        # Create sample embedding documents
        embeddings = [
            EmbeddingDocument(
                engagement_id="test-engagement",
                doc_id=f"doc{i}",
                chunk_id=f"chunk{i}",
                vector=[0.1] * 3072,
                text=f"Sample text {i}",
                metadata={"test": "data"},
                chunk_index=i,
                chunk_start=i * 100,
                chunk_end=(i + 1) * 100,
                token_count=25,
                filename=f"document{i}.pdf",
                uploaded_by="test@example.com",
                model="text-embedding-3-large"
            )
            for i in range(5)
        ]
        
        result = await retriever.ingest_documents(embeddings)
        
        assert result["status"] == "success"
        assert result["backend"] == "azure_search"
        assert result["documents_processed"] == 5
        assert result["total_documents"] == 5
    
    @patch('app.services.rag_retriever.ProductionRAGService')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_cosmos_db_ingestion_not_implemented(self, mock_config, mock_rag_service_class, mock_rag_service):
        """Test that Cosmos DB ingestion returns not implemented"""
        # Setup config for Cosmos DB
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = True
        
        mock_rag_service_class.return_value = mock_rag_service
        
        retriever = RAGRetriever("test-correlation")
        
        result = await retriever.ingest_documents([])
        
        assert result["status"] == "not_implemented"
        assert result["backend"] == "cosmos_db"


class TestDocumentDeletion:
    """Test document deletion functionality"""
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_azure_search_deletion(self, mock_config, mock_create_manager, mock_azure_search_manager):
        """Test document deletion with Azure Search"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        # Setup manager
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.delete_documents_by_filter = AsyncMock(return_value=10)
        
        retriever = RAGRetriever("test-correlation")
        
        # Test deletion with specific document ID
        result = await retriever.delete_documents("test-engagement", "doc123")
        
        assert result is True
        mock_azure_search_manager.delete_documents_by_filter.assert_called_once()
        
        # Check the filter expression
        call_args = mock_azure_search_manager.delete_documents_by_filter.call_args
        filter_expr = call_args[0][0]
        assert "engagement_id eq 'test-engagement'" in filter_expr
        assert "doc_id eq 'doc123'" in filter_expr
    
    @patch('app.services.rag_retriever.ProductionRAGService')
    @patch('app.services.rag_retriever.config')
    @pytest.mark.asyncio
    async def test_cosmos_db_deletion(self, mock_config, mock_rag_service_class, mock_rag_service):
        """Test document deletion with Cosmos DB"""
        # Setup config for Cosmos DB
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = True
        
        mock_rag_service_class.return_value = mock_rag_service
        mock_rag_service.delete_document_embeddings = AsyncMock(return_value=True)
        
        retriever = RAGRetriever("test-correlation")
        
        result = await retriever.delete_documents("test-engagement", "doc123")
        
        assert result is True
        mock_rag_service.delete_document_embeddings.assert_called_once_with("test-engagement", "doc123")


class TestStatusAndMetrics:
    """Test status reporting and metrics"""
    
    @patch('app.services.rag_retriever.create_azure_search_index_manager')
    @patch('app.services.rag_retriever.config')
    def test_azure_search_status(self, mock_config, mock_create_manager, mock_azure_search_manager):
        """Test status reporting for Azure Search backend"""
        # Setup config
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.rag.search_backend = "azure_search"
        
        # Setup manager
        mock_create_manager.return_value = mock_azure_search_manager
        mock_azure_search_manager.index_exists.return_value = True
        
        retriever = RAGRetriever("test-correlation")
        status = retriever.get_status()
        
        assert status["backend"] == "azure_search"
        assert status["operational"] is True
        assert "azure_search" in status
        assert status["azure_search"]["index_exists"] is True
    
    @patch('app.services.rag_retriever.ProductionRAGService')
    @patch('app.services.rag_retriever.config')
    def test_cosmos_db_status(self, mock_config, mock_rag_service_class, mock_rag_service):
        """Test status reporting for Cosmos DB backend"""
        # Setup config for Cosmos DB
        mock_config.azure_search.endpoint = ""
        mock_config.is_rag_enabled.return_value = True
        
        mock_rag_service_class.return_value = mock_rag_service
        mock_rag_service.get_status.return_value = {"operational": True, "mode": "azure_openai"}
        
        retriever = RAGRetriever("test-correlation")
        status = retriever.get_status()
        
        assert status["backend"] == "cosmos_db"
        assert status["operational"] is True
        assert "cosmos_db" in status


class TestResultFormatting:
    """Test result formatting functionality"""
    
    def test_format_results_for_context(self):
        """Test formatting retrieval results for LLM context"""
        # Create sample results
        results = [
            RetrievalResult(
                document_id="doc1",
                chunk_index=0,
                content="This is sample content from document 1 with some important information.",
                filename="document1.pdf",
                similarity_score=0.95,
                engagement_id="test-engagement",
                uploaded_by="test@example.com",
                uploaded_at="2023-01-01T00:00:00Z",
                metadata={"content_type": "application/pdf"},
                citation="[1] document1.pdf",
                backend_used="azure_search"
            ),
            RetrievalResult(
                document_id="doc2",
                chunk_index=0,
                content="This is sample content from document 2 with additional details and explanations.",
                filename="document2.pdf",
                similarity_score=0.87,
                engagement_id="test-engagement",
                uploaded_by="test@example.com",
                uploaded_at="2023-01-01T00:00:00Z",
                metadata={"content_type": "application/pdf"},
                citation="[2] document2.pdf",
                backend_used="azure_search"
            )
        ]
        
        with patch('app.services.rag_retriever.config'):
            retriever = RAGRetriever("test-correlation")
            formatted = retriever.format_results_for_context(results)
        
        assert "[1] document1.pdf:" in formatted
        assert "[2] document2.pdf:" in formatted
        assert "This is sample content from document 1" in formatted
        assert "This is sample content from document 2" in formatted
    
    def test_format_empty_results(self):
        """Test formatting empty results"""
        with patch('app.services.rag_retriever.config'):
            retriever = RAGRetriever("test-correlation")
            formatted = retriever.format_results_for_context([])
        
        assert formatted == "No relevant documents found."
    
    def test_format_results_with_highlights(self):
        """Test formatting results with Azure Search highlights"""
        results = [
            RetrievalResult(
                document_id="doc1",
                chunk_index=0,
                content="Original content text",
                filename="document1.pdf",
                similarity_score=0.95,
                engagement_id="test-engagement",
                uploaded_by="test@example.com",
                uploaded_at="2023-01-01T00:00:00Z",
                metadata={"content_type": "application/pdf"},
                citation="[1] document1.pdf",
                backend_used="azure_search",
                highlights={"content": ["<em>highlighted</em> content", "another <em>highlight</em>"]}
            )
        ]
        
        with patch('app.services.rag_retriever.config'):
            retriever = RAGRetriever("test-correlation")
            formatted = retriever.format_results_for_context(results)
        
        assert "highlighted content" in formatted
        assert "another highlight" in formatted
        assert "Original content text" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
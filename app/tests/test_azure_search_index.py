"""
Unit tests for the Azure Search Index Manager.
Tests index creation, document operations, and search functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from ..services.azure_search_index import (
    AzureSearchIndexManager, 
    SearchDocument, 
    SearchResult,
    create_azure_search_index_manager
)
from ..domain.models import EmbeddingDocument
from ..config import config


@pytest.fixture
def mock_azure_search_config():
    """Mock Azure Search configuration"""
    with patch('app.services.azure_search_index.config') as mock_config:
        mock_config.azure_search.endpoint = "https://test-search.search.windows.net"
        mock_config.azure_search.index_name = "test-index"
        mock_config.azure_search.api_key = "test-api-key"
        mock_config.azure_openai.endpoint = "https://test-openai.openai.azure.com"
        mock_config.azure_openai.embedding_model = "text-embedding-3-large"
        mock_config.azure_openai.api_key = "test-openai-key"
        mock_config.azure_openai.embedding_dimensions = 3072
        yield mock_config


@pytest.fixture
def mock_index_client():
    """Mock Azure Search Index Client"""
    client = Mock()
    client.create_or_update_index.return_value = Mock(name="test-index")
    client.delete_index.return_value = None
    client.get_index.return_value = Mock(name="test-index")
    return client


@pytest.fixture
def mock_search_client():
    """Mock Azure Search Client"""
    client = Mock()
    return client


@pytest.fixture
def sample_embedding_documents():
    """Sample embedding documents for testing"""
    return [
        EmbeddingDocument(
            engagement_id="test-engagement",
            doc_id="doc1",
            chunk_id="doc1_0",
            vector=[0.1] * 3072,
            text="Sample text content from document 1",
            metadata={"content_type": "application/pdf", "size": 1024},
            chunk_index=0,
            chunk_start=0,
            chunk_end=100,
            token_count=25,
            filename="document1.pdf",
            uploaded_by="test@example.com",
            model="text-embedding-3-large"
        ),
        EmbeddingDocument(
            engagement_id="test-engagement",
            doc_id="doc2",
            chunk_id="doc2_0",
            vector=[0.2] * 3072,
            text="Sample text content from document 2",
            metadata={"content_type": "application/pdf", "size": 2048},
            chunk_index=0,
            chunk_start=0,
            chunk_end=100,
            token_count=30,
            filename="document2.pdf",
            uploaded_by="test@example.com",
            model="text-embedding-3-large"
        )
    ]


class TestSearchDocumentConversion:
    """Test SearchDocument creation and conversion"""
    
    def test_from_embedding_document(self, sample_embedding_documents):
        """Test converting EmbeddingDocument to SearchDocument"""
        embed_doc = sample_embedding_documents[0]
        search_doc = SearchDocument.from_embedding_document(embed_doc)
        
        assert search_doc.id == embed_doc.id
        assert search_doc.engagement_id == embed_doc.engagement_id
        assert search_doc.doc_id == embed_doc.doc_id
        assert search_doc.chunk_id == embed_doc.chunk_id
        assert search_doc.content == embed_doc.text
        assert search_doc.filename == embed_doc.filename
        assert search_doc.uploaded_by == embed_doc.uploaded_by
        assert search_doc.chunk_index == embed_doc.chunk_index
        assert search_doc.vector == embed_doc.vector
        assert search_doc.token_count == embed_doc.token_count
        assert search_doc.model == embed_doc.model
        
        # Test metadata conversion
        assert search_doc.content_type == "application/pdf"
        assert search_doc.size == 1024
        assert '"content_type": "application/pdf"' in search_doc.metadata


class TestIndexManagerInitialization:
    """Test Azure Search Index Manager initialization"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.AzureKeyCredential')
    def test_initialization_with_api_key(self, mock_credential, mock_search_client, mock_index_client, mock_azure_search_config):
        """Test initialization with API key authentication"""
        mock_azure_search_config.azure_search.api_key = "test-api-key"
        
        manager = AzureSearchIndexManager("test-correlation")
        
        assert manager.correlation_id == "test-correlation"
        assert manager.index_name == "test-index"
        assert manager.endpoint == "https://test-search.search.windows.net"
        assert manager.vector_dimensions == 3072
        
        # Verify clients were created with API key
        mock_credential.assert_called_with("test-api-key")
        mock_index_client.assert_called_once()
        mock_search_client.assert_called_once()
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.DefaultAzureCredential')
    def test_initialization_with_managed_identity(self, mock_credential, mock_search_client, mock_index_client, mock_azure_search_config):
        """Test initialization with managed identity authentication"""
        mock_azure_search_config.azure_search.api_key = None
        
        manager = AzureSearchIndexManager("test-correlation")
        
        # Verify clients were created with managed identity
        mock_credential.assert_called_once()
        mock_index_client.assert_called_once()
        mock_search_client.assert_called_once()


class TestIndexOperations:
    """Test index creation and management operations"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    def test_create_index_success(self, mock_search_client, mock_index_client_class, mock_azure_search_config, mock_index_client):
        """Test successful index creation"""
        mock_index_client_class.return_value = mock_index_client
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.index_client = mock_index_client
        
        result = manager.create_index()
        
        assert result is True
        mock_index_client.create_or_update_index.assert_called_once()
        
        # Verify index configuration
        call_args = mock_index_client.create_or_update_index.call_args
        index = call_args[0][0]
        assert index.name == "test-index"
        assert index.vector_search is not None
        assert index.semantic_search is not None
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    def test_create_index_failure(self, mock_search_client, mock_index_client_class, mock_azure_search_config, mock_index_client):
        """Test index creation failure"""
        mock_index_client_class.return_value = mock_index_client
        mock_index_client.create_or_update_index.side_effect = Exception("Index creation failed")
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.index_client = mock_index_client
        
        result = manager.create_index()
        
        assert result is False
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    def test_delete_index(self, mock_search_client, mock_index_client_class, mock_azure_search_config, mock_index_client):
        """Test index deletion"""
        mock_index_client_class.return_value = mock_index_client
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.index_client = mock_index_client
        
        result = manager.delete_index()
        
        assert result is True
        mock_index_client.delete_index.assert_called_once_with("test-index")
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    def test_index_exists(self, mock_search_client, mock_index_client_class, mock_azure_search_config, mock_index_client):
        """Test checking if index exists"""
        mock_index_client_class.return_value = mock_index_client
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.index_client = mock_index_client
        
        # Test when index exists
        result = manager.index_exists()
        assert result is True
        mock_index_client.get_index.assert_called_once_with("test-index")
        
        # Test when index doesn't exist
        mock_index_client.get_index.side_effect = Exception("Index not found")
        result = manager.index_exists()
        assert result is False


class TestDocumentOperations:
    """Test document upload and management operations"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_upload_documents_success(self, mock_to_thread, mock_search_client_class, mock_index_client, 
                                          mock_azure_search_config, sample_embedding_documents):
        """Test successful document upload"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        
        # Mock upload results
        mock_upload_results = [
            Mock(succeeded=True, key="doc1_0"),
            Mock(succeeded=True, key="doc2_0")
        ]
        mock_to_thread.return_value = mock_upload_results
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        successful, errors = await manager.upload_documents(sample_embedding_documents)
        
        assert successful == 2
        assert len(errors) == 0
        
        # Verify upload was called
        mock_to_thread.assert_called()
        assert mock_search_client.upload_documents in [call[0][0] for call in mock_to_thread.call_args_list]
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_upload_documents_partial_failure(self, mock_to_thread, mock_search_client_class, mock_index_client,
                                                   mock_azure_search_config, sample_embedding_documents):
        """Test document upload with partial failures"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        
        # Mock upload results with one failure
        mock_upload_results = [
            Mock(succeeded=True, key="doc1_0"),
            Mock(succeeded=False, key="doc2_0", error_message="Upload failed")
        ]
        mock_to_thread.return_value = mock_upload_results
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        successful, errors = await manager.upload_documents(sample_embedding_documents)
        
        assert successful == 1
        assert len(errors) == 1
        assert "Upload failed" in errors[0]
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @pytest.mark.asyncio
    async def test_upload_empty_documents(self, mock_search_client_class, mock_index_client, mock_azure_search_config):
        """Test uploading empty document list"""
        manager = AzureSearchIndexManager("test-correlation")
        
        successful, errors = await manager.upload_documents([])
        
        assert successful == 0
        assert len(errors) == 0


class TestSearchOperations:
    """Test search functionality"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_search_success(self, mock_to_thread, mock_search_client_class, mock_index_client, mock_azure_search_config):
        """Test successful search operation"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        
        # Mock search results
        mock_search_results = [
            {
                "id": "result1",
                "engagement_id": "test-engagement",
                "doc_id": "doc1",
                "chunk_id": "doc1_0",
                "content": "Sample content 1",
                "filename": "document1.pdf",
                "uploaded_by": "test@example.com",
                "uploaded_at": "2023-01-01T00:00:00Z",
                "chunk_index": 0,
                "chunk_start": 0,
                "chunk_end": 100,
                "token_count": 25,
                "model": "text-embedding-3-large",
                "content_type": "application/pdf",
                "size": 1024,
                "vector": [0.1] * 3072,
                "metadata": '{"key": "value"}',
                "@search.score": 0.95,
                "@search.reranker_score": 0.98
            }
        ]
        mock_to_thread.return_value = mock_search_results
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        query_vector = [0.1] * 3072
        results = await manager.search(
            query_vector=query_vector,
            engagement_id="test-engagement",
            top_k=10,
            use_semantic_ranking=True
        )
        
        assert len(results) == 1
        result = results[0]
        assert result.document.id == "result1"
        assert result.document.content == "Sample content 1"
        assert result.score == 0.95
        assert result.reranker_score == 0.98
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_search_with_similarity_threshold(self, mock_to_thread, mock_search_client_class, mock_index_client, mock_azure_search_config):
        """Test search with similarity threshold filtering"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        
        # Mock search results with varying scores
        mock_search_results = [
            {
                "id": "result1",
                "engagement_id": "test-engagement",
                "doc_id": "doc1",
                "chunk_id": "doc1_0",
                "content": "High relevance content",
                "filename": "document1.pdf",
                "uploaded_by": "test@example.com",
                "uploaded_at": "2023-01-01T00:00:00Z",
                "chunk_index": 0,
                "chunk_start": 0,
                "chunk_end": 100,
                "token_count": 25,
                "model": "text-embedding-3-large",
                "content_type": "application/pdf",
                "size": 1024,
                "vector": [0.1] * 3072,
                "metadata": '{"key": "value"}',
                "@search.score": 0.95
            },
            {
                "id": "result2",
                "engagement_id": "test-engagement",
                "doc_id": "doc2",
                "chunk_id": "doc2_0",
                "content": "Low relevance content",
                "filename": "document2.pdf",
                "uploaded_by": "test@example.com",
                "uploaded_at": "2023-01-01T00:00:00Z",
                "chunk_index": 0,
                "chunk_start": 0,
                "chunk_end": 100,
                "token_count": 25,
                "model": "text-embedding-3-large",
                "content_type": "application/pdf",
                "size": 1024,
                "vector": [0.2] * 3072,
                "metadata": '{"key": "value"}',
                "@search.score": 0.3
            }
        ]
        mock_to_thread.return_value = mock_search_results
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        query_vector = [0.1] * 3072
        results = await manager.search(
            query_vector=query_vector,
            engagement_id="test-engagement",
            similarity_threshold=0.5
        )
        
        # Should only return results above threshold
        assert len(results) == 1
        assert results[0].document.content == "High relevance content"
        assert results[0].score == 0.95


class TestDocumentDeletion:
    """Test document deletion operations"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_delete_documents_by_filter(self, mock_to_thread, mock_search_client_class, mock_index_client, mock_azure_search_config):
        """Test deleting documents by filter"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        
        # Mock search results for finding documents to delete
        mock_search_results = [
            {"id": "doc1_0"},
            {"id": "doc1_1"},
            {"id": "doc1_2"}
        ]
        
        # Mock delete results
        mock_delete_results = [
            Mock(succeeded=True, key="doc1_0"),
            Mock(succeeded=True, key="doc1_1"),
            Mock(succeeded=True, key="doc1_2")
        ]
        
        # Setup to_thread calls
        mock_to_thread.side_effect = [mock_search_results, mock_delete_results]
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        deleted_count = await manager.delete_documents_by_filter("engagement_id eq 'test-engagement' and doc_id eq 'doc1'")
        
        assert deleted_count == 3
        
        # Verify both search and delete were called
        assert mock_to_thread.call_count == 2


class TestIndexStatistics:
    """Test index statistics and monitoring"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_get_index_stats(self, mock_to_thread, mock_search_client_class, mock_index_client_class, mock_azure_search_config):
        """Test getting index statistics"""
        # Setup mocks
        mock_search_client = Mock()
        mock_index_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        mock_index_client_class.return_value = mock_index_client
        
        # Mock search count results
        mock_count_result = Mock()
        mock_count_result.get_count.return_value = 1500
        mock_to_thread.return_value = mock_count_result
        
        # Mock index info
        mock_index = Mock()
        mock_index.fields = [Mock()] * 15  # 15 fields
        mock_index.vector_search = Mock()
        mock_index.semantic_search = Mock()
        mock_index_client.get_index.return_value = mock_index
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        manager.index_client = mock_index_client
        
        stats = await manager.get_index_stats()
        
        assert stats["index_name"] == "test-index"
        assert stats["total_documents"] == 1500
        assert stats["field_count"] == 15
        assert stats["vector_search_enabled"] is True
        assert stats["semantic_search_enabled"] is True


class TestFactoryFunction:
    """Test factory function"""
    
    def test_create_azure_search_index_manager(self, mock_azure_search_config):
        """Test factory function creates manager correctly"""
        manager = create_azure_search_index_manager("test-correlation")
        
        assert isinstance(manager, AzureSearchIndexManager)
        assert manager.correlation_id == "test-correlation"


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    def test_initialization_error(self, mock_search_client, mock_index_client, mock_azure_search_config):
        """Test error handling during initialization"""
        mock_index_client.side_effect = Exception("Authentication failed")
        
        with pytest.raises(Exception):
            AzureSearchIndexManager("test-correlation")
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_search_error(self, mock_to_thread, mock_search_client_class, mock_index_client, mock_azure_search_config):
        """Test error handling during search"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        mock_to_thread.side_effect = Exception("Search service unavailable")
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        with pytest.raises(Exception):
            await manager.search(
                query_vector=[0.1] * 3072,
                engagement_id="test-engagement"
            )
    
    @patch('app.services.azure_search_index.SearchIndexClient')
    @patch('app.services.azure_search_index.SearchClient')
    @patch('app.services.azure_search_index.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_upload_error(self, mock_to_thread, mock_search_client_class, mock_index_client, mock_azure_search_config, sample_embedding_documents):
        """Test error handling during upload"""
        # Setup mocks
        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client
        mock_to_thread.side_effect = Exception("Upload service unavailable")
        
        manager = AzureSearchIndexManager("test-correlation")
        manager.search_client = mock_search_client
        
        with pytest.raises(Exception):
            await manager.upload_documents(sample_embedding_documents)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
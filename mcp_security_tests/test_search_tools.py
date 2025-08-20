"""
Search tools tests for MCP Gateway
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

from mcp_tools.search_tools import SearchEmbedTool, SearchQueryTool, SearchListTool
from mcp_tools import McpError
from vector_store import VectorStoreManager

class TestSearchTools:
    """Test search tools functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.vector_store_manager = VectorStoreManager(self.temp_dir)
        self.engagement_id = "test_engagement"
        
        # Initialize tools
        self.embed_tool = SearchEmbedTool(self.vector_store_manager)
        self.query_tool = SearchQueryTool(self.vector_store_manager)
        self.list_tool = SearchListTool(self.vector_store_manager)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_embed_and_search_round_trip(self):
        """Test embedding text and then searching for it"""
        # Embed some test content
        test_text = "This is a cybersecurity policy document about access controls and authentication."
        
        embed_result = await self.embed_tool.execute({
            "text": test_text,
            "id": "policy_doc_1",
            "metadata": {"document_type": "policy", "category": "security"}
        }, self.engagement_id)
        
        assert embed_result.success
        assert embed_result.result["id"] == "policy_doc_1"
        assert embed_result.result["text_length"] == len(test_text)
        
        # Search for related content
        search_result = await self.query_tool.execute({
            "query": "authentication policy access control",
            "top_k": 5
        }, self.engagement_id)
        
        assert search_result.success
        assert len(search_result.result["results"]) > 0
        
        # Check that our embedded content is found
        found_ids = [r["id"] for r in search_result.result["results"]]
        assert "policy_doc_1" in found_ids
        
        # Verify metadata is preserved
        found_doc = next(r for r in search_result.result["results"] if r["id"] == "policy_doc_1")
        assert found_doc["metadata"]["document_type"] == "policy"
        assert found_doc["metadata"]["category"] == "security"
    
    @pytest.mark.asyncio
    async def test_embed_multiple_documents(self):
        """Test embedding multiple documents and searching"""
        documents = [
            {
                "id": "doc1",
                "text": "Network security policies and firewall configurations for enterprise environments.",
                "metadata": {"type": "network", "priority": "high"}
            },
            {
                "id": "doc2", 
                "text": "Identity and access management procedures for user authentication.",
                "metadata": {"type": "identity", "priority": "medium"}
            },
            {
                "id": "doc3",
                "text": "Data encryption standards and key management protocols.",
                "metadata": {"type": "encryption", "priority": "high"}
            }
        ]
        
        # Embed all documents
        for doc in documents:
            embed_result = await self.embed_tool.execute({
                "text": doc["text"],
                "id": doc["id"],
                "metadata": doc["metadata"]
            }, self.engagement_id)
            assert embed_result.success
        
        # Search for network-related content
        search_result = await self.query_tool.execute({
            "query": "network firewall security",
            "top_k": 2
        }, self.engagement_id)
        
        assert search_result.success
        assert len(search_result.result["results"]) > 0
        
        # The network document should be ranked highly
        top_result = search_result.result["results"][0]
        assert top_result["id"] == "doc1"
    
    @pytest.mark.asyncio
    async def test_search_with_score_threshold(self):
        """Test search with similarity score filtering"""
        # Embed a document
        await self.embed_tool.execute({
            "text": "Specific technical content about database security configurations.",
            "id": "db_doc"
        }, self.engagement_id)
        
        # Search with high score threshold (should return fewer results)
        search_result = await self.query_tool.execute({
            "query": "completely unrelated content about cooking recipes",
            "score_threshold": 0.8,  # High threshold
            "top_k": 10
        }, self.engagement_id)
        
        assert search_result.success
        # Should return fewer or no results due to high threshold
        assert len(search_result.result["results"]) <= 1
    
    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(self):
        """Test search with metadata filtering"""
        documents = [
            {"id": "doc1", "text": "Security policy", "metadata": {"department": "IT", "level": "high"}},
            {"id": "doc2", "text": "Security guidelines", "metadata": {"department": "HR", "level": "medium"}},
            {"id": "doc3", "text": "Security procedures", "metadata": {"department": "IT", "level": "low"}}
        ]
        
        # Embed documents
        for doc in documents:
            await self.embed_tool.execute(doc, self.engagement_id)
        
        # Search with metadata filter
        search_result = await self.query_tool.execute({
            "query": "security",
            "metadata_filter": {"department": "IT"},
            "top_k": 10
        }, self.engagement_id)
        
        assert search_result.success
        # Should only return IT department documents
        for result in search_result.result["results"]:
            assert result["metadata"]["department"] == "IT"
    
    @pytest.mark.asyncio
    async def test_list_vectors(self):
        """Test listing stored vectors"""
        # Start with empty store
        list_result = await self.list_tool.execute({}, self.engagement_id)
        assert list_result.success
        assert list_result.result["total_count"] == 0
        
        # Add some vectors
        for i in range(3):
            await self.embed_tool.execute({
                "text": f"Document {i} content",
                "id": f"doc_{i}"
            }, self.engagement_id)
        
        # List vectors
        list_result = await self.list_tool.execute({
            "limit": 10
        }, self.engagement_id)
        
        assert list_result.success
        assert list_result.result["total_count"] == 3
        assert len(list_result.result["vectors"]) == 3
        
        # Check vector IDs
        vector_ids = [v["id"] for v in list_result.result["vectors"]]
        assert "doc_0" in vector_ids
        assert "doc_1" in vector_ids
        assert "doc_2" in vector_ids
    
    @pytest.mark.asyncio
    async def test_list_with_pagination(self):
        """Test vector listing with pagination"""
        # Add multiple vectors
        for i in range(5):
            await self.embed_tool.execute({
                "text": f"Document {i} content",
                "id": f"doc_{i}"
            }, self.engagement_id)
        
        # List with pagination
        list_result = await self.list_tool.execute({
            "limit": 2,
            "offset": 1
        }, self.engagement_id)
        
        assert list_result.success
        assert list_result.result["total_count"] == 5
        assert len(list_result.result["vectors"]) == 2
        assert list_result.result["has_more"] == True
    
    @pytest.mark.asyncio
    async def test_text_chunking(self):
        """Test text chunking functionality"""
        # Long text that should be chunked
        long_text = "This is a very long document. " * 100  # ~3000 chars
        
        embed_result = await self.embed_tool.execute({
            "text": long_text,
            "id": "long_doc",
            "chunk_strategy": "sentence",
            "max_chunk_size": 500
        }, self.engagement_id)
        
        assert embed_result.success
        assert "chunks" in embed_result.result
        assert embed_result.result["total_chunks"] > 1
        
        # List vectors to see chunks
        list_result = await self.list_tool.execute({}, self.engagement_id)
        chunk_count = len([v for v in list_result.result["vectors"] 
                          if v["id"].startswith("long_doc_chunk_")])
        assert chunk_count == embed_result.result["total_chunks"]
    
    @pytest.mark.asyncio
    async def test_empty_text_error(self):
        """Test error handling for empty text"""
        with pytest.raises(McpError, match="EMPTY_TEXT"):
            await self.embed_tool.execute({
                "text": "   ",  # Only whitespace
                "id": "empty_doc"
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_text_too_long_error(self):
        """Test error handling for text that's too long"""
        very_long_text = "x" * 60000  # 60KB (exceeds 50KB limit)
        
        with pytest.raises(McpError, match="TEXT_TOO_LONG"):
            await self.embed_tool.execute({
                "text": very_long_text,
                "id": "huge_doc"
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_empty_query_error(self):
        """Test error handling for empty search query"""
        with pytest.raises(McpError, match="EMPTY_QUERY"):
            await self.query_tool.execute({
                "query": "   "  # Only whitespace
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_query_too_long_error(self):
        """Test error handling for query that's too long"""
        very_long_query = "search terms " * 200  # Very long query
        
        with pytest.raises(McpError, match="QUERY_TOO_LONG"):
            await self.query_tool.execute({
                "query": very_long_query
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        """Test searching in an empty vector store"""
        search_result = await self.query_tool.execute({
            "query": "anything"
        }, self.engagement_id)
        
        assert search_result.success
        assert len(search_result.result["results"]) == 0
        assert search_result.result["total_store_size"] == 0
    
    @pytest.mark.asyncio
    async def test_auto_generated_id(self):
        """Test automatic ID generation when not provided"""
        embed_result = await self.embed_tool.execute({
            "text": "Document without explicit ID"
        }, self.engagement_id)
        
        assert embed_result.success
        assert "id" in embed_result.result
        assert embed_result.result["id"].startswith("text_")

if __name__ == "__main__":
    pytest.main([__file__])
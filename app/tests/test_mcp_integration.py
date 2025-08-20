"""
Integration tests for MCP Gateway integration with orchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from ai.orchestrator import Orchestrator
from ai.llm import LLMClient
from ai.mcp_client import McpCallResult, McpClientError, NoOpMcpClient, HttpMcpClient

class MockLLMClient:
    """Mock LLM client for testing"""
    
    async def generate(self, system: str, user: str) -> str:
        # Return deterministic output for testing
        if "DocAnalyzer" in system:
            return """
            - [high] Identity: MFA not enforced for admin accounts
            - [medium] Data: DLP policies not implemented for M365
            - [low] SecOps: Incident response runbooks missing for P1 events
            """
        elif "GapRecommender" in system:
            return """
            1. Implement MFA for privileged accounts (P1, M effort, 4 weeks)
            2. Deploy DLP policies for Microsoft 365 (P2, M effort, 6 weeks)
            3. Create incident response runbooks (P3, S effort, 3 weeks)
            """
        return "Mock LLM response"

class TestMcpIntegration:
    """Test MCP integration with orchestrator"""
    
    def setup_method(self):
        """Set up test environment"""
        self.llm_client = MockLLMClient()
        self.engagement_id = "test_engagement"
        self.orchestrator = Orchestrator(self.llm_client, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_analyze_without_mcp(self):
        """Test traditional analysis without MCP"""
        assessment_id = "assessment_123"
        content = "Sample security policy document content."
        
        # Analyze without MCP
        findings, log = await self.orchestrator.analyze(assessment_id, content)
        
        # Verify results
        assert len(findings) == 3  # Based on mock LLM response
        assert findings[0].severity == "high"
        assert findings[0].area == "Identity"
        assert "MFA" in findings[0].title
        
        assert log.assessment_id == assessment_id
        assert log.agent == "DocAnalyzer"
        assert content[:200] in log.input_preview
    
    @pytest.mark.asyncio
    async def test_analyze_with_mcp_disabled(self):
        """Test MCP analysis when MCP client is disabled"""
        assessment_id = "assessment_123"
        content = "Sample content"
        
        with patch('ai.orchestrator.get_mcp_client') as mock_get_client:
            # Mock disabled MCP client
            mock_client = NoOpMcpClient()
            mock_get_client.return_value = mock_client
            
            with patch('ai.orchestrator.config.mcp.is_enabled', return_value=False):
                findings, log = await self.orchestrator.analyze_with_mcp(
                    assessment_id, content, self.engagement_id
                )
        
        # Should fall back to traditional analysis
        assert len(findings) == 3
        assert not log.input_preview.startswith("[MCP Enhanced]")
    
    @pytest.mark.asyncio
    async def test_analyze_with_mcp_file_enhancement(self):
        """Test MCP analysis with file content enhancement"""
        assessment_id = "assessment_123"
        file_reference = "security_policy.txt"  # Looks like a file reference
        file_content = "Detailed security policy content from file"
        
        # Mock MCP client that returns file content
        mock_client = AsyncMock()
        mock_client.is_enabled.return_value = True
        
        with patch('ai.orchestrator.get_mcp_client') as mock_get_client, \
             patch('ai.orchestrator.config.mcp.is_enabled', return_value=True), \
             patch('ai.orchestrator.mcp_fs_read') as mock_fs_read:
            
            mock_get_client.return_value = mock_client
            mock_fs_read.return_value = file_content
            
            findings, log = await self.orchestrator.analyze_with_mcp(
                assessment_id, file_reference, self.engagement_id
            )
        
        # Verify MCP enhancement was used
        assert log.input_preview.startswith("[MCP Enhanced]")
        assert len(findings) == 3
        
        # Verify file read was called
        mock_fs_read.assert_called_once_with(file_reference, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_analyze_with_mcp_search_enhancement(self):
        """Test MCP analysis with search context enhancement"""
        assessment_id = "assessment_123"
        content = "Long content that should trigger search for additional context"
        
        # Mock search results
        search_results = [
            {"id": "doc1", "text": "Related security document content", "score": 0.8},
            {"id": "doc2", "text": "Another relevant policy document", "score": 0.7}
        ]
        
        mock_client = AsyncMock()
        mock_client.is_enabled.return_value = True
        
        with patch('ai.orchestrator.get_mcp_client') as mock_get_client, \
             patch('ai.orchestrator.config.mcp.is_enabled', return_value=True), \
             patch('ai.orchestrator.mcp_search_query') as mock_search:
            
            mock_get_client.return_value = mock_client
            mock_search.return_value = search_results
            
            findings, log = await self.orchestrator.analyze_with_mcp(
                assessment_id, content, self.engagement_id
            )
        
        # Verify search enhancement was used
        assert log.input_preview.startswith("[MCP Enhanced]")
        assert len(findings) == 3
        
        # Verify search was called
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[0][0] == content[:500]  # Query is truncated content
        assert call_args[0][1] == self.engagement_id
    
    @pytest.mark.asyncio
    async def test_analyze_with_mcp_fallback_on_error(self):
        """Test graceful fallback when MCP operations fail"""
        assessment_id = "assessment_123"
        content = "test_file.txt"  # Looks like file reference
        
        mock_client = AsyncMock()
        mock_client.is_enabled.return_value = True
        
        with patch('ai.orchestrator.get_mcp_client') as mock_get_client, \
             patch('ai.orchestrator.config.mcp.is_enabled', return_value=True), \
             patch('ai.orchestrator.mcp_fs_read') as mock_fs_read:
            
            mock_get_client.return_value = mock_client
            # Simulate MCP error
            mock_fs_read.side_effect = McpClientError("File not found", "FILE_NOT_FOUND")
            
            findings, log = await self.orchestrator.analyze_with_mcp(
                assessment_id, content, self.engagement_id
            )
        
        # Should still work with fallback
        assert len(findings) == 3
        assert log.input_preview.startswith("[MCP Enhanced]")  # Still marked as MCP attempt
    
    @pytest.mark.asyncio
    async def test_analyze_mcp_vs_traditional_parity(self):
        """Test that MCP and traditional analysis produce comparable results"""
        assessment_id = "assessment_123"
        content = "Standard security policy content for analysis"
        
        # Get traditional analysis results
        traditional_findings, traditional_log = await self.orchestrator.analyze(
            assessment_id, content
        )
        
        # Get MCP analysis results (with MCP disabled so it falls back)
        with patch('ai.orchestrator.get_mcp_client') as mock_get_client:
            mock_client = NoOpMcpClient()
            mock_get_client.return_value = mock_client
            
            with patch('ai.orchestrator.config.mcp.is_enabled', return_value=False):
                mcp_findings, mcp_log = await self.orchestrator.analyze_with_mcp(
                    assessment_id, content, self.engagement_id
                )
        
        # Results should be equivalent (allowing for minor differences)
        assert len(traditional_findings) == len(mcp_findings)
        
        for trad, mcp in zip(traditional_findings, mcp_findings):
            assert trad.severity == mcp.severity
            assert trad.area == mcp.area
            # Titles should be very similar (exact match in this mock case)
            assert trad.title == mcp.title
    
    @pytest.mark.asyncio
    async def test_mcp_file_reference_detection(self):
        """Test file reference detection heuristics"""
        test_cases = [
            ("document.txt", True),           # Simple filename
            ("path/to/file.pdf", True),       # Path with extension
            ("config.json", True),            # Config file
            ("This is a long document content that should not be treated as a file reference", False),
            ("multi\nline\ncontent", False),  # Multi-line content
            ("", False),                      # Empty content
            ("file with spaces.docx", True),  # Filename with spaces (single line, has extension)
        ]
        
        for content, expected in test_cases:
            result = self.orchestrator._looks_like_file_reference(content)
            assert result == expected, f"Failed for content: '{content}'"
    
    @pytest.mark.asyncio 
    async def test_recommend_with_mcp_context(self):
        """Test recommendation generation (basic functionality)"""
        assessment_id = "assessment_123"
        findings_text = "- [high] Identity: MFA not enforced\n- [medium] Data: DLP missing"
        
        recommendations, log = await self.orchestrator.recommend(assessment_id, findings_text)
        
        # Verify recommendations were generated
        assert len(recommendations) == 3  # Based on mock response
        assert recommendations[0].priority in ["P1", "P2", "P3"]
        assert recommendations[0].effort in ["S", "M", "L"]
        
        assert log.assessment_id == assessment_id
        assert log.agent == "GapRecommender"

if __name__ == "__main__":
    pytest.main([__file__])
"""
Unit tests for chat command parser service
"""

import pytest
from services.chat_commands import ChatCommandParser


class TestChatCommandParser:
    """Test suite for ChatCommandParser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = ChatCommandParser()
    
    def test_parse_non_command_message(self):
        """Test that regular messages return None"""
        result = self.parser.parse_command("Hello, how are you?")
        assert result is None
        
        result = self.parser.parse_command("What is the weather like today")
        assert result is None
    
    def test_parse_empty_message(self):
        """Test that empty/invalid messages return None"""
        assert self.parser.parse_command("") is None
        assert self.parser.parse_command(None) is None
        assert self.parser.parse_command("   ") is None
    
    def test_parse_unknown_command(self):
        """Test that unknown commands return None"""
        result = self.parser.parse_command("/unknown command")
        assert result is None
        
        result = self.parser.parse_command("/notfound")
        assert result is None
    
    def test_parse_ingest_basic(self):
        """Test basic /ingest command parsing"""
        result = self.parser.parse_command("/ingest")
        
        assert result is not None
        assert result.command == "ingest"
        assert result.raw_text == "/ingest"
        assert result.inputs["source_type"] == "documents"
        assert result.inputs["force_reindex"] is False
        assert result.inputs["filter_pattern"] is None
    
    def test_parse_ingest_with_args(self):
        """Test /ingest command with arguments"""
        result = self.parser.parse_command("/ingest docs force")
        
        assert result is not None
        assert result.command == "ingest"
        assert result.inputs["source_type"] == "documents"
        assert result.inputs["force_reindex"] is True
        
        result = self.parser.parse_command("/ingest pattern:*.pdf")
        assert result.inputs["filter_pattern"] == "*.pdf"
        
        result = self.parser.parse_command("/ingest assessment reindex")
        assert result.inputs["source_type"] == "assessment"
        assert result.inputs["force_reindex"] is True
    
    def test_parse_minutes_basic(self):
        """Test basic /minutes command parsing"""
        result = self.parser.parse_command("/minutes")
        
        assert result is not None
        assert result.command == "minutes"
        assert result.inputs["format"] == "markdown"
        assert result.inputs["include_actions"] is True
        assert result.inputs["include_decisions"] is True
    
    def test_parse_minutes_with_args(self):
        """Test /minutes command with arguments"""
        result = self.parser.parse_command("/minutes json no-actions")
        
        assert result.inputs["format"] == "json"
        assert result.inputs["include_actions"] is False
        assert result.inputs["include_decisions"] is True
        
        result = self.parser.parse_command("/minutes html no-decisions from:2024-01-01")
        assert result.inputs["format"] == "html"
        assert result.inputs["include_decisions"] is False
        assert result.inputs["from_date"] == "2024-01-01"
    
    def test_parse_score_basic(self):
        """Test basic /score command parsing"""
        result = self.parser.parse_command("/score")
        
        assert result is not None
        assert result.command == "score"
        assert result.inputs["framework"] == "auto"
        assert result.inputs["include_recommendations"] is True
        assert result.inputs["format"] == "summary"
    
    def test_parse_score_with_args(self):
        """Test /score command with arguments"""
        result = self.parser.parse_command("/score nist detailed")
        
        assert result.inputs["framework"] == "nist"
        assert result.inputs["format"] == "detailed"
        
        result = self.parser.parse_command("/score cscm brief no-recommendations")
        assert result.inputs["framework"] == "cscm"
        assert result.inputs["format"] == "brief"
        assert result.inputs["include_recommendations"] is False
    
    def test_case_insensitive_commands(self):
        """Test that command parsing is case insensitive"""
        result = self.parser.parse_command("/INGEST")
        assert result is not None
        assert result.command == "ingest"
        
        result = self.parser.parse_command("/Minutes")
        assert result is not None
        assert result.command == "minutes"
        
        result = self.parser.parse_command("/SCORE")
        assert result is not None
        assert result.command == "score"
    
    def test_get_supported_commands(self):
        """Test getting list of supported commands"""
        commands = self.parser.get_supported_commands()
        
        assert isinstance(commands, list)
        assert "ingest" in commands
        assert "minutes" in commands
        assert "score" in commands
        assert len(commands) == 3
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly handled"""
        result = self.parser.parse_command("  /ingest  docs  force  ")
        
        assert result is not None
        assert result.command == "ingest"
        assert result.inputs["source_type"] == "documents"
        assert result.inputs["force_reindex"] is True
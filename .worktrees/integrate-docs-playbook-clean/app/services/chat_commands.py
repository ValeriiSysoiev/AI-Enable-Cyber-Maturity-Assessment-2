"""
Chat Command Parser Service

Parses orchestrator shell commands like /ingest, /minutes, /score
and extracts structured parameters for execution.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CommandParseResult:
    """Result of command parsing"""
    command: str  # Command name (e.g., "ingest")
    inputs: Dict[str, Any]  # Parsed parameters
    raw_text: str  # Original command text


class ChatCommandParser:
    """Parser for orchestrator chat shell commands"""
    
    def __init__(self):
        self.command_patterns = {
            'ingest': self._parse_ingest,
            'minutes': self._parse_minutes,
            'score': self._parse_score
        }
    
    def parse_command(self, message: str) -> Optional[CommandParseResult]:
        """
        Parse a chat message for orchestrator commands
        
        Args:
            message: User message text
            
        Returns:
            CommandParseResult if command found, None otherwise
        """
        if not message or not isinstance(message, str):
            return None
        
        message = message.strip()
        
        # Check if message starts with command prefix
        if not message.startswith('/'):
            return None
        
        # Extract command and arguments
        parts = message[1:].split(' ', 1)
        command_name = parts[0].lower()
        args_text = parts[1] if len(parts) > 1 else ""
        
        # Find parser for this command
        parser_func = self.command_patterns.get(command_name)
        if not parser_func:
            return None
        
        try:
            inputs = parser_func(args_text)
            return CommandParseResult(
                command=command_name,
                inputs=inputs,
                raw_text=message
            )
        except Exception as e:
            logger.warning(
                f"Failed to parse command '{command_name}': {str(e)}",
                extra={"command": command_name, "args": args_text}
            )
            return None
    
    def _parse_ingest(self, args: str) -> Dict[str, Any]:
        """Parse /ingest command arguments"""
        inputs = {
            'source_type': 'documents',
            'filter_pattern': None,
            'force_reindex': False
        }
        
        if args:
            # Simple pattern matching for common arguments
            if 'force' in args.lower() or 'reindex' in args.lower():
                inputs['force_reindex'] = True
            
            # Extract file pattern if specified
            pattern_match = re.search(r'pattern[:\s]+([^\s]+)', args, re.IGNORECASE)
            if pattern_match:
                inputs['filter_pattern'] = pattern_match.group(1)
            
            # Check for specific source type
            if 'docs' in args.lower() or 'documents' in args.lower():
                inputs['source_type'] = 'documents'
            elif 'assessment' in args.lower():
                inputs['source_type'] = 'assessment'
        
        return inputs
    
    def _parse_minutes(self, args: str) -> Dict[str, Any]:
        """Parse /minutes command arguments"""
        inputs = {
            'format': 'markdown',
            'include_actions': True,
            'include_decisions': True
        }
        
        if args:
            # Format specification
            if 'json' in args.lower():
                inputs['format'] = 'json'
            elif 'html' in args.lower():
                inputs['format'] = 'html'
            
            # Content filters
            if 'no-actions' in args.lower():
                inputs['include_actions'] = False
            if 'no-decisions' in args.lower():
                inputs['include_decisions'] = False
            
            # Extract date range if specified
            date_match = re.search(r'from[:\s]+([^\s]+)', args, re.IGNORECASE)
            if date_match:
                inputs['from_date'] = date_match.group(1)
            
            date_match = re.search(r'to[:\s]+([^\s]+)', args, re.IGNORECASE)
            if date_match:
                inputs['to_date'] = date_match.group(1)
        
        return inputs
    
    def _parse_score(self, args: str) -> Dict[str, Any]:
        """Parse /score command arguments"""
        inputs = {
            'framework': 'auto',
            'include_recommendations': True,
            'format': 'summary'
        }
        
        if args:
            # Framework specification
            frameworks = ['nist', 'iso27001', 'cis', 'cscm']
            for framework in frameworks:
                if framework in args.lower():
                    inputs['framework'] = framework
                    break
            
            # Output format
            if 'detailed' in args.lower() or 'full' in args.lower():
                inputs['format'] = 'detailed'
            elif 'brief' in args.lower():
                inputs['format'] = 'brief'
            
            # Options
            if 'no-recommendations' in args.lower():
                inputs['include_recommendations'] = False
        
        return inputs
    
    def get_supported_commands(self) -> List[str]:
        """Get list of supported command names"""
        return list(self.command_patterns.keys())


# Factory function for dependency injection
def create_chat_command_parser() -> ChatCommandParser:
    """Create chat command parser instance"""
    return ChatCommandParser()
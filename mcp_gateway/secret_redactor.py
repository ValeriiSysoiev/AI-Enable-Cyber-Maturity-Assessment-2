"""
Comprehensive secret redaction for MCP Gateway logging

Implements pattern-based detection and redaction of sensitive information
from logs, requests, and responses to prevent data leakage.
"""

import re
import json
import logging
from typing import Any, Dict, Union, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RedactionStats:
    """Statistics about redaction operations"""
    total_fields_processed: int = 0
    fields_redacted: int = 0
    patterns_matched: int = 0
    content_truncated: int = 0

class SecretRedactor:
    """Comprehensive secret redaction for logging and data handling"""
    
    def __init__(self, max_field_length: int = 500, max_total_size: int = 10000):
        self.max_field_length = max_field_length
        self.max_total_size = max_total_size
        
        # Sensitive field names (case-insensitive)
        self.sensitive_fields = {
            'password', 'passwd', 'pwd',
            'token', 'access_token', 'refresh_token', 'bearer_token', 'api_token',
            'secret', 'client_secret', 'app_secret',
            'key', 'api_key', 'private_key', 'public_key', 'encryption_key',
            'auth', 'authorization', 'authentication',
            'credential', 'credentials',
            'session', 'session_id', 'sessionid',
            'cookie', 'cookies',
            'jwt', 'oauth',
            'cert', 'certificate', 'pem',
            'connection_string', 'connstr', 'database_url',
            'ssn', 'social_security', 'credit_card', 'card_number',
            'email', 'phone', 'address'
        }
        
        # Regex patterns for detecting sensitive data
        self.sensitive_patterns = [
            # API keys and tokens
            (r'[A-Za-z0-9]{20,}', 'POTENTIAL_TOKEN'),
            # Base64 encoded data (potential secrets)
            (r'[A-Za-z0-9+/]{20,}={0,2}', 'POTENTIAL_BASE64'),
            # UUIDs (might be sensitive IDs)
            (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID'),
            # URLs with credentials
            (r'https?://[^:]+:[^@]+@[^\s]+', 'URL_WITH_CREDENTIALS'),
            # JWT tokens
            (r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 'JWT_TOKEN'),
            # Private keys
            (r'-----BEGIN[^-]+PRIVATE KEY-----.*?-----END[^-]+PRIVATE KEY-----', 'PRIVATE_KEY'),
            # Connection strings
            (r'(?:server|host|data source)=[^;]+;.*?(?:password|pwd)=[^;]+', 'CONNECTION_STRING'),
            # Credit card patterns
            (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', 'CREDIT_CARD'),
            # Social Security Numbers
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            # Email addresses (in some contexts might be sensitive)
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
            # IP addresses (might be sensitive in some contexts)
            (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 'IP_ADDRESS')
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), label)
            for pattern, label in self.sensitive_patterns
        ]
    
    def redact_data(self, data: Any, context: str = "unknown") -> tuple[Any, RedactionStats]:
        """
        Redact sensitive information from arbitrary data structures
        
        Args:
            data: Data to redact (dict, list, str, etc.)
            context: Context for logging (e.g., "request_payload", "response_data")
        
        Returns:
            Tuple of (redacted_data, redaction_stats)
        """
        stats = RedactionStats()
        
        try:
            redacted = self._redact_recursive(data, stats, context)
            
            # Apply size limits
            if isinstance(redacted, (dict, list)):
                size_check = len(json.dumps(redacted, default=str))
                if size_check > self.max_total_size:
                    redacted = f"[TRUNCATED - {size_check} bytes exceeds {self.max_total_size} limit]"
                    stats.content_truncated += 1
            
            logger.debug(f"Redaction completed for {context}: {stats}")
            return redacted, stats
            
        except Exception as e:
            logger.warning(f"Redaction failed for {context}: {e}")
            return "[REDACTION_ERROR]", stats
    
    def _redact_recursive(self, data: Any, stats: RedactionStats, context: str, depth: int = 0) -> Any:
        """Recursively redact data structures"""
        if depth > 10:  # Prevent infinite recursion
            return "[MAX_DEPTH_REACHED]"
        
        if isinstance(data, dict):
            return self._redact_dict(data, stats, context, depth)
        elif isinstance(data, list):
            return self._redact_list(data, stats, context, depth)
        elif isinstance(data, str):
            return self._redact_string(data, stats, context)
        elif isinstance(data, (int, float, bool, type(None))):
            return data
        else:
            # For other types, convert to string and redact
            return self._redact_string(str(data), stats, context)
    
    def _redact_dict(self, data: Dict[str, Any], stats: RedactionStats, context: str, depth: int) -> Dict[str, Any]:
        """Redact dictionary data"""
        redacted = {}
        
        for key, value in data.items():
            stats.total_fields_processed += 1
            
            # Check if field name is sensitive
            if self._is_sensitive_field(key):
                redacted[key] = "[REDACTED]"
                stats.fields_redacted += 1
                continue
            
            # Recursively redact value
            redacted[key] = self._redact_recursive(value, stats, f"{context}.{key}", depth + 1)
        
        return redacted
    
    def _redact_list(self, data: List[Any], stats: RedactionStats, context: str, depth: int) -> List[Any]:
        """Redact list data"""
        redacted = []
        
        for i, item in enumerate(data):
            if i > 100:  # Limit list processing to prevent performance issues
                redacted.append(f"[TRUNCATED - {len(data) - i} more items]")
                stats.content_truncated += 1
                break
            
            redacted.append(self._redact_recursive(item, stats, f"{context}[{i}]", depth + 1))
        
        return redacted
    
    def _redact_string(self, data: str, stats: RedactionStats, context: str) -> str:
        """Redact string data using pattern matching"""
        if not data or not isinstance(data, str):
            return data
        
        # Apply length limit
        if len(data) > self.max_field_length:
            data = data[:self.max_field_length] + f"...[TRUNCATED from {len(data)} chars]"
            stats.content_truncated += 1
        
        # Check against sensitive patterns
        redacted = data
        for pattern, label in self.compiled_patterns:
            if pattern.search(redacted):
                # Replace matches with redaction marker
                redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
                stats.patterns_matched += 1
        
        return redacted
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data"""
        if not field_name or not isinstance(field_name, str):
            return False
        
        field_lower = field_name.lower()
        
        # Direct match
        if field_lower in self.sensitive_fields:
            return True
        
        # Partial match (field contains sensitive terms)
        for sensitive_term in self.sensitive_fields:
            if sensitive_term in field_lower:
                return True
        
        return False
    
    def redact_for_logging(self, data: Any, context: str = "log") -> str:
        """Redact data specifically for logging purposes"""
        redacted_data, stats = self.redact_data(data, context)
        
        try:
            if isinstance(redacted_data, (dict, list)):
                return json.dumps(redacted_data, default=str, indent=None)
            else:
                return str(redacted_data)
        except Exception as e:
            logger.warning(f"Failed to serialize redacted data for logging: {e}")
            return f"[SERIALIZATION_ERROR: {type(redacted_data).__name__}]"
    
    def create_redacted_logger_adapter(self, base_logger: logging.Logger, context: Dict[str, Any]) -> logging.LoggerAdapter:
        """Create a logger adapter that automatically redacts context data"""
        redacted_context, _ = self.redact_data(context, "logger_context")
        return logging.LoggerAdapter(base_logger, redacted_context)

# Global redactor instance
default_redactor = SecretRedactor()

def redact_for_logs(data: Any, context: str = "log") -> str:
    """Convenience function for quick redaction"""
    return default_redactor.redact_for_logging(data, context)
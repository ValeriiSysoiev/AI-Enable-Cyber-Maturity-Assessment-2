"""
PII Scrubbing MCP Tool
Provides configurable PII redaction for transcripts and documents with audit logging.
"""
import sys
sys.path.append("/app")
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import json

from services.mcp_gateway.security import SecurityPolicy
from services.mcp_gateway.config import MCPConfig, MCPOperationContext

logger = logging.getLogger(__name__)

class PIIScrubberTool:
    """
    MCP tool for PII (Personally Identifiable Information) scrubbing.
    
    Features:
    - Configurable redaction patterns for emails, keys, government IDs
    - Audit logging of redaction counts and types
    - Support for multiple content types (text, JSON, structured data)
    - Customizable replacement tokens
    - Performance optimized regex patterns
    """
    
    TOOL_NAME = "pii.scrub"
    
    # Default PII patterns with descriptive names
    DEFAULT_PII_PATTERNS = {
        "email_address": {
            "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "replacement": "[REDACTED-EMAIL]",
            "description": "Email addresses (user@domain.com)"
        },
        "us_ssn": {
            "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
            "replacement": "[REDACTED-SSN]",
            "description": "US Social Security Numbers (XXX-XX-XXXX)"
        },
        "us_ssn_spaces": {
            "pattern": r'\b\d{3}\s\d{2}\s\d{4}\b',
            "replacement": "[REDACTED-SSN]",
            "description": "US Social Security Numbers with spaces (XXX XX XXXX)"
        },
        "credit_card": {
            "pattern": r'\b(?:\d{4}[- ]?){3}\d{4}\b',
            "replacement": "[REDACTED-CREDIT-CARD]",
            "description": "Credit card numbers (16 digits with optional separators)"
        },
        "phone_us": {
            "pattern": r'\b\d{3}-\d{3}-\d{4}\b',
            "replacement": "[REDACTED-PHONE]",
            "description": "US phone numbers (XXX-XXX-XXXX)"
        },
        "phone_us_parentheses": {
            "pattern": r'\(\d{3}\)\s?\d{3}-\d{4}',
            "replacement": "[REDACTED-PHONE]",
            "description": "US phone numbers with area code in parentheses"
        },
        "us_driver_license": {
            "pattern": r'\b[A-Z]{1,2}\d{6,8}\b',
            "replacement": "[REDACTED-DL]",
            "description": "US driver license patterns (state prefix + numbers)"
        },
        "ip_address": {
            "pattern": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "replacement": "[REDACTED-IP]",
            "description": "IPv4 addresses"
        },
        "api_key_generic": {
            "pattern": r'\b[A-Za-z0-9]{32,}\b',
            "replacement": "[REDACTED-API-KEY]",
            "description": "Generic API keys (32+ alphanumeric characters)"
        },
        "aws_access_key": {
            "pattern": r'\bAKIA[0-9A-Z]{16}\b',
            "replacement": "[REDACTED-AWS-KEY]",
            "description": "AWS Access Key IDs"
        },
        "github_token": {
            "pattern": r'\bghp_[A-Za-z0-9]{36}\b',
            "replacement": "[REDACTED-GITHUB-TOKEN]",
            "description": "GitHub Personal Access Tokens"
        },
        "uuid": {
            "pattern": r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            "replacement": "[REDACTED-UUID]",
            "description": "UUID identifiers"
        }
    }
    
    def __init__(self, config: MCPConfig):
        """Initialize PII scrubber with configuration."""
        self.config = config
        self.security = SecurityPolicy(config)
        
        # Compile regex patterns for performance
        self.compiled_patterns = {}
        self._compile_patterns()
        
        # Redaction statistics tracking
        self.redaction_stats = {}
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        for pattern_name, pattern_config in self.DEFAULT_PII_PATTERNS.items():
            try:
                self.compiled_patterns[pattern_name] = {
                    "regex": re.compile(pattern_config["pattern"], re.IGNORECASE),
                    "replacement": pattern_config["replacement"],
                    "description": pattern_config["description"]
                }
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern_name}': {e}")
    
    def validate_scrub_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize PII scrubbing configuration.
        
        Args:
            payload: Tool payload containing scrub configuration
            
        Returns:
            Dict containing validated configuration
        """
        scrub_config = payload.get("scrub_config", {})
        
        # Set defaults
        validated_config = {
            "enabled_patterns": scrub_config.get("enabled_patterns", list(self.DEFAULT_PII_PATTERNS.keys())),
            "case_sensitive": scrub_config.get("case_sensitive", False),
            "preserve_format": scrub_config.get("preserve_format", True),
            "audit_redactions": scrub_config.get("audit_redactions", True),
            "custom_patterns": scrub_config.get("custom_patterns", {}),
            "replacement_strategy": scrub_config.get("replacement_strategy", "token")  # token, asterisk, hash
        }
        
        # Validate enabled patterns
        invalid_patterns = []
        for pattern_name in validated_config["enabled_patterns"]:
            if pattern_name not in self.DEFAULT_PII_PATTERNS and pattern_name not in validated_config["custom_patterns"]:
                invalid_patterns.append(pattern_name)
        
        if invalid_patterns:
            raise ValueError(f"Unknown PII patterns: {invalid_patterns}")
        
        # Validate custom patterns
        for custom_name, custom_config in validated_config["custom_patterns"].items():
            if not isinstance(custom_config, dict):
                raise ValueError(f"Custom pattern '{custom_name}' must be a dictionary")
            
            required_fields = ["pattern", "replacement"]
            for field in required_fields:
                if field not in custom_config:
                    raise ValueError(f"Custom pattern '{custom_name}' missing required field: {field}")
            
            # Test regex compilation
            try:
                re.compile(custom_config["pattern"])
            except re.error as e:
                raise ValueError(f"Invalid regex in custom pattern '{custom_name}': {e}")
        
        return validated_config
    
    def scrub_text(self, text: str, config: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
        """
        Scrub PII from text content.
        
        Args:
            text: Text content to scrub
            config: Validated scrub configuration
            
        Returns:
            Tuple of (scrubbed_text, redaction_counts)
        """
        if not text or not isinstance(text, str):
            return text, {}
        
        scrubbed_text = text
        redaction_counts = {}
        
        # Process default patterns
        for pattern_name in config["enabled_patterns"]:
            if pattern_name in self.compiled_patterns:
                pattern_info = self.compiled_patterns[pattern_name]
                regex = pattern_info["regex"]
                replacement = pattern_info["replacement"]
                
                # Count matches before replacement
                matches = regex.findall(scrubbed_text)
                if matches:
                    redaction_counts[pattern_name] = len(matches)
                    scrubbed_text = regex.sub(replacement, scrubbed_text)
        
        # Process custom patterns
        for custom_name, custom_config in config["custom_patterns"].items():
            if custom_name in config["enabled_patterns"]:
                pattern = custom_config["pattern"]
                replacement = custom_config["replacement"]
                
                flags = 0 if config["case_sensitive"] else re.IGNORECASE
                
                try:
                    matches = re.findall(pattern, scrubbed_text, flags)
                    if matches:
                        redaction_counts[custom_name] = len(matches)
                        scrubbed_text = re.sub(pattern, replacement, scrubbed_text, flags=flags)
                except re.error as e:
                    logger.warning(f"Error applying custom pattern '{custom_name}': {e}")
        
        return scrubbed_text, redaction_counts
    
    def scrub_structured_data(self, data: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Scrub PII from structured data (JSON-like objects).
        
        Args:
            data: Structured data to scrub
            config: Validated scrub configuration
            
        Returns:
            Tuple of (scrubbed_data, redaction_counts)
        """
        scrubbed_data = {}
        total_redaction_counts = {}
        
        def scrub_value(value):
            """Recursively scrub values."""
            if isinstance(value, str):
                scrubbed_str, counts = self.scrub_text(value, config)
                # Aggregate counts
                for pattern, count in counts.items():
                    total_redaction_counts[pattern] = total_redaction_counts.get(pattern, 0) + count
                return scrubbed_str
            elif isinstance(value, dict):
                return {k: scrub_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [scrub_value(item) for item in value]
            else:
                return value
        
        for key, value in data.items():
            scrubbed_data[key] = scrub_value(value)
        
        return scrubbed_data, total_redaction_counts
    
    def generate_redaction_report(self, redaction_counts: Dict[str, int], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a detailed redaction audit report.
        
        Args:
            redaction_counts: Dictionary of pattern names to redaction counts
            config: Scrub configuration used
            
        Returns:
            Dict containing redaction report
        """
        total_redactions = sum(redaction_counts.values())
        
        # Categorize redactions
        categories = {
            "identity": ["email_address", "us_ssn", "us_ssn_spaces", "us_driver_license"],
            "financial": ["credit_card"],
            "contact": ["phone_us", "phone_us_parentheses"],
            "technical": ["ip_address", "api_key_generic", "aws_access_key", "github_token", "uuid"],
            "custom": []
        }
        
        # Identify custom patterns
        for pattern_name in redaction_counts.keys():
            if pattern_name not in self.DEFAULT_PII_PATTERNS:
                categories["custom"].append(pattern_name)
        
        category_counts = {}
        for category, patterns in categories.items():
            category_count = sum(redaction_counts.get(pattern, 0) for pattern in patterns)
            if category_count > 0:
                category_counts[category] = category_count
        
        return {
            "total_redactions": total_redactions,
            "redaction_counts": redaction_counts,
            "category_breakdown": category_counts,
            "patterns_used": list(redaction_counts.keys()),
            "config_applied": {
                "enabled_patterns": config["enabled_patterns"],
                "case_sensitive": config["case_sensitive"],
                "custom_patterns_count": len(config["custom_patterns"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str, call_id: str) -> Dict[str, Any]:
        """
        Execute PII scrubbing with audit logging.
        
        Args:
            payload: Tool execution payload
            engagement_id: Engagement identifier for sandboxing
            call_id: Unique call identifier for tracking
            
        Returns:
            Dict containing scrubbed content and audit information
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate scrub configuration
            config = self.validate_scrub_config(payload)
            
            # Extract content to scrub
            if "content" not in payload:
                raise ValueError("Missing required field: content")
            
            content = payload["content"]
            content_type = payload.get("content_type", "text")
            
            # Determine processing method based on content type
            if content_type == "text":
                if not isinstance(content, str):
                    raise ValueError("Content must be a string for content_type 'text'")
                
                scrubbed_content, redaction_counts = self.scrub_text(content, config)
                
            elif content_type == "json" or content_type == "structured":
                if not isinstance(content, dict):
                    raise ValueError("Content must be a dictionary for content_type 'json/structured'")
                
                scrubbed_content, redaction_counts = self.scrub_structured_data(content, config)
                
            else:
                raise ValueError(f"Unsupported content_type: {content_type}. Supported: text, json, structured")
            
            # Generate redaction report
            redaction_report = self.generate_redaction_report(redaction_counts, config)
            
            # Calculate processing metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Prepare result
            result = {
                "success": True,
                "tool": self.TOOL_NAME,
                "call_id": call_id,
                "engagement_id": engagement_id,
                "scrubbed_content": scrubbed_content,
                "original_content_type": content_type,
                "redaction_report": redaction_report,
                "processing_time_seconds": round(processing_time, 3),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Include original content length for analysis
            if isinstance(content, str):
                result["content_metrics"] = {
                    "original_length": len(content),
                    "scrubbed_length": len(scrubbed_content),
                    "reduction_percentage": round(((len(content) - len(scrubbed_content)) / len(content)) * 100, 2) if content else 0
                }
            
            # Audit logging
            if config.get("audit_redactions", True):
                logger.info(
                    "PII scrubbing completed",
                    extra={
                        "call_id": call_id,
                        "engagement_id": engagement_id,
                        "content_type": content_type,
                        "total_redactions": redaction_report["total_redactions"],
                        "patterns_detected": list(redaction_counts.keys()),
                        "processing_time_seconds": processing_time,
                        "redaction_categories": list(redaction_report["category_breakdown"].keys())
                    }
                )
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "tool": self.TOOL_NAME,
                "call_id": call_id,
                "engagement_id": engagement_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.error(
                "PII scrubbing failed",
                extra={
                    "call_id": call_id,
                    "engagement_id": engagement_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            return error_result


# Tool registration function
def register_tool(tool_registry: Dict[str, Any]) -> None:
    """Register the PII scrubbing tool with MCP gateway."""
    tool_registry[PIIScrubberTool.TOOL_NAME] = PIIScrubberTool
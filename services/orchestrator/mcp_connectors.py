"""
MCP Connectors for Enterprise Audio Transcription and PPTX Generation
Provides integration between orchestrator and Sprint v1.4 MCP tools.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from mcp_client import IMcpClient, generate_correlation_id

logger = logging.getLogger(__name__)

class MCPConnectors:
    """
    Enterprise MCP connectors for audio transcription and PPTX generation.
    
    Provides orchestrator integration with Sprint v1.4 MCP tools:
    - audio.transcribe: Workshop audio → text transcription
    - pii.scrub: GDPR/CCPA compliant content redaction
    - pptx.render: Executive roadmap presentation generation
    """
    
    def __init__(self, mcp_client: IMcpClient):
        """Initialize MCP connectors with client."""
        self.mcp_client = mcp_client
        
        # Feature flags for granular control
        self.audio_enabled = os.environ.get("MCP_CONNECTORS_AUDIO", "false").lower() == "true"
        self.pptx_enabled = os.environ.get("MCP_CONNECTORS_PPTX", "false").lower() == "true"
        self.pii_scrub_enabled = os.environ.get("MCP_CONNECTORS_PII_SCRUB", "true").lower() == "true"
        
        logger.info(
            "MCP Connectors initialized",
            extra={
                "audio_enabled": self.audio_enabled,
                "pptx_enabled": self.pptx_enabled,
                "pii_scrub_enabled": self.pii_scrub_enabled
            }
        )
    
    async def transcribe_audio(self, audio_data: str, mime_type: str, 
                             engagement_id: str, consent_type: str = "workshop",
                             options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transcribe audio using MCP audio.transcribe tool.
        
        Args:
            audio_data: Base64 encoded audio data
            mime_type: Audio MIME type (audio/wav, audio/mp3, etc.)
            engagement_id: Engagement identifier for tracking
            consent_type: Type of consent (workshop, interview, meeting, general)
            options: Additional transcription options
            
        Returns:
            Dict containing transcription results or error
        """
        if not self.audio_enabled:
            raise ValueError("Audio transcription connector is disabled. Enable with MCP_CONNECTORS_AUDIO=true")
        
        corr_id = generate_correlation_id()
        
        payload = {
            "consent": True,
            "consent_type": consent_type,
            "audio_data": audio_data,
            "mime_type": mime_type,
            "options": options or {
                "language": "auto",
                "include_timestamps": True
            }
        }
        
        # Enable PII scrubbing if configured
        if self.pii_scrub_enabled:
            payload["pii_scrub"] = {"enabled": True}
        
        try:
            logger.info(
                "Starting audio transcription via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "consent_type": consent_type,
                    "mime_type": mime_type,
                    "corr_id": corr_id,
                    "pii_scrub_enabled": self.pii_scrub_enabled
                }
            )
            
            result = await self.mcp_client.call("audio.transcribe", payload, engagement_id)
            
            # Apply additional PII scrubbing if transcription succeeded and separate scrubbing enabled
            if result.get("success") and self.pii_scrub_enabled and not payload.get("pii_scrub", {}).get("enabled"):
                transcript_text = result.get("transcription", {}).get("text", "")
                if transcript_text:
                    scrub_result = await self.scrub_pii_content(transcript_text, engagement_id, "text")
                    if scrub_result.get("success"):
                        result["transcription"]["text"] = scrub_result["scrubbed_content"]
                        result["pii_scrubbing_applied"] = scrub_result["redaction_report"]
            
            logger.info(
                "Audio transcription completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "call_id": result.get("call_id"),
                    "text_length": len(result.get("transcription", {}).get("text", ""))
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Audio transcription failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise
    
    async def scrub_pii_content(self, content: Any, engagement_id: str, 
                              content_type: str = "text",
                              scrub_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scrub PII from content using MCP pii.scrub tool.
        
        Args:
            content: Content to scrub (string or structured data)
            engagement_id: Engagement identifier for tracking
            content_type: Type of content (text, json, structured)
            scrub_config: Custom scrubbing configuration
            
        Returns:
            Dict containing scrubbed content and redaction report
        """
        if not self.pii_scrub_enabled:
            logger.info("PII scrubbing disabled, returning original content")
            return {
                "success": True,
                "scrubbed_content": content,
                "redaction_report": {"total_redactions": 0},
                "pii_scrub_enabled": False
            }
        
        corr_id = generate_correlation_id()
        
        # Default scrub configuration
        default_config = {
            "enabled_patterns": [
                "email_address", "us_ssn", "us_ssn_spaces", "credit_card", 
                "phone_us", "phone_us_parentheses", "aws_access_key", 
                "github_token", "ip_address"
            ],
            "case_sensitive": False,
            "audit_redactions": True
        }
        
        payload = {
            "content": content,
            "content_type": content_type,
            "scrub_config": scrub_config or default_config
        }
        
        try:
            logger.info(
                "Starting PII scrubbing via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "content_type": content_type,
                    "corr_id": corr_id
                }
            )
            
            result = await self.mcp_client.call("pii.scrub", payload, engagement_id)
            
            logger.info(
                "PII scrubbing completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "total_redactions": result.get("redaction_report", {}).get("total_redactions", 0)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "PII scrubbing failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise
    
    async def generate_roadmap_pptx(self, roadmap_data: Dict[str, Any], 
                                  engagement_id: str,
                                  presentation_config: Optional[Dict[str, Any]] = None,
                                  output_format: str = "base64") -> Dict[str, Any]:
        """
        Generate executive roadmap PPTX using MCP pptx.render tool.
        
        Args:
            roadmap_data: Roadmap data with initiatives, priorities, timeline
            engagement_id: Engagement identifier for tracking  
            presentation_config: Custom presentation configuration
            output_format: Output format (base64 or file)
            
        Returns:
            Dict containing generated presentation data
        """
        if not self.pptx_enabled:
            raise ValueError("PPTX generation connector is disabled. Enable with MCP_CONNECTORS_PPTX=true")
        
        corr_id = generate_correlation_id()
        
        # Transform roadmap data into presentation structure
        presentation_data = self._build_presentation_from_roadmap(roadmap_data, presentation_config)
        
        payload = {
            "presentation": presentation_data,
            "output_format": output_format
        }
        
        try:
            logger.info(
                "Starting PPTX generation via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "output_format": output_format,
                    "slide_count": len(presentation_data.get("slides", []))
                }
            )
            
            result = await self.mcp_client.call("pptx.render", payload, engagement_id)
            
            logger.info(
                "PPTX generation completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "file_size_bytes": result.get("presentation", {}).get("size_bytes", 0)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "PPTX generation failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise
    
    def _build_presentation_from_roadmap(self, roadmap_data: Dict[str, Any], 
                                       config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform roadmap data into presentation structure.
        
        Args:
            roadmap_data: Raw roadmap data from analysis
            config: Custom presentation configuration
            
        Returns:
            Dict containing presentation data structure
        """
        config = config or {}
        
        # Extract key information from roadmap
        title = config.get("title", "Cyber Maturity Roadmap")
        subtitle = config.get("subtitle", f"Generated on {datetime.now().strftime('%B %d, %Y')}")
        
        # Build executive summary slide
        executive_summary = []
        if "current_maturity" in roadmap_data:
            executive_summary.append(f"Current maturity level: {roadmap_data['current_maturity']}")
        if "target_maturity" in roadmap_data:
            executive_summary.append(f"Target maturity level: {roadmap_data['target_maturity']}")
        if "initiative_count" in roadmap_data:
            executive_summary.append(f"Total initiatives: {roadmap_data['initiative_count']}")
        if "investment_required" in roadmap_data:
            executive_summary.append(f"Investment required: {roadmap_data['investment_required']}")
        
        slides = [
            {
                "type": "content",
                "title": "Executive Summary",
                "content": executive_summary
            }
        ]
        
        # Add priority initiatives slide if available
        if "initiatives" in roadmap_data:
            initiatives = roadmap_data["initiatives"]
            high_priority = [init["title"] for init in initiatives if init.get("priority", "medium") == "high"]
            medium_priority = [init["title"] for init in initiatives if init.get("priority", "medium") == "medium"]
            
            if high_priority or medium_priority:
                slides.append({
                    "type": "two_content",
                    "title": "Priority Initiatives",
                    "left_content": ["High Priority:"] + [f"• {item}" for item in high_priority[:5]],
                    "right_content": ["Medium Priority:"] + [f"• {item}" for item in medium_priority[:5]]
                })
        
        # Add timeline slide if available
        if "timeline" in roadmap_data:
            timeline_items = []
            for quarter, activities in roadmap_data["timeline"].items():
                if activities:
                    timeline_items.append(f"{quarter}: {', '.join(activities[:3])}")
            
            if timeline_items:
                slides.append({
                    "type": "content",
                    "title": "Implementation Timeline",
                    "content": timeline_items
                })
        
        # Build citations from sources
        citations = []
        if "sources" in roadmap_data:
            for source in roadmap_data["sources"]:
                citations.append({
                    "title": source.get("title", "Untitled"),
                    "source": source.get("author", "Unknown"),
                    "date": source.get("date", "")
                })
        
        # Add default citations if none provided
        if not citations:
            citations = [
                {
                    "title": "NIST Cybersecurity Framework 2.0",
                    "source": "NIST",
                    "date": "2024"
                },
                {
                    "title": "AI-Enabled Cyber Maturity Assessment",
                    "source": "Internal Analysis",
                    "date": datetime.now().strftime("%Y")
                }
            ]
        
        return {
            "title": title,
            "subtitle": subtitle,
            "author": config.get("author", "AI Cyber Maturity Assessment"),
            "slides": slides,
            "citations": citations,
            "branding": config.get("branding", {
                "colors": {
                    "primary": (0, 102, 204),  # Professional blue
                    "secondary": (102, 102, 102),  # Gray
                    "accent": (255, 102, 0)  # Orange
                }
            }),
            "template": config.get("template", "executive")
        }
    
    async def process_workshop_minutes_to_maturity(self, minutes_text: str, 
                                                 engagement_id: str) -> Dict[str, Any]:
        """
        Process workshop minutes to pre-populate maturity assessment data.
        
        Args:
            minutes_text: Workshop minutes text content
            engagement_id: Engagement identifier for tracking
            
        Returns:
            Dict containing extracted maturity assessment data
        """
        corr_id = generate_correlation_id()
        
        # First, scrub PII from minutes if enabled
        if self.pii_scrub_enabled:
            try:
                scrub_result = await self.scrub_pii_content(
                    minutes_text, engagement_id, "text"
                )
                if scrub_result.get("success"):
                    minutes_text = scrub_result["scrubbed_content"]
                    logger.info(
                        "Applied PII scrubbing to workshop minutes",
                        extra={
                            "engagement_id": engagement_id,
                            "redactions": scrub_result.get("redaction_report", {}).get("total_redactions", 0)
                        }
                    )
            except Exception as e:
                logger.warning(f"PII scrubbing failed for minutes: {e}")
        
        # Extract maturity-related information (simplified implementation)
        # In a full implementation, this would use NLP/LLM analysis
        maturity_data = {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "source": "workshop_minutes",
            "engagement_id": engagement_id,
            "correlation_id": corr_id,
            "content_length": len(minutes_text),
            "suggested_assessments": self._extract_assessment_suggestions(minutes_text),
            "identified_gaps": self._extract_gaps_from_minutes(minutes_text),
            "stakeholder_concerns": self._extract_concerns_from_minutes(minutes_text)
        }
        
        logger.info(
            "Workshop minutes processed for maturity pre-population",
            extra={
                "engagement_id": engagement_id,
                "corr_id": corr_id,
                "suggestions_count": len(maturity_data["suggested_assessments"]),
                "gaps_count": len(maturity_data["identified_gaps"])
            }
        )
        
        return {
            "success": True,
            "maturity_data": maturity_data,
            "processing_metadata": {
                "pii_scrubbed": self.pii_scrub_enabled,
                "processing_time": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _extract_assessment_suggestions(self, text: str) -> List[Dict[str, Any]]:
        """Extract assessment suggestions from minutes text."""
        # Simplified keyword-based extraction
        suggestions = []
        
        security_keywords = {
            "identity": ["identity", "authentication", "access", "IAM"],
            "incident": ["incident", "response", "breach", "emergency"],
            "vulnerability": ["vulnerability", "patch", "scanning", "assessment"],
            "training": ["training", "awareness", "education", "phishing"],
            "compliance": ["compliance", "audit", "regulation", "policy"]
        }
        
        text_lower = text.lower()
        
        for category, keywords in security_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    suggestions.append({
                        "category": category,
                        "keyword": keyword,
                        "priority": "medium",
                        "extracted_from": "workshop_minutes"
                    })
                    break  # Only add one per category
        
        return suggestions[:5]  # Limit to top 5
    
    def _extract_gaps_from_minutes(self, text: str) -> List[Dict[str, str]]:
        """Extract security gaps mentioned in minutes."""
        gaps = []
        
        gap_indicators = [
            "lacking", "missing", "insufficient", "weak", "needs improvement",
            "gap", "deficiency", "vulnerability", "concern"
        ]
        
        text_lower = text.lower()
        
        for indicator in gap_indicators:
            if indicator in text_lower:
                gaps.append({
                    "indicator": indicator,
                    "context": "mentioned in workshop discussion",
                    "priority": "review_required"
                })
        
        return gaps[:3]  # Limit to top 3
    
    def _extract_concerns_from_minutes(self, text: str) -> List[Dict[str, str]]:
        """Extract stakeholder concerns from minutes."""
        concerns = []
        
        concern_keywords = [
            "worried", "concerned", "risk", "threat", "challenge",
            "issue", "problem", "difficulty"
        ]
        
        text_lower = text.lower()
        
        for keyword in concern_keywords:
            if keyword in text_lower:
                concerns.append({
                    "type": keyword,
                    "source": "stakeholder_discussion",
                    "requires_attention": True
                })
        
        return concerns[:3]  # Limit to top 3


# Factory function for creating MCP connectors
def create_mcp_connectors(mcp_client: IMcpClient) -> MCPConnectors:
    """Create MCP connectors instance with the provided client."""
    return MCPConnectors(mcp_client)
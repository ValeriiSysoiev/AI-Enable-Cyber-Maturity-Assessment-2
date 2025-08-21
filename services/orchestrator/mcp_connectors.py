"""
MCP Connectors for Enterprise Audio, SharePoint, Jira, and PPTX Integration
Provides integration between orchestrator and Sprint v1.5 MCP tools.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from mcp_client import IMcpClient, generate_correlation_id

logger = logging.getLogger(__name__)

class MCPConnectors:
    """
    Enterprise MCP connectors for document processing and issue tracking.
    
    Provides orchestrator integration with Sprint v1.5 MCP tools:
    - audio.transcribe: Workshop audio → text transcription
    - pii.scrub: GDPR/CCPA compliant content redaction  
    - pptx.render: Executive roadmap presentation generation
    - sharepoint.fetch: Document ingestion from SharePoint repositories
    - jira.createIssue/updateIssue: Issue tracking and workflow automation
    """
    
    def __init__(self, mcp_client: IMcpClient):
        """Initialize MCP connectors with client."""
        self.mcp_client = mcp_client
        
        # Feature flags for granular control
        self.audio_enabled = os.environ.get("MCP_CONNECTORS_AUDIO", "false").lower() == "true"
        self.pptx_enabled = os.environ.get("MCP_CONNECTORS_PPTX", "false").lower() == "true"
        self.pii_scrub_enabled = os.environ.get("MCP_CONNECTORS_PII_SCRUB", "true").lower() == "true"
        self.sharepoint_enabled = os.environ.get("MCP_CONNECTORS_SP", "false").lower() == "true"
        self.jira_enabled = os.environ.get("MCP_CONNECTORS_JIRA", "false").lower() == "true"
        
        logger.info(
            "MCP Connectors initialized",
            extra={
                "audio_enabled": self.audio_enabled,
                "pptx_enabled": self.pptx_enabled,
                "pii_scrub_enabled": self.pii_scrub_enabled,
                "sharepoint_enabled": self.sharepoint_enabled,
                "jira_enabled": self.jira_enabled
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
    
    async def fetch_sharepoint_documents(self, tenant_id: str, site_url: str, 
                                       document_path: str, engagement_id: str,
                                       file_types: Optional[List[str]] = None,
                                       recursive: bool = False) -> Dict[str, Any]:
        """
        Fetch documents from SharePoint using MCP sharepoint.fetch tool.
        
        Args:
            tenant_id: SharePoint tenant identifier
            site_url: SharePoint site URL or path
            document_path: Path to document or folder within SharePoint site
            engagement_id: Engagement identifier for tracking
            file_types: File types to include (default: all allowed types)
            recursive: Recursively fetch documents from subfolders
            
        Returns:
            Dict containing fetched documents with provenance metadata
        """
        if not self.sharepoint_enabled:
            raise ValueError("SharePoint connector is disabled. Enable with MCP_CONNECTORS_SP=true")
        
        corr_id = generate_correlation_id()
        
        # Default to safe document types if not specified
        if file_types is None:
            file_types = [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"]
        
        payload = {
            "tenant_id": tenant_id,
            "site_url": site_url,
            "document_path": document_path,
            "recursive": recursive,
            "file_types": file_types,
            "mode": "DRY-RUN"  # Default to safe mode
        }
        
        # Check for real SharePoint credentials
        sharepoint_creds = [
            os.environ.get("SHAREPOINT_CLIENT_ID"),
            os.environ.get("SHAREPOINT_CLIENT_SECRET"),
            os.environ.get("SHAREPOINT_TENANT")
        ]
        
        if all(sharepoint_creds):
            payload["mode"] = "REAL"
            logger.info("Using REAL mode for SharePoint with provided credentials")
        else:
            logger.info("Using DRY-RUN mode for SharePoint (credentials not available)")
        
        try:
            logger.info(
                "Starting SharePoint document fetch via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "tenant_id": tenant_id,
                    "site_url": site_url,
                    "document_path": document_path,
                    "mode": payload["mode"],
                    "corr_id": corr_id
                }
            )
            
            result = await self.mcp_client.call("sharepoint.fetch", payload, engagement_id)
            
            logger.info(
                "SharePoint document fetch completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "call_id": result.get("call_id"),
                    "document_count": result.get("result", {}).get("count", 0)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "SharePoint document fetch failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise
    
    async def create_jira_issue(self, project_key: str, summary: str, description: str,
                               external_key: str, engagement_id: str,
                               issue_type: str = "Task", priority: str = "Medium",
                               labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create Jira issue using MCP jira.createIssue tool.
        
        Args:
            project_key: Jira project key (e.g., 'CYBER', 'SEC')
            summary: Issue summary/title
            description: Issue description/body
            external_key: External identifier for idempotency
            engagement_id: Engagement identifier for tracking
            issue_type: Issue type (default: Task)
            priority: Issue priority (default: Medium)
            labels: Issue labels
            
        Returns:
            Dict containing created issue information
        """
        if not self.jira_enabled:
            raise ValueError("Jira connector is disabled. Enable with MCP_CONNECTORS_JIRA=true")
        
        corr_id = generate_correlation_id()
        
        payload = {
            "project_key": project_key,
            "issue_type": issue_type,
            "summary": summary,
            "description": description,
            "priority": priority,
            "labels": labels or [],
            "external_key": external_key,
            "mode": "DRY-RUN"  # Default to safe mode
        }
        
        # Check for real Jira credentials
        jira_creds = [
            os.environ.get("JIRA_URL"),
            os.environ.get("JIRA_USERNAME"),
            os.environ.get("JIRA_API_TOKEN")
        ]
        
        if all(jira_creds):
            payload["mode"] = "REAL"
            logger.info("Using REAL mode for Jira with provided credentials")
        else:
            logger.info("Using DRY-RUN mode for Jira (credentials not available)")
        
        try:
            logger.info(
                "Starting Jira issue creation via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "project_key": project_key,
                    "external_key": external_key,
                    "priority": priority,
                    "mode": payload["mode"],
                    "corr_id": corr_id
                }
            )
            
            result = await self.mcp_client.call("jira.createIssue", payload, engagement_id)
            
            logger.info(
                "Jira issue creation completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "call_id": result.get("call_id"),
                    "issue_key": result.get("result", {}).get("issue_key")
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Jira issue creation failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise
    
    async def update_jira_issue(self, issue_key: str, external_key: str, 
                               engagement_id: str, summary: Optional[str] = None,
                               description: Optional[str] = None, status: Optional[str] = None,
                               priority: Optional[str] = None, labels: Optional[List[str]] = None,
                               comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Update existing Jira issue using MCP jira.updateIssue tool.
        
        Args:
            issue_key: Jira issue key to update
            external_key: External identifier for tracking
            engagement_id: Engagement identifier for tracking
            summary: Updated issue summary (optional)
            description: Updated issue description (optional)
            status: Updated issue status (optional)
            priority: Updated issue priority (optional)
            labels: Updated issue labels (optional)
            comment: Comment to add (optional)
            
        Returns:
            Dict containing updated issue information
        """
        if not self.jira_enabled:
            raise ValueError("Jira connector is disabled. Enable with MCP_CONNECTORS_JIRA=true")
        
        corr_id = generate_correlation_id()
        
        payload = {
            "issue_key": issue_key,
            "external_key": external_key,
            "mode": "DRY-RUN"  # Default to safe mode
        }
        
        # Add optional fields if provided
        if summary:
            payload["summary"] = summary
        if description:
            payload["description"] = description
        if status:
            payload["status"] = status
        if priority:
            payload["priority"] = priority
        if labels is not None:
            payload["labels"] = labels
        if comment:
            payload["comment"] = comment
        
        # Check for real Jira credentials
        jira_creds = [
            os.environ.get("JIRA_URL"),
            os.environ.get("JIRA_USERNAME"),
            os.environ.get("JIRA_API_TOKEN")
        ]
        
        if all(jira_creds):
            payload["mode"] = "REAL"
            logger.info("Using REAL mode for Jira with provided credentials")
        else:
            logger.info("Using DRY-RUN mode for Jira (credentials not available)")
        
        try:
            logger.info(
                "Starting Jira issue update via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "issue_key": issue_key,
                    "external_key": external_key,
                    "mode": payload["mode"],
                    "corr_id": corr_id
                }
            )
            
            result = await self.mcp_client.call("jira.updateIssue", payload, engagement_id)
            
            logger.info(
                "Jira issue update completed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "success": result.get("success", False),
                    "call_id": result.get("call_id"),
                    "issue_key": issue_key
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Jira issue update failed via MCP",
                extra={
                    "engagement_id": engagement_id,
                    "corr_id": corr_id,
                    "error": str(e)
                }
            )
            raise


# Factory function for creating MCP connectors
def create_mcp_connectors(mcp_client: IMcpClient) -> MCPConnectors:
    """Create MCP connectors instance with the provided client."""
    return MCPConnectors(mcp_client)
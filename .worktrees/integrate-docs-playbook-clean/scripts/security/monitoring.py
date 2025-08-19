#!/usr/bin/env python3
"""
Security Monitoring and Alerting System

Integrates with Azure Application Insights and other monitoring systems
to provide comprehensive security event collection, analysis, and alerting.

Features:
- Real-time security event monitoring
- Threat detection and analysis
- Security metrics and dashboards
- Automated incident response
- Integration with existing observability stack
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import requests
import hashlib
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION_FAILURE = "auth_failure"
    SUSPICIOUS_ACCESS = "suspicious_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    UNAUTHORIZED_API_ACCESS = "unauthorized_api_access"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    UNUSUAL_ACTIVITY = "unusual_activity"
    MALWARE_DETECTED = "malware_detected"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CONFIGURATION_CHANGE = "config_change"

class SeverityLevel(Enum):
    """Security event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_id: str
    event_type: SecurityEventType
    severity: SeverityLevel
    timestamp: str
    source_ip: str
    user_id: Optional[str]
    endpoint: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]
    risk_score: int  # 0-100
    remediation_actions: List[str]
    
class SecurityMetrics:
    """Security metrics tracking."""
    
    def __init__(self):
        self.total_events = 0
        self.events_by_type = {}
        self.events_by_severity = {}
        self.risk_trends = []
        self.blocked_attacks = 0
        self.false_positives = 0

class SecurityMonitor:
    """Main security monitoring system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app_insights_key = config.get('app_insights_key')
        self.app_insights_endpoint = config.get('app_insights_endpoint')
        self.slack_webhook = config.get('slack_webhook')
        self.email_alerts = config.get('email_alerts', [])
        self.metrics = SecurityMetrics()
        
        # Threat intelligence feeds
        self.threat_feeds = config.get('threat_feeds', [])
        self.malicious_ips = set()
        self.known_attack_patterns = []
        
        # Load threat intelligence
        self._load_threat_intelligence()

    def _load_threat_intelligence(self) -> None:
        """Load threat intelligence data."""
        try:
            # Load known malicious IPs (example sources)
            malicious_ip_sources = [
                "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt",
                # Add more threat intelligence sources
            ]
            
            for source in malicious_ip_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        ips = [line.strip() for line in response.text.split('\n') 
                              if line.strip() and not line.startswith('#')]
                        self.malicious_ips.update(ips[:1000])  # Limit to prevent memory issues
                except Exception as e:
                    logger.warning(f"Failed to load threat intelligence from {source}: {e}")
                    
            logger.info(f"Loaded {len(self.malicious_ips)} malicious IPs")
            
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {e}")

    def analyze_request(self, request_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Analyze incoming request for security threats."""
        try:
            # Extract request information
            source_ip = request_data.get('source_ip', '')
            endpoint = request_data.get('endpoint', '')
            user_agent = request_data.get('user_agent', '')
            payload = request_data.get('payload', '')
            headers = request_data.get('headers', {})
            user_id = request_data.get('user_id')
            
            # Perform various security checks
            threat_level = 0
            detected_threats = []
            
            # 1. Check against known malicious IPs
            if source_ip in self.malicious_ips:
                threat_level += 50
                detected_threats.append("Known malicious IP")
            
            # 2. SQL Injection detection
            sql_patterns = [
                r"union\s+select", r"drop\s+table", r"insert\s+into",
                r"delete\s+from", r"update\s+set", r"exec\s*\(",
                r"'.*or.*1=1", r"'.*or.*'.*=.*'"
            ]
            
            if self._check_patterns(payload, sql_patterns):
                threat_level += 40
                detected_threats.append("SQL injection attempt")
                
            # 3. XSS detection
            xss_patterns = [
                r"<script.*?>.*?</script>", r"javascript:", r"onload=",
                r"onerror=", r"alert\s*\(", r"document\.cookie"
            ]
            
            if self._check_patterns(payload, xss_patterns):
                threat_level += 35
                detected_threats.append("XSS attempt")
                
            # 4. Path traversal detection
            if '../' in payload or '..\\' in payload:
                threat_level += 30
                detected_threats.append("Path traversal attempt")
                
            # 5. Command injection detection
            cmd_patterns = [
                r";\s*cat\s+", r";\s*ls\s+", r";\s*rm\s+",
                r"&&\s*cat", r"\|\s*cat", r"`.*`"
            ]
            
            if self._check_patterns(payload, cmd_patterns):
                threat_level += 45
                detected_threats.append("Command injection attempt")
                
            # 6. Suspicious user agent
            suspicious_ua_patterns = [
                "sqlmap", "nikto", "nmap", "burp", "owasp zap",
                "python-requests", "curl", "wget"
            ]
            
            if self._check_patterns(user_agent.lower(), suspicious_ua_patterns):
                threat_level += 20
                detected_threats.append("Suspicious user agent")
                
            # 7. Rate limiting check
            if self._check_rate_limit(source_ip):
                threat_level += 25
                detected_threats.append("Rate limit exceeded")
                
            # 8. Unusual endpoint access patterns
            if self._check_unusual_access_pattern(source_ip, endpoint, user_id):
                threat_level += 15
                detected_threats.append("Unusual access pattern")
                
            # Determine if this constitutes a security event
            if threat_level >= 30 or detected_threats:
                severity = self._calculate_severity(threat_level)
                event_type = self._determine_event_type(detected_threats)
                
                event = SecurityEvent(
                    event_id=self._generate_event_id(request_data),
                    event_type=event_type,
                    severity=severity,
                    timestamp=datetime.now().isoformat(),
                    source_ip=source_ip,
                    user_id=user_id,
                    endpoint=endpoint,
                    user_agent=user_agent,
                    details={
                        'threats_detected': detected_threats,
                        'threat_level': threat_level,
                        'payload_sample': payload[:500] if payload else '',
                        'headers': headers
                    },
                    risk_score=min(threat_level, 100),
                    remediation_actions=self._suggest_remediation(detected_threats, threat_level)
                )
                
                return event
                
        except Exception as e:
            logger.error(f"Error analyzing request: {e}")
            
        return None

    def _check_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns."""
        import re
        text_lower = text.lower()
        
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def _check_rate_limit(self, source_ip: str) -> bool:
        """Check if source IP has exceeded rate limits."""
        # This would integrate with your rate limiting system
        # For now, return a simple heuristic
        return False  # Implement based on your rate limiting logic

    def _check_unusual_access_pattern(self, source_ip: str, endpoint: str, user_id: Optional[str]) -> bool:
        """Check for unusual access patterns."""
        # This would analyze historical access patterns
        # Implementation depends on your analytics backend
        return False  # Implement based on your access analytics

    def _calculate_severity(self, threat_level: int) -> SeverityLevel:
        """Calculate severity based on threat level."""
        if threat_level >= 80:
            return SeverityLevel.CRITICAL
        elif threat_level >= 60:
            return SeverityLevel.HIGH
        elif threat_level >= 40:
            return SeverityLevel.MEDIUM
        elif threat_level >= 20:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO

    def _determine_event_type(self, detected_threats: List[str]) -> SecurityEventType:
        """Determine event type based on detected threats."""
        threat_text = ' '.join(detected_threats).lower()
        
        if 'sql injection' in threat_text:
            return SecurityEventType.SQL_INJECTION_ATTEMPT
        elif 'xss' in threat_text:
            return SecurityEventType.XSS_ATTEMPT
        elif 'rate limit' in threat_text:
            return SecurityEventType.RATE_LIMIT_EXCEEDED
        elif 'malicious ip' in threat_text:
            return SecurityEventType.SUSPICIOUS_ACCESS
        else:
            return SecurityEventType.UNUSUAL_ACTIVITY

    def _suggest_remediation(self, detected_threats: List[str], threat_level: int) -> List[str]:
        """Suggest remediation actions based on detected threats."""
        actions = []
        
        if threat_level >= 80:
            actions.append("Block source IP immediately")
            actions.append("Notify security team")
            actions.append("Review system logs")
            
        if 'sql injection' in ' '.join(detected_threats).lower():
            actions.append("Review database query parameters")
            actions.append("Enable SQL injection protection")
            
        if 'xss' in ' '.join(detected_threats).lower():
            actions.append("Review input sanitization")
            actions.append("Update Content Security Policy")
            
        if 'rate limit' in ' '.join(detected_threats).lower():
            actions.append("Implement stricter rate limiting")
            actions.append("Consider CAPTCHA for repeated requests")
            
        if not actions:
            actions.append("Monitor for additional suspicious activity")
            
        return actions

    def _generate_event_id(self, request_data: Dict[str, Any]) -> str:
        """Generate unique event ID."""
        data_str = json.dumps(request_data, sort_keys=True)
        timestamp = str(int(time.time()))
        return hashlib.sha256(f"{data_str}{timestamp}".encode()).hexdigest()[:16]

    def process_security_event(self, event: SecurityEvent) -> None:
        """Process and handle a security event."""
        try:
            # Update metrics
            self._update_metrics(event)
            
            # Log to Application Insights
            self._log_to_app_insights(event)
            
            # Send alerts if necessary
            if event.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                self._send_alerts(event)
                
            # Store for analysis
            self._store_event(event)
            
            # Take automated response actions
            self._automated_response(event)
            
            logger.info(f"Processed security event {event.event_id} - {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to process security event: {e}")

    def _update_metrics(self, event: SecurityEvent) -> None:
        """Update security metrics."""
        self.metrics.total_events += 1
        
        event_type = event.event_type.value
        if event_type not in self.metrics.events_by_type:
            self.metrics.events_by_type[event_type] = 0
        self.metrics.events_by_type[event_type] += 1
        
        severity = event.severity.value
        if severity not in self.metrics.events_by_severity:
            self.metrics.events_by_severity[severity] = 0
        self.metrics.events_by_severity[severity] += 1
        
        # Track risk trends
        self.metrics.risk_trends.append({
            'timestamp': event.timestamp,
            'risk_score': event.risk_score
        })
        
        # Keep only last 24 hours of trends
        cutoff = datetime.now() - timedelta(hours=24)
        self.metrics.risk_trends = [
            trend for trend in self.metrics.risk_trends
            if datetime.fromisoformat(trend['timestamp']) > cutoff
        ]

    def _log_to_app_insights(self, event: SecurityEvent) -> None:
        """Log security event to Azure Application Insights."""
        if not self.app_insights_key:
            return
            
        try:
            # Prepare telemetry data
            telemetry_data = {
                'name': 'SecurityEvent',
                'time': event.timestamp,
                'data': {
                    'baseType': 'EventData',
                    'baseData': {
                        'name': 'SecurityEvent',
                        'properties': {
                            'eventId': event.event_id,
                            'eventType': event.event_type.value,
                            'severity': event.severity.value,
                            'sourceIp': event.source_ip,
                            'userId': event.user_id or 'anonymous',
                            'endpoint': event.endpoint or 'unknown',
                            'userAgent': event.user_agent or 'unknown',
                            'riskScore': str(event.risk_score),
                            'threatsDetected': json.dumps(event.details.get('threats_detected', [])),
                            'remediationActions': json.dumps(event.remediation_actions)
                        },
                        'measurements': {
                            'threatLevel': event.details.get('threat_level', 0),
                            'riskScore': event.risk_score
                        }
                    }
                }
            }
            
            # Send to Application Insights
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"https://dc.services.visualstudio.com/v2/track",
                headers=headers,
                json=telemetry_data,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to send to Application Insights: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to log to Application Insights: {e}")

    def _send_alerts(self, event: SecurityEvent) -> None:
        """Send alerts for high-priority security events."""
        try:
            # Prepare alert message
            alert_message = self._format_alert_message(event)
            
            # Send Slack notification
            if self.slack_webhook:
                self._send_slack_alert(alert_message, event)
                
            # Send email notifications
            if self.email_alerts:
                self._send_email_alerts(alert_message, event)
                
        except Exception as e:
            logger.error(f"Failed to send alerts: {e}")

    def _format_alert_message(self, event: SecurityEvent) -> str:
        """Format alert message for notifications."""
        return f"""
🚨 **Security Alert - {event.severity.value.upper()}**

**Event ID:** {event.event_id}
**Type:** {event.event_type.value}
**Time:** {event.timestamp}
**Risk Score:** {event.risk_score}/100

**Source IP:** {event.source_ip}
**User:** {event.user_id or 'Anonymous'}
**Endpoint:** {event.endpoint or 'Unknown'}

**Threats Detected:**
{chr(10).join(f"• {threat}" for threat in event.details.get('threats_detected', []))}

**Recommended Actions:**
{chr(10).join(f"• {action}" for action in event.remediation_actions)}

**Details:** {json.dumps(event.details, indent=2)}
        """.strip()

    def _send_slack_alert(self, message: str, event: SecurityEvent) -> None:
        """Send Slack alert."""
        try:
            color = {
                SeverityLevel.CRITICAL: "danger",
                SeverityLevel.HIGH: "warning", 
                SeverityLevel.MEDIUM: "#ff9500",
                SeverityLevel.LOW: "good",
                SeverityLevel.INFO: "#36a64f"
            }.get(event.severity, "warning")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"Security Alert - {event.event_type.value}",
                    "text": message,
                    "footer": "Security Monitoring System",
                    "ts": int(time.time())
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Slack notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _send_email_alerts(self, message: str, event: SecurityEvent) -> None:
        """Send email alerts."""
        # Implementation depends on your email service
        # This is a placeholder for email notification logic
        logger.info(f"Email alert would be sent to {self.email_alerts} for event {event.event_id}")

    def _store_event(self, event: SecurityEvent) -> None:
        """Store security event for analysis."""
        # This would store events in your preferred database
        # For now, just log to file
        try:
            log_entry = {
                'timestamp': event.timestamp,
                'event': asdict(event)
            }
            
            log_file = f"security_events_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

    def _automated_response(self, event: SecurityEvent) -> None:
        """Take automated response actions."""
        try:
            # Block critical threats automatically
            if event.severity == SeverityLevel.CRITICAL:
                if event.source_ip and event.source_ip not in ['127.0.0.1', 'localhost']:
                    # Add to IP blocklist (implementation depends on your infrastructure)
                    logger.info(f"Would block IP {event.source_ip} due to critical threat")
                    
            # Rate limit on repeated suspicious activity
            if event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
                logger.info(f"Would increase rate limiting for IP {event.source_ip}")
                
        except Exception as e:
            logger.error(f"Failed to execute automated response: {e}")

    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """Get data for security dashboard."""
        return {
            'summary': {
                'total_events': self.metrics.total_events,
                'events_by_type': self.metrics.events_by_type,
                'events_by_severity': self.metrics.events_by_severity,
                'blocked_attacks': self.metrics.blocked_attacks,
                'false_positives': self.metrics.false_positives
            },
            'risk_trends': self.metrics.risk_trends[-100:],  # Last 100 data points
            'threat_intelligence': {
                'malicious_ips_count': len(self.malicious_ips),
                'last_updated': datetime.now().isoformat()
            }
        }

def load_config() -> Dict[str, Any]:
    """Load monitoring configuration."""
    return {
        'app_insights_key': os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'),
        'app_insights_endpoint': os.getenv('APPLICATIONINSIGHTS_ENDPOINT'),
        'slack_webhook': os.getenv('SLACK_WEBHOOK_URL'),
        'email_alerts': os.getenv('SECURITY_EMAIL_ALERTS', '').split(','),
        'threat_feeds': [
            # Add threat intelligence feed URLs
        ]
    }

def main():
    """Main entry point for security monitoring."""
    try:
        config = load_config()
        monitor = SecurityMonitor(config)
        
        # Example: Process a sample request
        sample_request = {
            'source_ip': '192.168.1.100',
            'endpoint': '/api/users',
            'user_agent': 'Mozilla/5.0',
            'payload': 'user_id=1',
            'headers': {'Content-Type': 'application/json'},
            'user_id': 'user123'
        }
        
        event = monitor.analyze_request(sample_request)
        if event:
            monitor.process_security_event(event)
            
        # Get dashboard data
        dashboard_data = monitor.get_security_dashboard_data()
        print(json.dumps(dashboard_data, indent=2))
        
    except Exception as e:
        logger.error(f"Security monitoring failed: {e}")

if __name__ == '__main__':
    main()
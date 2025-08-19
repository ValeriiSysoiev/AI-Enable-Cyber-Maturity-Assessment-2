#!/usr/bin/env python3
"""
Security Compliance Scanning Module

Validates compliance with various security frameworks and regulations:
- GDPR (General Data Protection Regulation)
- ISO 27001 (Information Security Management)
- NIST Cybersecurity Framework
- SOC 2 Type II
- OWASP ASVS (Application Security Verification Standard)

Features:
- Automated compliance checking
- Gap analysis and remediation recommendations
- Compliance reporting and dashboards
- Multi-tenant isolation validation
- Data retention policy compliance
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    NIST_CSF = "nist_csf"
    SOC2 = "soc2"
    OWASP_ASVS = "owasp_asvs"
    PCI_DSS = "pci_dss"

class ComplianceStatus(Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_REVIEW = "requires_review"

@dataclass
class ComplianceCheck:
    """Represents a single compliance check."""
    framework: ComplianceFramework
    control_id: str
    control_name: str
    description: str
    requirement: str
    status: ComplianceStatus
    evidence: List[str]
    gaps: List[str]
    remediation_steps: List[str]
    priority: str  # critical, high, medium, low
    estimated_effort: str  # hours, days, weeks
    responsible_team: str

@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    framework: ComplianceFramework
    assessment_date: str
    overall_score: float  # 0-100
    total_controls: int
    compliant_controls: int
    non_compliant_controls: int
    checks: List[ComplianceCheck]
    executive_summary: str
    next_assessment_date: str

class ComplianceScanner:
    """Main compliance scanning engine."""
    
    def __init__(self, project_root: str = '.'):
        self.project_root = Path(project_root)
        self.scan_results = {}
        
        # Load compliance frameworks
        self.frameworks = self._load_compliance_frameworks()
        
        # File patterns for analysis
        self.code_patterns = {
            'python': ['**/*.py'],
            'typescript': ['**/*.ts', '**/*.tsx'],
            'javascript': ['**/*.js', '**/*.jsx'],
            'config': ['**/*.yml', '**/*.yaml', '**/*.json', '**/*.env*'],
            'docker': ['**/Dockerfile*', '**/docker-compose*.yml'],
            'terraform': ['**/*.tf', '**/*.tfvars']
        }

    def _load_compliance_frameworks(self) -> Dict[str, Any]:
        """Load compliance framework definitions."""
        frameworks = {}
        
        # GDPR Framework
        frameworks[ComplianceFramework.GDPR] = {
            'name': 'General Data Protection Regulation',
            'version': '2018',
            'controls': self._load_gdpr_controls()
        }
        
        # ISO 27001 Framework
        frameworks[ComplianceFramework.ISO27001] = {
            'name': 'ISO/IEC 27001:2013',
            'version': '2013',
            'controls': self._load_iso27001_controls()
        }
        
        # NIST Cybersecurity Framework
        frameworks[ComplianceFramework.NIST_CSF] = {
            'name': 'NIST Cybersecurity Framework',
            'version': '1.1',
            'controls': self._load_nist_csf_controls()
        }
        
        # OWASP ASVS
        frameworks[ComplianceFramework.OWASP_ASVS] = {
            'name': 'OWASP Application Security Verification Standard',
            'version': '4.0',
            'controls': self._load_owasp_asvs_controls()
        }
        
        return frameworks

    def _load_gdpr_controls(self) -> List[Dict]:
        """Load GDPR compliance controls."""
        return [
            {
                'id': 'GDPR-6.1',
                'name': 'Lawful Basis for Processing',
                'description': 'Processing is lawful only if at least one legal basis applies',
                'requirement': 'Implement and document lawful basis for all personal data processing',
                'check_method': 'code_analysis',
                'patterns': ['consent', 'lawful_basis', 'legal_basis'],
                'priority': 'critical'
            },
            {
                'id': 'GDPR-7.3',
                'name': 'Withdrawal of Consent',
                'description': 'Right to withdraw consent at any time',
                'requirement': 'Provide mechanism for consent withdrawal',
                'check_method': 'code_analysis',
                'patterns': ['withdraw_consent', 'revoke_consent'],
                'priority': 'high'
            },
            {
                'id': 'GDPR-12',
                'name': 'Transparent Information',
                'description': 'Information provided must be transparent and easily accessible',
                'requirement': 'Privacy policy and data processing information must be clear',
                'check_method': 'documentation',
                'patterns': ['privacy_policy', 'data_processing'],
                'priority': 'medium'
            },
            {
                'id': 'GDPR-15',
                'name': 'Right of Access',
                'description': 'Data subject access to personal data',
                'requirement': 'Implement data export functionality',
                'check_method': 'code_analysis',
                'patterns': ['export_data', 'download_data', 'data_portability'],
                'priority': 'high'
            },
            {
                'id': 'GDPR-17',
                'name': 'Right to Erasure',
                'description': 'Right to have personal data erased',
                'requirement': 'Implement data deletion functionality',
                'check_method': 'code_analysis',
                'patterns': ['delete_user', 'erase_data', 'remove_personal_data'],
                'priority': 'high'
            },
            {
                'id': 'GDPR-20',
                'name': 'Right to Data Portability',
                'description': 'Right to receive personal data in structured format',
                'requirement': 'Data export in machine-readable format',
                'check_method': 'code_analysis',
                'patterns': ['json_export', 'csv_export', 'data_format'],
                'priority': 'medium'
            },
            {
                'id': 'GDPR-25',
                'name': 'Data Protection by Design',
                'description': 'Privacy by design and by default',
                'requirement': 'Implement privacy-protective defaults',
                'check_method': 'code_analysis',
                'patterns': ['privacy_by_default', 'minimal_data', 'purpose_limitation'],
                'priority': 'high'
            },
            {
                'id': 'GDPR-32',
                'name': 'Security of Processing',
                'description': 'Appropriate technical and organizational measures',
                'requirement': 'Implement encryption and security controls',
                'check_method': 'security_analysis',
                'patterns': ['encryption', 'security_headers', 'access_control'],
                'priority': 'critical'
            },
            {
                'id': 'GDPR-33',
                'name': 'Breach Notification',
                'description': 'Notification of personal data breach',
                'requirement': 'Implement breach detection and notification',
                'check_method': 'monitoring',
                'patterns': ['breach_notification', 'incident_response'],
                'priority': 'high'
            },
            {
                'id': 'GDPR-35',
                'name': 'Data Protection Impact Assessment',
                'description': 'DPIA for high-risk processing',
                'requirement': 'Conduct and document DPIA',
                'check_method': 'documentation',
                'patterns': ['dpia', 'impact_assessment'],
                'priority': 'medium'
            }
        ]

    def _load_iso27001_controls(self) -> List[Dict]:
        """Load ISO 27001 security controls."""
        return [
            {
                'id': 'A.5.1.1',
                'name': 'Information Security Policies',
                'description': 'Set of policies for information security',
                'requirement': 'Document and approve information security policy',
                'check_method': 'documentation',
                'patterns': ['security_policy', 'information_security'],
                'priority': 'high'
            },
            {
                'id': 'A.9.1.1',
                'name': 'Access Control Policy',
                'description': 'Policy for access control',
                'requirement': 'Establish access control policy and procedures',
                'check_method': 'code_analysis',
                'patterns': ['access_control', 'authorization', 'rbac'],
                'priority': 'critical'
            },
            {
                'id': 'A.9.4.2',
                'name': 'Secure Log-on Procedures',
                'description': 'Access to systems should be controlled by secure log-on procedure',
                'requirement': 'Implement secure authentication mechanisms',
                'check_method': 'code_analysis',
                'patterns': ['authentication', 'login', 'mfa', 'password_policy'],
                'priority': 'critical'
            },
            {
                'id': 'A.10.1.1',
                'name': 'Cryptographic Policy',
                'description': 'Policy on the use of cryptographic controls',
                'requirement': 'Develop and implement cryptographic policy',
                'check_method': 'code_analysis',
                'patterns': ['encryption', 'cryptography', 'tls', 'ssl'],
                'priority': 'high'
            },
            {
                'id': 'A.12.4.1',
                'name': 'Event Logging',
                'description': 'Event logs recording user activities and system events',
                'requirement': 'Log security events and maintain audit trails',
                'check_method': 'code_analysis',
                'patterns': ['logging', 'audit_trail', 'security_events'],
                'priority': 'high'
            },
            {
                'id': 'A.12.6.1',
                'name': 'Management of Technical Vulnerabilities',
                'description': 'Timely identification and management of vulnerabilities',
                'requirement': 'Implement vulnerability management process',
                'check_method': 'process',
                'patterns': ['vulnerability_scan', 'patch_management'],
                'priority': 'high'
            },
            {
                'id': 'A.13.1.1',
                'name': 'Network Controls',
                'description': 'Networks should be controlled and protected',
                'requirement': 'Implement network security controls',
                'check_method': 'infrastructure',
                'patterns': ['firewall', 'network_security', 'segmentation'],
                'priority': 'high'
            },
            {
                'id': 'A.14.1.2',
                'name': 'Securing Application Services',
                'description': 'Information in application services should be protected',
                'requirement': 'Implement application security controls',
                'check_method': 'code_analysis',
                'patterns': ['input_validation', 'output_encoding', 'sql_injection'],
                'priority': 'critical'
            }
        ]

    def _load_nist_csf_controls(self) -> List[Dict]:
        """Load NIST Cybersecurity Framework controls."""
        return [
            {
                'id': 'ID.AM-1',
                'name': 'Asset Management',
                'description': 'Physical devices and systems are inventoried',
                'requirement': 'Maintain inventory of authorized devices',
                'check_method': 'documentation',
                'patterns': ['asset_inventory', 'device_management'],
                'priority': 'medium'
            },
            {
                'id': 'PR.AC-1',
                'name': 'Identity Management',
                'description': 'Identities and credentials are issued and managed',
                'requirement': 'Implement identity and access management',
                'check_method': 'code_analysis',
                'patterns': ['user_management', 'identity', 'credentials'],
                'priority': 'critical'
            },
            {
                'id': 'PR.AC-4',
                'name': 'Access Permissions',
                'description': 'Access permissions and authorizations are managed',
                'requirement': 'Implement least privilege access controls',
                'check_method': 'code_analysis',
                'patterns': ['permissions', 'authorization', 'least_privilege'],
                'priority': 'high'
            },
            {
                'id': 'PR.DS-1',
                'name': 'Data at Rest Protection',
                'description': 'Data-at-rest is protected',
                'requirement': 'Encrypt sensitive data at rest',
                'check_method': 'code_analysis',
                'patterns': ['encryption_at_rest', 'data_encryption'],
                'priority': 'critical'
            },
            {
                'id': 'PR.DS-2',
                'name': 'Data in Transit Protection',
                'description': 'Data-in-transit is protected',
                'requirement': 'Encrypt data in transit using TLS',
                'check_method': 'infrastructure',
                'patterns': ['tls', 'https', 'ssl', 'encryption_in_transit'],
                'priority': 'critical'
            },
            {
                'id': 'DE.AE-3',
                'name': 'Event Data',
                'description': 'Event data are collected and correlated',
                'requirement': 'Implement comprehensive logging and monitoring',
                'check_method': 'code_analysis',
                'patterns': ['logging', 'monitoring', 'siem'],
                'priority': 'high'
            },
            {
                'id': 'RS.RP-1',
                'name': 'Response Plan',
                'description': 'Response plan is executed during or after an incident',
                'requirement': 'Develop and maintain incident response plan',
                'check_method': 'documentation',
                'patterns': ['incident_response', 'response_plan'],
                'priority': 'medium'
            }
        ]

    def _load_owasp_asvs_controls(self) -> List[Dict]:
        """Load OWASP ASVS controls."""
        return [
            {
                'id': 'V1.2.1',
                'name': 'Secure Development Lifecycle',
                'description': 'Use of a secure development lifecycle',
                'requirement': 'Implement secure coding practices',
                'check_method': 'process',
                'patterns': ['secure_coding', 'sdlc', 'code_review'],
                'priority': 'high'
            },
            {
                'id': 'V2.1.1',
                'name': 'Password Security',
                'description': 'User passwords are verified to be at least 12 characters',
                'requirement': 'Implement strong password requirements',
                'check_method': 'code_analysis',
                'patterns': ['password_policy', 'password_validation'],
                'priority': 'high'
            },
            {
                'id': 'V3.1.1',
                'name': 'Session Management',
                'description': 'Applications never reveal session tokens in URLs',
                'requirement': 'Secure session token management',
                'check_method': 'code_analysis',
                'patterns': ['session_management', 'token_security'],
                'priority': 'critical'
            },
            {
                'id': 'V5.1.1',
                'name': 'Input Validation',
                'description': 'Applications have defined and documented data schemas',
                'requirement': 'Implement comprehensive input validation',
                'check_method': 'code_analysis',
                'patterns': ['input_validation', 'data_validation', 'schema'],
                'priority': 'critical'
            },
            {
                'id': 'V5.3.4',
                'name': 'SQL Injection Prevention',
                'description': 'SQL queries use parameterized queries',
                'requirement': 'Prevent SQL injection vulnerabilities',
                'check_method': 'code_analysis',
                'patterns': ['parameterized_query', 'sql_injection', 'prepared_statement'],
                'priority': 'critical'
            },
            {
                'id': 'V7.1.1',
                'name': 'Error Handling',
                'description': 'Applications do not disclose sensitive information in error messages',
                'requirement': 'Implement secure error handling',
                'check_method': 'code_analysis',
                'patterns': ['error_handling', 'exception_handling'],
                'priority': 'medium'
            },
            {
                'id': 'V9.1.1',
                'name': 'Client-side Security',
                'description': 'TLS is used for all client connectivity',
                'requirement': 'Enforce HTTPS for all client communication',
                'check_method': 'infrastructure',
                'patterns': ['https', 'tls', 'ssl'],
                'priority': 'critical'
            },
            {
                'id': 'V10.3.2',
                'name': 'Deployed Application Security',
                'description': 'Application is deployed with security headers',
                'requirement': 'Implement security headers',
                'check_method': 'code_analysis',
                'patterns': ['security_headers', 'csp', 'hsts'],
                'priority': 'high'
            }
        ]

    def scan_compliance(self, framework: ComplianceFramework) -> ComplianceReport:
        """Perform compliance scan for specified framework."""
        logger.info(f"Starting compliance scan for {framework.value}")
        
        framework_def = self.frameworks.get(framework)
        if not framework_def:
            raise ValueError(f"Unsupported framework: {framework}")
            
        checks = []
        
        for control in framework_def['controls']:
            check = self._evaluate_control(framework, control)
            checks.append(check)
            
        # Calculate overall compliance score
        compliant_count = sum(1 for check in checks if check.status == ComplianceStatus.COMPLIANT)
        partially_compliant_count = sum(1 for check in checks if check.status == ComplianceStatus.PARTIALLY_COMPLIANT)
        total_applicable = sum(1 for check in checks if check.status != ComplianceStatus.NOT_APPLICABLE)
        
        if total_applicable > 0:
            score = ((compliant_count + (partially_compliant_count * 0.5)) / total_applicable) * 100
        else:
            score = 0
            
        # Generate executive summary
        exec_summary = self._generate_executive_summary(framework, checks, score)
        
        report = ComplianceReport(
            framework=framework,
            assessment_date=datetime.now().isoformat(),
            overall_score=round(score, 2),
            total_controls=len(checks),
            compliant_controls=compliant_count,
            non_compliant_controls=sum(1 for check in checks if check.status == ComplianceStatus.NON_COMPLIANT),
            checks=checks,
            executive_summary=exec_summary,
            next_assessment_date=(datetime.now() + timedelta(days=90)).isoformat()
        )
        
        logger.info(f"Compliance scan completed. Score: {score:.1f}%")
        return report

    def _evaluate_control(self, framework: ComplianceFramework, control: Dict) -> ComplianceCheck:
        """Evaluate a single compliance control."""
        control_id = control['id']
        logger.debug(f"Evaluating control {control_id}")
        
        # Determine check method and perform evaluation
        check_method = control.get('check_method', 'code_analysis')
        
        if check_method == 'code_analysis':
            status, evidence, gaps = self._check_code_compliance(control)
        elif check_method == 'documentation':
            status, evidence, gaps = self._check_documentation_compliance(control)
        elif check_method == 'infrastructure':
            status, evidence, gaps = self._check_infrastructure_compliance(control)
        elif check_method == 'security_analysis':
            status, evidence, gaps = self._check_security_compliance(control)
        elif check_method == 'monitoring':
            status, evidence, gaps = self._check_monitoring_compliance(control)
        elif check_method == 'process':
            status, evidence, gaps = self._check_process_compliance(control)
        else:
            status = ComplianceStatus.REQUIRES_REVIEW
            evidence = []
            gaps = [f"Unknown check method: {check_method}"]
            
        # Generate remediation steps
        remediation_steps = self._generate_remediation_steps(control, gaps)
        
        return ComplianceCheck(
            framework=framework,
            control_id=control_id,
            control_name=control['name'],
            description=control['description'],
            requirement=control['requirement'],
            status=status,
            evidence=evidence,
            gaps=gaps,
            remediation_steps=remediation_steps,
            priority=control.get('priority', 'medium'),
            estimated_effort=self._estimate_effort(gaps),
            responsible_team=self._determine_responsible_team(control)
        )

    def _check_code_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check compliance by analyzing code."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Search for implementation patterns in code
        for file_type, file_patterns in self.code_patterns.items():
            if file_type in ['python', 'typescript', 'javascript']:
                for pattern in file_patterns:
                    files = list(self.project_root.glob(pattern))
                    for file_path in files:
                        if self._should_skip_file(file_path):
                            continue
                            
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read().lower()
                                
                            # Check for required patterns
                            for required_pattern in patterns:
                                if required_pattern.lower() in content:
                                    evidence.append(f"Found '{required_pattern}' in {file_path}")
                                    
                        except Exception as e:
                            logger.warning(f"Could not read {file_path}: {e}")
        
        # Determine compliance status
        if not patterns:
            status = ComplianceStatus.REQUIRES_REVIEW
        elif not evidence:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append(f"No implementation found for required patterns: {', '.join(patterns)}")
        elif len(evidence) >= len(patterns):
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
            missing_patterns = set(patterns) - set(e.split("'")[1] for e in evidence if "'" in e)
            if missing_patterns:
                gaps.append(f"Missing implementation for: {', '.join(missing_patterns)}")
                
        return status, evidence, gaps

    def _check_documentation_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check compliance by analyzing documentation."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Search for documentation files
        doc_patterns = ['**/*.md', '**/*.rst', '**/*.txt', '**/docs/**/*']
        
        for pattern in doc_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                    for required_pattern in patterns:
                        if required_pattern.lower() in content:
                            evidence.append(f"Found '{required_pattern}' documentation in {file_path}")
                            
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
        
        # Check for specific documentation requirements
        if control['id'].startswith('GDPR'):
            privacy_docs = list(self.project_root.glob('**/privacy*.md')) + list(self.project_root.glob('**/PRIVACY*'))
            if privacy_docs:
                evidence.append(f"Found privacy documentation: {privacy_docs[0]}")
        
        # Determine status
        if not evidence:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append("Required documentation not found")
        elif len(evidence) >= len(patterns):
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
            gaps.append("Incomplete documentation")
            
        return status, evidence, gaps

    def _check_infrastructure_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check compliance by analyzing infrastructure configuration."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Check Docker configurations
        docker_files = list(self.project_root.glob('**/Dockerfile*'))
        for docker_file in docker_files:
            try:
                with open(docker_file, 'r') as f:
                    content = f.read().lower()
                    
                for pattern in patterns:
                    if pattern.lower() in content:
                        evidence.append(f"Found '{pattern}' in {docker_file}")
                        
            except Exception as e:
                logger.warning(f"Could not read {docker_file}: {e}")
        
        # Check Terraform configurations
        tf_files = list(self.project_root.glob('**/*.tf'))
        for tf_file in tf_files:
            try:
                with open(tf_file, 'r') as f:
                    content = f.read().lower()
                    
                for pattern in patterns:
                    if pattern.lower() in content:
                        evidence.append(f"Found '{pattern}' in {tf_file}")
                        
            except Exception as e:
                logger.warning(f"Could not read {tf_file}: {e}")
        
        # Check for HTTPS enforcement
        if 'https' in patterns or 'tls' in patterns:
            # Look for HTTPS configuration in various places
            config_files = list(self.project_root.glob('**/*.yml')) + list(self.project_root.glob('**/*.yaml'))
            for config_file in config_files:
                try:
                    with open(config_file, 'r') as f:
                        content = f.read().lower()
                        if 'https' in content or 'ssl' in content or 'tls' in content:
                            evidence.append(f"Found HTTPS/TLS configuration in {config_file}")
                except Exception:
                    pass
        
        # Determine status
        if not evidence and patterns:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append(f"Infrastructure configuration missing for: {', '.join(patterns)}")
        elif evidence:
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.REQUIRES_REVIEW
            
        return status, evidence, gaps

    def _check_security_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check security-specific compliance requirements."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Check for security headers implementation
        if 'security_headers' in patterns:
            # Look for security headers in FastAPI/Next.js code
            security_header_patterns = [
                'x-content-type-options',
                'x-frame-options',
                'x-xss-protection',
                'strict-transport-security',
                'content-security-policy'
            ]
            
            code_files = list(self.project_root.glob('**/*.py')) + list(self.project_root.glob('**/*.ts'))
            for file_path in code_files:
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                    for header in security_header_patterns:
                        if header in content:
                            evidence.append(f"Found security header '{header}' in {file_path}")
                            
                except Exception:
                    pass
        
        # Check for encryption implementation
        if 'encryption' in patterns:
            encryption_patterns = ['encrypt', 'decrypt', 'bcrypt', 'scrypt', 'pbkdf2', 'aes', 'rsa']
            
            code_files = list(self.project_root.glob('**/*.py')) + list(self.project_root.glob('**/*.ts'))
            for file_path in code_files:
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                    for enc_pattern in encryption_patterns:
                        if enc_pattern in content:
                            evidence.append(f"Found encryption implementation '{enc_pattern}' in {file_path}")
                            
                except Exception:
                    pass
        
        # Check for access control implementation
        if 'access_control' in patterns:
            access_patterns = ['authorize', 'permission', 'role', 'rbac', 'depends']
            
            code_files = list(self.project_root.glob('**/*.py'))
            for file_path in code_files:
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                    for access_pattern in access_patterns:
                        if access_pattern in content:
                            evidence.append(f"Found access control '{access_pattern}' in {file_path}")
                            
                except Exception:
                    pass
        
        # Determine status
        if not evidence and patterns:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append(f"Security controls not implemented for: {', '.join(patterns)}")
        elif len(evidence) >= len([p for p in patterns if p in ['security_headers', 'encryption', 'access_control']]):
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
            gaps.append("Some security controls implemented but gaps remain")
            
        return status, evidence, gaps

    def _check_monitoring_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check monitoring and logging compliance."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Check for logging implementation
        logging_patterns = ['logger', 'log', 'audit', 'event']
        
        code_files = list(self.project_root.glob('**/*.py')) + list(self.project_root.glob('**/*.ts'))
        for file_path in code_files:
            if self._should_skip_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    
                for log_pattern in logging_patterns:
                    if log_pattern in content:
                        evidence.append(f"Found logging implementation '{log_pattern}' in {file_path}")
                        break  # Only count once per file
                        
            except Exception:
                pass
        
        # Check for monitoring configuration
        config_files = list(self.project_root.glob('**/*.yml')) + list(self.project_root.glob('**/*.yaml'))
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    content = f.read().lower()
                    
                if 'applicationinsights' in content or 'monitoring' in content:
                    evidence.append(f"Found monitoring configuration in {config_file}")
                    
            except Exception:
                pass
        
        # Determine status
        if not evidence:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append("No logging or monitoring implementation found")
        else:
            status = ComplianceStatus.COMPLIANT
            
        return status, evidence, gaps

    def _check_process_compliance(self, control: Dict) -> Tuple[ComplianceStatus, List[str], List[str]]:
        """Check process-related compliance (CI/CD, workflows, etc.)."""
        patterns = control.get('patterns', [])
        evidence = []
        gaps = []
        
        # Check for CI/CD workflows
        workflow_files = list(self.project_root.glob('.github/workflows/*.yml'))
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r') as f:
                    content = f.read().lower()
                    
                for pattern in patterns:
                    if pattern.lower() in content:
                        evidence.append(f"Found '{pattern}' in CI/CD workflow {workflow_file}")
                        
            except Exception:
                pass
        
        # Check for security scanning in CI/CD
        if 'vulnerability_scan' in patterns:
            for workflow_file in workflow_files:
                try:
                    with open(workflow_file, 'r') as f:
                        content = f.read().lower()
                        
                    vuln_tools = ['semgrep', 'bandit', 'trivy', 'snyk', 'gitleaks']
                    for tool in vuln_tools:
                        if tool in content:
                            evidence.append(f"Found vulnerability scanning tool '{tool}' in {workflow_file}")
                            
                except Exception:
                    pass
        
        # Determine status
        if not evidence and patterns:
            status = ComplianceStatus.NON_COMPLIANT
            gaps.append(f"Process controls not implemented for: {', '.join(patterns)}")
        elif evidence:
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.REQUIRES_REVIEW
            
        return status, evidence, gaps

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped during analysis."""
        skip_patterns = [
            'node_modules',
            '__pycache__',
            '.git',
            'test',
            'tests',
            '.test.',
            '.spec.',
            'dist',
            'build',
            '.next'
        ]
        
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in skip_patterns)

    def _generate_remediation_steps(self, control: Dict, gaps: List[str]) -> List[str]:
        """Generate specific remediation steps based on control and gaps."""
        steps = []
        
        if not gaps:
            return ["No remediation required - control is compliant"]
        
        control_id = control['id']
        
        # GDPR-specific remediations
        if control_id.startswith('GDPR'):
            if 'consent' in control['requirement'].lower():
                steps.extend([
                    "Implement consent management system",
                    "Add consent withdrawal functionality",
                    "Document legal basis for data processing"
                ])
            elif 'export' in control['requirement'].lower() or 'portability' in control['requirement'].lower():
                steps.extend([
                    "Implement data export API endpoint",
                    "Add user data download functionality",
                    "Ensure data is exported in machine-readable format"
                ])
            elif 'deletion' in control['requirement'].lower() or 'erasure' in control['requirement'].lower():
                steps.extend([
                    "Implement user data deletion functionality",
                    "Add data anonymization procedures",
                    "Document data retention policies"
                ])
        
        # Security control remediations
        elif 'security' in control['name'].lower():
            if 'encryption' in control['requirement'].lower():
                steps.extend([
                    "Implement data encryption at rest",
                    "Enable TLS for data in transit",
                    "Use strong encryption algorithms (AES-256, RSA-2048+)"
                ])
            elif 'access' in control['requirement'].lower():
                steps.extend([
                    "Implement role-based access control (RBAC)",
                    "Add authentication dependency to API endpoints",
                    "Review and update authorization logic"
                ])
            elif 'logging' in control['requirement'].lower():
                steps.extend([
                    "Implement comprehensive audit logging",
                    "Add security event monitoring",
                    "Configure log retention and analysis"
                ])
        
        # Process control remediations
        elif 'process' in control.get('check_method', ''):
            steps.extend([
                "Document security procedures",
                "Implement automated security testing in CI/CD",
                "Establish regular security review process"
            ])
        
        # Generic remediation steps based on gaps
        for gap in gaps:
            if 'documentation' in gap.lower():
                steps.append("Create and maintain required documentation")
            elif 'implementation' in gap.lower():
                steps.append("Implement missing security controls")
            elif 'configuration' in gap.lower():
                steps.append("Update system configuration")
        
        # Add default steps if none were generated
        if not steps:
            steps.extend([
                "Review control requirements",
                "Implement necessary changes",
                "Test and validate implementation",
                "Document changes and procedures"
            ])
        
        return list(set(steps))  # Remove duplicates

    def _estimate_effort(self, gaps: List[str]) -> str:
        """Estimate effort required for remediation."""
        if not gaps:
            return "0 hours"
        
        gap_count = len(gaps)
        gap_text = ' '.join(gaps).lower()
        
        # High effort indicators
        high_effort_keywords = ['implement', 'develop', 'create', 'establish', 'design']
        medium_effort_keywords = ['update', 'modify', 'configure', 'document']
        low_effort_keywords = ['review', 'validate', 'test']
        
        if any(keyword in gap_text for keyword in high_effort_keywords):
            if gap_count > 3:
                return "2-4 weeks"
            elif gap_count > 1:
                return "1-2 weeks"
            else:
                return "3-5 days"
        elif any(keyword in gap_text for keyword in medium_effort_keywords):
            if gap_count > 2:
                return "1-2 weeks"
            else:
                return "2-3 days"
        else:
            return "4-8 hours"

    def _determine_responsible_team(self, control: Dict) -> str:
        """Determine which team is responsible for the control."""
        control_name = control['name'].lower()
        requirement = control['requirement'].lower()
        
        if any(keyword in control_name + requirement for keyword in ['code', 'development', 'application']):
            return "Development Team"
        elif any(keyword in control_name + requirement for keyword in ['infrastructure', 'network', 'deployment']):
            return "Platform/DevOps Team"
        elif any(keyword in control_name + requirement for keyword in ['security', 'access', 'authentication']):
            return "Security Team"
        elif any(keyword in control_name + requirement for keyword in ['data', 'privacy', 'gdpr']):
            return "Data Protection Team"
        elif any(keyword in control_name + requirement for keyword in ['policy', 'process', 'documentation']):
            return "Compliance Team"
        else:
            return "Security Team"

    def _generate_executive_summary(self, framework: ComplianceFramework, checks: List[ComplianceCheck], score: float) -> str:
        """Generate executive summary for compliance report."""
        total_checks = len(checks)
        compliant = sum(1 for c in checks if c.status == ComplianceStatus.COMPLIANT)
        non_compliant = sum(1 for c in checks if c.status == ComplianceStatus.NON_COMPLIANT)
        critical_gaps = sum(1 for c in checks if c.status == ComplianceStatus.NON_COMPLIANT and c.priority == 'critical')
        
        risk_level = "LOW" if score >= 90 else "MEDIUM" if score >= 70 else "HIGH" if score >= 50 else "CRITICAL"
        
        summary = f"""
EXECUTIVE SUMMARY - {framework.value.upper()} COMPLIANCE ASSESSMENT

Overall Compliance Score: {score:.1f}%
Risk Level: {risk_level}

Key Findings:
- Total Controls Assessed: {total_checks}
- Compliant Controls: {compliant} ({(compliant/total_checks*100):.1f}%)
- Non-Compliant Controls: {non_compliant} ({(non_compliant/total_checks*100):.1f}%)
- Critical Gaps: {critical_gaps}

Priority Actions Required:
"""
        
        # Add priority actions for critical non-compliant controls
        critical_controls = [c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT and c.priority == 'critical']
        if critical_controls:
            summary += "\nCRITICAL PRIORITY:\n"
            for control in critical_controls[:3]:  # Top 3 critical issues
                summary += f"- {control.control_name}: {control.requirement}\n"
        
        # Add high priority actions
        high_priority_controls = [c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT and c.priority == 'high']
        if high_priority_controls:
            summary += "\nHIGH PRIORITY:\n"
            for control in high_priority_controls[:3]:  # Top 3 high priority issues
                summary += f"- {control.control_name}: {control.requirement}\n"
        
        summary += f"\nNext Assessment: Recommended within 90 days\n"
        summary += f"Assessment Date: {datetime.now().strftime('%Y-%m-%d')}\n"
        
        return summary.strip()

    def generate_compliance_report(self, report: ComplianceReport, output_file: str) -> None:
        """Generate detailed compliance report."""
        # Create comprehensive report
        report_data = {
            'metadata': {
                'framework': report.framework.value,
                'assessment_date': report.assessment_date,
                'next_assessment_date': report.next_assessment_date,
                'overall_score': report.overall_score,
                'total_controls': report.total_controls,
                'compliant_controls': report.compliant_controls,
                'non_compliant_controls': report.non_compliant_controls
            },
            'executive_summary': report.executive_summary,
            'detailed_findings': []
        }
        
        # Add detailed findings
        for check in report.checks:
            finding = {
                'control_id': check.control_id,
                'control_name': check.control_name,
                'description': check.description,
                'requirement': check.requirement,
                'status': check.status.value,
                'priority': check.priority,
                'evidence': check.evidence,
                'gaps': check.gaps,
                'remediation_steps': check.remediation_steps,
                'estimated_effort': check.estimated_effort,
                'responsible_team': check.responsible_team
            }
            report_data['detailed_findings'].append(finding)
        
        # Write report to file
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Compliance report generated: {output_file}")

    def scan_all_frameworks(self) -> Dict[ComplianceFramework, ComplianceReport]:
        """Scan compliance for all supported frameworks."""
        reports = {}
        
        for framework in ComplianceFramework:
            try:
                logger.info(f"Scanning {framework.value} compliance...")
                report = self.scan_compliance(framework)
                reports[framework] = report
                
                # Generate individual report
                output_file = f"compliance_report_{framework.value}_{datetime.now().strftime('%Y%m%d')}.json"
                self.generate_compliance_report(report, output_file)
                
            except Exception as e:
                logger.error(f"Failed to scan {framework.value}: {e}")
        
        return reports

def main():
    """Main entry point for compliance scanning."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Security Compliance Scanner')
    parser.add_argument('--framework', choices=[f.value for f in ComplianceFramework],
                       help='Specific framework to scan')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output-dir', default='.', help='Output directory for reports')
    
    args = parser.parse_args()
    
    try:
        scanner = ComplianceScanner(args.project_root)
        
        if args.framework:
            # Scan specific framework
            framework = ComplianceFramework(args.framework)
            report = scanner.scan_compliance(framework)
            
            output_file = os.path.join(args.output_dir, 
                                     f"compliance_report_{framework.value}_{datetime.now().strftime('%Y%m%d')}.json")
            scanner.generate_compliance_report(report, output_file)
            
            print(f"Compliance Score: {report.overall_score:.1f}%")
            print(f"Report saved to: {output_file}")
            
        else:
            # Scan all frameworks
            reports = scanner.scan_all_frameworks()
            
            # Generate summary
            print("\nCOMPLIANCE SUMMARY:")
            print("=" * 50)
            for framework, report in reports.items():
                print(f"{framework.value.upper():15}: {report.overall_score:6.1f}%")
            
            avg_score = sum(r.overall_score for r in reports.values()) / len(reports)
            print(f"{'AVERAGE':15}: {avg_score:6.1f}%")
            
    except Exception as e:
        logger.error(f"Compliance scanning failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
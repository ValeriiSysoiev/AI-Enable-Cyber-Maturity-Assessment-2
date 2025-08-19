#!/usr/bin/env python3
"""
Automated Security Remediation Orchestrator

This script analyzes security scan results and applies safe remediations automatically,
while flagging risky changes for manual review through PR creation.

Usage:
    python auto_remediate.py --scan-results=scan-results/ --mode=auto_safe
    python auto_remediate.py --scan-results=scan-results/ --mode=review_only
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from packaging import version
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityFinding:
    """Represents a security finding from scan results."""
    tool: str
    severity: str
    category: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    cve_id: Optional[str] = None
    package_name: Optional[str] = None
    current_version: Optional[str] = None
    fixed_version: Optional[str] = None
    remediation_suggestion: Optional[str] = None

@dataclass
class RemediationAction:
    """Represents a remediation action to be taken."""
    action_type: str  # 'dependency_update', 'config_change', 'code_fix'
    risk_level: str   # 'safe', 'medium', 'high'
    description: str
    file_path: str
    original_content: str
    new_content: str
    reasoning: str
    auto_applicable: bool = True

@dataclass
class RemediationReport:
    """Report of remediation activities."""
    status: str
    scan_date: str
    safe_fixes_applied: int
    risky_issues_found: int
    fixes_applied: List[Dict]
    manual_review_required: List[Dict]
    errors: List[str]

class SecurityRemediator:
    """Main class for automated security remediation."""
    
    def __init__(self, scan_results_dir: str, mode: str = 'auto_safe'):
        self.scan_results_dir = Path(scan_results_dir)
        self.mode = mode
        self.findings: List[SecurityFinding] = []
        self.remediations: List[RemediationAction] = []
        self.report = RemediationReport(
            status='initialized',
            scan_date=datetime.now().isoformat(),
            safe_fixes_applied=0,
            risky_issues_found=0,
            fixes_applied=[],
            manual_review_required=[],
            errors=[]
        )
        
        # Safe remediation patterns and thresholds
        self.safe_patterns = {
            'dependency_patch': r'^\d+\.\d+\.(\d+)$',  # Patch version updates only
            'dependency_minor': r'^\d+\.(\d+)\.\d+$',   # Minor version updates (configurable)
            'security_headers': [
                'X-Content-Type-Options',
                'X-Frame-Options', 
                'X-XSS-Protection',
                'Strict-Transport-Security',
                'Content-Security-Policy'
            ],
            'logging_improvements': [
                'sensitive_data_masking',
                'audit_logging',
                'error_sanitization'
            ]
        }
        
        # Risky patterns that require manual review
        self.risky_patterns = {
            'major_updates': r'^(\d+)\.\d+\.\d+$',  # Major version changes
            'auth_changes': ['login', 'authentication', 'authorization', 'session'],
            'crypto_changes': ['encrypt', 'decrypt', 'hash', 'crypto', 'ssl', 'tls'],
            'db_schema': ['migration', 'alter table', 'drop table', 'create table'],
            'api_breaking': ['@app.route', 'def ', 'class ', 'async def']
        }

    def load_scan_results(self) -> None:
        """Load and parse all security scan results."""
        logger.info("Loading security scan results...")
        
        # Load different types of scan results
        self._load_semgrep_results()
        self._load_bandit_results() 
        self._load_dependency_results()
        self._load_secrets_results()
        self._load_infrastructure_results()
        
        logger.info(f"Loaded {len(self.findings)} security findings")

    def _load_semgrep_results(self) -> None:
        """Load Semgrep SAST results."""
        semgrep_file = self.scan_results_dir / 'sast-results' / 'semgrep-results.json'
        if not semgrep_file.exists():
            return
            
        try:
            with open(semgrep_file) as f:
                data = json.load(f)
                
            for result in data.get('results', []):
                finding = SecurityFinding(
                    tool='semgrep',
                    severity=result.get('extra', {}).get('severity', 'INFO'),
                    category='sast',
                    description=result.get('extra', {}).get('message', ''),
                    file_path=result.get('path', ''),
                    line_number=result.get('start', {}).get('line'),
                    rule_id=result.get('check_id'),
                    remediation_suggestion=result.get('extra', {}).get('fix')
                )
                self.findings.append(finding)
                
        except Exception as e:
            self.report.errors.append(f"Failed to load Semgrep results: {e}")

    def _load_bandit_results(self) -> None:
        """Load Bandit Python security results."""
        bandit_file = self.scan_results_dir / 'sast-results' / 'bandit-results.json'
        if not bandit_file.exists():
            return
            
        try:
            with open(bandit_file) as f:
                data = json.load(f)
                
            for result in data.get('results', []):
                finding = SecurityFinding(
                    tool='bandit',
                    severity=result.get('issue_severity', 'INFO'),
                    category='sast',
                    description=result.get('issue_text', ''),
                    file_path=result.get('filename', ''),
                    line_number=result.get('line_number'),
                    rule_id=result.get('test_id')
                )
                self.findings.append(finding)
                
        except Exception as e:
            self.report.errors.append(f"Failed to load Bandit results: {e}")

    def _load_dependency_results(self) -> None:
        """Load dependency vulnerability scan results."""
        # Load pip-audit results
        pip_audit_file = self.scan_results_dir / 'vulnerability-results' / 'pip-audit-results.json'
        if pip_audit_file.exists():
            try:
                with open(pip_audit_file) as f:
                    data = json.load(f)
                    
                for vuln in data.get('vulnerabilities', []):
                    finding = SecurityFinding(
                        tool='pip-audit',
                        severity='HIGH' if vuln.get('is_skipped', False) else 'MEDIUM',
                        category='dependency',
                        description=f"Vulnerable dependency: {vuln.get('package', 'unknown')}",
                        file_path='app/requirements.txt',
                        package_name=vuln.get('package'),
                        current_version=vuln.get('installed_version'),
                        fixed_version=vuln.get('fixed_versions', [None])[0] if vuln.get('fixed_versions') else None,
                        cve_id=vuln.get('id')
                    )
                    self.findings.append(finding)
                    
            except Exception as e:
                self.report.errors.append(f"Failed to load pip-audit results: {e}")
        
        # Load npm audit results
        npm_audit_file = self.scan_results_dir / 'vulnerability-results' / 'npm-audit-results.json'
        if npm_audit_file.exists():
            try:
                with open(npm_audit_file) as f:
                    data = json.load(f)
                    
                for vuln_id, vuln in data.get('vulnerabilities', {}).items():
                    finding = SecurityFinding(
                        tool='npm-audit',
                        severity=vuln.get('severity', 'INFO').upper(),
                        category='dependency',
                        description=f"Vulnerable dependency: {vuln.get('name', 'unknown')}",
                        file_path='web/package.json',
                        package_name=vuln.get('name'),
                        current_version=vuln.get('range', ''),
                        fixed_version=vuln.get('fixAvailable', {}).get('version') if isinstance(vuln.get('fixAvailable'), dict) else None
                    )
                    self.findings.append(finding)
                    
            except Exception as e:
                self.report.errors.append(f"Failed to load npm-audit results: {e}")

    def _load_secrets_results(self) -> None:
        """Load secret detection results."""
        secrets_file = self.scan_results_dir / 'secrets-results' / 'gitleaks-results.json'
        if not secrets_file.exists():
            return
            
        try:
            with open(secrets_file) as f:
                data = json.load(f)
                
            for secret in data:
                finding = SecurityFinding(
                    tool='gitleaks',
                    severity='CRITICAL',
                    category='secrets',
                    description=f"Potential secret detected: {secret.get('Description', '')}",
                    file_path=secret.get('File', ''),
                    line_number=secret.get('StartLine'),
                    rule_id=secret.get('RuleID')
                )
                self.findings.append(finding)
                
        except Exception as e:
            self.report.errors.append(f"Failed to load Gitleaks results: {e}")

    def _load_infrastructure_results(self) -> None:
        """Load infrastructure security scan results."""
        # Load tfsec results
        tfsec_file = self.scan_results_dir / 'infrastructure-results' / 'tfsec-results.json'
        if tfsec_file.exists():
            try:
                with open(tfsec_file) as f:
                    data = json.load(f)
                    
                for result in data.get('results', []):
                    finding = SecurityFinding(
                        tool='tfsec',
                        severity=result.get('severity', 'INFO'),
                        category='infrastructure',
                        description=result.get('description', ''),
                        file_path=result.get('location', {}).get('filename', ''),
                        line_number=result.get('location', {}).get('start_line'),
                        rule_id=result.get('rule_id')
                    )
                    self.findings.append(finding)
                    
            except Exception as e:
                self.report.errors.append(f"Failed to load tfsec results: {e}")

    def analyze_remediations(self) -> None:
        """Analyze findings and determine safe vs risky remediations."""
        logger.info("Analyzing remediations...")
        
        for finding in self.findings:
            if finding.category == 'dependency':
                self._analyze_dependency_remediation(finding)
            elif finding.category == 'sast':
                self._analyze_sast_remediation(finding)
            elif finding.category == 'secrets':
                self._analyze_secrets_remediation(finding)
            elif finding.category == 'infrastructure':
                self._analyze_infrastructure_remediation(finding)

    def _analyze_dependency_remediation(self, finding: SecurityFinding) -> None:
        """Analyze dependency vulnerability remediations."""
        if not finding.package_name or not finding.fixed_version:
            return
            
        # Determine if this is a safe update
        risk_level = self._assess_dependency_risk(
            finding.current_version, 
            finding.fixed_version,
            finding.package_name
        )
        
        if risk_level == 'safe':
            if finding.tool == 'pip-audit':
                remediation = self._create_pip_update_remediation(finding)
            elif finding.tool == 'npm-audit':
                remediation = self._create_npm_update_remediation(finding)
            else:
                return
                
            if remediation:
                self.remediations.append(remediation)
        else:
            # Flag for manual review
            self.report.manual_review_required.append({
                'type': 'dependency_update',
                'description': f"Dependency update requires manual review: {finding.package_name}",
                'risk_level': risk_level,
                'current_version': finding.current_version,
                'fixed_version': finding.fixed_version,
                'file_path': finding.file_path
            })

    def _assess_dependency_risk(self, current_ver: str, fixed_ver: str, package_name: str) -> str:
        """Assess risk level of dependency update."""
        try:
            current = version.parse(current_ver) if current_ver else None
            fixed = version.parse(fixed_ver) if fixed_ver else None
            
            if not current or not fixed:
                return 'high'
                
            # Major version change = high risk
            if current.major != fixed.major:
                return 'high'
                
            # Minor version change = medium risk for core packages
            core_packages = [
                'fastapi', 'uvicorn', 'sqlalchemy', 'next', 'react', 
                'express', 'django', 'flask', 'spring'
            ]
            
            if current.minor != fixed.minor:
                if any(core in package_name.lower() for core in core_packages):
                    return 'medium'
                return 'safe'  # Minor updates generally safe for non-core packages
                
            # Patch version change = safe
            return 'safe'
            
        except Exception:
            return 'high'  # Default to high risk if we can't parse versions

    def _create_pip_update_remediation(self, finding: SecurityFinding) -> Optional[RemediationAction]:
        """Create pip dependency update remediation."""
        requirements_file = Path('app/requirements.txt')
        if not requirements_file.exists():
            return None
            
        try:
            with open(requirements_file) as f:
                content = f.read()
                
            # Find and update the specific package
            pattern = rf'^{re.escape(finding.package_name)}==.*$'
            new_line = f"{finding.package_name}=={finding.fixed_version}"
            
            new_content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
            
            if new_content != content:
                return RemediationAction(
                    action_type='dependency_update',
                    risk_level='safe',
                    description=f"Update {finding.package_name} to {finding.fixed_version} (security fix)",
                    file_path=str(requirements_file),
                    original_content=content,
                    new_content=new_content,
                    reasoning=f"Safe patch-level security update for CVE: {finding.cve_id or 'N/A'}"
                )
                
        except Exception as e:
            logger.error(f"Failed to create pip remediation: {e}")
            
        return None

    def _create_npm_update_remediation(self, finding: SecurityFinding) -> Optional[RemediationAction]:
        """Create npm dependency update remediation."""
        package_file = Path('web/package.json')
        if not package_file.exists():
            return None
            
        try:
            with open(package_file) as f:
                package_data = json.load(f)
                
            # Update dependencies or devDependencies
            updated = False
            for dep_type in ['dependencies', 'devDependencies']:
                if dep_type in package_data and finding.package_name in package_data[dep_type]:
                    package_data[dep_type][finding.package_name] = f"^{finding.fixed_version}"
                    updated = True
                    break
                    
            if updated:
                new_content = json.dumps(package_data, indent=2)
                with open(package_file) as f:
                    original_content = f.read()
                    
                return RemediationAction(
                    action_type='dependency_update',
                    risk_level='safe',
                    description=f"Update {finding.package_name} to {finding.fixed_version} (security fix)",
                    file_path=str(package_file),
                    original_content=original_content,
                    new_content=new_content,
                    reasoning=f"Safe security update for npm package"
                )
                
        except Exception as e:
            logger.error(f"Failed to create npm remediation: {e}")
            
        return None

    def _analyze_sast_remediation(self, finding: SecurityFinding) -> None:
        """Analyze static analysis findings for auto-remediation."""
        # Focus on safe configuration and logging improvements
        safe_sast_patterns = [
            'missing-security-header',
            'weak-random',
            'logging-sensitive-data',
            'hardcoded-credentials'  # For removal, not replacement
        ]
        
        if finding.rule_id and any(pattern in finding.rule_id.lower() for pattern in safe_sast_patterns):
            remediation = self._create_sast_remediation(finding)
            if remediation:
                self.remediations.append(remediation)
        else:
            # Flag for manual review
            self.report.manual_review_required.append({
                'type': 'code_fix',
                'description': f"SAST finding requires manual review: {finding.description}",
                'risk_level': 'medium',
                'file_path': finding.file_path,
                'line_number': finding.line_number,
                'rule_id': finding.rule_id
            })

    def _create_sast_remediation(self, finding: SecurityFinding) -> Optional[RemediationAction]:
        """Create SAST-based code remediation."""
        file_path = Path(finding.file_path)
        if not file_path.exists():
            return None
            
        try:
            with open(file_path) as f:
                lines = f.readlines()
                
            # Apply specific fixes based on rule type
            if 'missing-security-header' in finding.rule_id.lower():
                return self._fix_missing_security_headers(finding, file_path, lines)
            elif 'logging-sensitive-data' in finding.rule_id.lower():
                return self._fix_sensitive_logging(finding, file_path, lines)
                
        except Exception as e:
            logger.error(f"Failed to create SAST remediation: {e}")
            
        return None

    def _fix_missing_security_headers(self, finding: SecurityFinding, file_path: Path, lines: List[str]) -> Optional[RemediationAction]:
        """Fix missing security headers in FastAPI apps."""
        if 'main.py' not in file_path.name:
            return None
            
        # Add security headers middleware
        security_middleware = '''
# Security Headers Middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

'''
        
        # Find where to insert the middleware
        app_creation_line = -1
        for i, line in enumerate(lines):
            if 'app = FastAPI' in line:
                app_creation_line = i
                break
                
        if app_creation_line >= 0:
            # Insert after app creation
            new_lines = lines[:app_creation_line+1] + [security_middleware] + lines[app_creation_line+1:]
            new_content = ''.join(new_lines)
            original_content = ''.join(lines)
            
            return RemediationAction(
                action_type='config_change',
                risk_level='safe',
                description="Add security headers middleware to FastAPI app",
                file_path=str(file_path),
                original_content=original_content,
                new_content=new_content,
                reasoning="Adding standard security headers improves security posture without breaking functionality"
            )
            
        return None

    def _fix_sensitive_logging(self, finding: SecurityFinding, file_path: Path, lines: List[str]) -> Optional[RemediationAction]:
        """Fix sensitive data logging issues."""
        if not finding.line_number:
            return None
            
        line_idx = finding.line_number - 1
        if line_idx >= len(lines):
            return None
            
        original_line = lines[line_idx]
        
        # Simple pattern replacement for common sensitive data
        sensitive_patterns = {
            r'password["\']?\s*:\s*["\']?([^"\'}\s,]+)': r'password": "***REDACTED***"',
            r'token["\']?\s*:\s*["\']?([^"\'}\s,]+)': r'token": "***REDACTED***"',
            r'secret["\']?\s*:\s*["\']?([^"\'}\s,]+)': r'secret": "***REDACTED***"',
            r'api_key["\']?\s*:\s*["\']?([^"\'}\s,]+)': r'api_key": "***REDACTED***"'
        }
        
        new_line = original_line
        for pattern, replacement in sensitive_patterns.items():
            new_line = re.sub(pattern, replacement, new_line, flags=re.IGNORECASE)
            
        if new_line != original_line:
            new_lines = lines.copy()
            new_lines[line_idx] = new_line
            
            return RemediationAction(
                action_type='code_fix',
                risk_level='safe',
                description="Mask sensitive data in logging statements",
                file_path=str(file_path),
                original_content=''.join(lines),
                new_content=''.join(new_lines),
                reasoning="Preventing sensitive data exposure in logs"
            )
            
        return None

    def _analyze_secrets_remediation(self, finding: SecurityFinding) -> None:
        """Analyze secrets findings - these always require manual review."""
        self.report.manual_review_required.append({
            'type': 'secret_removal',
            'description': f"Hardcoded secret detected: {finding.description}",
            'risk_level': 'critical',
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'rule_id': finding.rule_id
        })

    def _analyze_infrastructure_remediation(self, finding: SecurityFinding) -> None:
        """Analyze infrastructure findings for safe configuration fixes."""
        safe_infra_patterns = [
            'aws-cloudtrail-encryption-disabled',
            'azure-storage-default-action-allow',
            'missing-description'
        ]
        
        if finding.rule_id and any(pattern in finding.rule_id.lower() for pattern in safe_infra_patterns):
            remediation = self._create_infrastructure_remediation(finding)
            if remediation:
                self.remediations.append(remediation)
        else:
            self.report.manual_review_required.append({
                'type': 'infrastructure_fix',
                'description': f"Infrastructure issue requires manual review: {finding.description}",
                'risk_level': 'medium',
                'file_path': finding.file_path,
                'rule_id': finding.rule_id
            })

    def _create_infrastructure_remediation(self, finding: SecurityFinding) -> Optional[RemediationAction]:
        """Create safe infrastructure configuration fixes."""
        # This would implement safe Terraform configuration improvements
        # For now, flag for manual review to avoid breaking infrastructure
        return None

    def apply_safe_remediations(self) -> None:
        """Apply all safe remediations automatically."""
        if self.mode == 'review_only':
            logger.info("Review-only mode: skipping automatic application")
            return
            
        logger.info(f"Applying {len(self.remediations)} safe remediations...")
        
        applied_fixes = []
        for remediation in self.remediations:
            try:
                # Apply the remediation
                with open(remediation.file_path, 'w') as f:
                    f.write(remediation.new_content)
                    
                applied_fixes.append({
                    'type': remediation.action_type,
                    'description': remediation.description,
                    'file_path': remediation.file_path,
                    'reasoning': remediation.reasoning
                })
                
                logger.info(f"Applied fix: {remediation.description}")
                
            except Exception as e:
                error_msg = f"Failed to apply remediation to {remediation.file_path}: {e}"
                logger.error(error_msg)
                self.report.errors.append(error_msg)
                
        self.report.fixes_applied = applied_fixes
        self.report.safe_fixes_applied = len(applied_fixes)

    def generate_report(self, output_file: str) -> None:
        """Generate comprehensive remediation report."""
        self.report.status = 'completed'
        self.report.risky_issues_found = len(self.report.manual_review_required)
        
        # Write report to file
        with open(output_file, 'w') as f:
            json.dump(asdict(self.report), f, indent=2)
            
        logger.info(f"Remediation report saved to {output_file}")
        logger.info(f"Safe fixes applied: {self.report.safe_fixes_applied}")
        logger.info(f"Risky issues flagged: {self.report.risky_issues_found}")

def main():
    """Main entry point for the auto-remediation script."""
    parser = argparse.ArgumentParser(description='Automated Security Remediation')
    parser.add_argument('--scan-results', required=True, help='Directory containing scan results')
    parser.add_argument('--mode', choices=['auto_safe', 'review_only'], default='auto_safe',
                       help='Remediation mode')
    parser.add_argument('--output', default='remediation-report.json', help='Output report file')
    parser.add_argument('--commit-changes', type=bool, default=False, 
                       help='Automatically commit changes')
    
    args = parser.parse_args()
    
    try:
        # Initialize remediation system
        remediator = SecurityRemediator(args.scan_results, args.mode)
        
        # Load scan results
        remediator.load_scan_results()
        
        if not remediator.findings:
            logger.info("No security findings to remediate")
            return
            
        # Analyze remediations
        remediator.analyze_remediations()
        
        # Apply safe remediations
        if args.mode == 'auto_safe':
            remediator.apply_safe_remediations()
            
        # Generate report
        remediator.generate_report(args.output)
        
        logger.info("Auto-remediation completed successfully")
        
    except Exception as e:
        logger.error(f"Auto-remediation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
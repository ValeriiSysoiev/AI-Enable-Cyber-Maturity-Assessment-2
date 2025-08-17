#!/usr/bin/env python3
"""
Security System Validation Script

Validates that the comprehensive security remediation system is properly configured
and all components are functional.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import get_config, get_environment_config, validate_configuration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecuritySystemValidator:
    """Validates the security remediation system setup."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config = get_config()
        self.env_config = get_environment_config()
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def validate_all(self) -> Dict[str, List[str]]:
        """Run all validation checks."""
        logger.info("Starting comprehensive security system validation...")
        
        # Core configuration validation
        self._validate_configuration()
        
        # File structure validation
        self._validate_file_structure()
        
        # Workflow validation
        self._validate_workflows()
        
        # Security rules validation
        self._validate_security_rules()
        
        # Script validation
        self._validate_scripts()
        
        # Documentation validation
        self._validate_documentation()
        
        # Environment validation
        self._validate_environment()
        
        # Generate summary
        self._generate_summary()
        
        return self.validation_results

    def _validate_configuration(self) -> None:
        """Validate configuration files and settings."""
        logger.info("Validating configuration...")
        
        try:
            # Check configuration validity
            issues = validate_configuration()
            if issues:
                for issue in issues:
                    self.validation_results['failed'].append(f"Config: {issue}")
            else:
                self.validation_results['passed'].append("Configuration validation passed")
                
        except Exception as e:
            self.validation_results['failed'].append(f"Configuration validation error: {e}")

    def _validate_file_structure(self) -> None:
        """Validate required file structure exists."""
        logger.info("Validating file structure...")
        
        required_directories = [
            '.github/workflows',
            'scripts/security',
            'security/rules',
            'docs/security'
        ]
        
        required_files = [
            '.github/workflows/security-scan.yml',
            'scripts/security/auto_remediate.py',
            'scripts/security/monitoring.py',
            'scripts/security/compliance.py',
            'scripts/security/config.py',
            'security/rules/fastapi-security.yml',
            'security/rules/nextjs-security.yml',
            'security/rules/gdpr-compliance.yml',
            'security/rules/.semgrepignore',
            'docs/security/README.md',
            'docs/security/scanning-runbook.md',
            'docs/security/remediation-procedures.md',
            'docs/security/incident-response.md'
        ]
        
        # Check directories
        for directory in required_directories:
            path = self.project_root / directory
            if path.exists() and path.is_dir():
                self.validation_results['passed'].append(f"Directory exists: {directory}")
            else:
                self.validation_results['failed'].append(f"Missing directory: {directory}")
        
        # Check files
        for file_path in required_files:
            path = self.project_root / file_path
            if path.exists() and path.is_file():
                self.validation_results['passed'].append(f"File exists: {file_path}")
            else:
                self.validation_results['failed'].append(f"Missing file: {file_path}")

    def _validate_workflows(self) -> None:
        """Validate GitHub Actions workflows."""
        logger.info("Validating GitHub Actions workflows...")
        
        workflow_file = self.project_root / '.github/workflows/security-scan.yml'
        
        if not workflow_file.exists():
            self.validation_results['failed'].append("Security workflow file missing")
            return
        
        try:
            with open(workflow_file, 'r') as f:
                workflow_content = yaml.safe_load(f)
            
            # Check required workflow components
            required_components = [
                'on',  # Triggers
                'jobs',  # Job definitions
                'permissions'  # Required permissions
            ]
            
            for component in required_components:
                if component in workflow_content:
                    self.validation_results['passed'].append(f"Workflow has {component}")
                else:
                    self.validation_results['failed'].append(f"Workflow missing {component}")
            
            # Check for required jobs
            required_jobs = [
                'sast-scan',
                'secrets-scan', 
                'vulnerability-scan',
                'infrastructure-scan',
                'auto-remediation'
            ]
            
            jobs = workflow_content.get('jobs', {})
            for job in required_jobs:
                if job in jobs:
                    self.validation_results['passed'].append(f"Workflow has job: {job}")
                else:
                    self.validation_results['failed'].append(f"Workflow missing job: {job}")
                    
        except yaml.YAMLError as e:
            self.validation_results['failed'].append(f"Workflow YAML syntax error: {e}")
        except Exception as e:
            self.validation_results['failed'].append(f"Workflow validation error: {e}")

    def _validate_security_rules(self) -> None:
        """Validate security scanning rules."""
        logger.info("Validating security rules...")
        
        rules_dir = self.project_root / 'security/rules'
        rule_files = [
            'fastapi-security.yml',
            'nextjs-security.yml', 
            'gdpr-compliance.yml'
        ]
        
        for rule_file in rule_files:
            rule_path = rules_dir / rule_file
            
            if not rule_path.exists():
                self.validation_results['failed'].append(f"Missing rule file: {rule_file}")
                continue
            
            try:
                with open(rule_path, 'r') as f:
                    rules_content = yaml.safe_load(f)
                
                # Check rule structure
                if 'rules' in rules_content and isinstance(rules_content['rules'], list):
                    rule_count = len(rules_content['rules'])
                    self.validation_results['passed'].append(f"{rule_file}: {rule_count} rules loaded")
                    
                    # Validate individual rules
                    for i, rule in enumerate(rules_content['rules']):
                        required_fields = ['id', 'message', 'languages']
                        missing_fields = [field for field in required_fields if field not in rule]
                        
                        if missing_fields:
                            self.validation_results['warnings'].append(
                                f"{rule_file} rule {i}: missing fields {missing_fields}"
                            )
                else:
                    self.validation_results['failed'].append(f"{rule_file}: invalid rule structure")
                    
            except yaml.YAMLError as e:
                self.validation_results['failed'].append(f"{rule_file}: YAML syntax error: {e}")
            except Exception as e:
                self.validation_results['failed'].append(f"{rule_file}: validation error: {e}")

    def _validate_scripts(self) -> None:
        """Validate security scripts syntax and imports."""
        logger.info("Validating security scripts...")
        
        scripts = [
            'auto_remediate.py',
            'monitoring.py',
            'compliance.py',
            'config.py'
        ]
        
        scripts_dir = self.project_root / 'scripts/security'
        
        for script in scripts:
            script_path = scripts_dir / script
            
            if not script_path.exists():
                self.validation_results['failed'].append(f"Missing script: {script}")
                continue
            
            try:
                # Basic syntax validation
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Compile to check syntax
                compile(content, str(script_path), 'exec')
                self.validation_results['passed'].append(f"Script syntax valid: {script}")
                
                # Check for required imports
                if 'import' in content:
                    self.validation_results['passed'].append(f"Script has imports: {script}")
                
                # Check for main execution guard
                if 'if __name__ == \'__main__\':' in content:
                    self.validation_results['passed'].append(f"Script has main guard: {script}")
                else:
                    self.validation_results['warnings'].append(f"Script missing main guard: {script}")
                    
            except SyntaxError as e:
                self.validation_results['failed'].append(f"Script syntax error in {script}: {e}")
            except Exception as e:
                self.validation_results['failed'].append(f"Script validation error in {script}: {e}")

    def _validate_documentation(self) -> None:
        """Validate documentation completeness."""
        logger.info("Validating documentation...")
        
        docs_dir = self.project_root / 'docs/security'
        required_docs = [
            'README.md',
            'scanning-runbook.md',
            'remediation-procedures.md',
            'incident-response.md'
        ]
        
        for doc in required_docs:
            doc_path = docs_dir / doc
            
            if not doc_path.exists():
                self.validation_results['failed'].append(f"Missing documentation: {doc}")
                continue
            
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check minimum content length
                if len(content) > 1000:
                    self.validation_results['passed'].append(f"Documentation complete: {doc}")
                else:
                    self.validation_results['warnings'].append(f"Documentation may be incomplete: {doc}")
                
                # Check for required sections
                if doc == 'README.md':
                    required_sections = ['Overview', 'Quick Start', 'Tools & Scripts']
                    for section in required_sections:
                        if section.lower() in content.lower():
                            self.validation_results['passed'].append(f"README has section: {section}")
                        else:
                            self.validation_results['warnings'].append(f"README missing section: {section}")
                            
            except Exception as e:
                self.validation_results['failed'].append(f"Documentation validation error in {doc}: {e}")

    def _validate_environment(self) -> None:
        """Validate environment configuration."""
        logger.info("Validating environment...")
        
        # Check critical environment variables
        critical_env_vars = [
            'GITHUB_TOKEN'
        ]
        
        optional_env_vars = [
            'APPLICATIONINSIGHTS_CONNECTION_STRING',
            'SLACK_WEBHOOK_URL',
            'SECURITY_EMAIL_ALERTS'
        ]
        
        for var in critical_env_vars:
            if os.getenv(var):
                self.validation_results['passed'].append(f"Environment variable set: {var}")
            else:
                self.validation_results['failed'].append(f"Missing critical environment variable: {var}")
        
        for var in optional_env_vars:
            if os.getenv(var):
                self.validation_results['passed'].append(f"Optional environment variable set: {var}")
            else:
                self.validation_results['warnings'].append(f"Optional environment variable not set: {var}")
        
        # Check Python environment
        try:
            import requests
            import yaml
            import packaging
            self.validation_results['passed'].append("Required Python packages available")
        except ImportError as e:
            self.validation_results['failed'].append(f"Missing Python package: {e}")

    def _generate_summary(self) -> None:
        """Generate validation summary."""
        passed_count = len(self.validation_results['passed'])
        failed_count = len(self.validation_results['failed'])
        warning_count = len(self.validation_results['warnings'])
        
        total_checks = passed_count + failed_count + warning_count
        success_rate = (passed_count / total_checks * 100) if total_checks > 0 else 0
        
        logger.info(f"\n{'='*60}")
        logger.info("SECURITY SYSTEM VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Checks: {total_checks}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Warnings: {warning_count}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if failed_count > 0:
            logger.error(f"\n❌ FAILED CHECKS ({failed_count}):")
            for failure in self.validation_results['failed']:
                logger.error(f"  - {failure}")
        
        if warning_count > 0:
            logger.warning(f"\n⚠️  WARNINGS ({warning_count}):")
            for warning in self.validation_results['warnings']:
                logger.warning(f"  - {warning}")
        
        if failed_count == 0:
            logger.info("\n✅ All critical validations passed!")
            logger.info("Security remediation system is ready for deployment.")
        else:
            logger.error("\n❌ Validation failed. Please address the issues above before deployment.")

def main():
    """Main validation entry point."""
    try:
        validator = SecuritySystemValidator()
        results = validator.validate_all()
        
        # Exit with error code if any validations failed
        if results['failed']:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation script failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
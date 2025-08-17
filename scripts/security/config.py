#!/usr/bin/env python3
"""
Security System Configuration

Central configuration for the automated security remediation system.
"""

import os
from pathlib import Path
from typing import Dict, List, Any

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Security scanning configuration
SECURITY_CONFIG = {
    # Scan settings
    'scan_timeout': 600,  # 10 minutes
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'excluded_paths': [
        'node_modules',
        '__pycache__',
        '.git',
        'dist',
        'build',
        '.next',
        'coverage',
        'logs'
    ],
    
    # Auto-remediation settings
    'auto_remediation': {
        'enabled': True,
        'max_risk_score': 20,
        'safe_categories': [
            'dependency_update',
            'config_change',
            'logging_improvement',
            'security_headers'
        ],
        'excluded_packages': [
            'fastapi',
            'next',
            'react',
            'django',
            'flask'
        ]
    },
    
    # Compliance frameworks
    'compliance_frameworks': [
        'gdpr',
        'iso27001',
        'nist_csf',
        'owasp_asvs'
    ],
    
    # Notification settings
    'notifications': {
        'slack_webhook': os.getenv('SLACK_WEBHOOK_URL'),
        'email_alerts': os.getenv('SECURITY_EMAIL_ALERTS', '').split(','),
        'critical_threshold': 80
    },
    
    # Azure integration
    'azure': {
        'app_insights_key': os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'),
        'subscription_id': os.getenv('AZURE_SUBSCRIPTION_ID'),
        'resource_group': os.getenv('AZURE_RESOURCE_GROUP')
    }
}

# File patterns for different scan types
FILE_PATTERNS = {
    'python': ['**/*.py'],
    'typescript': ['**/*.ts', '**/*.tsx'],
    'javascript': ['**/*.js', '**/*.jsx'],
    'config': ['**/*.yml', '**/*.yaml', '**/*.json'],
    'docker': ['**/Dockerfile*', '**/docker-compose*.yml'],
    'terraform': ['**/*.tf', '**/*.tfvars']
}

# Security rules configuration
SECURITY_RULES = {
    'custom_rules_path': PROJECT_ROOT / 'security' / 'rules',
    'rule_files': [
        'fastapi-security.yml',
        'nextjs-security.yml',
        'gdpr-compliance.yml'
    ],
    'ignore_file': '.semgrepignore'
}

# Risk assessment thresholds
RISK_THRESHOLDS = {
    'safe': 0,
    'low': 20,
    'medium': 50,
    'high': 80,
    'critical': 100
}

def get_config() -> Dict[str, Any]:
    """Get complete security configuration."""
    return {
        'project_root': str(PROJECT_ROOT),
        'security': SECURITY_CONFIG,
        'file_patterns': FILE_PATTERNS,
        'rules': SECURITY_RULES,
        'risk_thresholds': RISK_THRESHOLDS
    }

def get_environment_config() -> Dict[str, str]:
    """Get environment-specific configuration."""
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'debug_mode': os.getenv('DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'github_token': os.getenv('GITHUB_TOKEN'),
        'azure_tenant_id': os.getenv('AZURE_TENANT_ID'),
        'azure_client_id': os.getenv('AZURE_CLIENT_ID'),
        'azure_client_secret': os.getenv('AZURE_CLIENT_SECRET')
    }

def validate_configuration() -> List[str]:
    """Validate security configuration and return any issues."""
    issues = []
    
    # Check required environment variables
    required_env_vars = [
        'GITHUB_TOKEN',
        'APPLICATIONINSIGHTS_CONNECTION_STRING'
    ]
    
    for var in required_env_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")
    
    # Check if security rules exist
    rules_path = SECURITY_RULES['custom_rules_path']
    if not rules_path.exists():
        issues.append(f"Security rules directory not found: {rules_path}")
    
    for rule_file in SECURITY_RULES['rule_files']:
        rule_path = rules_path / rule_file
        if not rule_path.exists():
            issues.append(f"Security rule file not found: {rule_path}")
    
    return issues
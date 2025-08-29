#!/usr/bin/env python3
"""
CORS Configuration Helper

This script helps configure CORS origins for different environments,
ensuring secure configuration and preventing wildcard origins in production.
"""

import os
import sys
from typing import List, Set


def get_production_origins() -> List[str]:
    """Get the recommended production CORS origins based on Azure deployment"""
    return [
        # Azure Container Apps endpoints
        "https://web-cybermat-prd-aca.icystone-69c102b0.westeurope.azurecontainerapps.io",
        "https://web-cybermat-prd.azurecontainerapps.io",
        
        # Azure App Service endpoints (if applicable)
        "https://web-cybermat-prd.azurewebsites.net",
        
        # Custom domain (when configured)
        # "https://cybermaturity.example.com",
    ]


def get_staging_origins() -> List[str]:
    """Get the recommended staging CORS origins"""
    return [
        "https://web-cybermat-stg-aca.icystone-69c102b0.westeurope.azurecontainerapps.io",
        "https://web-cybermat-stg.azurecontainerapps.io",
        "https://web-cybermat-stg.azurewebsites.net",
    ]


def get_development_origins() -> List[str]:
    """Get the recommended development CORS origins"""
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8080",  # Alternative port
    ]


def validate_origins(origins: List[str], environment: str) -> tuple[bool, List[str]]:
    """
    Validate CORS origins for security issues
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for wildcard
    if "*" in origins:
        errors.append(f"ERROR: Wildcard origin (*) is not allowed in {environment}")
    
    # Check for localhost in production
    if environment.lower() in ["production", "prod"]:
        for origin in origins:
            if "localhost" in origin.lower() or "127.0.0.1" in origin:
                errors.append(f"ERROR: Local origin '{origin}' should not be in production")
            
            if not origin.startswith("https://"):
                errors.append(f"WARNING: Non-HTTPS origin '{origin}' in production")
    
    # Check for duplicates
    unique_origins = set(origins)
    if len(unique_origins) != len(origins):
        errors.append("WARNING: Duplicate origins detected")
    
    # Check for trailing slashes (should not have them)
    for origin in origins:
        if origin.endswith("/"):
            errors.append(f"WARNING: Origin '{origin}' should not have trailing slash")
    
    return (len([e for e in errors if e.startswith("ERROR")]) == 0, errors)


def generate_env_var(origins: List[str]) -> str:
    """Generate the environment variable value"""
    return ",".join(origins)


def main():
    """Main configuration helper"""
    print("🔒 CORS Configuration Helper")
    print("=" * 50)
    
    # Get current environment
    current_env = os.getenv("ENVIRONMENT", "development").lower()
    current_origins = os.getenv("API_ALLOWED_ORIGINS", "")
    
    print(f"\n📍 Current Environment: {current_env}")
    print(f"📍 Current Origins: {current_origins if current_origins else '(not set)'}")
    
    # Get recommended origins
    if current_env in ["production", "prod"]:
        recommended = get_production_origins()
    elif current_env in ["staging", "stage", "stg"]:
        recommended = get_staging_origins()
    else:
        recommended = get_development_origins()
    
    print(f"\n✅ Recommended origins for {current_env}:")
    for origin in recommended:
        print(f"   - {origin}")
    
    # Validate current configuration
    if current_origins:
        current_list = [o.strip() for o in current_origins.split(",") if o.strip()]
        is_valid, errors = validate_origins(current_list, current_env)
        
        if errors:
            print("\n⚠️  Configuration Issues:")
            for error in errors:
                print(f"   {error}")
        
        if not is_valid:
            print("\n❌ Current configuration has security issues!")
    
    # Generate environment variable
    env_var = generate_env_var(recommended)
    print(f"\n📝 Set this environment variable:")
    print(f"   API_ALLOWED_ORIGINS={env_var}")
    
    # Platform-specific instructions
    print("\n🚀 Platform-specific setup:")
    print("\n   Azure Portal:")
    print(f"   az webapp config appsettings set --name api-cybermat-{current_env[:3]} \\")
    print(f"     --resource-group rg-cybermat-{current_env[:3]} \\")
    print(f'     --settings API_ALLOWED_ORIGINS="{env_var}"')
    
    print("\n   Docker/Local:")
    print(f'   export API_ALLOWED_ORIGINS="{env_var}"')
    
    print("\n   .env file:")
    print(f"   API_ALLOWED_ORIGINS={env_var}")
    
    # Security reminders
    print("\n🔐 Security Reminders:")
    print("   - Never use wildcard (*) in production")
    print("   - Always use HTTPS in production")
    print("   - Update origins when domains change")
    print("   - Remove unused/old origins regularly")
    print("   - Test CORS with actual cross-origin requests")


if __name__ == "__main__":
    main()
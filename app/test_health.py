#!/usr/bin/env python3
"""
Simple health check test for the API
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_health():
    """Test the health endpoint"""
    try:
        # Set minimal environment
        os.environ.setdefault('CI_MODE', '1')  # Lightweight mode
        os.environ.setdefault('DISABLE_ML', '1')  # Disable ML features
        os.environ.setdefault('LOG_LEVEL', 'INFO')
        
        print("Testing health endpoint...")
        
        # Import after setting environment
        from api.routes.version import health_check
        
        # Call health check
        result = await health_check()
        
        print(f"Health check result: {result}")
        
        if result.get("status") == "healthy":
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_health())
    sys.exit(0 if success else 1)
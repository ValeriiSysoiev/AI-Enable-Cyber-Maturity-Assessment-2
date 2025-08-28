#!/usr/bin/env python3
"""
Simple startup script for Azure App Service with comprehensive debugging
"""
import os
import sys
import subprocess
import traceback
import json

def debug_environment():
    """Debug environment variables and Python setup"""
    print("=== ENVIRONMENT DEBUG ===")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {json.dumps(sys.path[:5], indent=2)}")
    
    # Key environment variables
    env_vars = ['PORT', 'PYTHONPATH', 'DATA_BACKEND', 'AUTH_MODE', 'CI_MODE', 'DISABLE_ML']
    print(f"Environment variables:")
    for var in env_vars:
        print(f"  {var}: {os.environ.get(var, 'NOT_SET')}")

def test_imports():
    """Test critical imports step by step"""
    print("\n=== IMPORT TESTING ===")
    
    # Test basic imports
    test_modules = [
        "config",
        "domain.models", 
        "domain.repository",
        "api.security",
        "api.routes.version"
    ]
    
    import_results = {}
    for module in test_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
            import_results[module] = "SUCCESS"
        except Exception as e:
            print(f"✗ {module}: {str(e)[:100]}")
            import_results[module] = str(e)
    
    # Test main app import
    try:
        print("\n=== TESTING MAIN APP ===")
        from api.main import app
        print("✓ Successfully imported api.main:app")
        
        # Check available routes
        routes = []
        route_errors = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f"✓ Found {len(routes)} routes")
        if len(routes) > 10:
            print("✓ Business routes available - API should be functional")
            print(f"Sample routes: {routes[:10]}")
        else:
            print("⚠️ Limited routes - may have loading issues")
            print(f"Available routes: {routes}")
        
        return True, len(routes)
        
    except Exception as e:
        print(f"✗ Failed to import main app: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False, 0

def main():
    # Get port from environment, default to 8000
    port = os.environ.get('PORT', '8000')
    
    # Validate port is numeric
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError("Port out of range")
    except ValueError:
        print(f"Invalid PORT value: {port}, using default 8000")
        port = "8000"
    
    print(f"🚀 Starting API server on port {port}")
    
    # Debug environment
    debug_environment()
    
    # Test imports
    app_imported, route_count = test_imports()
    
    if not app_imported:
        print("\n❌ CRITICAL: Cannot import main application!")
        print("🔄 Attempting to start anyway - uvicorn may provide more details...")
    elif route_count < 10:
        print(f"\n⚠️ WARNING: Only {route_count} routes loaded")
        print("🔍 This indicates route loading issues")
    else:
        print(f"\n✅ SUCCESS: {route_count} routes loaded - API should be fully functional")
    
    # Start uvicorn with verbose logging
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "api.main:app", 
        "--host", "0.0.0.0", 
        "--port", port,
        "--log-level", "debug",  # Maximum verbosity
        "--access-log"           # Enable access logging
    ]
    
    print(f"\n=== STARTING UVICORN ===")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 50)
    
    # Execute uvicorn
    os.execvp(sys.executable, cmd)

if __name__ == "__main__":
    main()


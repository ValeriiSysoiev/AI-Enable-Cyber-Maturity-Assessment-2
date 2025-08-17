#!/usr/bin/env python3
"""
Test runner script for RAG functionality.
Run this to execute all RAG-related tests.
"""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all RAG tests"""
    test_dir = Path(__file__).parent
    app_dir = test_dir.parent
    
    # Add app directory to Python path
    sys.path.insert(0, str(app_dir.parent))
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_dir / "test_rag_endpoints.py"),
            "-v",
            "--tb=short",
            "--no-header"
        ], capture_output=True, text=True, cwd=str(app_dir.parent))
        
        print("RAG Tests Output:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print("=" * 50)
            print(result.stderr)
        
        if result.returncode == 0:
            print("\nAll RAG tests passed! ✓")
        else:
            print(f"\nSome tests failed (exit code: {result.returncode}) ✗")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
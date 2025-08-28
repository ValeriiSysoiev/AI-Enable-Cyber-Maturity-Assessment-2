#!/usr/bin/env python3
"""
Test script for key API endpoints.
Tests both minimal fallback and full FastAPI endpoints.
"""
import requests
import json
import sys
from datetime import datetime


def test_endpoint(url: str, expected_status: int = 200, description: str = ""):
    """Test a single endpoint and return result."""
    try:
        print(f"Testing {description}: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == expected_status:
            print(f"  ✓ Status: {response.status_code}")
            
            # Try to parse JSON response
            try:
                data = response.json()
                print(f"  ✓ Valid JSON response")
                
                # Print key fields if they exist
                if 'status' in data:
                    print(f"  ✓ Status: {data['status']}")
                if 'version' in data:
                    print(f"  ✓ Version: {data['version']}")
                if 'git_sha' in data:
                    print(f"  ✓ Git SHA: {data['git_sha']}")
                if 'timestamp' in data:
                    print(f"  ✓ Timestamp: {data['timestamp']}")
                    
                return True, data
            except json.JSONDecodeError:
                print(f"  ! Non-JSON response: {response.text[:200]}")
                return False, response.text
                
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {str(e)}")
        return False, None
    except Exception as e:
        print(f"  ✗ Test error: {str(e)}")
        return False, None


def main():
    """Run endpoint tests against local server."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("API Endpoint Testing")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Test time: {datetime.now().isoformat()}")
    print()
    
    # Define test cases
    test_cases = [
        # Health endpoints
        ("/api/health", 200, "Health Check"),
        ("/health", 200, "Health Check (alt)"),
        
        # Version and system info
        ("/api/version", 200, "Version Info"),
        
        # Features
        ("/api/features", 200, "Feature Flags"),
        
        # Admin status
        ("/api/admin/status", 200, "Admin Status"),
        
        # Presets
        ("/api/presets", 200, "List Presets"),
        
        # Engagements (may require auth)
        ("/api/engagements", 200, "List Engagements"),
        
        # Performance metrics (may require auth)
        ("/api/performance/metrics", 200, "Performance Metrics"),
    ]
    
    # Run tests
    results = []
    for endpoint, expected_status, description in test_cases:
        url = f"{base_url}{endpoint}"
        success, data = test_endpoint(url, expected_status, description)
        results.append((endpoint, success, data))
        print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    # List failed tests
    failed_tests = [(endpoint, data) for endpoint, success, data in results if not success]
    if failed_tests:
        print("Failed tests:")
        for endpoint, error in failed_tests:
            print(f"  ✗ {endpoint}: {error}")
    else:
        print("All tests passed! ✓")
    
    # Return exit code
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
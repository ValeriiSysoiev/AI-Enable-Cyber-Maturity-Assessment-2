#!/usr/bin/env python3
"""
Test script to verify admin endpoints are working properly.
This script can be used to test both local and deployed instances.
"""

import requests
import json
import sys
import os
from typing import Dict, Any


def test_admin_endpoints(base_url: str, admin_email: str) -> Dict[str, Any]:
    """Test admin endpoints with proper authentication headers."""
    
    results = {
        "status_endpoint": {"tested": False, "success": False, "error": None, "response": None},
        "auth_diagnostics_endpoint": {"tested": False, "success": False, "error": None, "response": None}
    }
    
    # Headers for admin authentication
    headers = {
        "X-User-Email": admin_email,
        "X-Engagement-ID": "default",
        "Content-Type": "application/json"
    }
    
    # Test /api/admin/status endpoint
    try:
        response = requests.get(f"{base_url}/api/admin/status", headers=headers, timeout=30)
        results["status_endpoint"]["tested"] = True
        
        if response.status_code == 200:
            results["status_endpoint"]["success"] = True
            results["status_endpoint"]["response"] = response.json()
        else:
            results["status_endpoint"]["error"] = f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        results["status_endpoint"]["tested"] = True
        results["status_endpoint"]["error"] = str(e)
    
    # Test /api/admin/auth-diagnostics endpoint
    try:
        response = requests.get(f"{base_url}/api/admin/auth-diagnostics", headers=headers, timeout=30)
        results["auth_diagnostics_endpoint"]["tested"] = True
        
        if response.status_code == 200:
            results["auth_diagnostics_endpoint"]["success"] = True
            results["auth_diagnostics_endpoint"]["response"] = response.json()
        else:
            results["auth_diagnostics_endpoint"]["error"] = f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        results["auth_diagnostics_endpoint"]["tested"] = True
        results["auth_diagnostics_endpoint"]["error"] = str(e)
    
    return results


def print_results(results: Dict[str, Any], base_url: str):
    """Print formatted test results."""
    print(f"\n=== Admin Endpoints Test Results ===")
    print(f"Base URL: {base_url}")
    print(f"{'='*50}")
    
    for endpoint, data in results.items():
        status = "✅ PASS" if data["success"] else "❌ FAIL" if data["tested"] else "⏭ SKIP"
        print(f"\n{endpoint.replace('_', ' ').title()}: {status}")
        
        if data["tested"]:
            if data["success"]:
                print(f"  Response: {json.dumps(data['response'], indent=2)[:200]}...")
            else:
                print(f"  Error: {data['error']}")
        else:
            print("  Endpoint not tested")


def test_basic_connectivity(base_url: str) -> bool:
    """Test basic API connectivity."""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        return response.status_code == 200
    except:
        return False


def main():
    """Main test execution."""
    # Configuration
    base_urls = [
        "https://api-aaa-demo.bravewater-3d70a706.canadacentral.azurecontainerapps.io",
        "http://localhost:8000"
    ]
    admin_email = "va.sysoiev@audit3a.com"
    
    # Check command line arguments
    if len(sys.argv) > 1:
        base_urls = [sys.argv[1]]
    
    if len(sys.argv) > 2:
        admin_email = sys.argv[2]
    
    print("🧪 Admin Endpoints Verification Script")
    print("=====================================")
    
    for base_url in base_urls:
        print(f"\nTesting: {base_url}")
        
        # Test basic connectivity first
        if test_basic_connectivity(base_url):
            print("✅ Basic API connectivity: OK")
            
            # Run admin endpoint tests
            results = test_admin_endpoints(base_url, admin_email)
            print_results(results, base_url)
            
            # Summary
            all_success = all(data["success"] for data in results.values() if data["tested"])
            if all_success:
                print(f"\n🎉 All admin endpoints are working properly!")
                return 0
            else:
                print(f"\n⚠️  Some admin endpoints have issues - see details above")
        else:
            print(f"❌ Basic API connectivity: FAILED")
            print(f"   Cannot reach {base_url}/health")
            print(f"   This suggests the API is not deployed or accessible")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
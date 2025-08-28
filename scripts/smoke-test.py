#!/usr/bin/env python3
"""
Comprehensive Smoke Test Suite for API
Validates critical endpoints and functionality after deployment
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiohttp
import argparse


class SmokeTestResult:
    def __init__(self, name: str, passed: bool, message: str, duration: float, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.details = details or {}
        self.timestamp = datetime.now()


class SmokeTestRunner:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results: List[SmokeTestResult] = []
    
    async def run_test(self, name: str, test_func) -> SmokeTestResult:
        """Run a single test and return result"""
        start_time = time.time()
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            if isinstance(result, tuple):
                passed, message, details = result
            else:
                passed, message, details = result, "Test passed", {}
            
            return SmokeTestResult(name, passed, message, duration, details)
            
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(name, False, f"Test failed with exception: {str(e)}", duration)
    
    async def test_basic_endpoints(self) -> Tuple[bool, str, Dict]:
        """Test basic health endpoints"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as session:
            endpoints = ['/health', '/version', '/']
            results = {}
            
            for endpoint in endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        results[endpoint] = {
                            'status': response.status,
                            'response_time': response.headers.get('X-Response-Time', 'N/A')
                        }
                        if response.status != 200:
                            return False, f"Endpoint {endpoint} returned {response.status}", results
                except Exception as e:
                    results[endpoint] = {'error': str(e)}
                    return False, f"Failed to reach {endpoint}: {str(e)}", results
            
            return True, "All basic endpoints responding", results
    
    async def test_openapi_schema(self) -> Tuple[bool, str, Dict]:
        """Test OpenAPI schema and count endpoints"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as session:
            try:
                async with session.get(f"{self.base_url}/openapi.json") as response:
                    if response.status != 200:
                        return False, f"OpenAPI schema unavailable (status: {response.status})", {}
                    
                    schema = await response.json()
                    paths = list(schema.get('paths', {}).keys())
                    
                    total_endpoints = len(paths)
                    api_endpoints = [p for p in paths if p.startswith('/api/')]
                    business_endpoints = [p for p in api_endpoints if p not in ['/', '/health', '/version']]
                    
                    # Critical endpoints that should be present
                    critical_endpoints = ['/api/features', '/api/engagements', '/api/domain-assessments']
                    critical_present = [ep for ep in critical_endpoints if any(ep in p for p in paths)]
                    
                    details = {
                        'total_endpoints': total_endpoints,
                        'api_endpoints': len(api_endpoints),
                        'business_endpoints': len(business_endpoints), 
                        'critical_present': critical_present,
                        'sample_endpoints': sorted(paths)[:10]
                    }
                    
                    if total_endpoints < 10:
                        return False, f"Insufficient endpoints loaded: {total_endpoints} (expected >10)", details
                    
                    if len(critical_present) == 0:
                        return False, "No critical business endpoints found", details
                    
                    return True, f"API schema healthy with {total_endpoints} endpoints", details
                    
            except Exception as e:
                return False, f"Failed to fetch OpenAPI schema: {str(e)}", {}
    
    async def test_diagnostic_endpoints(self) -> Tuple[bool, str, Dict]:
        """Test diagnostic endpoints if available"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as session:
            endpoints = ['/api/diagnostic', '/api/router-status']
            results = {}
            available_count = 0
            
            for endpoint in endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                results[endpoint] = {'status': 'available', 'data': data}
                                available_count += 1
                            except:
                                results[endpoint] = {'status': 'available', 'data': 'non-json'}
                                available_count += 1
                        else:
                            results[endpoint] = {'status': f'unavailable ({response.status})'}
                except Exception as e:
                    results[endpoint] = {'error': str(e)}
            
            if available_count == 0:
                return False, "No diagnostic endpoints available", results
            
            return True, f"{available_count}/2 diagnostic endpoints available", results
    
    async def test_cors_headers(self) -> Tuple[bool, str, Dict]:
        """Test CORS configuration"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as session:
            try:
                headers = {'Origin': 'https://test.example.com'}
                async with session.options(f"{self.base_url}/health", headers=headers) as response:
                    cors_headers = {
                        'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                        'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                        'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                    }
                    
                    has_cors = any(cors_headers.values())
                    
                    return True, f"CORS headers {'present' if has_cors else 'not configured'}", cors_headers
                    
            except Exception as e:
                return False, f"CORS test failed: {str(e)}", {}
    
    async def test_performance_basic(self) -> Tuple[bool, str, Dict]:
        """Test basic performance of health endpoint"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as session:
            times = []
            errors = 0
            
            for i in range(5):
                try:
                    start = time.time()
                    async with session.get(f"{self.base_url}/health") as response:
                        duration = time.time() - start
                        times.append(duration)
                        if response.status != 200:
                            errors += 1
                except Exception:
                    errors += 1
                    
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            if not times:
                return False, "All requests failed", {'errors': errors}
            
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            details = {
                'avg_response_time': round(avg_time * 1000, 2),  # ms
                'max_response_time': round(max_time * 1000, 2),  # ms
                'errors': errors,
                'success_rate': f"{((5-errors)/5)*100:.1f}%"
            }
            
            if avg_time > 2.0:  # 2 second threshold
                return False, f"Average response time too slow: {avg_time*1000:.0f}ms", details
            
            if errors > 1:  # Allow 1 error out of 5
                return False, f"Too many errors: {errors}/5", details
            
            return True, f"Performance acceptable (avg: {avg_time*1000:.0f}ms)", details
    
    async def run_all_tests(self) -> Dict:
        """Run all smoke tests"""
        print(f"🔍 Starting smoke tests for {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("Basic Endpoints", self.test_basic_endpoints),
            ("OpenAPI Schema", self.test_openapi_schema), 
            ("Diagnostic Endpoints", self.test_diagnostic_endpoints),
            ("CORS Configuration", self.test_cors_headers),
            ("Basic Performance", self.test_performance_basic),
        ]
        
        tasks = [self.run_test(name, test_func) for name, test_func in tests]
        results = await asyncio.gather(*tasks)
        
        # Print results
        passed = 0
        failed = 0
        
        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration = f"{result.duration*1000:.0f}ms"
            print(f"{status} {result.name:20} ({duration:>6}) - {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
            
            if result.passed:
                passed += 1
            else:
                failed += 1
        
        print("=" * 60)
        print(f"📊 Results: {passed} passed, {failed} failed, {passed+failed} total")
        
        # Summary
        overall_status = "PASS" if failed == 0 else "FAIL"
        critical_passed = any("OpenAPI Schema" in r.name and r.passed for r in results)
        
        summary = {
            'overall_status': overall_status,
            'passed': passed,
            'failed': failed,
            'total': passed + failed,
            'critical_passed': critical_passed,
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'duration_ms': round(r.duration * 1000, 2),
                    'details': r.details
                }
                for r in results
            ]
        }
        
        return summary


async def main():
    parser = argparse.ArgumentParser(description='Run API smoke tests')
    parser.add_argument('--url', required=True, help='Base URL of the API')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file for JSON results')
    parser.add_argument('--fail-fast', action='store_true', help='Exit on first failure')
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(args.url, args.timeout)
    summary = await runner.run_all_tests()
    
    # Write JSON output if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"📄 Results written to {args.output}")
    
    # Print final status
    if summary['overall_status'] == 'PASS':
        print("\n🎉 All smoke tests passed! API is healthy.")
        sys.exit(0)
    else:
        print(f"\n💥 {summary['failed']} tests failed. API may have issues.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
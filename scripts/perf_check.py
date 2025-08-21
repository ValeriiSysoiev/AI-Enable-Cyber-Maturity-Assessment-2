#!/usr/bin/env python3
"""
Performance budget checking for CI/CD including UI grid operations
Validates that grid operations meet p95 < 2s performance targets
"""
import asyncio
import aiohttp
import json
import sys
import time
import os
import statistics
from typing import Dict, List, Any, Optional
import argparse

class PerformanceBudget:
    """Performance budget checker with configurable thresholds"""
    
    def __init__(self, base_url: str, enable_grid_tests: bool = False):
        self.base_url = base_url.rstrip('/')
        self.results: List[Dict[str, Any]] = []
        self.enable_grid_tests = enable_grid_tests
        self.grid_results: List[Dict[str, Any]] = []
        
        # Performance thresholds
        self.p95_threshold_ms = float(os.getenv('PERF_GRID_OPERATIONS_P95_THRESHOLD_MS', 2000))
        self.test_iterations = int(os.getenv('PERF_TEST_ITERATIONS', 5))
        
        # Default performance budgets (in milliseconds)
        self.budgets = {
            '/health': 200,           # Health check should be fast
            '/docs': 1000,            # API docs acceptable load time
            '/projects': 2000,        # Read API with reasonable limit
            '/presets/': 1500,        # Presets should load quickly
        }
        
        # Grid operation endpoints and their test configurations
        self.grid_operations = {
            '/api/roadmap/resource-profile/calculate': {
                'method': 'POST',
                'payload': {
                    "initiatives": [{
                        "name": "Test Initiative",
                        "t_shirt_size": "M",
                        "duration_weeks": 24,
                        "type": "security_implementation"
                    }],
                    "wave_duration_weeks": 12
                },
                'budget_ms': self.p95_threshold_ms
            },
            '/api/roadmap/resource-profile/gantt': {
                'method': 'POST',
                'payload': {
                    "include_resource_overlay": True,
                    "include_skill_heatmap": True
                },
                'budget_ms': self.p95_threshold_ms
            },
            '/api/roadmap/resource-profile/wave-overlay': {
                'method': 'POST',
                'payload': {
                    "planning_horizon_weeks": 52,
                    "aggregate_by": "month"
                },
                'budget_ms': self.p95_threshold_ms
            },
            '/api/roadmap/resource-profile/export': {
                'method': 'POST',
                'payload': {
                    "export_format": "detailed",
                    "include_skills": True,
                    "include_costs": True
                },
                'budget_ms': self.p95_threshold_ms
            }
        }
    
    async def check_endpoint(
        self, 
        session: aiohttp.ClientSession, 
        endpoint: str, 
        budget: int
    ) -> Dict[str, Any]:
        """Check single endpoint performance against budget"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            async with session.get(url, timeout=10) as response:
                await response.text()  # Read response body
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                result = {
                    'endpoint': endpoint,
                    'url': url,
                    'status_code': response.status,
                    'response_time_ms': round(response_time, 2),
                    'budget_ms': budget,
                    'within_budget': response_time <= budget,
                    'performance_ratio': round(response_time / budget, 2)
                }
                
                print(f"{'✅' if result['within_budget'] else '❌'} {endpoint}: "
                      f"{result['response_time_ms']}ms (budget: {budget}ms)")
                
                return result
                
        except Exception as e:
            result = {
                'endpoint': endpoint,
                'url': url,
                'error': str(e),
                'within_budget': False,
                'performance_ratio': float('inf')
            }
            
            print(f"❌ {endpoint}: ERROR - {str(e)}")
            return result
    
    async def check_grid_operation(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check grid operation performance with multiple iterations"""
        url = f"{self.base_url}{endpoint}"
        method = config['method']
        payload = config['payload']
        budget_ms = config['budget_ms']
        
        durations = []
        errors = []
        
        print(f"🧪 Testing {endpoint} ({self.test_iterations} iterations)...")
        
        try:
            for i in range(self.test_iterations):
                start_time = time.time()
                
                try:
                    if method == 'POST':
                        async with session.post(url, json=payload, timeout=30) as response:
                            await response.read()
                            status_code = response.status
                    else:  # GET
                        async with session.get(url, params=payload, timeout=30) as response:
                            await response.read()
                            status_code = response.status
                    
                    duration_ms = (time.time() - start_time) * 1000
                    durations.append(duration_ms)
                    
                    # Skip auth errors for testing
                    if status_code not in [401, 403]:
                        print(f"  Iteration {i+1}: {duration_ms:.1f}ms")
                    
                except Exception as e:
                    errors.append(str(e))
                    print(f"  Iteration {i+1}: ERROR - {str(e)}")
            
            if not durations:
                return {
                    'endpoint': endpoint,
                    'url': url,
                    'method': method,
                    'error': f"All {self.test_iterations} iterations failed",
                    'within_budget': False,
                    'p95_ms': float('inf'),
                    'budget_ms': budget_ms
                }
            
            # Calculate P95
            durations.sort()
            p95_index = int(len(durations) * 0.95)
            p95_ms = durations[p95_index] if p95_index < len(durations) else durations[-1]
            
            within_budget = p95_ms <= budget_ms
            
            result = {
                'endpoint': endpoint,
                'url': url,
                'method': method,
                'iterations': len(durations),
                'p95_ms': round(p95_ms, 2),
                'avg_ms': round(sum(durations) / len(durations), 2),
                'min_ms': round(min(durations), 2),
                'max_ms': round(max(durations), 2),
                'budget_ms': budget_ms,
                'within_budget': within_budget,
                'performance_ratio': round(p95_ms / budget_ms, 2),
                'errors': len(errors),
                'error_rate': round(len(errors) / (len(durations) + len(errors)), 2)
            }
            
            status_icon = '✅' if within_budget else '❌'
            print(f"{status_icon} {endpoint}: P95={p95_ms:.1f}ms (budget: {budget_ms}ms)")
            
            return result
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'url': url,
                'method': method,
                'error': str(e),
                'within_budget': False,
                'p95_ms': float('inf'),
                'budget_ms': budget_ms
            }
    
    async def run_grid_performance_tests(self) -> Dict[str, Any]:
        """Run grid operation performance tests"""
        if not self.enable_grid_tests:
            return {'enabled': False, 'message': 'Grid tests disabled'}
        
        print(f"\n🎯 Grid Operations Performance Tests (P95 < {self.p95_threshold_ms}ms)")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Test all grid operations
            tasks = [
                self.check_grid_operation(session, endpoint, config)
                for endpoint, config in self.grid_operations.items()
            ]
            
            self.grid_results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Calculate summary
        total_tests = len(self.grid_results)
        passed_tests = sum(1 for r in self.grid_results if r.get('within_budget', False))
        failed_tests = total_tests - passed_tests
        
        # Calculate overall P95
        all_p95s = [r['p95_ms'] for r in self.grid_results 
                   if isinstance(r.get('p95_ms'), (int, float)) and r['p95_ms'] != float('inf')]
        
        overall_p95 = statistics.quantiles(all_p95s, n=20)[18] if all_p95s else float('inf')
        
        summary = {
            'enabled': True,
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0,
            'overall_p95_ms': round(overall_p95, 2) if overall_p95 != float('inf') else 'N/A',
            'p95_threshold_ms': self.p95_threshold_ms,
            'results': self.grid_results
        }
        
        # Print summary
        print(f"\n📊 Grid Performance Summary")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Overall P95: {summary['overall_p95_ms']}ms (threshold: {self.p95_threshold_ms}ms)")
        
        return summary
    
    def should_skip_performance_checks(self) -> bool:
        """Check if performance checks should be skipped for docs-only changes"""
        # Check environment variable
        if os.getenv('SKIP_PERFORMANCE_CHECKS', '').lower() == 'true':
            return True
        
        # Check if this is a docs-only change
        docs_only = os.getenv('DOCS_ONLY_CHANGE', '').lower() == 'true'
        if docs_only:
            print("ℹ️ Skipping performance checks for docs-only changes")
            return True
        
        return False
    
    async def run_performance_check(self) -> Dict[str, Any]:
        """Run performance checks against all configured endpoints"""
        print(f"🏁 Performance Budget Check - {self.base_url}")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Check all endpoints in parallel
            tasks = [
                self.check_endpoint(session, endpoint, budget)
                for endpoint, budget in self.budgets.items()
            ]
            
            self.results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Run grid performance tests if enabled
        grid_summary = {}
        if self.enable_grid_tests:
            grid_summary = await self.run_grid_performance_tests()
        
        # Calculate summary
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.get('within_budget', False))
        failed_checks = total_checks - passed_checks
        
        summary = {
            'base_url': self.base_url,
            'total_checks': total_checks,
            'passed': passed_checks,
            'failed': failed_checks,
            'success_rate': round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
            'results': self.results,
            'grid_tests': grid_summary,
            'timestamp': time.time()
        }
        
        # Print summary
        print("\n📊 Performance Summary")
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {failed_checks}")
        print(f"Success Rate: {summary['success_rate']}%")
        
        return summary
    
    def check_regression_threshold(self, threshold: float = 20.0) -> bool:
        """Check if any endpoint exceeded regression threshold"""
        for result in self.results:
            if not result.get('within_budget', False):
                ratio = result.get('performance_ratio', 0)
                if ratio > (1 + threshold / 100):  # e.g., 1.20 for 20% threshold
                    print(f"🚨 Regression detected: {result['endpoint']} "
                          f"exceeded budget by {(ratio - 1) * 100:.1f}%")
                    return False
        return True

async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Performance Budget Checker')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Base URL to test (default: http://localhost:8000)')
    parser.add_argument('--threshold', type=float, default=20.0,
                       help='Regression threshold percentage (default: 20.0)')
    parser.add_argument('--output', help='Output file for results (JSON)')
    parser.add_argument('--fail-on-regression', action='store_true',
                       help='Exit with error code if regression detected')
    parser.add_argument('--enable-grid-tests', action='store_true',
                       help='Enable grid operation performance tests')
    parser.add_argument('--skip-docs-only', action='store_true',
                       help='Skip tests for docs-only changes')
    parser.add_argument('--iterations', type=int, default=5,
                       help='Number of test iterations for grid tests (default: 5)')
    parser.add_argument('--p95-threshold', type=float,
                       help='P95 threshold in milliseconds (overrides environment)')
    
    args = parser.parse_args()
    
    # Check if we should skip performance checks
    if args.skip_docs_only and os.getenv('DOCS_ONLY_CHANGE', '').lower() == 'true':
        print("ℹ️ Skipping performance checks for docs-only changes")
        return
    
    # Override environment variables if provided
    if args.p95_threshold:
        os.environ['PERF_GRID_OPERATIONS_P95_THRESHOLD_MS'] = str(args.p95_threshold)
    if args.iterations:
        os.environ['PERF_TEST_ITERATIONS'] = str(args.iterations)
    
    # Run performance check
    checker = PerformanceBudget(args.url, enable_grid_tests=args.enable_grid_tests)
    
    # Check if we should skip all checks
    if checker.should_skip_performance_checks():
        return
    
    summary = await checker.run_performance_check()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Check for regressions
    if args.fail_on_regression:
        # Check basic performance budget
        if not checker.check_regression_threshold(args.threshold):
            print("\n💥 Performance regression detected - failing CI")
            sys.exit(1)
        elif summary['failed'] > 0:
            print("\n💥 Performance budget violations detected - failing CI")
            sys.exit(1)
        
        # Check grid test failures if enabled
        grid_tests = summary.get('grid_tests', {})
        if grid_tests.get('enabled', False) and grid_tests.get('failed', 0) > 0:
            print("\n💥 Grid performance tests failed - failing CI")
            print(f"Grid tests: {grid_tests['failed']}/{grid_tests['total_tests']} failed")
            sys.exit(1)
    
    # Print final summary
    grid_info = ""
    if summary.get('grid_tests', {}).get('enabled', False):
        grid_tests = summary['grid_tests']
        grid_info = f" | Grid: {grid_tests['success_rate']}%"
    
    print(f"\n🎉 Performance check complete - Basic: {summary['success_rate']}%{grid_info}")

if __name__ == '__main__':
    asyncio.run(main())
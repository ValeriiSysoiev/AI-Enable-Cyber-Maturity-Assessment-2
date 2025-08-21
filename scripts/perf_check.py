#!/usr/bin/env python3
"""
Lightweight performance budget checking for CI/CD
"""
import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, List, Any
import argparse

class PerformanceBudget:
    """Performance budget checker with configurable thresholds"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results: List[Dict[str, Any]] = []
        
        # Default performance budgets (in milliseconds)
        self.budgets = {
            '/health': 200,           # Health check should be fast
            '/docs': 1000,            # API docs acceptable load time
            '/projects': 2000,        # Read API with reasonable limit
            '/presets/': 1500,        # Presets should load quickly
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
    
    args = parser.parse_args()
    
    # Run performance check
    checker = PerformanceBudget(args.url)
    summary = await checker.run_performance_check()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Check for regressions
    if args.fail_on_regression:
        if not checker.check_regression_threshold(args.threshold):
            print("\n💥 Performance regression detected - failing CI")
            sys.exit(1)
        elif summary['failed'] > 0:
            print("\n💥 Performance budget violations detected - failing CI")
            sys.exit(1)
    
    print(f"\n🎉 Performance check complete - {summary['success_rate']}% success rate")

if __name__ == '__main__':
    asyncio.run(main())
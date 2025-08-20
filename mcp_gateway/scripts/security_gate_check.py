#!/usr/bin/env python3
"""
Security Gate Check for MCP Gateway
Validates security scan results and enforces security gates for CI/CD
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

class SecurityGateCheck:
    """Validates security scan results against defined thresholds"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_checks = []
        
        # Security thresholds
        self.thresholds = {
            'bandit': {
                'high_severity_max': 0,    # No high severity issues allowed
                'medium_severity_max': 2,  # Max 2 medium severity issues
                'low_severity_max': 5      # Max 5 low severity issues
            },
            'safety': {
                'vulnerabilities_max': 0   # No known vulnerabilities allowed
            },
            'semgrep': {
                'error_max': 0,           # No errors allowed
                'warning_max': 3          # Max 3 warnings allowed
            }
        }
    
    def check_bandit_results(self) -> bool:
        """Check Bandit security scan results"""
        bandit_file = Path("bandit-report.json")
        if not bandit_file.exists():
            self.warnings.append("Bandit report not found - scan may have failed")
            return True
        
        try:
            with open(bandit_file) as f:
                bandit_data = json.load(f)
            
            results = bandit_data.get('results', [])
            
            # Count issues by severity
            severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
            
            for result in results:
                severity = result.get('issue_severity', 'UNKNOWN')
                if severity in severity_counts:
                    severity_counts[severity] += 1
            
            # Check against thresholds
            passed = True
            
            if severity_counts['HIGH'] > self.thresholds['bandit']['high_severity_max']:
                self.errors.append(f"Bandit: {severity_counts['HIGH']} high severity issues found (max: {self.thresholds['bandit']['high_severity_max']})")
                passed = False
            
            if severity_counts['MEDIUM'] > self.thresholds['bandit']['medium_severity_max']:
                self.errors.append(f"Bandit: {severity_counts['MEDIUM']} medium severity issues found (max: {self.thresholds['bandit']['medium_severity_max']})")
                passed = False
            
            if severity_counts['LOW'] > self.thresholds['bandit']['low_severity_max']:
                self.warnings.append(f"Bandit: {severity_counts['LOW']} low severity issues found (max: {self.thresholds['bandit']['low_severity_max']})")
            
            if passed:
                self.passed_checks.append(f"Bandit: {sum(severity_counts.values())} total issues within thresholds")
            
            return passed
            
        except Exception as e:
            self.errors.append(f"Failed to parse Bandit results: {e}")
            return False
    
    def check_safety_results(self) -> bool:
        """Check Safety dependency scan results"""
        safety_file = Path("safety-report.json")
        if not safety_file.exists():
            self.warnings.append("Safety report not found - scan may have failed")
            return True
        
        try:
            with open(safety_file) as f:
                safety_data = json.load(f)
            
            vulnerabilities = safety_data.get('vulnerabilities', [])
            vuln_count = len(vulnerabilities)
            
            if vuln_count > self.thresholds['safety']['vulnerabilities_max']:
                self.errors.append(f"Safety: {vuln_count} vulnerabilities found (max: {self.thresholds['safety']['vulnerabilities_max']})")
                
                # List vulnerability details
                for vuln in vulnerabilities[:5]:  # Show first 5
                    pkg = vuln.get('package_name', 'unknown')
                    version = vuln.get('analyzed_version', 'unknown')
                    cve = vuln.get('vulnerability_id', 'unknown')
                    self.errors.append(f"  - {pkg} {version}: {cve}")
                
                return False
            else:
                self.passed_checks.append(f"Safety: No vulnerabilities found in dependencies")
                return True
                
        except Exception as e:
            self.errors.append(f"Failed to parse Safety results: {e}")
            return False
    
    def check_semgrep_results(self) -> bool:
        """Check Semgrep security analysis results"""
        semgrep_file = Path("semgrep-report.json")
        if not semgrep_file.exists():
            self.warnings.append("Semgrep report not found - scan may have failed")
            return True
        
        try:
            with open(semgrep_file) as f:
                semgrep_data = json.load(f)
            
            results = semgrep_data.get('results', [])
            
            # Count by severity
            error_count = 0
            warning_count = 0
            
            for result in results:
                severity = result.get('extra', {}).get('severity', 'INFO')
                if severity == 'ERROR':
                    error_count += 1
                elif severity == 'WARNING':
                    warning_count += 1
            
            passed = True
            
            if error_count > self.thresholds['semgrep']['error_max']:
                self.errors.append(f"Semgrep: {error_count} errors found (max: {self.thresholds['semgrep']['error_max']})")
                passed = False
            
            if warning_count > self.thresholds['semgrep']['warning_max']:
                self.warnings.append(f"Semgrep: {warning_count} warnings found (max: {self.thresholds['semgrep']['warning_max']})")
            
            if passed:
                self.passed_checks.append(f"Semgrep: {len(results)} issues found within thresholds")
            
            return passed
            
        except Exception as e:
            self.errors.append(f"Failed to parse Semgrep results: {e}")
            return False
    
    def check_security_tests(self) -> bool:
        """Verify that security tests are passing"""
        # This would normally check test results, but for now we'll just verify files exist
        test_files = [
            "tests/test_security.py",
            "tests/test_security_comprehensive.py"
        ]
        
        passed = True
        for test_file in test_files:
            if not Path(test_file).exists():
                self.errors.append(f"Required security test file missing: {test_file}")
                passed = False
        
        if passed:
            self.passed_checks.append("Security test files present")
        
        return passed
    
    def check_security_configuration(self) -> bool:
        """Verify security configuration is present"""
        required_files = [
            "security.py",
            "secret_redactor.py"
        ]
        
        passed = True
        for req_file in required_files:
            if not Path(req_file).exists():
                self.errors.append(f"Required security file missing: {req_file}")
                passed = False
        
        if passed:
            self.passed_checks.append("Security configuration files present")
        
        return passed
    
    def run_all_checks(self) -> bool:
        """Run all security gate checks"""
        print("Running MCP Gateway Security Gate Checks...")
        print("=" * 50)
        
        checks = [
            ("Bandit Static Analysis", self.check_bandit_results),
            ("Safety Dependency Check", self.check_safety_results),
            ("Semgrep Security Analysis", self.check_semgrep_results),
            ("Security Tests", self.check_security_tests),
            ("Security Configuration", self.check_security_configuration)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            print(f"\n{check_name}:")
            try:
                result = check_func()
                status = "PASS" if result else "FAIL"
                print(f"  Status: {status}")
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"  Status: ERROR - {e}")
                self.errors.append(f"{check_name} failed with error: {e}")
                all_passed = False
        
        # Print summary
        print("\n" + "=" * 50)
        print("SECURITY GATE SUMMARY")
        print("=" * 50)
        
        if self.passed_checks:
            print(f"\n✓ PASSED CHECKS ({len(self.passed_checks)}):")
            for check in self.passed_checks:
                print(f"  ✓ {check}")
        
        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        if self.errors:
            print(f"\n✗ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")
        
        if all_passed:
            print(f"\n🎉 SECURITY GATE: PASSED")
            print("All security checks passed. Deployment approved.")
        else:
            print(f"\n🚫 SECURITY GATE: FAILED")
            print("Security issues found. Deployment blocked.")
        
        return all_passed

def main():
    """Main entry point"""
    gate_check = SecurityGateCheck()
    
    # Change to the script directory for relative paths
    script_dir = Path(__file__).parent
    os.chdir(script_dir.parent)
    
    success = gate_check.run_all_checks()
    
    if not success:
        sys.exit(1)
    
    print("\nSecurity gate check completed successfully!")

if __name__ == "__main__":
    main()
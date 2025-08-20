#!/usr/bin/env python3
"""
Security Controls Verification for MCP Gateway
Verifies that all required security controls are properly implemented
"""

import sys
import importlib.util
import inspect
from pathlib import Path
from typing import List, Tuple, Any

class SecurityControlVerifier:
    """Verifies implementation of required security controls"""
    
    def __init__(self):
        self.passed_controls = []
        self.failed_controls = []
        self.warnings = []
    
    def verify_security_validator(self) -> bool:
        """Verify SecurityValidator implementation"""
        try:
            # Import the security module
            spec = importlib.util.spec_from_file_location("security", Path("security.py"))
            security_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(security_module)
            
            # Check required classes exist
            required_classes = ['SecurityValidator', 'PathSecurityError', 'CrossTenantError', 'MimeTypeError']
            for cls_name in required_classes:
                if not hasattr(security_module, cls_name):
                    self.failed_controls.append(f"Missing required class: {cls_name}")
                    return False
            
            # Check SecurityValidator has required methods
            validator_class = getattr(security_module, 'SecurityValidator')
            required_methods = [
                'validate_tool_access',
                'validate_file_path', 
                'validate_mime_type',
                'validate_request_size',
                'secure_file_write',
                'prevent_cross_tenant_access',
                'set_engagement_allowlist',
                'get_engagement_allowlist'
            ]
            
            for method_name in required_methods:
                if not hasattr(validator_class, method_name):
                    self.failed_controls.append(f"SecurityValidator missing method: {method_name}")
                    return False
            
            # Verify that dangerous patterns are defined
            validator_instance = validator_class("./test_data", max_file_size_mb=1)
            if not hasattr(validator_instance, 'dangerous_patterns') or not validator_instance.dangerous_patterns:
                self.failed_controls.append("SecurityValidator missing dangerous_patterns")
                return False
            
            # Verify MIME type allowlist exists
            if not hasattr(validator_instance, 'allowed_mime_types') or not validator_instance.allowed_mime_types:
                self.failed_controls.append("SecurityValidator missing allowed_mime_types")
                return False
            
            self.passed_controls.append("SecurityValidator implementation complete")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"SecurityValidator verification failed: {e}")
            return False
    
    def verify_secret_redactor(self) -> bool:
        """Verify SecretRedactor implementation"""
        try:
            # Import the secret redactor module
            spec = importlib.util.spec_from_file_location("secret_redactor", Path("secret_redactor.py"))
            redactor_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(redactor_module)
            
            # Check required classes exist
            if not hasattr(redactor_module, 'SecretRedactor'):
                self.failed_controls.append("Missing SecretRedactor class")
                return False
            
            # Check SecretRedactor has required methods
            redactor_class = getattr(redactor_module, 'SecretRedactor')
            required_methods = [
                'redact_data',
                'redact_for_logging',
                '_redact_string',
                '_is_sensitive_field'
            ]
            
            for method_name in required_methods:
                if not hasattr(redactor_class, method_name):
                    self.failed_controls.append(f"SecretRedactor missing method: {method_name}")
                    return False
            
            # Verify sensitive field patterns exist
            redactor_instance = redactor_class()
            if not hasattr(redactor_instance, 'sensitive_fields') or not redactor_instance.sensitive_fields:
                self.failed_controls.append("SecretRedactor missing sensitive_fields")
                return False
            
            # Verify sensitive patterns exist
            if not hasattr(redactor_instance, 'sensitive_patterns') or not redactor_instance.sensitive_patterns:
                self.failed_controls.append("SecretRedactor missing sensitive_patterns")
                return False
            
            self.passed_controls.append("SecretRedactor implementation complete")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"SecretRedactor verification failed: {e}")
            return False
    
    def verify_filesystem_tools_security(self) -> bool:
        """Verify filesystem tools have security enhancements"""
        try:
            # Import fs_tools module
            spec = importlib.util.spec_from_file_location("fs_tools", Path("mcp_tools/fs_tools.py"))
            fs_tools_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fs_tools_module)
            
            # Check that FsWriteTool uses secure_file_write
            write_tool_class = getattr(fs_tools_module, 'FsWriteTool')
            
            # Get the source code of the execute method
            execute_method = getattr(write_tool_class, 'execute')
            source = inspect.getsource(execute_method)
            
            # Check for security enhancements
            required_features = [
                'secure_file_write',  # Should use secure file write method
                'MimeTypeError',      # Should handle MIME type errors
            ]
            
            for feature in required_features:
                if feature not in source:
                    self.failed_controls.append(f"FsWriteTool missing security feature: {feature}")
                    return False
            
            # Check FsReadTool validates MIME types
            read_tool_class = getattr(fs_tools_module, 'FsReadTool')
            read_execute_method = getattr(read_tool_class, 'execute')
            read_source = inspect.getsource(read_execute_method)
            
            if 'validate_mime_type' not in read_source:
                self.failed_controls.append("FsReadTool missing MIME type validation")
                return False
            
            self.passed_controls.append("Filesystem tools security enhancements present")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"Filesystem tools verification failed: {e}")
            return False
    
    def verify_main_gateway_security(self) -> bool:
        """Verify main gateway has security integrations"""
        try:
            # Read main.py file
            main_file = Path("main.py")
            if not main_file.exists():
                self.failed_controls.append("main.py file not found")
                return False
            
            main_content = main_file.read_text()
            
            # Check for security integrations
            required_imports = [
                'from security import',
                'from secret_redactor import',
                'CrossTenantError',
                'MimeTypeError'
            ]
            
            for import_stmt in required_imports:
                if import_stmt not in main_content:
                    self.failed_controls.append(f"Missing security import: {import_stmt}")
                    return False
            
            # Check for security validations in mcp_call
            required_validations = [
                'validate_request_size',
                'validate_tool_access',
                'redact_sensitive_data'
            ]
            
            for validation in required_validations:
                if validation not in main_content:
                    self.failed_controls.append(f"Missing security validation: {validation}")
                    return False
            
            self.passed_controls.append("Main gateway security integrations present")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"Main gateway verification failed: {e}")
            return False
    
    def verify_test_coverage(self) -> bool:
        """Verify comprehensive security test coverage"""
        try:
            test_files = [
                Path("tests/test_security.py"),
                Path("tests/test_security_comprehensive.py")
            ]
            
            for test_file in test_files:
                if not test_file.exists():
                    self.failed_controls.append(f"Missing security test file: {test_file}")
                    return False
            
            # Check comprehensive test file has required test classes
            comprehensive_tests = Path("tests/test_security_comprehensive.py").read_text()
            
            required_test_classes = [
                'TestCrossTenantIsolation',
                'TestPathTraversalAttacks', 
                'TestOversizePayloadProtection',
                'TestMimeTypeValidation',
                'TestSecretRedaction',
                'TestFilePermissionSecurity'
            ]
            
            for test_class in required_test_classes:
                if test_class not in comprehensive_tests:
                    self.failed_controls.append(f"Missing test class: {test_class}")
                    return False
            
            self.passed_controls.append("Comprehensive security test coverage present")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"Test coverage verification failed: {e}")
            return False
    
    def verify_ci_cd_security(self) -> bool:
        """Verify CI/CD security configurations"""
        try:
            # Check for security workflow
            workflow_file = Path(".github/workflows/security-scan.yml")
            if not workflow_file.exists():
                self.failed_controls.append("Missing CI/CD security workflow")
                return False
            
            workflow_content = workflow_file.read_text()
            
            # Check for required security tools
            required_tools = ['bandit', 'safety', 'semgrep', 'trufflehog']
            for tool in required_tools:
                if tool not in workflow_content.lower():
                    self.failed_controls.append(f"Missing security tool in CI/CD: {tool}")
                    return False
            
            # Check for security gate script
            gate_script = Path("scripts/security_gate_check.py")
            if not gate_script.exists():
                self.failed_controls.append("Missing security gate check script")
                return False
            
            self.passed_controls.append("CI/CD security configurations present")
            return True
            
        except Exception as e:
            self.failed_controls.append(f"CI/CD security verification failed: {e}")
            return False
    
    def run_all_verifications(self) -> bool:
        """Run all security control verifications"""
        print("Verifying MCP Gateway Security Controls...")
        print("=" * 50)
        
        verifications = [
            ("Security Validator Implementation", self.verify_security_validator),
            ("Secret Redactor Implementation", self.verify_secret_redactor), 
            ("Filesystem Tools Security", self.verify_filesystem_tools_security),
            ("Main Gateway Security", self.verify_main_gateway_security),
            ("Security Test Coverage", self.verify_test_coverage),
            ("CI/CD Security Configuration", self.verify_ci_cd_security)
        ]
        
        all_passed = True
        
        for verification_name, verification_func in verifications:
            print(f"\n{verification_name}:")
            try:
                result = verification_func()
                status = "PASS" if result else "FAIL"
                print(f"  Status: {status}")
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"  Status: ERROR - {e}")
                self.failed_controls.append(f"{verification_name} failed with error: {e}")
                all_passed = False
        
        # Print summary
        print("\n" + "=" * 50)
        print("SECURITY CONTROLS VERIFICATION SUMMARY")
        print("=" * 50)
        
        if self.passed_controls:
            print(f"\n✓ PASSED CONTROLS ({len(self.passed_controls)}):")
            for control in self.passed_controls:
                print(f"  ✓ {control}")
        
        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        if self.failed_controls:
            print(f"\n✗ FAILED CONTROLS ({len(self.failed_controls)}):")
            for control in self.failed_controls:
                print(f"  ✗ {control}")
        
        if all_passed:
            print(f"\n🎉 SECURITY CONTROLS: VERIFIED")
            print("All required security controls are properly implemented.")
        else:
            print(f"\n🚫 SECURITY CONTROLS: INCOMPLETE")
            print("Some security controls are missing or incomplete.")
        
        return all_passed

def main():
    """Main entry point"""
    verifier = SecurityControlVerifier()
    
    # Change to the script directory for relative paths
    script_dir = Path(__file__).parent
    import os
    os.chdir(script_dir.parent)
    
    success = verifier.run_all_verifications()
    
    if not success:
        sys.exit(1)
    
    print("\nSecurity controls verification completed successfully!")

if __name__ == "__main__":
    main()
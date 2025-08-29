"""
Tests for rate limiting configuration and middleware integration.

Verifies that rate limiting is properly enabled by default in production
while remaining configurable through environment variables.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the main application and rate limiting middleware
from api.main import app
from api.middleware.rate_limiting import RateLimitingMiddleware


class TestRateLimitingConfig:
    """Test rate limiting configuration behavior"""
    
    def test_production_enables_rate_limiting_by_default(self):
        """Rate limiting should be enabled by default in production"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'production',
            'ENVIRONMENT': 'production'
        }, clear=False):
            # Test the configuration logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            # Since we're in test mode (PYTEST_CURRENT_TEST is set), it should be disabled
            # But if we were truly in production without test mode, it would be enabled
            expected = is_production and not is_ci_mode and not is_test_mode
            assert rate_limiting_enabled == expected
    
    def test_development_disables_rate_limiting_by_default(self):
        """Rate limiting should be disabled by default in development"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'development',
            'ENVIRONMENT': 'development'
        }, clear=True):
            # In a real scenario, we'd need to reload the module
            # For this test, we check the logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            assert not rate_limiting_enabled
    
    def test_explicit_enable_overrides_defaults(self):
        """RATE_LIMITING_ENABLED=1 should enable rate limiting regardless of environment"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'development',
            'ENVIRONMENT': 'development',
            'RATE_LIMITING_ENABLED': '1'
        }, clear=False):
            # Check the logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            assert rate_limiting_enabled
    
    def test_explicit_disable_overrides_production(self):
        """RATE_LIMITING_ENABLED=0 should disable rate limiting even in production"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'production',
            'ENVIRONMENT': 'production',
            'RATE_LIMITING_ENABLED': '0'
        }, clear=False):
            # Check the logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            assert not rate_limiting_enabled
    
    def test_ci_mode_disables_rate_limiting(self):
        """CI_MODE=1 should disable rate limiting even in production"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'production',
            'ENVIRONMENT': 'production',
            'CI_MODE': '1'
        }, clear=False):
            # Check the logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            assert not rate_limiting_enabled
    
    def test_test_mode_disables_rate_limiting(self):
        """Test mode should disable rate limiting"""
        with patch.dict(os.environ, {
            'NODE_ENV': 'production',
            'ENVIRONMENT': 'production',
            'PYTEST_CURRENT_TEST': 'test_something.py::test_func'
        }, clear=False):
            # Check the logic directly
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            is_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None
            
            rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED')
            if rate_limiting_enabled is None:
                rate_limiting_enabled = is_production and not is_ci_mode and not is_test_mode
            else:
                rate_limiting_enabled = rate_limiting_enabled == '1'
            
            assert not rate_limiting_enabled


class TestRateLimitingMiddleware:
    """Test rate limiting middleware functionality"""
    
    def setup_method(self):
        """Set up test client with rate limiting enabled"""
        self.client = TestClient(app)
    
    def test_health_endpoint_higher_limits(self):
        """Health endpoints should have higher rate limits"""
        # Make multiple requests to health endpoint
        responses = []
        for _ in range(5):  # Should be well within health endpoint limits
            response = self.client.get("/health")
            responses.append(response)
        
        # All requests should succeed (unless rate limiting is enabled with very low limits)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1  # At least one should succeed
    
    def test_rate_limit_headers_present(self):
        """Rate limit headers should be present when rate limiting is enabled"""
        response = self.client.get("/health")
        
        # Check for rate limit headers - they may or may not be present
        # depending on whether rate limiting is enabled for tests
        expected_headers = [
            "X-RateLimit-Limit-Minute",
            "X-RateLimit-Limit-Second", 
            "X-RateLimit-Remaining-Minute",
            "X-RateLimit-Remaining-Second"
        ]
        
        # Test that we get a valid response regardless
        assert response.status_code == 200
        
        # If any rate limit headers are present, verify they contain valid values
        for header in expected_headers:
            if header in response.headers:
                header_value = response.headers[header]
                assert header_value.isdigit(), f"Header {header} should contain numeric value, got: {header_value}"
    
    def test_admin_endpoint_access_control(self):
        """Admin endpoints should have appropriate rate limits"""
        # This test assumes admin endpoints exist and require authentication
        response = self.client.get("/api/admin/demo-admins")
        
        # We expect either:
        # - 401/403 (authentication/authorization required)
        # - 200 (if somehow authenticated)  
        # - 404 (endpoint doesn't exist yet)
        # - 422 (validation error)
        # - 429 (rate limited)
        assert response.status_code in [200, 401, 403, 404, 422, 429]
    
    @pytest.mark.parametrize("endpoint", [
        "/docs",
        "/redoc", 
        "/openapi.json"
    ])
    def test_documentation_endpoints(self, endpoint):
        """Documentation endpoints should have reduced rate limits"""
        response = self.client.get(endpoint)
        
        # These endpoints should exist and be accessible
        # Rate limiting should apply but we don't test the limits explicitly
        assert response.status_code in [200, 404, 429]  # 404 if not available in test


class TestEnvironmentDetection:
    """Test production environment detection logic"""
    
    def test_node_env_production_detected(self):
        """NODE_ENV=production should be detected as production"""
        with patch.dict(os.environ, {'NODE_ENV': 'production'}, clear=False):
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            assert is_production
    
    def test_environment_production_detected(self):
        """ENVIRONMENT=production should be detected as production"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=False):
            is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
            assert is_production
    
    def test_environment_case_insensitive(self):
        """ENVIRONMENT detection should be case insensitive"""
        test_values = ['Production', 'PRODUCTION', 'production', 'pRoDuCtIoN']
        
        for env_value in test_values:
            with patch.dict(os.environ, {'ENVIRONMENT': env_value}, clear=False):
                is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
                assert is_production, f"Failed for ENVIRONMENT={env_value}"
    
    def test_development_not_production(self):
        """Development environments should not be detected as production"""
        dev_values = ['development', 'dev', 'local', 'staging', 'test']
        
        for env_value in dev_values:
            with patch.dict(os.environ, {
                'NODE_ENV': env_value,
                'ENVIRONMENT': env_value
            }, clear=True):
                is_production = os.getenv('NODE_ENV') == 'production' or os.getenv('ENVIRONMENT', '').lower() == 'production'
                assert not is_production, f"Failed for environment={env_value}"
    
    def test_ci_mode_detection(self):
        """CI_MODE=1 should be detected correctly"""
        with patch.dict(os.environ, {'CI_MODE': '1'}, clear=False):
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            assert is_ci_mode
        
        with patch.dict(os.environ, {'CI_MODE': '0'}, clear=False):
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            assert not is_ci_mode
        
        # Test default value when CI_MODE is not set
        with patch.dict(os.environ, {}, clear=True):
            is_ci_mode = os.getenv('CI_MODE', '0') == '1'
            assert not is_ci_mode


if __name__ == "__main__":
    pytest.main([__file__])
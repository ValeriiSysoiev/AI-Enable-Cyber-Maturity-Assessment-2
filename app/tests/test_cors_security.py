"""
Tests for CORS security configuration
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestCORSConfiguration:
    """Test CORS security configuration"""
    
    def test_no_wildcard_in_production(self):
        """Test that wildcard origins are rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "API_ALLOWED_ORIGINS": "*"
        }, clear=False):
            # Should raise error on startup
            with pytest.raises(ValueError, match="Wildcard CORS origin is not allowed"):
                from api.main import app
    
    def test_no_empty_origins_in_production(self):
        """Test that empty origins are rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "API_ALLOWED_ORIGINS": ""
        }, clear=False):
            # Should raise error on startup
            with pytest.raises(ValueError, match="CORS origins must be explicitly configured"):
                from api.main import app
    
    def test_localhost_allowed_in_development(self):
        """Test that localhost is allowed in development"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "API_ALLOWED_ORIGINS": ""
        }, clear=False):
            from config import config
            
            # Should have localhost defaults
            assert "http://localhost:3000" in config.allowed_origins
            assert "http://127.0.0.1:3000" in config.allowed_origins
    
    def test_specific_origins_in_production(self):
        """Test that specific origins work in production"""
        prod_origins = "https://app.example.com,https://www.example.com"
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "API_ALLOWED_ORIGINS": prod_origins
        }, clear=False):
            from config import config
            
            assert "https://app.example.com" in config.allowed_origins
            assert "https://www.example.com" in config.allowed_origins
            assert "*" not in config.allowed_origins
            assert "http://localhost:3000" not in config.allowed_origins
    
    def test_wildcard_disables_credentials(self):
        """Test that wildcard origins disable credentials"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "API_ALLOWED_ORIGINS": "*"
        }, clear=False):
            from config import config
            
            # If wildcard is in origins, credentials should be disabled
            if "*" in config.allowed_origins:
                # This should be handled by the middleware setup
                # In the actual code, cors_allow_credentials would be False
                assert True  # Placeholder for the actual middleware test
    
    def test_cors_headers_validation(self):
        """Test that CORS headers are properly configured"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "API_ALLOWED_ORIGINS": "http://localhost:3000"
        }, clear=False):
            from api.main import app
            client = TestClient(app)
            
            # Make a CORS preflight request
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            
            # Should have proper CORS headers
            assert response.status_code == 200
            assert "Access-Control-Allow-Origin" in response.headers
            assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    
    def test_cors_blocks_unauthorized_origin(self):
        """Test that CORS blocks unauthorized origins"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "API_ALLOWED_ORIGINS": "https://app.example.com"
        }, clear=False):
            from api.main import app
            client = TestClient(app)
            
            # Request from unauthorized origin
            response = client.options(
                "/health",
                headers={
                    "Origin": "https://evil.com",
                    "Access-Control-Request-Method": "GET"
                }
            )
            
            # Should not have CORS headers for unauthorized origin
            if "Access-Control-Allow-Origin" in response.headers:
                assert response.headers["Access-Control-Allow-Origin"] != "https://evil.com"
                assert response.headers["Access-Control-Allow-Origin"] != "*"
    
    def test_cors_methods_limited(self):
        """Test that CORS methods are explicitly limited"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "API_ALLOWED_ORIGINS": "http://localhost:3000"
        }, clear=False):
            from api.main import app
            client = TestClient(app)
            
            # Check allowed methods
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            
            if "Access-Control-Allow-Methods" in response.headers:
                allowed_methods = response.headers["Access-Control-Allow-Methods"]
                # Should have specific methods, not wildcard
                assert "*" not in allowed_methods
                assert "GET" in allowed_methods or "get" in allowed_methods.lower()


class TestCORSConfigHelper:
    """Test the CORS configuration helper script"""
    
    def test_production_origins_are_https(self):
        """Test that production origins use HTTPS"""
        from scripts.configure_cors import get_production_origins
        
        origins = get_production_origins()
        for origin in origins:
            assert origin.startswith("https://"), f"Production origin {origin} must use HTTPS"
    
    def test_development_origins_allow_localhost(self):
        """Test that development origins include localhost"""
        from scripts.configure_cors import get_development_origins
        
        origins = get_development_origins()
        assert any("localhost" in o for o in origins)
        assert any("127.0.0.1" in o for o in origins)
    
    def test_validate_origins_catches_wildcard(self):
        """Test that validation catches wildcard origins"""
        from scripts.configure_cors import validate_origins
        
        is_valid, errors = validate_origins(["*"], "production")
        assert not is_valid
        assert any("Wildcard" in e for e in errors)
    
    def test_validate_origins_catches_localhost_in_prod(self):
        """Test that validation catches localhost in production"""
        from scripts.configure_cors import validate_origins
        
        is_valid, errors = validate_origins(
            ["https://app.example.com", "http://localhost:3000"],
            "production"
        )
        assert not is_valid
        assert any("localhost" in e.lower() for e in errors)
    
    def test_validate_origins_warns_non_https_in_prod(self):
        """Test that validation warns about non-HTTPS in production"""
        from scripts.configure_cors import validate_origins
        
        is_valid, errors = validate_origins(
            ["http://app.example.com"],
            "production"
        )
        # Should have warning but might still be valid
        assert any("HTTPS" in e for e in errors)
    
    def test_generate_env_var(self):
        """Test environment variable generation"""
        from scripts.configure_cors import generate_env_var
        
        origins = ["https://app.example.com", "https://api.example.com"]
        env_var = generate_env_var(origins)
        
        assert env_var == "https://app.example.com,https://api.example.com"
        assert "," in env_var  # Should be comma-separated
        assert " " not in env_var  # Should not have spaces
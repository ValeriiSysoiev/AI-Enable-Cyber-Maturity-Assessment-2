"""
Tests for CSF 2.0 Taxonomy Service and API endpoints

Tests cover service load/access performance, API endpoint shape and response structure.
Focus on fast taxonomy loading and structured data validation.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, mock_open
from fastapi.testclient import TestClient

from app.services.csf_taxonomy import CSFTaxonomyService, get_csf_service
from app.domain.models import CSFFunction, CSFCategory, CSFSubcategory
from app.api.main import app


# Test data for mocking
MOCK_CSF_DATA = {
    "version": "2.0",
    "metadata": {
        "title": "Test CSF 2.0",
        "description": "Test taxonomy",
        "created_at": "2025-08-18"
    },
    "functions": [
        {
            "id": "GV",
            "title": "Govern",
            "description": "Test govern function",
            "categories": [
                {
                    "id": "GV.OC",
                    "title": "Organizational Context",
                    "description": "Test category",
                    "subcategories": [
                        {
                            "id": "GV.OC-01",
                            "title": "Mission and Objectives",
                            "description": "Test subcategory"
                        }
                    ]
                }
            ]
        },
        {
            "id": "ID",
            "title": "Identify",
            "description": "Test identify function",
            "categories": [
                {
                    "id": "ID.AM",
                    "title": "Asset Management",
                    "description": "Test category 2",
                    "subcategories": [
                        {
                            "id": "ID.AM-01",
                            "title": "Asset Inventory",
                            "description": "Test subcategory 2"
                        },
                        {
                            "id": "ID.AM-02",
                            "title": "Asset Classification",
                            "description": "Test subcategory 3"
                        }
                    ]
                }
            ]
        }
    ]
}


@pytest.fixture
def csf_service():
    """Fresh CSF service instance for each test"""
    return CSFTaxonomyService()


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


class TestCSFTaxonomyService:
    """Test CSF taxonomy service functionality"""
    
    def test_load_csf_taxonomy_success(self, csf_service):
        """Test successful taxonomy loading"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            taxonomy = csf_service.load_csf_taxonomy()
            
            assert taxonomy["version"] == "2.0"
            assert len(taxonomy["functions"]) == 2
            assert taxonomy["functions"][0]["id"] == "GV"
    
    def test_load_csf_taxonomy_file_not_found(self, csf_service):
        """Test handling of missing taxonomy file"""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                csf_service.load_csf_taxonomy()
    
    def test_load_csf_taxonomy_invalid_json(self, csf_service):
        """Test handling of invalid JSON"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with pytest.raises(ValueError):
                csf_service.load_csf_taxonomy()
    
    def test_get_functions_performance(self, csf_service):
        """Test get_functions performance meets p95 < 2s requirement"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            # Measure performance
            start_time = time.time()
            functions = csf_service.get_functions()
            duration = time.time() - start_time
            
            # Verify performance requirement
            assert duration < 2.0, f"get_functions took {duration:.3f}s, should be < 2s"
            
            # Verify structure
            assert len(functions) == 2
            assert isinstance(functions[0], CSFFunction)
            assert functions[0].id == "GV"
            assert len(functions[0].categories) == 1
            assert len(functions[0].categories[0].subcategories) == 1
    
    def test_get_functions_caching(self, csf_service):
        """Test function caching works correctly"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)) as mock_file:
            # First call
            functions1 = csf_service.get_functions()
            
            # Second call should use cache
            functions2 = csf_service.get_functions()
            
            # Should be same objects (cached)
            assert functions1 is functions2
            
            # File should only be read once due to caching
            assert mock_file.call_count == 1
    
    def test_get_categories_all(self, csf_service):
        """Test getting all categories"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            categories = csf_service.get_categories()
            
            assert len(categories) == 2  # One from each function
            assert categories[0].id == "GV.OC"
            assert categories[1].id == "ID.AM"
    
    def test_get_categories_filtered(self, csf_service):
        """Test getting categories filtered by function"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            categories = csf_service.get_categories("GV")
            
            assert len(categories) == 1
            assert categories[0].id == "GV.OC"
            assert categories[0].function_id == "GV"
    
    def test_get_subcategories_all(self, csf_service):
        """Test getting all subcategories"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            subcategories = csf_service.get_subcategories()
            
            assert len(subcategories) == 3  # 1 + 2 from mock data
            assert subcategories[0].id == "GV.OC-01"
            assert subcategories[1].id == "ID.AM-01"
            assert subcategories[2].id == "ID.AM-02"
    
    def test_get_subcategories_filtered(self, csf_service):
        """Test getting subcategories filtered by function and category"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            subcategories = csf_service.get_subcategories("ID", "ID.AM")
            
            assert len(subcategories) == 2
            assert all(s.function_id == "ID" for s in subcategories)
            assert all(s.category_id == "ID.AM" for s in subcategories)
    
    def test_get_function_by_id(self, csf_service):
        """Test getting specific function by ID"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            function = csf_service.get_function_by_id("GV")
            
            assert function is not None
            assert function.id == "GV"
            assert function.title == "Govern"
            
            # Test not found
            not_found = csf_service.get_function_by_id("XX")
            assert not_found is None


class TestCSFAPI:
    """Test CSF API endpoints"""
    
    def test_get_csf_functions_endpoint(self, client):
        """Test GET /api/v1/csf/functions endpoint"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/functions")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "version" in data
            assert "functions" in data
            assert "metadata" in data
            
            # Verify data content
            assert data["version"] == "2.0"
            assert len(data["functions"]) == 2
            
            # Verify first function structure
            function = data["functions"][0]
            assert function["id"] == "GV"
            assert function["title"] == "Govern"
            assert len(function["categories"]) == 1
            
            # Verify category structure
            category = function["categories"][0]
            assert category["id"] == "GV.OC"
            assert category["function_id"] == "GV"
            assert len(category["subcategories"]) == 1
            
            # Verify subcategory structure
            subcategory = category["subcategories"][0]
            assert subcategory["id"] == "GV.OC-01"
            assert subcategory["function_id"] == "GV"
            assert subcategory["category_id"] == "GV.OC"
    
    def test_get_csf_function_by_id_endpoint(self, client):
        """Test GET /api/v1/csf/functions/{function_id} endpoint"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/functions/GV")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["id"] == "GV"
            assert data["title"] == "Govern"
            assert len(data["categories"]) == 1
    
    def test_get_csf_function_not_found(self, client):
        """Test function not found returns 404"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/functions/XX")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_get_csf_categories_endpoint(self, client):
        """Test GET /api/v1/csf/categories endpoint"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/categories")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 2
            assert data[0]["id"] == "GV.OC"
            assert data[1]["id"] == "ID.AM"
    
    def test_get_csf_categories_filtered(self, client):
        """Test GET /api/v1/csf/categories with function filter"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/categories?function_id=GV")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 1
            assert data[0]["id"] == "GV.OC"
            assert data[0]["function_id"] == "GV"
    
    def test_get_csf_subcategories_endpoint(self, client):
        """Test GET /api/v1/csf/subcategories endpoint"""
        mock_json = json.dumps(MOCK_CSF_DATA)
        
        with patch("builtins.open", mock_open(read_data=mock_json)):
            response = client.get("/api/v1/csf/subcategories")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 3  # Total subcategories in mock data
    
    def test_api_error_handling_file_not_found(self, client):
        """Test API error handling when taxonomy file not found"""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            response = client.get("/api/v1/csf/functions")
            
            assert response.status_code == 500
            assert "not available" in response.json()["detail"].lower()
    
    def test_api_error_handling_invalid_json(self, client):
        """Test API error handling for invalid JSON"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            response = client.get("/api/v1/csf/functions")
            
            assert response.status_code == 500
            assert "format" in response.json()["detail"].lower()


class TestCSFServiceSingleton:
    """Test CSF service singleton functionality"""
    
    def test_get_csf_service_singleton(self):
        """Test that get_csf_service returns same instance"""
        service1 = get_csf_service()
        service2 = get_csf_service()
        
        assert service1 is service2
        assert isinstance(service1, CSFTaxonomyService)
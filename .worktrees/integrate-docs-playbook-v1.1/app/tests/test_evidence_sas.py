"""
Tests for Evidence SAS token generation and validation.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from api.main import app
from api.routes.evidence import _validate_mime_type, _validate_file_size, _safe_filename

client = TestClient(app)

class TestEvidenceSASValidation:
    """Test evidence SAS validation functions"""
    
    def test_validate_mime_type_allowed(self):
        """Test MIME type validation for allowed types"""
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "image/png",
            "image/jpeg"
        ]
        
        for mime_type in allowed_types:
            assert _validate_mime_type(mime_type) == True
            assert _validate_mime_type(mime_type.upper()) == True  # Case insensitive
    
    def test_validate_mime_type_disallowed(self):
        """Test MIME type validation for disallowed types"""
        disallowed_types = [
            "application/x-executable",
            "text/html",
            "application/javascript",
            "video/mp4",
            "audio/mpeg"
        ]
        
        for mime_type in disallowed_types:
            assert _validate_mime_type(mime_type) == False
    
    def test_validate_file_size_within_limit(self):
        """Test file size validation within limits"""
        # Test sizes within 25MB default limit
        assert _validate_file_size(1024) == True  # 1KB
        assert _validate_file_size(1024 * 1024) == True  # 1MB
        assert _validate_file_size(25 * 1024 * 1024) == True  # 25MB exactly
    
    def test_validate_file_size_exceeds_limit(self):
        """Test file size validation exceeding limits"""
        # Test sizes exceeding 25MB default limit
        assert _validate_file_size(26 * 1024 * 1024) == False  # 26MB
        assert _validate_file_size(100 * 1024 * 1024) == False  # 100MB
    
    def test_safe_filename_sanitization(self):
        """Test filename sanitization"""
        test_cases = [
            ("normal_file.pdf", "normal_file.pdf"),
            ("file with spaces.docx", "file with spaces.docx"),
            ("file<>:\"/\\|?*.txt", "file_________.txt"),
            ("../../../etc/passwd", "__/___/etc/passwd"),
            ("file..name.pdf", "file__name.pdf"),
            ("a" * 300 + ".pdf", "a" * 250 + ".pdf")  # Length limit
        ]
        
        for input_name, expected in test_cases:
            result = _safe_filename(input_name)
            assert result == expected
            assert len(result) <= 255


class TestEvidenceSASEndpoint:
    """Test evidence SAS endpoint functionality"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence._get_storage_config')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_generate_sas_success(
        self, 
        mock_require_role, 
        mock_get_user, 
        mock_storage_config,
        mock_check_membership
    ):
        """Test successful SAS token generation"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_storage_config.return_value = {
            "account": "teststorage",
            "key": "test-key",
            "container": "evidence"
        }
        mock_check_membership.return_value = True
        
        # Test request
        request_data = {
            "engagement_id": "eng-123",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024 * 1024  # 1MB
        }
        
        response = client.post("/api/v1/evidence/sas", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "upload_url" in data
        assert "blob_path" in data
        assert "expires_at" in data
        assert "max_size" in data
        assert "allowed_types" in data
        
        # Verify blob path format
        assert data["blob_path"].startswith("engagements/eng-123/evidence/")
        assert data["blob_path"].endswith("/test.pdf")
        
        # Verify expiration is within expected range (≤5 minutes)
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
        time_diff = expires_at - now
        assert time_diff <= timedelta(minutes=5)
        assert time_diff > timedelta(minutes=0)
    
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_generate_sas_invalid_mime_type(self, mock_require_role, mock_get_user):
        """Test SAS generation with invalid MIME type"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        request_data = {
            "engagement_id": "eng-123",
            "filename": "malware.exe",
            "mime_type": "application/x-executable",
            "size_bytes": 1024
        }
        
        response = client.post("/api/v1/evidence/sas", json=request_data)
        
        assert response.status_code == 415
        assert "Unsupported media type" in response.json()["detail"]
    
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_generate_sas_file_too_large(self, mock_require_role, mock_get_user):
        """Test SAS generation with oversized file"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        request_data = {
            "engagement_id": "eng-123",
            "filename": "large.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 100 * 1024 * 1024  # 100MB
        }
        
        response = client.post("/api/v1/evidence/sas", json=request_data)
        
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_generate_sas_not_member(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_check_membership
    ):
        """Test SAS generation denied for non-members"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = False
        
        request_data = {
            "engagement_id": "eng-123",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024
        }
        
        response = client.post("/api/v1/evidence/sas", json=request_data)
        
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


class TestEvidenceCompleteEndpoint:
    """Test evidence completion endpoint"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_complete_upload_success(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_check_membership
    ):
        """Test successful evidence completion"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        request_data = {
            "engagement_id": "eng-123",
            "blob_path": "engagements/eng-123/evidence/uuid/test.pdf",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "client_checksum": "abc123"
        }
        
        response = client.post("/api/v1/evidence/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "evidence_id" in data
        assert "checksum" in data
        assert "pii_flag" in data


class TestEvidenceListEndpoint:
    """Test evidence listing endpoint"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_list_evidence_success(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_check_membership
    ):
        """Test successful evidence listing"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        response = client.get("/api/v1/evidence?engagement_id=eng-123")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_list_evidence_not_member(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_check_membership
    ):
        """Test evidence listing denied for non-members"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = False
        
        response = client.get("/api/v1/evidence?engagement_id=eng-123")
        
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


class TestEvidenceLinkEndpoint:
    """Test evidence linking endpoint"""
    
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_link_evidence_success(self, mock_require_role, mock_get_user):
        """Test successful evidence linking"""
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        request_data = {
            "item_type": "assessment",
            "item_id": "assessment-123"
        }
        
        response = client.post("/api/v1/evidence/evidence-123/links", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Link created"
        assert data["evidence_id"] == "evidence-123"
        assert data["item_type"] == "assessment"
        assert data["item_id"] == "assessment-123"
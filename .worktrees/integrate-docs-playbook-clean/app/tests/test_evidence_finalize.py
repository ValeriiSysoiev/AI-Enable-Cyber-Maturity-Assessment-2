"""
Tests for Evidence finalization with checksum computation and PII detection.
"""
import pytest
from unittest.mock import patch, AsyncMock
from services.evidence_processing import EvidenceProcessor


class TestEvidenceProcessor:
    """Test Evidence processing service"""
    
    @pytest.mark.asyncio
    async def test_compute_checksum_mock(self):
        """Test checksum computation in mock mode"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob client to return None (development mode)
        with patch.object(processor, '_get_blob_client', return_value=None):
            result = await processor.compute_checksum("test/path/file.pdf")
            
            assert result is not None
            assert result.startswith("mock-sha256-")
            assert len(result) > 20  # Mock includes hash portion
    
    @pytest.mark.asyncio
    async def test_verify_blob_exists_mock(self):
        """Test blob verification in mock mode"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob client to return None (development mode)
        with patch.object(processor, '_get_blob_client', return_value=None):
            exists, size = await processor.verify_blob_exists("test/path/file.pdf")
            
            assert exists is True
            assert size == 1024  # Mock size
    
    @pytest.mark.asyncio
    async def test_detect_pii_text_file(self):
        """Test PII detection for text files"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob client to return None (development mode)
        with patch.object(processor, '_get_blob_client', return_value=None):
            # Mock: PII detected in 10% of files (hash-based)
            result1 = await processor.detect_pii("test1.txt", "text/plain")
            result2 = await processor.detect_pii("test2.txt", "text/plain")
            
            # Results should be deterministic based on path hash
            assert isinstance(result1, bool)
            assert isinstance(result2, bool)
    
    @pytest.mark.asyncio
    async def test_detect_pii_non_text_file(self):
        """Test PII detection skips non-text files"""
        processor = EvidenceProcessor("test-correlation")
        
        result = await processor.detect_pii("image.png", "image/png")
        
        # Should skip PII detection for images
        assert result is False
    
    @pytest.mark.asyncio
    @patch('services.evidence_processing.BlobServiceClient')
    async def test_compute_checksum_with_blob(self, mock_blob_service):
        """Test checksum computation with actual blob client"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob service and client
        mock_blob_client = AsyncMock()
        mock_blob_service.return_value = mock_blob_client
        
        mock_blob = AsyncMock()
        mock_blob_client.get_blob_client.return_value = mock_blob
        
        # Mock blob stream
        mock_stream = AsyncMock()
        mock_stream.chunks.return_value = [b"test content"]
        mock_blob.download_blob.return_value = mock_stream
        
        with patch.object(processor, '_get_blob_client', return_value=mock_blob_client):
            result = await processor.compute_checksum("test/path/file.pdf")
            
            # Should return actual SHA-256 hash of "test content"
            expected_hash = "1eebdf4fdc9fc7bf283031b93f9aef3338de9052f584eb64bb4db6b77fab0cc6"  # SHA-256 of "test content"
            assert result == expected_hash
    
    @pytest.mark.asyncio
    @patch('services.evidence_processing.BlobServiceClient')
    async def test_detect_pii_with_patterns(self, mock_blob_service):
        """Test PII detection with actual patterns"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob service and client
        mock_blob_client = AsyncMock()
        mock_blob_service.return_value = mock_blob_client
        
        mock_blob = AsyncMock()
        mock_blob_client.get_blob_client.return_value = mock_blob
        
        # Mock blob content with PII
        content_with_pii = "Contact John Doe at john.doe@example.com or call 555-123-4567"
        mock_stream = AsyncMock()
        mock_stream.readall.return_value = content_with_pii.encode('utf-8')
        mock_blob.download_blob.return_value = mock_stream
        
        with patch.object(processor, '_get_blob_client', return_value=mock_blob_client):
            result = await processor.detect_pii("test.txt", "text/plain")
            
            # Should detect email and phone number
            assert result is True
    
    @pytest.mark.asyncio
    @patch('services.evidence_processing.BlobServiceClient')
    async def test_detect_pii_no_patterns(self, mock_blob_service):
        """Test PII detection with no PII patterns"""
        processor = EvidenceProcessor("test-correlation")
        
        # Mock blob service and client
        mock_blob_client = AsyncMock()
        mock_blob_service.return_value = mock_blob_client
        
        mock_blob = AsyncMock()
        mock_blob_client.get_blob_client.return_value = mock_blob
        
        # Mock blob content without PII
        content_no_pii = "This is a sample document about cybersecurity best practices."
        mock_stream = AsyncMock()
        mock_stream.readall.return_value = content_no_pii.encode('utf-8')
        mock_blob.download_blob.return_value = mock_stream
        
        with patch.object(processor, '_get_blob_client', return_value=mock_blob_client):
            result = await processor.detect_pii("test.txt", "text/plain")
            
            # Should not detect PII
            assert result is False


class TestEvidenceFinalizeEndpoint:
    """Test evidence finalize endpoint integration"""
    
    @pytest.mark.asyncio
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.EvidenceProcessor')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_complete_upload_success(
        self, 
        mock_require_role,
        mock_get_user,
        mock_create_repo,
        mock_processor_class,
        mock_check_membership
    ):
        """Test successful evidence completion with full processing"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock processor
        mock_processor = AsyncMock()
        mock_processor.verify_blob_exists.return_value = (True, 1024)
        mock_processor.compute_checksum.return_value = "sha256-checksum-value"
        mock_processor.detect_pii.return_value = False
        mock_processor_class.return_value = mock_processor
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_stored_evidence = AsyncMock()
        mock_stored_evidence.id = "evidence-123"
        mock_repo.store_evidence.return_value = mock_stored_evidence
        mock_create_repo.return_value = mock_repo
        
        request_data = {
            "engagement_id": "eng-123",
            "blob_path": "engagements/eng-123/evidence/uuid/test.pdf",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "client_checksum": "sha256-checksum-value"
        }
        
        response = client.post("/api/v1/evidence/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["evidence_id"] == "evidence-123"
        assert data["checksum"] == "sha256-checksum-value"
        assert data["pii_flag"] is False
        assert data["size"] == 1024
        
        # Verify calls
        mock_processor.verify_blob_exists.assert_called_once()
        mock_processor.compute_checksum.assert_called_once()
        mock_processor.detect_pii.assert_called_once()
        mock_repo.store_evidence.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.EvidenceProcessor')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_complete_upload_blob_not_found(
        self, 
        mock_require_role,
        mock_get_user,
        mock_processor_class,
        mock_check_membership
    ):
        """Test evidence completion when blob not found"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock processor - blob not found
        mock_processor = AsyncMock()
        mock_processor.verify_blob_exists.return_value = (False, 0)
        mock_processor_class.return_value = mock_processor
        
        request_data = {
            "engagement_id": "eng-123",
            "blob_path": "engagements/eng-123/evidence/uuid/missing.pdf",
            "filename": "missing.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024
        }
        
        response = client.post("/api/v1/evidence/complete", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.EvidenceProcessor')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_complete_upload_checksum_mismatch(
        self, 
        mock_require_role,
        mock_get_user,
        mock_processor_class,
        mock_check_membership
    ):
        """Test evidence completion with checksum mismatch"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock processor - checksum mismatch
        mock_processor = AsyncMock()
        mock_processor.verify_blob_exists.return_value = (True, 1024)
        mock_processor.compute_checksum.return_value = "server-checksum"
        mock_processor_class.return_value = mock_processor
        
        request_data = {
            "engagement_id": "eng-123",
            "blob_path": "engagements/eng-123/evidence/uuid/test.pdf",
            "filename": "test.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "client_checksum": "different-checksum"
        }
        
        response = client.post("/api/v1/evidence/complete", json=request_data)
        
        assert response.status_code == 422
        assert "checksum mismatch" in response.json()["detail"].lower()
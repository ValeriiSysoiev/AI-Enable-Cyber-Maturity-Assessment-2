"""
Integration tests for Evidence management flow including links.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from domain.models import Evidence

client = TestClient(app)


class TestEvidenceFlowIntegration:
    """Integration tests for complete evidence management flow"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence._get_storage_config')
    @patch('api.routes.evidence.EvidenceProcessor')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_complete_evidence_workflow_with_links(
        self, 
        mock_require_role,
        mock_get_user,
        mock_create_repo,
        mock_processor_class,
        mock_storage_config,
        mock_check_membership
    ):
        """Test complete evidence workflow: SAS → Upload → Complete → Link → List → Unlink"""
        
        # Setup common mocks
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        mock_storage_config.return_value = {
            "account": "teststorage",
            "key": "test-key",
            "container": "evidence"
        }
        
        # Mock processor
        mock_processor = AsyncMock()
        mock_processor.verify_blob_exists.return_value = (True, 1024)
        mock_processor.compute_checksum.return_value = "sha256-checksum-value"
        mock_processor.detect_pii.return_value = False
        mock_processor_class.return_value = mock_processor
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_create_repo.return_value = mock_repo
        
        engagement_id = "eng-123"
        filename = "test-document.pdf"
        
        # Step 1: Generate SAS token
        sas_request = {
            "engagement_id": engagement_id,
            "filename": filename,
            "mime_type": "application/pdf",
            "size_bytes": 1024
        }
        
        sas_response = client.post("/api/v1/evidence/sas", json=sas_request)
        assert sas_response.status_code == 200
        sas_data = sas_response.json()
        
        blob_path = sas_data["blob_path"]
        assert blob_path.startswith(f"engagements/{engagement_id}/evidence/")
        assert blob_path.endswith(f"/{filename}")
        
        # Step 2: Complete upload (simulate successful upload)
        mock_stored_evidence = Evidence(
            id="evidence-456",
            engagement_id=engagement_id,
            blob_path=blob_path,
            filename=filename,
            checksum_sha256="sha256-checksum-value",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=[]
        )
        mock_repo.store_evidence.return_value = mock_stored_evidence
        
        complete_request = {
            "engagement_id": engagement_id,
            "blob_path": blob_path,
            "filename": filename,
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "client_checksum": "sha256-checksum-value"
        }
        
        complete_response = client.post("/api/v1/evidence/complete", json=complete_request)
        assert complete_response.status_code == 200
        complete_data = complete_response.json()
        
        evidence_id = complete_data["evidence_id"]
        assert evidence_id == "evidence-456"
        assert complete_data["checksum"] == "sha256-checksum-value"
        assert complete_data["pii_flag"] is False
        
        # Step 3: Link evidence to assessment items
        mock_repo.get_evidence_by_id.return_value = mock_stored_evidence
        mock_repo.update_evidence_links.return_value = True
        
        # Link to first assessment
        link_request_1 = {
            "item_type": "assessment",
            "item_id": "assessment-789"
        }
        
        link_response_1 = client.post(f"/api/v1/evidence/{evidence_id}/links", json=link_request_1)
        assert link_response_1.status_code == 200
        link_data_1 = link_response_1.json()
        
        assert link_data_1["message"] == "Link created"
        assert link_data_1["evidence_id"] == evidence_id
        assert link_data_1["item_type"] == "assessment"
        assert link_data_1["item_id"] == "assessment-789"
        
        # Update mock evidence with first link for subsequent operations
        mock_stored_evidence.linked_items = [{"item_type": "assessment", "item_id": "assessment-789"}]
        
        # Link to second assessment
        link_request_2 = {
            "item_type": "question",
            "item_id": "question-101"
        }
        
        link_response_2 = client.post(f"/api/v1/evidence/{evidence_id}/links", json=link_request_2)
        assert link_response_2.status_code == 200
        link_data_2 = link_response_2.json()
        
        assert link_data_2["total_links"] == 2
        
        # Update mock evidence with both links
        mock_stored_evidence.linked_items = [
            {"item_type": "assessment", "item_id": "assessment-789"},
            {"item_type": "question", "item_id": "question-101"}
        ]
        
        # Step 4: List evidence and verify pagination
        mock_repo.list_evidence.return_value = ([mock_stored_evidence], 1)
        
        list_response = client.get(f"/api/v1/evidence?engagement_id={engagement_id}&page=1&page_size=10")
        assert list_response.status_code == 200
        
        # Check pagination headers
        assert list_response.headers["X-Total-Count"] == "1"
        assert list_response.headers["X-Page"] == "1"
        assert list_response.headers["X-Page-Size"] == "10"
        assert list_response.headers["X-Total-Pages"] == "1"
        assert list_response.headers["X-Has-Next"] == "false"
        assert list_response.headers["X-Has-Previous"] == "false"
        
        list_data = list_response.json()
        assert len(list_data) == 1
        assert list_data[0]["id"] == evidence_id
        assert len(list_data[0]["linked_items"]) == 2
        
        # Step 5: Remove one link
        link_id = "assessment:assessment-789"
        
        unlink_response = client.delete(f"/api/v1/evidence/{evidence_id}/links/{link_id}")
        assert unlink_response.status_code == 200
        unlink_data = unlink_response.json()
        
        assert unlink_data["message"] == "Link removed"
        assert unlink_data["evidence_id"] == evidence_id
        assert unlink_data["item_type"] == "assessment"
        assert unlink_data["item_id"] == "assessment-789"
        assert unlink_data["remaining_links"] == 1
        
        # Verify all repository method calls were made
        mock_repo.store_evidence.assert_called_once()
        assert mock_repo.get_evidence_by_id.call_count >= 2  # Called for linking operations
        assert mock_repo.update_evidence_links.call_count >= 2  # Called for link operations
        mock_repo.list_evidence.assert_called_once()
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_evidence_isolation_enforcement(
        self, 
        mock_require_role,
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test that engagement isolation is enforced across all operations"""
        
        # Setup mocks
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_create_repo.return_value = mock_repo
        
        engagement_id = "eng-123"
        evidence_id = "evidence-456"
        
        # Test isolation for different operations
        operations = [
            ("list", lambda: client.get(f"/api/v1/evidence?engagement_id={engagement_id}")),
            ("link", lambda: client.post(f"/api/v1/evidence/{evidence_id}/links", json={"item_type": "assessment", "item_id": "test"})),
            ("unlink", lambda: client.delete(f"/api/v1/evidence/{evidence_id}/links/assessment:test"))
        ]
        
        for operation_name, operation_func in operations:
            # Test when user is NOT a member
            mock_check_membership.return_value = False
            
            response = operation_func()
            
            assert response.status_code == 403, f"Operation {operation_name} should deny access for non-members"
            assert "not a member" in response.json()["detail"], f"Operation {operation_name} should have proper error message"
            
            # Test when user IS a member  
            mock_check_membership.return_value = True
            
            # Set up additional mocks needed for successful operations
            if operation_name in ["link", "unlink"]:
                mock_evidence = Evidence(
                    id=evidence_id,
                    engagement_id=engagement_id,
                    blob_path="test/path.pdf",
                    filename="test.pdf",
                    checksum_sha256="abc123",
                    size=1024,
                    mime_type="application/pdf",
                    uploaded_by="user@example.com",
                    linked_items=[{"item_type": "assessment", "item_id": "test"}] if operation_name == "unlink" else []
                )
                mock_repo.get_evidence_by_id.return_value = mock_evidence
                mock_repo.update_evidence_links.return_value = True
            elif operation_name == "list":
                mock_repo.list_evidence.return_value = ([], 0)
            
            response = operation_func()
            
            # These should succeed (or fail for different reasons, not access)
            assert response.status_code != 403, f"Operation {operation_name} should allow access for members"
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_evidence_error_handling_chain(
        self, 
        mock_require_role,
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test error handling across the evidence management chain"""
        
        # Setup mocks
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock repository that fails
        mock_repo = AsyncMock()
        mock_create_repo.return_value = mock_repo
        
        evidence_id = "evidence-456"
        
        # Test 1: Evidence not found for linking
        mock_repo.get_evidence_by_id.return_value = None
        
        link_request = {
            "item_type": "assessment",
            "item_id": "assessment-789"
        }
        
        link_response = client.post(f"/api/v1/evidence/{evidence_id}/links", json=link_request)
        assert link_response.status_code == 404
        assert "Evidence not found" in link_response.json()["detail"]
        
        # Test 2: Repository failure during link update
        mock_evidence = Evidence(
            id=evidence_id,
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=[]
        )
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_repo.update_evidence_links.return_value = False  # Simulate failure
        
        link_response = client.post(f"/api/v1/evidence/{evidence_id}/links", json=link_request)
        assert link_response.status_code == 500
        assert "Failed to update evidence links" in link_response.json()["detail"]
        
        # Test 3: Repository exception during list operation
        mock_repo.list_evidence.side_effect = Exception("Database connection failed")
        
        list_response = client.get("/api/v1/evidence?engagement_id=eng-123")
        assert list_response.status_code == 500
        assert "Failed to retrieve evidence list" in list_response.json()["detail"]
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_evidence_audit_logging_integration(
        self, 
        mock_require_role,
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test that audit logging occurs throughout evidence operations"""
        
        # Setup mocks
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation-789"
        }
        mock_check_membership.return_value = True
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_create_repo.return_value = mock_repo
        
        # Mock evidence for operations
        mock_evidence = Evidence(
            id="evidence-456",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=[{"item_type": "assessment", "item_id": "assessment-789"}]
        )
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_repo.update_evidence_links.return_value = True
        mock_repo.list_evidence.return_value = ([mock_evidence], 1)
        
        # Capture logs
        with patch('api.routes.evidence.logger') as mock_logger:
            
            # Test link operation logging
            link_request = {
                "item_type": "question",
                "item_id": "question-101"
            }
            
            client.post("/api/v1/evidence/evidence-456/links", json=link_request)
            
            # Verify audit logs for link operation
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if "Evidence link created" in str(call)]
            assert len(info_calls) > 0, "Should log evidence link creation"
            
            # Verify correlation ID is included in logs
            log_call = info_calls[0]
            log_extra = log_call[1]["extra"]
            assert log_extra["correlation_id"] == "test-correlation-789"
            assert log_extra["user_email"] == "user@example.com"
            assert log_extra["evidence_id"] == "evidence-456"
            
            # Reset logger mock
            mock_logger.reset_mock()
            
            # Test unlink operation logging
            client.delete("/api/v1/evidence/evidence-456/links/assessment:assessment-789")
            
            # Verify audit logs for unlink operation
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if "Evidence link removed" in str(call)]
            assert len(info_calls) > 0, "Should log evidence link removal"
            
            # Reset logger mock
            mock_logger.reset_mock()
            
            # Test list operation logging
            client.get("/api/v1/evidence?engagement_id=eng-123")
            
            # Verify audit logs for list operation
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if "Evidence list request completed" in str(call)]
            assert len(info_calls) > 0, "Should log evidence list requests"
            
            # Verify engagement isolation logging
            mock_check_membership.return_value = False
            mock_logger.reset_mock()
            
            client.get("/api/v1/evidence?engagement_id=eng-456")  # Different engagement
            
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if "Evidence list denied - not a member" in str(call)]
            assert len(warning_calls) > 0, "Should log access denials with warning level"
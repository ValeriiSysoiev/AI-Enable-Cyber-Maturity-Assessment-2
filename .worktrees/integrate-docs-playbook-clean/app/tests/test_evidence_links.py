"""
Unit tests for Evidence linking/unlinking functionality.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from api.main import app
from domain.models import Evidence

client = TestClient(app)


class TestEvidenceLinking:
    """Test evidence linking functionality"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_link_evidence_success(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test successful evidence linking"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock existing evidence
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=[]
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_repo.update_evidence_links.return_value = True
        mock_create_repo.return_value = mock_repo
        
        request_data = {
            "item_type": "assessment",
            "item_id": "assessment-456"
        }
        
        response = client.post("/api/v1/evidence/evidence-123/links", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Link created"
        assert data["evidence_id"] == "evidence-123"
        assert data["item_type"] == "assessment"
        assert data["item_id"] == "assessment-456"
        assert data["total_links"] == 1
        
        # Verify repository calls
        mock_repo.get_evidence_by_id.assert_called_once_with("evidence-123")
        mock_repo.update_evidence_links.assert_called_once()
        
        # Check the updated links passed to repository
        call_args = mock_repo.update_evidence_links.call_args
        updated_links = call_args[0][2]  # Third argument
        assert len(updated_links) == 1
        assert updated_links[0]["item_type"] == "assessment"
        assert updated_links[0]["item_id"] == "assessment-456"
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_link_evidence_duplicate_link(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test linking evidence with duplicate link (should not add duplicate)"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock existing evidence with existing link
        existing_link = {"item_type": "assessment", "item_id": "assessment-456"}
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=[existing_link]
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_repo.update_evidence_links.return_value = True
        mock_create_repo.return_value = mock_repo
        
        request_data = {
            "item_type": "assessment",
            "item_id": "assessment-456"  # Same as existing
        }
        
        response = client.post("/api/v1/evidence/evidence-123/links", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return success but not add duplicate
        assert data["total_links"] == 1  # Should remain 1, not become 2
        
        # Verify repository calls
        mock_repo.get_evidence_by_id.assert_called_once()
        # update_evidence_links should not be called for duplicates
        mock_repo.update_evidence_links.assert_not_called()
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_link_evidence_not_found(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test linking non-existent evidence"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        # Mock repository - evidence not found
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = None
        mock_create_repo.return_value = mock_repo
        
        request_data = {
            "item_type": "assessment",
            "item_id": "assessment-456"
        }
        
        response = client.post("/api/v1/evidence/nonexistent-123/links", json=request_data)
        
        assert response.status_code == 404
        assert "Evidence not found" in response.json()["detail"]
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_link_evidence_access_denied(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test linking evidence when user is not a member"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = False  # User not a member
        
        # Mock existing evidence
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="other@example.com",
            linked_items=[]
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_create_repo.return_value = mock_repo
        
        request_data = {
            "item_type": "assessment",
            "item_id": "assessment-456"
        }
        
        response = client.post("/api/v1/evidence/evidence-123/links", json=request_data)
        
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


class TestEvidenceUnlinking:
    """Test evidence unlinking functionality"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_unlink_evidence_success(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test successful evidence unlinking"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock existing evidence with links
        existing_links = [
            {"item_type": "assessment", "item_id": "assessment-456"},
            {"item_type": "question", "item_id": "question-789"}
        ]
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=existing_links
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_repo.update_evidence_links.return_value = True
        mock_create_repo.return_value = mock_repo
        
        # Remove the first link
        link_id = "assessment:assessment-456"
        
        response = client.delete(f"/api/v1/evidence/evidence-123/links/{link_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Link removed"
        assert data["evidence_id"] == "evidence-123"
        assert data["item_type"] == "assessment"
        assert data["item_id"] == "assessment-456"
        assert data["remaining_links"] == 1
        
        # Verify repository calls
        mock_repo.get_evidence_by_id.assert_called_once_with("evidence-123")
        mock_repo.update_evidence_links.assert_called_once()
        
        # Check the updated links passed to repository
        call_args = mock_repo.update_evidence_links.call_args
        updated_links = call_args[0][2]  # Third argument
        assert len(updated_links) == 1
        assert updated_links[0]["item_type"] == "question"
        assert updated_links[0]["item_id"] == "question-789"
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_unlink_evidence_invalid_link_id_format(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test unlinking with invalid link_id format"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        
        # Invalid link_id without colon
        link_id = "invalid-format"
        
        response = client.delete(f"/api/v1/evidence/evidence-123/links/{link_id}")
        
        assert response.status_code == 400
        assert "Invalid link_id format" in response.json()["detail"]
        assert "item_type:item_id" in response.json()["detail"]
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_unlink_evidence_link_not_found(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test unlinking non-existent link"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock existing evidence with different links
        existing_links = [
            {"item_type": "question", "item_id": "question-789"}
        ]
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="user@example.com",
            linked_items=existing_links
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_create_repo.return_value = mock_repo
        
        # Try to remove non-existent link
        link_id = "assessment:assessment-456"
        
        response = client.delete(f"/api/v1/evidence/evidence-123/links/{link_id}")
        
        assert response.status_code == 404
        assert "Evidence link not found" in response.json()["detail"]
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_unlink_evidence_access_denied(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test unlinking evidence when user is not a member"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = False  # User not a member
        
        # Mock existing evidence
        mock_evidence = Evidence(
            id="evidence-123",
            engagement_id="eng-123",
            blob_path="test/path.pdf",
            filename="test.pdf",
            checksum_sha256="abc123",
            size=1024,
            mime_type="application/pdf",
            uploaded_by="other@example.com",
            linked_items=[{"item_type": "assessment", "item_id": "assessment-456"}]
        )
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_evidence_by_id.return_value = mock_evidence
        mock_create_repo.return_value = mock_repo
        
        link_id = "assessment:assessment-456"
        
        response = client.delete(f"/api/v1/evidence/evidence-123/links/{link_id}")
        
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


class TestEvidenceListPagination:
    """Test evidence list pagination headers"""
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_list_evidence_pagination_headers(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test evidence listing returns proper pagination headers"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock repository with pagination data
        mock_repo = AsyncMock()
        mock_evidence_list = [
            Evidence(
                id=f"evidence-{i}",
                engagement_id="eng-123",
                blob_path=f"test/path{i}.pdf",
                filename=f"test{i}.pdf",
                checksum_sha256=f"abc{i}",
                size=1024,
                mime_type="application/pdf",
                uploaded_by="user@example.com",
                linked_items=[]
            ) for i in range(10)  # 10 items on current page
        ]
        total_count = 95  # Total items across all pages
        mock_repo.list_evidence.return_value = (mock_evidence_list, total_count)
        mock_create_repo.return_value = mock_repo
        
        # Request page 2 with page_size 10
        response = client.get("/api/v1/evidence?engagement_id=eng-123&page=2&page_size=10")
        
        assert response.status_code == 200
        
        # Check pagination headers
        assert response.headers["X-Total-Count"] == "95"
        assert response.headers["X-Page"] == "2"
        assert response.headers["X-Page-Size"] == "10"
        assert response.headers["X-Total-Pages"] == "10"  # ceil(95/10) = 10
        assert response.headers["X-Has-Next"] == "true"   # Page 2 of 10, has next
        assert response.headers["X-Has-Previous"] == "true"  # Page 2, has previous
        
        # Verify response data
        data = response.json()
        assert len(data) == 10
        assert data[0]["id"] == "evidence-0"
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_list_evidence_first_page_headers(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test pagination headers for first page"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_evidence_list = []  # Empty first page
        total_count = 25
        mock_repo.list_evidence.return_value = (mock_evidence_list, total_count)
        mock_create_repo.return_value = mock_repo
        
        # Request first page
        response = client.get("/api/v1/evidence?engagement_id=eng-123&page=1&page_size=10")
        
        assert response.status_code == 200
        
        # Check pagination headers for first page
        assert response.headers["X-Total-Count"] == "25"
        assert response.headers["X-Page"] == "1"
        assert response.headers["X-Page-Size"] == "10"
        assert response.headers["X-Total-Pages"] == "3"  # ceil(25/10) = 3
        assert response.headers["X-Has-Next"] == "true"   # Page 1 of 3, has next
        assert response.headers["X-Has-Previous"] == "false"  # Page 1, no previous
    
    @patch('api.routes.evidence._check_engagement_membership')
    @patch('api.routes.evidence.create_cosmos_repository')
    @patch('security.deps.get_current_user')
    @patch('security.deps.require_role')
    async def test_list_evidence_last_page_headers(
        self, 
        mock_require_role, 
        mock_get_user,
        mock_create_repo,
        mock_check_membership
    ):
        """Test pagination headers for last page"""
        # Mock dependencies
        mock_require_role.return_value = None
        mock_get_user.return_value = {
            "email": "user@example.com",
            "roles": ["Member"],
            "correlation_id": "test-correlation"
        }
        mock_check_membership.return_value = True
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_evidence_list = []  # Last page with few items
        total_count = 25
        mock_repo.list_evidence.return_value = (mock_evidence_list, total_count)
        mock_create_repo.return_value = mock_repo
        
        # Request last page (page 3 of 3)
        response = client.get("/api/v1/evidence?engagement_id=eng-123&page=3&page_size=10")
        
        assert response.status_code == 200
        
        # Check pagination headers for last page
        assert response.headers["X-Total-Count"] == "25"
        assert response.headers["X-Page"] == "3"
        assert response.headers["X-Page-Size"] == "10"
        assert response.headers["X-Total-Pages"] == "3"  # ceil(25/10) = 3
        assert response.headers["X-Has-Next"] == "false"   # Page 3 of 3, no next
        assert response.headers["X-Has-Previous"] == "true"  # Page 3, has previous
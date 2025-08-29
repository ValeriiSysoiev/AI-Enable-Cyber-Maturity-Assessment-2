"""
Tests for the authorization service - ensuring proper access control
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from api.authorization import AuthorizationService, require_engagement_access
from domain.models import Engagement, Membership, Assessment
from fastapi import HTTPException


class TestAuthorizationService:
    """Test suite for AuthorizationService"""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository"""
        repo = Mock()
        return repo
    
    @pytest.fixture
    def auth_service(self, mock_repository):
        """Create an authorization service with mock repository"""
        return AuthorizationService(mock_repository)
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_admin_always_has_access(self, auth_service):
        """Test that system admins always have access to engagements"""
        result = await auth_service.check_engagement_access(
            user_email="admin@example.com",
            engagement_id="eng-123",
            is_admin=True
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_member_has_access(self, auth_service, mock_repository):
        """Test that engagement members have access"""
        # Setup mock memberships
        mock_membership = Membership(
            id="mem-1",
            engagement_id="eng-123",
            user_email="user@example.com",
            role="member"
        )
        mock_repository.list_memberships_for_engagement.return_value = [mock_membership]
        
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",
            engagement_id="eng-123",
            is_admin=False
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_non_member_denied(self, auth_service, mock_repository):
        """Test that non-members are denied access"""
        # Setup mock with no matching membership
        mock_membership = Membership(
            id="mem-1",
            engagement_id="eng-123",
            user_email="other@example.com",
            role="member"
        )
        mock_repository.list_memberships_for_engagement.return_value = [mock_membership]
        
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",
            engagement_id="eng-123",
            is_admin=False
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_with_required_role(self, auth_service, mock_repository):
        """Test access check with specific role requirement"""
        # Setup mock membership with member role
        mock_membership = Membership(
            id="mem-1",
            engagement_id="eng-123",
            user_email="user@example.com",
            role="member"
        )
        mock_repository.list_memberships_for_engagement.return_value = [mock_membership]
        
        # Should fail when owner role is required but user is member
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",
            engagement_id="eng-123",
            required_role="owner",
            is_admin=False
        )
        assert result is False
        
        # Should succeed when member role is required and user is member
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",
            engagement_id="eng-123",
            required_role="member",
            is_admin=False
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_case_insensitive_email(self, auth_service, mock_repository):
        """Test that email comparison is case-insensitive"""
        mock_membership = Membership(
            id="mem-1",
            engagement_id="eng-123",
            user_email="User@Example.COM",
            role="member"
        )
        mock_repository.list_memberships_for_engagement.return_value = [mock_membership]
        
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",  # Different case
            engagement_id="eng-123",
            is_admin=False
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_engagement_access_exception_handling(self, auth_service, mock_repository):
        """Test that exceptions result in access denial (fail closed)"""
        mock_repository.list_memberships_for_engagement.side_effect = Exception("Database error")
        
        result = await auth_service.check_engagement_access(
            user_email="user@example.com",
            engagement_id="eng-123",
            is_admin=False
        )
        assert result is False  # Should fail closed on error
    
    @pytest.mark.asyncio
    async def test_check_assessment_access_admin_has_access(self, auth_service, mock_repository):
        """Test that admins have access to all assessments"""
        result = await auth_service.check_assessment_access(
            user_email="admin@example.com",
            assessment_id="assess-123",
            is_admin=True
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_assessment_access_via_engagement(self, auth_service, mock_repository):
        """Test assessment access is checked via engagement membership"""
        # Setup mock assessment
        mock_assessment = Assessment(
            id="assess-123",
            name="Test Assessment",
            engagement_id="eng-123",
            framework="NIST-CSF"
        )
        mock_repository.get_assessment.return_value = mock_assessment
        
        # Setup mock membership
        mock_membership = Membership(
            id="mem-1",
            engagement_id="eng-123",
            user_email="user@example.com",
            role="member"
        )
        mock_repository.list_memberships_for_engagement.return_value = [mock_membership]
        
        result = await auth_service.check_assessment_access(
            user_email="user@example.com",
            assessment_id="assess-123",
            is_admin=False
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_assessment_access_assessment_not_found(self, auth_service, mock_repository):
        """Test that non-existent assessments result in access denial"""
        mock_repository.get_assessment.return_value = None
        
        result = await auth_service.check_assessment_access(
            user_email="user@example.com",
            assessment_id="nonexistent",
            is_admin=False
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_authorized_engagements(self, auth_service, mock_repository):
        """Test listing engagements user has access to"""
        mock_engagements = [
            Engagement(id="eng-1", name="Project 1", created_by="user@example.com"),
            Engagement(id="eng-2", name="Project 2", created_by="other@example.com")
        ]
        mock_repository.list_engagements_for_user.return_value = mock_engagements
        
        result = await auth_service.list_authorized_engagements(
            user_email="user@example.com",
            is_admin=False
        )
        assert len(result) == 2
        assert result == mock_engagements
    
    @pytest.mark.asyncio
    async def test_list_authorized_engagements_error_returns_empty(self, auth_service, mock_repository):
        """Test that errors in listing engagements return empty list"""
        mock_repository.list_engagements_for_user.side_effect = Exception("Database error")
        
        result = await auth_service.list_authorized_engagements(
            user_email="user@example.com",
            is_admin=False
        )
        assert result == []
    
    def test_validate_engagement_id_format_valid(self, auth_service):
        """Test validation of valid engagement ID formats"""
        valid_ids = [
            "eng-123",
            "engagement_456",
            "ABC123",
            "test-engagement-id",
            "a1b2c3d4e5"
        ]
        
        for eng_id in valid_ids:
            assert auth_service.validate_engagement_id_format(eng_id) is True
    
    def test_validate_engagement_id_format_invalid(self, auth_service):
        """Test rejection of invalid engagement ID formats"""
        invalid_ids = [
            "",  # Empty
            "a",  # Too short
            "ab",  # Too short
            "eng/123",  # Contains slash
            "../etc/passwd",  # Path traversal attempt
            "eng..123",  # Contains dots
            "eng<script>",  # Contains HTML
            "eng;DROP TABLE",  # SQL injection attempt
            "a" * 101,  # Too long
            "-start",  # Starts with hyphen
            "end-",  # Ends with hyphen
            "_start",  # Starts with underscore
            "end_"  # Ends with underscore
        ]
        
        for eng_id in invalid_ids:
            assert auth_service.validate_engagement_id_format(eng_id) is False


class TestRequireEngagementAccessDecorator:
    """Test suite for require_engagement_access decorator"""
    
    @pytest.mark.asyncio
    async def test_require_engagement_access_missing_context(self):
        """Test that missing context raises 400 error"""
        from api.authorization import require_engagement_access
        
        check_access = require_engagement_access()
        
        # Mock context without required fields
        mock_context = {}
        mock_auth_service = Mock(spec=AuthorizationService)
        
        with pytest.raises(HTTPException) as exc_info:
            await check_access(context=mock_context, auth_service=mock_auth_service)
        
        assert exc_info.value.status_code == 400
        assert "User email and engagement ID are required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_engagement_access_invalid_id_format(self):
        """Test that invalid engagement ID format raises 400 error"""
        from api.authorization import require_engagement_access
        
        check_access = require_engagement_access()
        
        mock_context = {
            "user_email": "user@example.com",
            "engagement_id": "../etc/passwd"  # Invalid format
        }
        mock_auth_service = Mock(spec=AuthorizationService)
        mock_auth_service.validate_engagement_id_format.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await check_access(context=mock_context, auth_service=mock_auth_service)
        
        assert exc_info.value.status_code == 400
        assert "Invalid engagement ID format" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_engagement_access_denied(self):
        """Test that access denial raises 403 error"""
        from api.authorization import require_engagement_access
        
        check_access = require_engagement_access()
        
        mock_context = {
            "user_email": "user@example.com",
            "engagement_id": "eng-123"
        }
        mock_auth_service = Mock(spec=AuthorizationService)
        mock_auth_service.validate_engagement_id_format.return_value = True
        mock_auth_service.check_engagement_access = AsyncMock(return_value=False)
        
        with patch('api.authorization.is_admin_with_demo_fallback', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await check_access(context=mock_context, auth_service=mock_auth_service)
        
        assert exc_info.value.status_code == 403
        assert "You do not have access to this engagement" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_engagement_access_with_role_requirement(self):
        """Test decorator with specific role requirement"""
        from api.authorization import require_engagement_access
        
        check_access = require_engagement_access(required_role="owner")
        
        mock_context = {
            "user_email": "user@example.com",
            "engagement_id": "eng-123"
        }
        mock_auth_service = Mock(spec=AuthorizationService)
        mock_auth_service.validate_engagement_id_format.return_value = True
        mock_auth_service.check_engagement_access = AsyncMock(return_value=True)
        
        with patch('api.authorization.is_admin_with_demo_fallback', return_value=False):
            result = await check_access(context=mock_context, auth_service=mock_auth_service)
        
        # Verify the role was passed to the check
        mock_auth_service.check_engagement_access.assert_called_with(
            "user@example.com",
            "eng-123",
            required_role="owner",
            is_admin=False
        )
        assert result == mock_context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
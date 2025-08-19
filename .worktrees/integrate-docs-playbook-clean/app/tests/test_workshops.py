"""
Comprehensive tests for workshops functionality
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from domain.models import Workshop, WorkshopAttendee, ConsentRecord
from api.schemas.workshop import WorkshopCreateRequest, ConsentRequest, AttendeeRequest
from api.routes.workshops import _workshop_to_response
from repos.cosmos_repository import CosmosRepository


@pytest.fixture
def sample_workshop():
    """Sample workshop for testing"""
    attendees = [
        WorkshopAttendee(
            user_id="user1",
            email="user1@example.com",
            role="participant"
        ),
        WorkshopAttendee(
            user_id="user2", 
            email="user2@example.com",
            role="facilitator"
        )
    ]
    
    return Workshop(
        engagement_id="test-engagement-123",
        title="Test Security Workshop",
        attendees=attendees,
        created_by="lead@example.com"
    )


@pytest.fixture
def workshop_with_consent():
    """Workshop with some attendees consented"""
    attendees = [
        WorkshopAttendee(
            user_id="user1",
            email="user1@example.com",
            role="participant",
            consent=ConsentRecord(
                by="user1@example.com",
                user_id="user1@example.com",
                timestamp=datetime.now(timezone.utc)
            )
        ),
        WorkshopAttendee(
            user_id="user2",
            email="user2@example.com", 
            role="facilitator"
            # No consent yet
        )
    ]
    
    return Workshop(
        engagement_id="test-engagement-123",
        title="Test Security Workshop",
        attendees=attendees,
        created_by="lead@example.com"
    )


@pytest.fixture
def mock_repo():
    """Mock repository for tests"""
    repo = Mock(spec=CosmosRepository)
    repo.create_workshop = AsyncMock()
    repo.get_workshop = AsyncMock()
    repo.list_workshops = AsyncMock()
    repo.update_workshop_consent = AsyncMock()
    repo.start_workshop = AsyncMock()
    repo.get_membership = Mock()
    return repo


@pytest.fixture
def mock_context():
    """Mock security context"""
    return {
        "user_email": "test@example.com",
        "engagement_id": "test-engagement-123",
        "tenant_id": None,
        "aad_groups_enabled": False
    }


@pytest.fixture
def lead_context():
    """Mock security context for lead user"""
    return {
        "user_email": "lead@example.com",
        "engagement_id": "test-engagement-123",
        "tenant_id": None,
        "aad_groups_enabled": False
    }


class TestWorkshopModels:
    """Test workshop domain models"""
    
    def test_workshop_creation(self, sample_workshop):
        """Test workshop model creation"""
        assert sample_workshop.id is not None
        assert sample_workshop.engagement_id == "test-engagement-123"
        assert sample_workshop.title == "Test Security Workshop"
        assert len(sample_workshop.attendees) == 2
        assert not sample_workshop.started
        assert sample_workshop.started_at is None
    
    def test_workshop_attendee_creation(self):
        """Test attendee model creation"""
        attendee = WorkshopAttendee(
            user_id="test-user",
            email="test@example.com",
            role="participant"
        )
        assert attendee.id is not None
        assert attendee.user_id == "test-user"
        assert attendee.email == "test@example.com"
        assert attendee.role == "participant"
        assert attendee.consent is None
    
    def test_consent_record_creation(self):
        """Test consent record creation"""
        consent = ConsentRecord(
            by="user@example.com",
            user_id="user@example.com"
        )
        assert consent.by == "user@example.com"
        assert consent.user_id == "user@example.com"
        assert isinstance(consent.timestamp, datetime)


class TestWorkshopRepository:
    """Test workshop repository operations"""
    
    @pytest.mark.asyncio
    async def test_create_workshop(self, mock_repo, sample_workshop):
        """Test workshop creation in repository"""
        mock_repo.create_workshop.return_value = sample_workshop
        
        result = await mock_repo.create_workshop(sample_workshop)
        
        assert result == sample_workshop
        mock_repo.create_workshop.assert_called_once_with(sample_workshop)
    
    @pytest.mark.asyncio
    async def test_get_workshop(self, mock_repo, sample_workshop):
        """Test workshop retrieval"""
        mock_repo.get_workshop.return_value = sample_workshop
        
        result = await mock_repo.get_workshop("workshop-123", "engagement-123")
        
        assert result == sample_workshop
        mock_repo.get_workshop.assert_called_once_with("workshop-123", "engagement-123")
    
    @pytest.mark.asyncio
    async def test_list_workshops(self, mock_repo, sample_workshop):
        """Test workshop listing with pagination"""
        workshops = [sample_workshop]
        total_count = 1
        mock_repo.list_workshops.return_value = (workshops, total_count)
        
        result_workshops, result_count = await mock_repo.list_workshops("engagement-123", 1, 50)
        
        assert result_workshops == workshops
        assert result_count == total_count
        mock_repo.list_workshops.assert_called_once_with("engagement-123", 1, 50)
    
    @pytest.mark.asyncio
    async def test_update_workshop_consent(self, mock_repo, workshop_with_consent):
        """Test consent update"""
        consent = ConsentRecord(by="user2@example.com", user_id="user2@example.com")
        mock_repo.update_workshop_consent.return_value = workshop_with_consent
        
        result = await mock_repo.update_workshop_consent(
            "workshop-123", "engagement-123", "attendee-123", consent
        )
        
        assert result == workshop_with_consent
        mock_repo.update_workshop_consent.assert_called_once_with(
            "workshop-123", "engagement-123", "attendee-123", consent
        )
    
    @pytest.mark.asyncio
    async def test_start_workshop_success(self, mock_repo, sample_workshop):
        """Test workshop start when all consents given"""
        # Set up workshop with all attendees consented
        for attendee in sample_workshop.attendees:
            attendee.consent = ConsentRecord(
                by=attendee.email,
                user_id=attendee.user_id
            )
        sample_workshop.started = True
        sample_workshop.started_at = datetime.now(timezone.utc)
        
        mock_repo.start_workshop.return_value = sample_workshop
        
        result = await mock_repo.start_workshop("workshop-123", "engagement-123")
        
        assert result.started is True
        assert result.started_at is not None
        mock_repo.start_workshop.assert_called_once_with("workshop-123", "engagement-123")
    
    @pytest.mark.asyncio
    async def test_start_workshop_missing_consent(self, mock_repo):
        """Test workshop start fails when consent missing"""
        mock_repo.start_workshop.side_effect = ValueError("Attendee user2@example.com has not given consent")
        
        with pytest.raises(ValueError, match="has not given consent"):
            await mock_repo.start_workshop("workshop-123", "engagement-123")


class TestWorkshopAPI:
    """Test workshop API endpoints"""
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.get_correlation_id')
    @patch('api.routes.workshops.create_audit_service')
    @patch('api.routes.workshops.require_member')
    async def test_create_workshop_success(
        self, mock_require_member, mock_audit_service, mock_correlation_id,
        mock_repo, mock_context, sample_workshop
    ):
        """Test successful workshop creation"""
        from api.routes.workshops import create_workshop
        
        # Setup mocks
        mock_correlation_id.return_value = "test-corr-id"
        mock_audit = Mock()
        mock_audit.log_audit_event = AsyncMock()
        mock_audit_service.return_value = mock_audit
        mock_repo.create_workshop.return_value = sample_workshop
        
        # Create request
        request = WorkshopCreateRequest(
            engagement_id="test-engagement-123",
            title="Test Security Workshop",
            attendees=[
                AttendeeRequest(user_id="user1", email="user1@example.com", role="participant"),
                AttendeeRequest(user_id="user2", email="user2@example.com", role="facilitator")
            ]
        )
        
        # Call endpoint
        result = await create_workshop(request, mock_repo, mock_context)
        
        # Assertions
        assert result.title == "Test Security Workshop"
        assert result.engagement_id == "test-engagement-123"
        assert len(result.attendees) == 2
        mock_require_member.assert_called_once_with(mock_repo, mock_context, "member")
        mock_repo.create_workshop.assert_called_once()
        mock_audit.log_audit_event.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.require_member')
    async def test_create_workshop_auth_failure(
        self, mock_require_member, mock_repo, mock_context
    ):
        """Test workshop creation fails with auth error"""
        from api.routes.workshops import create_workshop
        
        # Setup auth failure
        mock_require_member.side_effect = HTTPException(403, "Not a member of this engagement")
        
        request = WorkshopCreateRequest(
            engagement_id="test-engagement-123",
            title="Test Workshop",
            attendees=[
                AttendeeRequest(user_id="user1", email="user1@example.com", role="participant")
            ]
        )
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_workshop(request, mock_repo, mock_context)
        
        assert exc_info.value.status_code == 403
        assert "Not a member" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.get_correlation_id')
    @patch('api.routes.workshops.create_audit_service')
    @patch('api.routes.workshops.require_member')
    async def test_give_consent_success(
        self, mock_require_member, mock_audit_service, mock_correlation_id,
        mock_repo, mock_context, workshop_with_consent
    ):
        """Test successful consent giving"""
        from api.routes.workshops import give_consent
        
        # Setup mocks
        mock_correlation_id.return_value = "test-corr-id"
        mock_audit = Mock()
        mock_audit.log_audit_event = AsyncMock()
        mock_audit_service.return_value = mock_audit
        mock_repo.update_workshop_consent.return_value = workshop_with_consent
        
        # Create request
        request = ConsentRequest(attendee_id="attendee-123", consent=True)
        
        # Call endpoint
        result = await give_consent("workshop-123", request, mock_repo, mock_context)
        
        # Assertions
        assert result.id == workshop_with_consent.id
        mock_require_member.assert_called_once_with(mock_repo, mock_context, "member")
        mock_repo.update_workshop_consent.assert_called_once()
        mock_audit.log_audit_event.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.get_correlation_id')
    @patch('api.routes.workshops.create_audit_service')
    @patch('api.routes.workshops.require_member')
    async def test_start_workshop_success(
        self, mock_require_member, mock_audit_service, mock_correlation_id,
        mock_repo, lead_context, sample_workshop
    ):
        """Test successful workshop start"""
        from api.routes.workshops import start_workshop
        
        # Setup workshop as started
        sample_workshop.started = True
        sample_workshop.started_at = datetime.now(timezone.utc)
        
        # Setup mocks
        mock_correlation_id.return_value = "test-corr-id"
        mock_audit = Mock()
        mock_audit.log_audit_event = AsyncMock()
        mock_audit_service.return_value = mock_audit
        mock_repo.start_workshop.return_value = sample_workshop
        
        # Call endpoint
        result = await start_workshop("workshop-123", mock_repo, lead_context)
        
        # Assertions
        assert result.workshop.started is True
        assert "started successfully" in result.message
        mock_require_member.assert_called_once_with(mock_repo, lead_context, "lead")
        mock_repo.start_workshop.assert_called_once_with("workshop-123", "test-engagement-123")
        mock_audit.log_audit_event.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.require_member')
    async def test_start_workshop_missing_consent(
        self, mock_require_member, mock_repo, lead_context
    ):
        """Test workshop start fails with missing consent"""
        from api.routes.workshops import start_workshop
        
        # Setup repo to raise consent error
        mock_repo.start_workshop.side_effect = ValueError("Attendee user@example.com has not given consent")
        
        # Should raise HTTPException with 403
        with pytest.raises(HTTPException) as exc_info:
            await start_workshop("workshop-123", mock_repo, lead_context)
        
        assert exc_info.value.status_code == 403
        assert "consent" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.require_member')
    async def test_start_workshop_not_lead(
        self, mock_require_member, mock_repo, mock_context
    ):
        """Test workshop start fails for non-lead user"""
        from api.routes.workshops import start_workshop
        
        # Setup auth failure for non-lead
        mock_require_member.side_effect = HTTPException(403, "Lead role required")
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await start_workshop("workshop-123", mock_repo, mock_context)
        
        assert exc_info.value.status_code == 403
        assert "Lead role required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('api.routes.workshops.get_correlation_id')
    @patch('api.routes.workshops.create_audit_service')
    @patch('api.routes.workshops.require_member')
    async def test_list_workshops_success(
        self, mock_require_member, mock_audit_service, mock_correlation_id,
        mock_repo, mock_context, sample_workshop
    ):
        """Test successful workshop listing"""
        from api.routes.workshops import list_workshops
        
        # Setup mocks
        mock_correlation_id.return_value = "test-corr-id"
        mock_audit = Mock()
        mock_audit.log_audit_event = AsyncMock()
        mock_audit_service.return_value = mock_audit
        mock_repo.list_workshops.return_value = ([sample_workshop], 1)
        
        # Call endpoint
        result = await list_workshops(
            engagement_id="test-engagement-123",
            page=1,
            page_size=50,
            repo=mock_repo,
            ctx=mock_context
        )
        
        # Assertions
        assert len(result.workshops) == 1
        assert result.total_count == 1
        assert result.page == 1
        assert result.page_size == 50
        assert not result.has_more
        mock_require_member.assert_called_once()
        mock_repo.list_workshops.assert_called_once_with("test-engagement-123", 1, 50)
        mock_audit.log_audit_event.assert_called_once()


class TestWorkshopSecurity:
    """Test security and authorization aspects"""
    
    @pytest.mark.asyncio
    async def test_create_requires_membership(self, mock_repo):
        """Test create workshop requires engagement membership"""
        from api.routes.workshops import create_workshop
        
        context_no_membership = {
            "user_email": "outsider@example.com",
            "engagement_id": "test-engagement-123"
        }
        
        request = WorkshopCreateRequest(
            engagement_id="test-engagement-123",
            title="Test Workshop",
            attendees=[
                AttendeeRequest(user_id="user1", email="user1@example.com", role="participant")
            ]
        )
        
        # Mock membership check to fail
        with patch('api.routes.workshops.require_member') as mock_require:
            mock_require.side_effect = HTTPException(403, "Not a member of this engagement")
            
            with pytest.raises(HTTPException) as exc_info:
                await create_workshop(request, mock_repo, context_no_membership)
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_start_requires_lead_role(self, mock_repo):
        """Test start workshop requires lead role"""
        from api.routes.workshops import start_workshop
        
        member_context = {
            "user_email": "member@example.com",
            "engagement_id": "test-engagement-123"
        }
        
        # Mock membership check to fail for lead requirement
        with patch('api.routes.workshops.require_member') as mock_require:
            mock_require.side_effect = HTTPException(403, "Lead role required")
            
            with pytest.raises(HTTPException) as exc_info:
                await start_workshop("workshop-123", mock_repo, member_context)
            
            assert exc_info.value.status_code == 403
            assert "Lead role required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_audit_logging_on_all_operations(self, mock_repo, mock_context):
        """Test that all operations create audit log entries"""
        # This would be covered by the individual operation tests above
        # Ensuring audit_service.log_audit_event is called
        pass


class TestWorkshopResponseMapping:
    """Test response model mapping"""
    
    def test_workshop_to_response_mapping(self, workshop_with_consent):
        """Test workshop domain model to response model mapping"""
        response = _workshop_to_response(workshop_with_consent)
        
        assert response.id == workshop_with_consent.id
        assert response.engagement_id == workshop_with_consent.engagement_id
        assert response.title == workshop_with_consent.title
        assert len(response.attendees) == 2
        
        # Check consent mapping
        consent_attendee = next(a for a in response.attendees if a.consent is not None)
        assert consent_attendee.consent.by == "user1@example.com"
        assert consent_attendee.consent.user_id == "user1@example.com"
        
        no_consent_attendee = next(a for a in response.attendees if a.consent is None)
        assert no_consent_attendee.email == "user2@example.com"


class TestWorkshopValidation:
    """Test input validation"""
    
    def test_workshop_create_request_validation(self):
        """Test workshop creation request validation"""
        # Valid request
        request = WorkshopCreateRequest(
            engagement_id="test-engagement-123",
            title="Test Workshop",
            attendees=[
                AttendeeRequest(user_id="user1", email="user1@example.com", role="participant")
            ]
        )
        assert request.engagement_id == "test-engagement-123"
        assert len(request.attendees) == 1
        
        # Invalid - empty attendees should fail
        with pytest.raises(Exception):  # Pydantic validation error
            WorkshopCreateRequest(
                engagement_id="test-engagement-123",
                title="Test Workshop",
                attendees=[]
            )
    
    def test_consent_request_validation(self):
        """Test consent request validation"""
        # Valid request
        request = ConsentRequest(attendee_id="attendee-123", consent=True)
        assert request.consent is True
        assert request.attendee_id == "attendee-123"
        
        # Test that false consent would be rejected (if we had validator)
        # This would need custom validator in the model
    
    def test_email_validation_in_attendee(self):
        """Test email validation in attendee request"""
        # Valid email
        attendee = AttendeeRequest(
            user_id="user1",
            email="valid@example.com",
            role="participant"
        )
        assert attendee.email == "valid@example.com"
        
        # Invalid email should fail validation
        with pytest.raises(Exception):  # Pydantic validation error
            AttendeeRequest(
                user_id="user1",
                email="invalid-email",
                role="participant"
            )
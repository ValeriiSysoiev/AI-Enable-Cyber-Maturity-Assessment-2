"""
Comprehensive tests for Minutes Agent functionality.

Tests cover:
- Domain models (Minutes, MinutesSection)
- Repository operations (create, get, update)
- Minutes agent service
- API endpoints with security
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from domain.models import Minutes, MinutesSection
from domain.repository import InMemoryRepository
from services.minutes_agent import MinutesAgent, create_minutes_agent
from api.routes.minutes import router as minutes_router
from fastapi import FastAPI


# Test fixtures
@pytest.fixture
def sample_minutes_section():
    """Sample minutes section for testing"""
    return MinutesSection(
        attendees=["Alice Smith", "Bob Jones", "Carol Wilson"],
        decisions=["Approved security upgrade", "Set monthly review meetings"],
        actions=["Alice to draft proposal by Friday", "Bob to review compliance"],
        questions=["What's the budget for implementation?", "Timeline for rollout?"]
    )

@pytest.fixture
def sample_minutes(sample_minutes_section):
    """Sample minutes for testing"""
    return Minutes(
        workshop_id="workshop-123",
        status="draft",
        sections=sample_minutes_section,
        generated_by="agent",
        updated_by="test@example.com"
    )

@pytest.fixture
def sample_workshop_data():
    """Sample workshop data for agent testing"""
    return {
        "id": "workshop-123",
        "type": "security",
        "attendees": ["Alice Smith", "Bob Jones"],
        "additional_context": {"topic": "Security Assessment"}
    }

@pytest.fixture
def in_memory_repo():
    """In-memory repository for testing"""
    return InMemoryRepository()

@pytest.fixture
def minutes_agent():
    """Minutes agent instance for testing"""
    return create_minutes_agent("test-correlation-id")

@pytest.fixture
def mock_security_context():
    """Mock security context for API tests"""
    return {
        "user_email": "test@example.com",
        "engagement_id": "engagement-123",
        "tenant_id": None,
        "aad_groups_enabled": False,
        "aad_groups": [],
        "aad_roles": [],
        "is_aad_admin": False,
        "tenant_validated": True
    }


# Domain Model Tests
class TestMinutesModels:
    
    def test_minutes_section_creation(self):
        """Test MinutesSection model creation and defaults"""
        section = MinutesSection()
        
        assert section.attendees == []
        assert section.decisions == []
        assert section.actions == []
        assert section.questions == []
    
    def test_minutes_section_with_data(self, sample_minutes_section):
        """Test MinutesSection with sample data"""
        assert len(sample_minutes_section.attendees) == 3
        assert len(sample_minutes_section.decisions) == 2
        assert len(sample_minutes_section.actions) == 2
        assert len(sample_minutes_section.questions) == 2
    
    def test_minutes_creation(self, sample_minutes):
        """Test Minutes model creation"""
        assert sample_minutes.workshop_id == "workshop-123"
        assert sample_minutes.status == "draft"
        assert sample_minutes.generated_by == "agent"
        assert sample_minutes.updated_by == "test@example.com"
        assert sample_minutes.published_at is None
        assert isinstance(sample_minutes.created_at, datetime)
        assert sample_minutes.id  # Should have auto-generated ID
    
    def test_minutes_serialization(self, sample_minutes):
        """Test Minutes model serialization"""
        data = sample_minutes.model_dump()
        
        assert data["workshop_id"] == "workshop-123"
        assert data["status"] == "draft"
        assert "sections" in data
        assert "attendees" in data["sections"]


# Repository Tests
class TestMinutesRepository:
    
    def test_create_minutes(self, in_memory_repo, sample_minutes):
        """Test creating minutes in repository"""
        result = in_memory_repo.create_minutes(sample_minutes)
        
        assert result.id == sample_minutes.id
        assert result.workshop_id == sample_minutes.workshop_id
        assert result.status == sample_minutes.status
    
    def test_create_duplicate_minutes_fails(self, in_memory_repo, sample_minutes):
        """Test that creating duplicate minutes fails"""
        in_memory_repo.create_minutes(sample_minutes)
        
        with pytest.raises(ValueError, match="Minutes with ID .* already exists"):
            in_memory_repo.create_minutes(sample_minutes)
    
    def test_get_minutes(self, in_memory_repo, sample_minutes):
        """Test getting minutes by ID"""
        in_memory_repo.create_minutes(sample_minutes)
        
        result = in_memory_repo.get_minutes(sample_minutes.id)
        
        assert result is not None
        assert result.id == sample_minutes.id
        assert result.workshop_id == sample_minutes.workshop_id
    
    def test_get_nonexistent_minutes(self, in_memory_repo):
        """Test getting non-existent minutes returns None"""
        result = in_memory_repo.get_minutes("nonexistent-id")
        assert result is None
    
    def test_update_minutes(self, in_memory_repo, sample_minutes, sample_minutes_section):
        """Test updating existing minutes"""
        # Create original
        in_memory_repo.create_minutes(sample_minutes)
        
        # Update
        updated_minutes = Minutes(
            id=sample_minutes.id,
            workshop_id=sample_minutes.workshop_id,
            status="published",
            sections=sample_minutes_section,
            generated_by="human",
            updated_by="editor@example.com",
            created_at=sample_minutes.created_at
        )
        
        result = in_memory_repo.update_minutes(updated_minutes)
        
        assert result.status == "published"
        assert result.generated_by == "human"
        assert result.updated_by == "editor@example.com"
    
    def test_update_nonexistent_minutes_fails(self, in_memory_repo, sample_minutes):
        """Test updating non-existent minutes fails"""
        with pytest.raises(ValueError, match="Minutes with ID .* does not exist"):
            in_memory_repo.update_minutes(sample_minutes)
    
    def test_get_minutes_by_workshop(self, in_memory_repo, sample_minutes_section):
        """Test getting all minutes for a workshop"""
        workshop_id = "workshop-123"
        
        # Create multiple minutes for same workshop
        minutes1 = Minutes(
            workshop_id=workshop_id,
            sections=sample_minutes_section,
            updated_by="user1@example.com"
        )
        minutes2 = Minutes(
            workshop_id=workshop_id,
            sections=sample_minutes_section,
            updated_by="user2@example.com"
        )
        # Different workshop
        minutes3 = Minutes(
            workshop_id="other-workshop",
            sections=sample_minutes_section,
            updated_by="user3@example.com"
        )
        
        in_memory_repo.create_minutes(minutes1)
        in_memory_repo.create_minutes(minutes2)
        in_memory_repo.create_minutes(minutes3)
        
        result = in_memory_repo.get_minutes_by_workshop(workshop_id)
        
        assert len(result) == 2
        assert all(m.workshop_id == workshop_id for m in result)


# Minutes Agent Service Tests
class TestMinutesAgent:
    
    @pytest.mark.asyncio
    async def test_generate_draft_minutes_basic(self, minutes_agent, sample_workshop_data):
        """Test basic draft minutes generation"""
        result = await minutes_agent.generate_draft_minutes(sample_workshop_data)
        
        assert isinstance(result, MinutesSection)
        assert len(result.attendees) > 0
        assert len(result.decisions) > 0
        assert len(result.actions) > 0
        assert len(result.questions) > 0
    
    @pytest.mark.asyncio
    async def test_generate_security_workshop_minutes(self, minutes_agent):
        """Test minutes generation for security workshop"""
        workshop_data = {
            "id": "sec-workshop-456",
            "type": "security",
            "attendees": ["Security Lead", "Compliance Officer"]
        }
        
        result = await minutes_agent.generate_draft_minutes(workshop_data)
        
        # Should have security-specific content
        decisions = " ".join(result.decisions).lower()
        assert "security" in decisions or "authentication" in decisions or "risk" in decisions
    
    @pytest.mark.asyncio
    async def test_extract_attendees_from_workshop(self, minutes_agent):
        """Test attendees extraction from workshop data"""
        workshop_data = {
            "id": "workshop-789",
            "attendees": ["Custom Attendee 1", "Custom Attendee 2"]
        }
        
        result = await minutes_agent.generate_draft_minutes(workshop_data)
        
        assert "Custom Attendee 1" in result.attendees
        assert "Custom Attendee 2" in result.attendees
    
    @pytest.mark.asyncio
    async def test_generate_with_participants_key(self, minutes_agent):
        """Test extraction when workshop uses 'participants' key"""
        workshop_data = {
            "id": "workshop-participants",
            "participants": ["Participant 1", "Participant 2"]
        }
        
        result = await minutes_agent.generate_draft_minutes(workshop_data)
        
        assert "Participant 1" in result.attendees
        assert "Participant 2" in result.attendees
    
    @pytest.mark.asyncio
    async def test_generate_with_no_attendees(self, minutes_agent):
        """Test generation with default attendees when none provided"""
        workshop_data = {"id": "workshop-no-attendees"}
        
        result = await minutes_agent.generate_draft_minutes(workshop_data)
        
        # Should have default attendees
        assert len(result.attendees) >= 4
        assert "Workshop Facilitator" in result.attendees
    
    def test_create_minutes_agent_factory(self):
        """Test minutes agent factory function"""
        agent = create_minutes_agent("test-correlation")
        
        assert isinstance(agent, MinutesAgent)
        assert agent.correlation_id == "test-correlation"


# API Endpoint Tests
class TestMinutesAPI:
    
    @pytest.fixture
    def app_with_minutes(self):
        """FastAPI app with minutes router for testing"""
        app = FastAPI()
        app.include_router(minutes_router)
        
        # Mock repository
        mock_repo = Mock(spec=InMemoryRepository)
        app.state.repo = mock_repo
        
        return app, mock_repo
    
    @pytest.fixture
    def client(self, app_with_minutes):
        """Test client for API endpoints"""
        app, mock_repo = app_with_minutes
        return TestClient(app), mock_repo
    
    def test_generate_minutes_requires_auth(self, client):
        """Test that generate minutes endpoint requires authentication"""
        test_client, _ = client
        
        response = test_client.post(
            "/api/v1/workshops/test-workshop/minutes:generate",
            json={"workshop_type": "security"}
        )
        
        # Should fail due to missing headers
        assert response.status_code == 422  # Validation error for missing headers
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    @patch('api.routes.minutes.create_minutes_agent')
    def test_generate_minutes_success(
        self, 
        mock_create_agent, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes_section,
        mock_security_context
    ):
        """Test successful minutes generation"""
        test_client, mock_repo = client
        
        # Mock security context
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None  # Success
        
        # Mock agent
        mock_agent = Mock()
        mock_agent.generate_draft_minutes = AsyncMock(return_value=sample_minutes_section)
        mock_create_agent.return_value = mock_agent
        
        # Mock repository
        mock_minutes = Minutes(
            workshop_id="test-workshop",
            sections=sample_minutes_section,
            updated_by=mock_security_context["user_email"]
        )
        mock_repo.create_minutes.return_value = mock_minutes
        
        response = test_client.post(
            "/api/v1/workshops/test-workshop/minutes:generate",
            json={"workshop_type": "security"},
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["workshop_id"] == "test-workshop"
        assert data["status"] == "draft"
        assert data["generated_by"] == "agent"
        assert "sections" in data
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_generate_minutes_member_check_failure(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        mock_security_context
    ):
        """Test minutes generation with membership check failure"""
        test_client, _ = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.side_effect = HTTPException(status_code=403, detail="Not a member")
        
        response = test_client.post(
            "/api/v1/workshops/test-workshop/minutes:generate",
            json={"workshop_type": "security"},
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 403
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_update_draft_minutes_only(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes_section,
        mock_security_context
    ):
        """Test that only draft minutes can be updated"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        
        # Mock existing published minutes
        existing_minutes = Minutes(
            id="minutes-123",
            workshop_id="test-workshop",
            status="published",  # Not draft
            sections=sample_minutes_section,
            updated_by="original@example.com"
        )
        mock_repo.get_minutes.return_value = existing_minutes
        
        response = test_client.patch(
            "/api/v1/minutes/minutes-123",
            json={"sections": sample_minutes_section.model_dump()},
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 403
        assert "draft minutes" in response.json()["detail"]
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_get_minutes_success(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes,
        mock_security_context
    ):
        """Test successful retrieval of minutes"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        mock_repo.get_minutes.return_value = sample_minutes
        
        response = test_client.get(
            f"/api/v1/minutes/{sample_minutes.id}",
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_minutes.id
        assert data["workshop_id"] == sample_minutes.workshop_id
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_get_nonexistent_minutes(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        mock_security_context
    ):
        """Test retrieval of non-existent minutes"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        mock_repo.get_minutes.return_value = None
        
        response = test_client.get(
            "/api/v1/minutes/nonexistent-id",
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 404


# Integration Tests
class TestMinutesIntegration:
    
    @pytest.mark.asyncio
    async def test_end_to_end_minutes_workflow(self, in_memory_repo, minutes_agent, sample_workshop_data):
        """Test complete workflow: generate -> store -> retrieve -> update"""
        
        # 1. Generate minutes using agent
        sections = await minutes_agent.generate_draft_minutes(sample_workshop_data)
        
        # 2. Create minutes in repository
        minutes = Minutes(
            workshop_id=sample_workshop_data["id"],
            sections=sections,
            updated_by="workflow@example.com"
        )
        stored_minutes = in_memory_repo.create_minutes(minutes)
        
        # 3. Retrieve minutes
        retrieved_minutes = in_memory_repo.get_minutes(stored_minutes.id)
        assert retrieved_minutes is not None
        assert retrieved_minutes.status == "draft"
        
        # 4. Update minutes to published
        updated_minutes = Minutes(
            id=retrieved_minutes.id,
            workshop_id=retrieved_minutes.workshop_id,
            status="published",
            sections=retrieved_minutes.sections,
            generated_by="human",
            updated_by="publisher@example.com",
            created_at=retrieved_minutes.created_at,
            published_at=datetime.now(timezone.utc)
        )
        
        final_minutes = in_memory_repo.update_minutes(updated_minutes)
        assert final_minutes.status == "published"
        assert final_minutes.generated_by == "human"
        assert final_minutes.published_at is not None
    
    def test_minutes_cross_engagement_security(self, in_memory_repo, sample_minutes_section):
        """Test that minutes are properly scoped by workshop/engagement"""
        
        # Create minutes for different workshops
        minutes1 = Minutes(
            workshop_id="engagement-1-workshop",
            sections=sample_minutes_section,
            updated_by="user1@example.com"
        )
        minutes2 = Minutes(
            workshop_id="engagement-2-workshop", 
            sections=sample_minutes_section,
            updated_by="user2@example.com"
        )
        
        in_memory_repo.create_minutes(minutes1)
        in_memory_repo.create_minutes(minutes2)
        
        # Should only get minutes for specific workshop
        workshop1_minutes = in_memory_repo.get_minutes_by_workshop("engagement-1-workshop")
        workshop2_minutes = in_memory_repo.get_minutes_by_workshop("engagement-2-workshop")
        
        assert len(workshop1_minutes) == 1
        assert len(workshop2_minutes) == 1
        assert workshop1_minutes[0].id != workshop2_minutes[0].id


# Publish Workflow Tests
class TestMinutesPublishWorkflow:
    
    def test_content_hash_computation(self, sample_minutes):
        """Test content hash computation for immutability"""
        hash1 = sample_minutes.compute_content_hash()
        hash2 = sample_minutes.compute_content_hash()
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_content_hash_changes_with_content(self, sample_minutes, sample_minutes_section):
        """Test that content hash changes when content changes"""
        original_hash = sample_minutes.compute_content_hash()
        
        # Modify content
        new_section = MinutesSection(
            attendees=sample_minutes_section.attendees + ["New Attendee"],
            decisions=sample_minutes_section.decisions,
            actions=sample_minutes_section.actions,
            questions=sample_minutes_section.questions
        )
        
        modified_minutes = Minutes(
            id=sample_minutes.id,
            workshop_id=sample_minutes.workshop_id,
            status=sample_minutes.status,
            sections=new_section,
            generated_by=sample_minutes.generated_by,
            updated_by=sample_minutes.updated_by,
            created_at=sample_minutes.created_at
        )
        
        modified_hash = modified_minutes.compute_content_hash()
        assert original_hash != modified_hash
    
    def test_content_integrity_validation(self, sample_minutes):
        """Test content integrity validation"""
        # Draft minutes without hash should be valid
        assert sample_minutes.validate_content_integrity() == True
        
        # Set content hash
        content_hash = sample_minutes.compute_content_hash()
        sample_minutes.content_hash = content_hash
        
        # Should still be valid
        assert sample_minutes.validate_content_integrity() == True
        
        # Tamper with hash
        sample_minutes.content_hash = "invalid_hash"
        assert sample_minutes.validate_content_integrity() == False
    
    def test_publish_minutes_workflow(self, in_memory_repo, sample_minutes):
        """Test the complete publish workflow"""
        # Create draft minutes
        stored_minutes = in_memory_repo.create_minutes(sample_minutes)
        assert stored_minutes.status == "draft"
        assert stored_minutes.content_hash is None
        
        # Publish minutes
        published_minutes = in_memory_repo.publish_minutes(stored_minutes.id)
        
        assert published_minutes.status == "published"
        assert published_minutes.content_hash is not None
        assert published_minutes.published_at is not None
        assert len(published_minutes.content_hash) == 64  # SHA-256 hex
    
    def test_publish_only_draft_minutes(self, in_memory_repo, sample_minutes):
        """Test that only draft minutes can be published"""
        # Create and publish minutes first
        stored_minutes = in_memory_repo.create_minutes(sample_minutes)
        published_minutes = in_memory_repo.publish_minutes(stored_minutes.id)
        
        # Try to publish again - should fail
        with pytest.raises(ValueError, match="Can only publish draft minutes"):
            in_memory_repo.publish_minutes(published_minutes.id)
    
    def test_editing_published_minutes_fails(self, in_memory_repo, sample_minutes):
        """Test that published minutes cannot be edited"""
        # Create and publish minutes
        stored_minutes = in_memory_repo.create_minutes(sample_minutes)
        published_minutes = in_memory_repo.publish_minutes(stored_minutes.id)
        
        # Try to edit published minutes - should fail
        modified_minutes = Minutes(
            id=published_minutes.id,
            workshop_id=published_minutes.workshop_id,
            status="published",
            sections=published_minutes.sections,
            generated_by="human",
            updated_by="editor@example.com",
            created_at=published_minutes.created_at
        )
        
        # The update should work but API layer should prevent this
        # Here we test that the can_edit() method works correctly
        assert not published_minutes.can_edit()
        assert published_minutes.is_published()
    
    def test_create_new_version_workflow(self, in_memory_repo, sample_minutes):
        """Test creating new version for editing published minutes"""
        # Create and publish original
        stored_minutes = in_memory_repo.create_minutes(sample_minutes)
        published_minutes = in_memory_repo.publish_minutes(stored_minutes.id)
        
        # Create new version
        new_version = in_memory_repo.create_new_version(published_minutes.id, "editor@example.com")
        
        # Verify new version properties
        assert new_version.id != published_minutes.id
        assert new_version.workshop_id == published_minutes.workshop_id
        assert new_version.status == "draft"
        assert new_version.parent_id == published_minutes.id
        assert new_version.generated_by == "human"
        assert new_version.updated_by == "editor@example.com"
        assert new_version.content_hash is None
        assert new_version.published_at is None
        
        # Content should be copied from parent
        assert new_version.sections.attendees == published_minutes.sections.attendees
        assert new_version.sections.decisions == published_minutes.sections.decisions
    
    def test_version_chain_integrity(self, in_memory_repo, sample_minutes):
        """Test that version chains maintain proper relationships"""
        # Create original -> publish -> create new version -> publish -> create another version
        original = in_memory_repo.create_minutes(sample_minutes)
        published_v1 = in_memory_repo.publish_minutes(original.id)
        
        draft_v2 = in_memory_repo.create_new_version(published_v1.id, "editor1@example.com")
        published_v2 = in_memory_repo.publish_minutes(draft_v2.id)
        
        draft_v3 = in_memory_repo.create_new_version(published_v2.id, "editor2@example.com")
        
        # Verify chain
        assert original.parent_id is None  # Original has no parent
        assert published_v1.id == original.id  # Same record, just published
        assert draft_v2.parent_id == published_v1.id
        assert published_v2.id == draft_v2.id  # Same record, just published
        assert draft_v3.parent_id == published_v2.id


# API Tests for Publish Functionality
class TestPublishAPI:
    
    @pytest.fixture
    def app_with_minutes(self):
        """FastAPI app with minutes router for testing"""
        app = FastAPI()
        app.include_router(minutes_router)
        
        # Mock repository
        mock_repo = Mock(spec=InMemoryRepository)
        app.state.repo = mock_repo
        
        return app, mock_repo
    
    @pytest.fixture
    def client(self, app_with_minutes):
        """Test client for API endpoints"""
        app, mock_repo = app_with_minutes
        return TestClient(app), mock_repo
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_publish_minutes_endpoint(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes,
        mock_security_context
    ):
        """Test the publish minutes API endpoint"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        
        # Mock published minutes result
        published_minutes = Minutes(
            id=sample_minutes.id,
            workshop_id=sample_minutes.workshop_id,
            status="published",
            sections=sample_minutes.sections,
            generated_by=sample_minutes.generated_by,
            published_at=datetime.now(timezone.utc),
            content_hash="abc123",
            updated_by=sample_minutes.updated_by,
            created_at=sample_minutes.created_at
        )
        mock_repo.publish_minutes.return_value = published_minutes
        
        response = test_client.post(
            f"/api/v1/minutes/{sample_minutes.id}:publish",
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["content_hash"] == "abc123"
        assert data["published_at"] is not None
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_create_new_version_endpoint(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes,
        mock_security_context
    ):
        """Test the create new version API endpoint"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        
        # Mock new version result
        new_version = Minutes(
            workshop_id=sample_minutes.workshop_id,
            status="draft",
            sections=sample_minutes.sections,
            generated_by="human",
            parent_id=sample_minutes.id,
            updated_by="test@example.com"
        )
        mock_repo.create_new_version.return_value = new_version
        
        response = test_client.post(
            f"/api/v1/minutes/{sample_minutes.id}/versions/new",
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert data["parent_id"] == sample_minutes.id
        assert data["generated_by"] == "human"
        assert data["updated_by"] == "test@example.com"
    
    @patch('api.routes.minutes.current_context')
    @patch('api.routes.minutes.require_member')
    def test_patch_published_minutes_returns_409(
        self, 
        mock_require_member, 
        mock_current_context,
        client,
        sample_minutes_section,
        mock_security_context
    ):
        """Test that PATCH returns 409 for published minutes with guidance"""
        test_client, mock_repo = client
        
        mock_current_context.return_value = mock_security_context
        mock_require_member.return_value = None
        
        # Mock existing published minutes
        published_minutes = Minutes(
            id="minutes-123",
            workshop_id="test-workshop",
            status="published",
            sections=sample_minutes_section,
            updated_by="original@example.com"
        )
        mock_repo.get_minutes.return_value = published_minutes
        
        response = test_client.patch(
            "/api/v1/minutes/minutes-123",
            json={"sections": sample_minutes_section.model_dump()},
            headers={
                "X-User-Email": "test@example.com",
                "X-Engagement-ID": "engagement-123"
            }
        )
        
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "Cannot edit published minutes" in detail
        assert "/versions/new" in detail  # Should guide to new version endpoint
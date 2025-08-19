"""
Integration tests for chat API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from api.main import app
from domain.models import ChatMessage, RunCard, Membership, Engagement
from domain.repository import InMemoryRepository


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_repo():
    """Mock repository with test data"""
    repo = InMemoryRepository()
    
    # Create test engagement and membership
    engagement = Engagement(
        id="test-engagement-123",
        name="Test Engagement", 
        created_by="test@example.com"
    )
    membership = Membership(
        engagement_id="test-engagement-123",
        user_email="test@example.com",
        role="member"
    )
    
    repo.create_engagement(engagement)
    repo.add_membership(membership)
    
    return repo


@pytest.fixture
def auth_headers():
    """Standard auth headers for tests"""
    return {
        "X-User-Email": "test@example.com",
        "X-Engagement-ID": "test-engagement-123",
        "X-Correlation-ID": "test-correlation-123"
    }


class TestChatEndpoints:
    """Test suite for chat API endpoints"""
    
    def test_send_message_success(self, client, mock_repo, auth_headers):
        """Test successful message sending"""
        app.state.repo = mock_repo
        
        response = client.post(
            "/api/v1/chat/message",
            json={
                "message": "Hello, how can I help?",
                "correlation_id": "test-correlation-123"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["engagement_id"] == "test-engagement-123"
        assert data["message"] == "Hello, how can I help?"
        assert data["sender"] == "user"
        assert "timestamp" in data
    
    def test_send_command_creates_run_card(self, client, mock_repo, auth_headers):
        """Test that sending a command creates a RunCard"""
        app.state.repo = mock_repo
        
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "/ingest docs force"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check that a run card was created
        run_cards, total = mock_repo.list_run_cards("test-engagement-123")
        assert len(run_cards) == 1
        
        run_card = run_cards[0]
        assert run_card.command == "/ingest docs force"
        assert run_card.inputs["source_type"] == "documents"
        assert run_card.inputs["force_reindex"] is True
        assert run_card.status == "queued"
        assert run_card.created_by == "test@example.com"
    
    def test_send_message_missing_headers(self, client, mock_repo):
        """Test message sending with missing headers"""
        app.state.repo = mock_repo
        
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "Hello"}
        )
        
        assert response.status_code == 422
    
    def test_send_message_invalid_engagement(self, client, mock_repo, auth_headers):
        """Test message sending with invalid engagement"""
        app.state.repo = mock_repo
        
        invalid_headers = auth_headers.copy()
        invalid_headers["X-Engagement-ID"] = "invalid-engagement"
        
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "Hello"},
            headers=invalid_headers
        )
        
        assert response.status_code == 403
    
    def test_send_message_validation_error(self, client, mock_repo, auth_headers):
        """Test message sending with validation errors"""
        app.state.repo = mock_repo
        
        # Empty message
        response = client.post(
            "/api/v1/chat/message",
            json={"message": ""},
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Message too long
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "x" * 2001},
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_get_chat_history(self, client, mock_repo, auth_headers):
        """Test getting chat message history"""
        app.state.repo = mock_repo
        
        # Create some test messages
        for i in range(5):
            msg = ChatMessage(
                engagement_id="test-engagement-123",
                message=f"Test message {i}",
                sender="user"
            )
            mock_repo.create_chat_message(msg)
        
        response = client.get(
            "/api/v1/chat/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["has_next"] is False
        assert len(data["messages"]) == 5
    
    def test_get_chat_history_pagination(self, client, mock_repo, auth_headers):
        """Test chat history pagination"""
        app.state.repo = mock_repo
        
        # Create test messages
        for i in range(10):
            msg = ChatMessage(
                engagement_id="test-engagement-123",
                message=f"Test message {i}",
                sender="user"
            )
            mock_repo.create_chat_message(msg)
        
        response = client.get(
            "/api/v1/chat/messages?page=1&page_size=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["messages"]) == 3
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["has_next"] is True
    
    def test_get_run_cards(self, client, mock_repo, auth_headers):
        """Test getting run cards"""
        app.state.repo = mock_repo
        
        # Create some test run cards
        for i in range(3):
            card = RunCard(
                engagement_id="test-engagement-123",
                command=f"/test command {i}",
                inputs={"param": f"value{i}"},
                status="queued" if i % 2 == 0 else "done",
                created_by="test@example.com"
            )
            mock_repo.create_run_card(card)
        
        response = client.get(
            "/api/v1/chat/run-cards",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "run_cards" in data
        assert data["total"] == 3
        assert len(data["run_cards"]) == 3
    
    def test_get_run_cards_status_filter(self, client, mock_repo, auth_headers):
        """Test filtering run cards by status"""
        app.state.repo = mock_repo
        
        # Create run cards with different statuses
        statuses = ["queued", "running", "done", "error"]
        for i, status in enumerate(statuses):
            card = RunCard(
                engagement_id="test-engagement-123",
                command=f"/test command {i}",
                inputs={},
                status=status,
                created_by="test@example.com"
            )
            mock_repo.create_run_card(card)
        
        # Filter by "done" status
        response = client.get(
            "/api/v1/chat/run-cards?status=done",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["run_cards"]) == 1
        assert data["run_cards"][0]["status"] == "done"
    
    def test_get_run_cards_invalid_status_filter(self, client, mock_repo, auth_headers):
        """Test invalid status filter"""
        app.state.repo = mock_repo
        
        response = client.get(
            "/api/v1/chat/run-cards?status=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_chat_endpoints_require_membership(self, client, mock_repo, auth_headers):
        """Test that chat endpoints require engagement membership"""
        app.state.repo = mock_repo
        
        # Use email not in engagement
        unauthorized_headers = auth_headers.copy()
        unauthorized_headers["X-User-Email"] = "unauthorized@example.com"
        
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "Hello"},
            headers=unauthorized_headers
        )
        assert response.status_code == 403
        
        response = client.get(
            "/api/v1/chat/messages",
            headers=unauthorized_headers
        )
        assert response.status_code == 403
        
        response = client.get(
            "/api/v1/chat/run-cards",
            headers=unauthorized_headers
        )
        assert response.status_code == 403
"""
Pytest configuration and shared fixtures for RAG tests.
"""
import pytest
import os
from unittest.mock import Mock, patch

# Set test environment variables
os.environ["RAG_MODE"] = "none"  # Disable RAG by default in tests
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment configuration"""
    with patch('app.config.config') as mock_config:
        # Mock configuration for tests
        mock_config.rag.mode = "none"
        mock_config.rag.enabled = False
        mock_config.is_rag_enabled.return_value = False
        mock_config.logging.level = "DEBUG"
        mock_config.logging.format = "text"
        yield mock_config


@pytest.fixture
def mock_correlation_id():
    """Standard correlation ID for tests"""
    return "test-correlation-id-12345"


@pytest.fixture
def mock_engagement_context():
    """Mock engagement context"""
    return {
        "engagement_id": "test-engagement-id",
        "user_email": "test@example.com",
        "role": "member"
    }
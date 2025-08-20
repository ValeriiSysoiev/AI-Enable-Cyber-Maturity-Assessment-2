"""
Pytest configuration for E2E UAT tests.
"""
import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator

# Pytest-asyncio configuration
pytest_plugins = ['pytest_asyncio']

def pytest_configure(config):
    """Configure pytest for E2E testing."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "uat: mark test as UAT (User Acceptance Test)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end integration test"
    )
    config.addinivalue_line(
        "markers", "playwright: mark test as requiring Playwright browser automation"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (>30 seconds)"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def uat_environment():
    """Setup UAT environment configuration."""
    return {
        "base_url": os.environ.get("UAT_BASE_URL", "http://localhost:3000"),
        "api_url": os.environ.get("UAT_API_URL", "http://localhost:8000"),
        "timeout": int(os.environ.get("UAT_TIMEOUT", "30")),
        "headless": os.environ.get("HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.environ.get("SLOW_MO", "0"))
    }

@pytest.fixture(autouse=True)
def setup_uat_environment():
    """Automatically setup UAT environment variables for all tests."""
    with pytest.MonkeyPatch.context() as m:
        # Set UAT mode environment variables
        m.setenv("UAT_MODE", "true")
        m.setenv("MCP_ENABLED", "true")
        m.setenv("MCP_CONNECTORS_AUDIO", "true")
        m.setenv("MCP_CONNECTORS_PPTX", "true")
        m.setenv("MCP_CONNECTORS_PII_SCRUB", "true")
        
        # Set test-specific configurations
        m.setenv("ENVIRONMENT", "test")
        m.setenv("LOG_LEVEL", "DEBUG")
        
        yield

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on file location
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        if "uat" in str(item.fspath):
            item.add_marker(pytest.mark.uat)
        
        if "playwright" in str(item.fspath):
            item.add_marker(pytest.mark.playwright)
        
        # Mark slow tests (those with longer timeouts)
        if hasattr(item, 'get_closest_marker'):
            asyncio_marker = item.get_closest_marker('asyncio')
            if asyncio_marker and 'timeout' in str(item.function):
                item.add_marker(pytest.mark.slow)

@pytest.fixture
def mock_mcp_responses():
    """Provide mock MCP responses for testing."""
    return {
        "audio_transcribe": {
            "success": True,
            "transcription": {
                "text": "This is a mock transcription of the workshop discussion.",
                "confidence_score": 0.95,
                "language": "en-US",
                "timestamps": [
                    {"start": 0.0, "end": 2.5, "text": "This is a mock"},
                    {"start": 2.5, "end": 5.0, "text": "transcription of the"},
                    {"start": 5.0, "end": 8.0, "text": "workshop discussion."}
                ]
            },
            "processing_metadata": {
                "duration_seconds": 8.0,
                "audio_format": "wav",
                "processing_time": 2.1
            },
            "pii_scrubbing_applied": {
                "total_redactions": 0,
                "patterns_checked": ["email_address", "phone_us", "us_ssn"]
            }
        },
        "pptx_render": {
            "success": True,
            "presentation": {
                "format": "base64",
                "data": "UEsDBAoAAAAAAGFaSVAAAAA...",  # Truncated base64
                "size_bytes": 2048000,
                "slide_count": 6,
                "template": "executive"
            },
            "generation_metadata": {
                "generation_time": 4.2,
                "template_used": "executive",
                "branding_applied": True
            }
        },
        "pii_scrub": {
            "success": True,
            "scrubbed_content": "Workshop minutes with [REDACTED] information removed.",
            "redaction_report": {
                "total_redactions": 1,
                "patterns_found": ["email_address"],
                "redaction_details": [
                    {"pattern": "email_address", "count": 1, "positions": [[25, 43]]}
                ]
            }
        }
    }
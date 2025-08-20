"""Basic tests for MCP client integration."""

import os
import asyncio
import sys
import traceback

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import McpGatewayClient, MockMcpClient, create_mcp_client


def test_create_mcp_client_disabled():
    """Test that MockMcpClient is created when MCP is disabled."""
    old_enabled = os.environ.get("MCP_ENABLED")
    try:
        os.environ["MCP_ENABLED"] = "false"
        client = create_mcp_client()
        assert isinstance(client, MockMcpClient), f"Expected MockMcpClient, got {type(client)}"
        return True
    finally:
        if old_enabled is not None:
            os.environ["MCP_ENABLED"] = old_enabled
        elif "MCP_ENABLED" in os.environ:
            del os.environ["MCP_ENABLED"]


def test_create_mcp_client_enabled_no_url():
    """Test that MockMcpClient is created when MCP is enabled but no URL is set."""
    old_enabled = os.environ.get("MCP_ENABLED")
    old_url = os.environ.get("MCP_GATEWAY_URL")
    try:
        os.environ["MCP_ENABLED"] = "true"
        if "MCP_GATEWAY_URL" in os.environ:
            del os.environ["MCP_GATEWAY_URL"]
        client = create_mcp_client()
        assert isinstance(client, MockMcpClient), f"Expected MockMcpClient, got {type(client)}"
        return True
    finally:
        if old_enabled is not None:
            os.environ["MCP_ENABLED"] = old_enabled
        elif "MCP_ENABLED" in os.environ:
            del os.environ["MCP_ENABLED"]
        if old_url is not None:
            os.environ["MCP_GATEWAY_URL"] = old_url


def test_create_mcp_client_enabled_with_url():
    """Test that McpGatewayClient is created when MCP is properly configured."""
    old_enabled = os.environ.get("MCP_ENABLED")
    old_url = os.environ.get("MCP_GATEWAY_URL")
    try:
        os.environ["MCP_ENABLED"] = "true"
        os.environ["MCP_GATEWAY_URL"] = "http://localhost:8080"
        client = create_mcp_client()
        assert isinstance(client, McpGatewayClient), f"Expected McpGatewayClient, got {type(client)}"
        assert client.gateway_url == "http://localhost:8080"
        return True
    finally:
        if old_enabled is not None:
            os.environ["MCP_ENABLED"] = old_enabled
        elif "MCP_ENABLED" in os.environ:
            del os.environ["MCP_ENABLED"]
        if old_url is not None:
            os.environ["MCP_GATEWAY_URL"] = old_url
        elif "MCP_GATEWAY_URL" in os.environ:
            del os.environ["MCP_GATEWAY_URL"]


async def test_mock_mcp_client_call():
    """Test MockMcpClient call method."""
    client = MockMcpClient()
    result = await client.call("test_tool", {"test": "payload"}, "test_engagement")
    
    assert "mcp_call_id" in result, "mcp_call_id missing from result"
    assert result["mock"] is True, "mock field should be True"
    assert result["tool"] == "test_tool", f"Expected tool 'test_tool', got {result.get('tool')}"
    assert result["engagement_id"] == "test_engagement", f"Expected engagement_id 'test_engagement', got {result.get('engagement_id')}"
    return True


def test_gateway_client_initialization():
    """Test McpGatewayClient initialization."""
    client = McpGatewayClient("http://localhost:8080")
    assert client.gateway_url == "http://localhost:8080"
    assert client.timeout == 30  # default timeout
    
    client_with_timeout = McpGatewayClient("http://localhost:8080", timeout=60)
    assert client_with_timeout.timeout == 60
    return True


async def run_tests():
    """Run all tests."""
    tests = [
        ("Create client disabled", test_create_mcp_client_disabled),
        ("Create client no URL", test_create_mcp_client_enabled_no_url),
        ("Create client with URL", test_create_mcp_client_enabled_with_url),
        ("Mock client call", test_mock_mcp_client_call),
        ("Gateway client init", test_gateway_client_initialization),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                print(f"✓ {test_name} test passed")
                passed += 1
            else:
                print(f"✗ {test_name} test failed")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} test failed with error: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    if success:
        print("\nAll tests passed! MCP integration is working correctly.")
    else:
        print("\nSome tests failed. Please check the implementation.")
        sys.exit(1)
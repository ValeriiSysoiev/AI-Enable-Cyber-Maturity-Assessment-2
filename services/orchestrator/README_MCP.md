# MCP Client Integration for Orchestrator Service

This document describes the MCP (Model Context Protocol) client implementation for the AI Orchestrator service in Sprint v1.3.

## Overview

The MCP client shim enables the orchestrator to route service calls through an MCP Gateway while maintaining full backward compatibility with existing direct service calls.

## Key Components

### 1. MCP Client Interface (`mcp_client.py`)

- **`IMcpClient`**: Abstract interface defining the `call(tool, payload, engagement_id)` method
- **`McpGatewayClient`**: HTTP client implementation for calling MCP Gateway tools
- **`MockMcpClient`**: Fallback client for testing and when MCP is disabled
- **`create_mcp_client()`**: Factory function that creates the appropriate client based on configuration

### 2. Updated Orchestrator (`main.py`)

- Integrated MCP client with feature flag support
- Added correlation ID logging for request tracing
- Implemented graceful fallback to direct service calls
- Added engagement tracking for MCP operations

### 3. Enhanced Models (`common/models.py`)

- Added `mcp_call_id` field to track MCP operations across all data models
- Maintains backward compatibility with existing field structure

## Configuration

### Environment Variables

- **`MCP_ENABLED`**: Enable/disable MCP integration (default: `false`)
- **`MCP_GATEWAY_URL`**: URL of the MCP Gateway service (required when MCP enabled)
- **`MCP_TIMEOUT`**: Request timeout in seconds (default: `30`)

### Example Configuration

```bash
# Enable MCP integration
export MCP_ENABLED=true
export MCP_GATEWAY_URL=http://localhost:8200
export MCP_TIMEOUT=60
```

## API Behavior

### With MCP Disabled (Default)
- All service calls go directly to existing microservices
- Response format remains unchanged
- No MCP-related fields added to responses

### With MCP Enabled
- Service calls are routed through MCP Gateway
- Graceful fallback to direct calls if MCP fails
- Additional response fields:
  - `mcp_enabled: true`
  - `engagement_id: "eng_xxxxx"`
  - `correlation_id: "corr_xxxxx"`
  - `mcp_call_id` in individual service responses

## MCP Tool Mapping

The orchestrator maps its service calls to the following MCP tools:

| Service | Endpoint | MCP Tool |
|---------|----------|----------|
| Documentation Analyzer | `/analyze` | `analyze_documents` |
| Gap Analysis | `/analyze` | `gap_analysis` |
| Initiative Generation | `/generate` | `initiative_generation` |
| Prioritization | `/prioritize` | `prioritization` |
| Roadmap Planning | `/plan` | `roadmap_planning` |
| Report Generation | `/generate` | `report_generation` |

## Logging and Monitoring

### Correlation ID Tracking
Every request generates a unique correlation ID (`corr_xxxxx`) that is propagated through all MCP calls for end-to-end tracing.

### Structured Logging
All MCP operations are logged with structured data including:
- Correlation ID
- Engagement ID
- MCP call ID
- Tool name
- Duration and success/failure status

### Example Log Entry
```json
{
  "level": "INFO",
  "message": "MCP call completed successfully",
  "corr_id": "corr_abc123def456",
  "mcp_call_id": "mcp_789xyz012",
  "tool": "analyze_documents",
  "engagement_id": "eng_proj1234",
  "duration_ms": 1250,
  "status_code": 200
}
```

## Testing

Run the integration tests to verify MCP functionality:

```bash
cd /path/to/orchestrator
python3 test_mcp_integration.py
```

Tests cover:
- Client factory behavior with different configurations
- Mock client functionality
- Gateway client initialization
- Error handling and fallback scenarios

## Backward Compatibility

The implementation maintains 100% backward compatibility:
- Existing API contracts are preserved
- Response formats remain unchanged when MCP is disabled
- No breaking changes to existing functionality
- Graceful degradation when MCP services are unavailable

## Error Handling

- **MCP Gateway Unavailable**: Falls back to direct service calls
- **Network Timeouts**: Configurable timeout with fallback
- **Invalid Responses**: Logs errors and continues with fallback
- **Configuration Errors**: Automatically uses mock client

## Performance Considerations

- Minimal overhead when MCP is disabled
- Configurable timeouts prevent hanging requests
- Structured logging provides performance metrics
- Correlation IDs enable request tracing across services
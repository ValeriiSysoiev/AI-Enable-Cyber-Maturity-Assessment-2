# MCP Gateway Service

Model Context Protocol (MCP) gateway service for AI-Enabled Cyber Maturity Assessment platform.

## Overview

The MCP Gateway provides a lightweight foundation for integrating Model Context Protocol functionality into the cyber maturity assessment platform. This service acts as a bridge between AI tools and the assessment system, enabling structured context management and tool integration.

## Features

- **Health Monitoring**: Standard health check endpoints
- **Context Management**: Basic MCP context operations  
- **Structured Logging**: Correlation ID tracking for all operations
- **OpenAPI Documentation**: Auto-generated API docs at `/docs`
- **Docker Integration**: Ready for containerized deployment

## Configuration

Environment variables:

- `MCP_ENABLED`: Enable/disable MCP functionality (default: `true`)
- `MCP_DATA_ROOT`: Data directory path (default: `/app/data`)
- `MCP_MAX_FILE_SIZE_MB`: Maximum file size for operations (default: `10`)
- `MCP_MAX_SEARCH_RESULTS`: Maximum search results returned (default: `20`)
- `MCP_GATEWAY_PORT`: Service port (default: `8200`)

## Usage

Start with Docker Compose (profile required):
```bash
docker-compose --profile mcp up mcp-gateway
```

## API Endpoints

- `GET /health` - Health check
- `GET /` - Service information
- `POST /mcp/context` - MCP context operations
- `GET /mcp/status` - MCP service status
- `GET /docs` - OpenAPI documentation

## Development

The service follows established patterns:
- Type safety with Pydantic models
- Structured logging with correlation IDs
- Standard error handling
- Docker health checks
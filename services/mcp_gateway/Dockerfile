FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements and install dependencies
COPY services/mcp_gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY services/mcp_gateway/ /app/

# Create data directory for MCP operations
RUN mkdir -p /app/data

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8200
ENV MCP_ENABLED=true
ENV MCP_DATA_ROOT=/app/data
ENV MCP_MAX_FILE_SIZE_MB=10
ENV MCP_MAX_SEARCH_RESULTS=20
ENV MCP_GATEWAY_PORT=8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8200/health')"

EXPOSE 8200

CMD ["sh", "-c", "uvicorn main:app --host ${HOST} --port ${PORT}"]
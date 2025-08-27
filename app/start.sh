#!/bin/bash
# Startup script for Azure App Service
set -e

# Set default port if not provided
if [ -z "$PORT" ]; then
    export PORT=8000
fi

echo "Starting uvicorn on port $PORT..."
exec uvicorn api.main:app --host 0.0.0.0 --port $PORT


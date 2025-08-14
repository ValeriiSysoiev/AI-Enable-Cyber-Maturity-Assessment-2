#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "Starting API server..."
cd app

# Set environment variables
export ADMIN_EMAILS="${ADMIN_EMAILS:-you@company.com}"
export AZURE_STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT:-}"
export AZURE_STORAGE_CONTAINER="${AZURE_STORAGE_CONTAINER:-docs}"
export USE_MANAGED_IDENTITY="${USE_MANAGED_IDENTITY:-false}"
export WEB_ORIGIN="${WEB_ORIGIN:-http://localhost:3000}"

# Create data directory for FileRepository
mkdir -p ../data/engagements

# Run API server
exec python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "Starting web server..."
cd web

# Set environment variables
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000}"
export NEXT_PUBLIC_ADMIN_EMAILS="${NEXT_PUBLIC_ADMIN_EMAILS:-you@company.com}"

# Run web server
exec npm run dev

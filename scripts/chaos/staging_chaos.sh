#!/bin/bash
# Staging Chaos Engineering Probe
# Controlled failure injection for resilience testing

set -euo pipefail

CHAOS_ENABLED="${CHAOS_ENABLED:-0}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
FAILURE_DURATION="${FAILURE_DURATION:-30}"

if [[ "$CHAOS_ENABLED" != "1" ]]; then
    echo "❌ Chaos testing disabled. Set CHAOS_ENABLED=1 to enable."
    exit 0
fi

if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "🚫 Chaos testing blocked in production environment"
    exit 1
fi

echo "🔥 Starting staging chaos probe..."
echo "📅 Duration: ${FAILURE_DURATION}s"

# Simulate API container failure
docker-compose kill api || echo "API container stopped"
sleep "$FAILURE_DURATION"
docker-compose up -d api || echo "API container restarted"

echo "✅ Chaos probe completed. Check alerts and recovery."
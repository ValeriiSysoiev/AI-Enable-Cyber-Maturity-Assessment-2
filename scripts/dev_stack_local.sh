#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

export ADMIN_EMAILS="${ADMIN_EMAILS:-you@company.com}"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "tmux is not installed. Running services in background..."
    
    # API
    echo "Starting API server..."
    scripts/dev_api_local.sh &
    API_PID=$!
    sleep 2
    
    # Verify API server started successfully
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "ERROR: API server failed to start (PID: $API_PID)"
        exit 1
    fi
    echo "API server started successfully (PID: $API_PID)"
    
    # WEB
    echo "Starting web server..."
    scripts/dev_web_local.sh &
    WEB_PID=$!
    sleep 1
    
    # Verify web server started successfully
    if ! kill -0 "$WEB_PID" 2>/dev/null; then
        echo "ERROR: Web server failed to start (PID: $WEB_PID)"
        # Clean up API server
        kill "$API_PID" 2>/dev/null
        exit 1
    fi
    echo "Web server started successfully (PID: $WEB_PID)"
    
    echo "Services started:"
    echo "  API: http://localhost:8000 (PID: $API_PID)"
    echo "  Web: http://localhost:3000 (PID: $WEB_PID)"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait and cleanup on exit
    trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
    wait
else
    # Kill any existing session
    tmux kill-session -t aimaturity 2>/dev/null || true
    
    # API
    tmux new-session -d -s aimaturity 'scripts/dev_api_local.sh'
    sleep 2
    
    # WEB
    tmux split-window -t aimaturity -h 'scripts/dev_web_local.sh'
    
    echo "Services starting in tmux..."
    echo "  API: http://localhost:8000"
    echo "  Web: http://localhost:3000"
    echo ""
    echo "Use 'tmux attach -t aimaturity' to view logs"
    
    tmux attach -t aimaturity
fi

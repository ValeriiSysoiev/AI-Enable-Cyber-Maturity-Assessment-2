SHELL := /bin/bash
.PHONY: venv deps dev demo demo-mcp deploy-admin urls smoke

venv:
	python3 -m venv .venv

deps:
	. .venv/bin/activate && python -m pip install --upgrade pip && \
	find services -name requirements.txt -print0 | xargs -0 -n1 python -m pip install -r && \
	python -m pip install honcho

dev:
	[ -f .env ] || cp .env.example .env; \
	. .venv/bin/activate && honcho start

# Standard demo mode - preserves existing behavior
demo:
	@echo "Starting demo mode (standard orchestrator services)..."
	@if ! docker compose ps | grep -q "Up"; then \
		if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Warning: Port 3000 is in use, web will fallback to 3001"; \
		fi; \
		if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Error: Port 8000 (API) is already in use"; \
			exit 1; \
		fi; \
		docker compose up --build -d; \
	else \
		echo "Services already running"; \
	fi
	@echo "Demo services started. API: http://localhost:8000"

# MCP-enabled demo mode
demo-mcp:
	@echo "Starting demo mode with MCP Gateway enabled..."
	@if ! docker compose ps | grep -q "Up"; then \
		if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Warning: Port 3000 is in use, web will fallback to 3001"; \
		fi; \
		if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Error: Port 8000 (API) is already in use"; \
			exit 1; \
		fi; \
		if lsof -Pi :8020 -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Error: Port 8020 (MCP Gateway) is already in use"; \
			exit 1; \
		fi; \
		MCP_ENABLED=true docker compose --profile mcp up --build -d; \
	else \
		echo "Services already running"; \
	fi
	@echo "MCP Demo services started. API: http://localhost:8000, MCP Gateway: http://localhost:8020"
	@echo "Waiting for MCP Gateway health check..."
	@timeout 60s bash -c 'until curl -s http://localhost:8020/health >/dev/null 2>&1; do sleep 2; done' || echo "Warning: MCP Gateway health check timeout"

deploy-admin:
	bash ./scripts/deploy_admin.sh

urls:
	bash scripts/print_urls.sh

smoke:
	bash scripts/smoke.sh

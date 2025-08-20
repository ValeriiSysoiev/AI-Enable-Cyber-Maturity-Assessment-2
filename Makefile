SHELL := /bin/bash
.PHONY: venv deps dev deploy-admin urls smoke demo demo-mcp demo-setup demo-mcp-setup demo-health demo-seed

venv:
	python3 -m venv .venv

deps:
	. .venv/bin/activate && python -m pip install --upgrade pip && \
	find services -name requirements.txt -print0 | xargs -0 -n1 python -m pip install -r && \
	python -m pip install honcho

dev:
	[ -f .env ] || cp .env.example .env; \
	. .venv/bin/activate && honcho start

deploy-admin:
	bash ./scripts/deploy_admin.sh

urls:
	bash scripts/print_urls.sh

smoke:
	bash scripts/smoke.sh

# Demo targets for local development
demo: demo-setup demo-health demo-seed
	@echo ""
	@echo "🚀 Demo environment is ready!"
	@echo "Open http://localhost:3000 to start exploring the AI-Enabled Cyber Maturity Assessment tool"

# MCP-enabled demo targets
demo-mcp: demo-mcp-setup demo-health demo-seed
	@echo ""
	@echo "🚀 Demo environment with MCP Gateway is ready!"
	@echo "Open http://localhost:3000 to start exploring the AI-Enabled Cyber Maturity Assessment tool"
	@echo "MCP Gateway is available at http://localhost:8200"
	@echo "MCP Tools API documentation: http://localhost:8200/docs"

demo-setup:
	@echo "Starting demo environment..."
	@echo "Checking for port conflicts..."
	@if netstat -an | grep LISTEN | grep -q ":3000 "; then \
		echo "⚠️  Port 3000 is already in use. Please stop the conflicting service."; \
		netstat -an | grep ":3000 "; \
		exit 1; \
	fi
	@if netstat -an | grep LISTEN | grep -q ":8000 "; then \
		echo "⚠️  Port 8000 is already in use. Please stop the conflicting service."; \
		netstat -an | grep ":8000 "; \
		exit 1; \
	fi
	@echo "✅ Port check passed"
	docker compose up -d --build

demo-mcp-setup:
	@echo "Starting demo environment with MCP Gateway..."
	@export MCP=1 && docker compose --profile mcp up -d --build

demo-health:
	@echo "Running health checks..."
	bash scripts/health_check_local.sh

demo-seed:
	@echo "Seeding demo data..."
	bash scripts/seed_demo_data.sh
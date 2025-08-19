SHELL := /bin/bash
.PHONY: venv deps dev deploy-admin urls smoke

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

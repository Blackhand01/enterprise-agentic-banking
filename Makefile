.PHONY: help setup run dev docs stop restart smoke reset-audit reset-data compile clean check-port

PORT ?= 8000
HOST ?= 127.0.0.1
APP ?= src.backend.api_server:app
UVICORN ?= uvicorn
PYTHON ?= $(shell if python3 -m pip show fastapi >/dev/null 2>&1; then command -v python3; elif command -v $(UVICORN) >/dev/null 2>&1; then uvicorn_path=`command -v $(UVICORN)`; sed -n '1s/^\#!//p' "$$uvicorn_path"; else echo python3; fi)

help:
	@echo "Enterprise Agentic Banking Prototype"
	@echo ""
	@echo "Commands:"
	@echo "  make setup        Install Python dependencies"
	@echo "  make run          Start the Part A prototype at http://$(HOST):$(PORT)"
	@echo "  make dev          Start with uvicorn reload enabled"
	@echo "  make docs         Regenerate Part B and Part C HTML versions"
	@echo "  make stop         Stop the process listening on $(HOST):$(PORT)"
	@echo "  make restart      Stop and restart the prototype"
	@echo "  make smoke        Run quick backend/API checks"
	@echo "  make reset-audit  Reset src/bank_data/audit_log.json to []"
	@echo "  make reset-data   Reset the SQLite database from JSON seed"
	@echo "  make compile      Compile Python modules"
	@echo "  make clean        Remove Python cache files"

check-port:
	@if lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P >/dev/null 2>&1; then \
		echo "Port $(PORT) is already in use."; \
		echo "Open http://$(HOST):$(PORT) if the app is already running, or run: make stop"; \
		lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P; \
		exit 1; \
	fi

setup:
	$(PYTHON) -m pip install -r requirements.txt

run: check-port
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT)

dev: check-port
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT) --reload

docs:
	pandoc docs/part_B-architecture_system_design.md \
		--standalone \
		--metadata pagetitle="Part B - Architecture and System Design" \
		--lua-filter scripts/mermaid-filter.lua \
		-H scripts/html-head.html \
		-o docs/part_B-architecture_system_design.html
	pandoc docs/part_C-process_decision.md \
		--standalone \
		--metadata pagetitle="Part C - Process and Decisions" \
		--lua-filter scripts/mermaid-filter.lua \
		-H scripts/html-head.html \
		-o docs/part_C-process_decision.html

stop:
	@pids=$$(lsof -tiTCP:$(PORT) -sTCP:LISTEN 2>/dev/null | sort -u); \
	if [ -z "$$pids" ]; then \
		echo "No process is listening on port $(PORT)."; \
		exit 0; \
	fi; \
	echo "Stopping process on port $(PORT)..."; \
	kill $$pids 2>/dev/null || true; \
	pkill -TERM -f "uvicorn .*$(APP).*--port $(PORT)" 2>/dev/null || true; \
	for attempt in 1 2 3 4 5; do \
		sleep 1; \
		if ! lsof -tiTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
			echo "Port $(PORT) released."; \
			exit 0; \
		fi; \
	done; \
	remaining=$$(lsof -tiTCP:$(PORT) -sTCP:LISTEN 2>/dev/null | sort -u); \
	if [ -n "$$remaining" ]; then \
		echo "Force-stopping remaining processes on port $(PORT)..."; \
		kill -9 $$remaining 2>/dev/null || true; \
		pkill -KILL -f "uvicorn .*$(APP).*--port $(PORT)" 2>/dev/null || true; \
		sleep 1; \
	fi; \
	if lsof -tiTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Port $(PORT) is still busy after stop."; \
		lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P; \
		exit 1; \
	else \
		echo "Port $(PORT) released."; \
	fi

restart: stop
	$(MAKE) run

smoke:
	find src/backend -name "*.py" -print0 | xargs -0 $(PYTHON) -m py_compile
	node --check src/frontend/app.js
	node scripts/ui-state-smoke.js
	$(PYTHON) scripts/smoke.py

reset-audit:
	@printf '[]\n' > src/bank_data/audit_log.json
	@echo "audit log reset"

reset-data:
	$(PYTHON) -c "from src.backend.api_server import service; service.reset_data(); service.reset_audit(); print('SQLite database reset')"

compile:
	find src/backend -name "*.py" -print0 | xargs -0 $(PYTHON) -m py_compile

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

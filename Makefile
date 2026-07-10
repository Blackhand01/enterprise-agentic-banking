.PHONY: help setup run dev docs stop restart smoke reset-audit reset-data compile clean check-port check-deps doctor package

PORT ?= 8000
HOST ?= 127.0.0.1
APP ?= src.backend.api_server:app
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
RUN_PYTHON := $(shell if [ -x "$(VENV_PYTHON)" ]; then echo "$(VENV_PYTHON)"; else command -v $(PYTHON) 2>/dev/null || echo $(PYTHON); fi)
DIST_DIR ?= dist
DIST_NAME ?= enterprise-agentic-banking

help:
	@echo "Enterprise Agentic Banking Prototype"
	@echo ""
	@echo "Commands:"
	@echo "  make setup        Create .venv and install Python dependencies"
	@echo "  make run          Start the Part A prototype at http://$(HOST):$(PORT)"
	@echo "  make dev          Start with uvicorn reload enabled"
	@echo "  make doctor       Show the Python environment used by Make"
	@echo "  make package      Build a clean zip under $(DIST_DIR)/"
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
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

check-deps:
	@$(RUN_PYTHON) -c "import fastapi, uvicorn" >/dev/null 2>&1 || { \
		echo "Python dependencies are missing for $(RUN_PYTHON)."; \
		echo "Run: make setup"; \
		exit 1; \
	}

doctor:
	@echo "Base Python: $$(command -v $(PYTHON) 2>/dev/null || echo 'not found')"
	@echo "Run Python:  $(RUN_PYTHON)"
	@$(RUN_PYTHON) --version
	@$(RUN_PYTHON) -m pip show fastapi uvicorn >/dev/null 2>&1 && \
		echo "Dependencies: installed" || \
		echo "Dependencies: missing; run 'make setup'"

run: check-port check-deps
	$(RUN_PYTHON) -m uvicorn $(APP) --host $(HOST) --port $(PORT)

dev: check-port check-deps
	$(RUN_PYTHON) -m uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

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

smoke: check-deps
	find src/backend -name "*.py" -print0 | xargs -0 $(RUN_PYTHON) -m py_compile
	node --check src/frontend/app.js
	node scripts/ui-state-smoke.js
	$(RUN_PYTHON) scripts/smoke.py

reset-audit:
	@printf '[]\n' > src/bank_data/audit_log.json
	@echo "audit log reset"

reset-data:
	$(RUN_PYTHON) -c "from src.backend.api_server import service; service.reset_data(); service.reset_audit(); print('SQLite database reset')"

compile:
	find src/backend -name "*.py" -print0 | xargs -0 $(RUN_PYTHON) -m py_compile

package:
	rm -rf $(DIST_DIR)/$(DIST_NAME) $(DIST_DIR)/$(DIST_NAME).zip
	mkdir -p $(DIST_DIR)
	rsync -a ./ $(DIST_DIR)/$(DIST_NAME)/ \
		--exclude .git \
		--exclude .venv \
		--exclude .env \
		--exclude __pycache__ \
		--exclude '*.pyc' \
		--exclude '.DS_Store' \
		--exclude '$(DIST_DIR)' \
		--exclude 'src/bank_data/*.db' \
		--exclude 'src/bank_data/*.db-*'
	cd $(DIST_DIR) && zip -qr $(DIST_NAME).zip $(DIST_NAME)
	@echo "Created $(DIST_DIR)/$(DIST_NAME).zip"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

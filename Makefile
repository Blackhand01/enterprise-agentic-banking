.PHONY: help setup run dev docs stop restart smoke reset-audit reset-data compile clean check-port

PORT ?= 8000
HOST ?= 127.0.0.1
APP ?= src.backend.main:app

help:
	@echo "Prototipo Enterprise Agentic Banking"
	@echo ""
	@echo "Comandi:"
	@echo "  make setup        Installa le dipendenze Python"
	@echo "  make run          Avvia il prototipo Parte A su http://$(HOST):$(PORT)"
	@echo "  make dev          Avvia con reload uvicorn abilitato"
	@echo "  make docs         Rigenera le versioni HTML di Parte B e Parte C"
	@echo "  make stop         Ferma il processo in ascolto su $(HOST):$(PORT)"
	@echo "  make restart      Ferma e riavvia il prototipo"
	@echo "  make smoke        Esegue controlli rapidi backend/API"
	@echo "  make reset-audit  Reimposta src/bank_data/audit_log.json a []"
	@echo "  make reset-data   Reimposta il database SQLite dal seed JSON"
	@echo "  make compile      Compila i moduli Python"
	@echo "  make clean        Rimuove i file cache Python"

check-port:
	@if lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P >/dev/null 2>&1; then \
		echo "La porta $(PORT) e gia in uso."; \
		echo "Apri http://$(HOST):$(PORT) se l'app e gia in esecuzione, oppure esegui: make stop"; \
		lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P; \
		exit 1; \
	fi

setup:
	python3 -m pip install -r requirements.txt

run: check-port
	uvicorn $(APP) --host $(HOST) --port $(PORT)

dev: check-port
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

docs:
	pandoc docs/part_B-architecture_system_design.md \
		--standalone \
		--metadata pagetitle="Parte B - Architettura e System Design" \
		--lua-filter scripts/mermaid-filter.lua \
		-H scripts/html-head.html \
		-o docs/part_B-architecture_system_design.html
	pandoc docs/part_C-process_decision.md \
		--standalone \
		--metadata pagetitle="Parte C - Processo e decisioni" \
		--lua-filter scripts/mermaid-filter.lua \
		-H scripts/html-head.html \
		-o docs/part_C-process_decision.html

stop:
	@pids=$$(lsof -tiTCP:$(PORT) -sTCP:LISTEN 2>/dev/null | sort -u); \
	if [ -z "$$pids" ]; then \
		echo "Nessun processo in ascolto sulla porta $(PORT)."; \
		exit 0; \
	fi; \
	echo "Arresto processo sulla porta $(PORT)..."; \
	kill $$pids 2>/dev/null || true; \
	pkill -TERM -f "uvicorn .*$(APP).*--port $(PORT)" 2>/dev/null || true; \
	for attempt in 1 2 3 4 5; do \
		sleep 1; \
		if ! lsof -tiTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
			echo "Porta $(PORT) liberata."; \
			exit 0; \
		fi; \
	done; \
	remaining=$$(lsof -tiTCP:$(PORT) -sTCP:LISTEN 2>/dev/null | sort -u); \
	if [ -n "$$remaining" ]; then \
		echo "Forzo arresto dei processi rimasti sulla porta $(PORT)..."; \
		kill -9 $$remaining 2>/dev/null || true; \
		pkill -KILL -f "uvicorn .*$(APP).*--port $(PORT)" 2>/dev/null || true; \
		sleep 1; \
	fi; \
	if lsof -tiTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "La porta $(PORT) e ancora occupata dopo lo stop."; \
		lsof -iTCP:$(PORT) -sTCP:LISTEN -n -P; \
		exit 1; \
	else \
		echo "Porta $(PORT) liberata."; \
	fi

restart: stop
	$(MAKE) run

smoke:
	find src/backend -name "*.py" -print0 | xargs -0 python3 -m py_compile
	node --check src/frontend/app.js
	node scripts/ui-state-smoke.js
	python3 scripts/smoke.py

reset-audit:
	@printf '[]\n' > src/bank_data/audit_log.json
	@echo "audit log reimpostato"

reset-data:
	python3 -c "from src.backend.main import service; service.reset_data(); service.reset_audit(); print('database SQLite reimpostato')"

compile:
	find src/backend -name "*.py" -print0 | xargs -0 python3 -m py_compile

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

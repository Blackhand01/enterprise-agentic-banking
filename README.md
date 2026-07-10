# TCS Agentic Bank

An agentic banking prototype where the assistant can reason over verified customer data, explain a savings recommendation, and request approval before any money movement is committed.

![TCS Agentic Bank GUI](docs/assets/app-gui.png)

## Experience

The demo focuses on one concrete banking journey: after salary arrives, the app evaluates checking liquidity, upcoming expenses, and the `Emergency_Fund` goal. It then proposes a transfer, shows the projected impact, routes the action through deterministic guardrails, and records the trace.

The interface is designed to make the AI decision inspectable:

- `Customer Goal` shows the savings target, current pace, remaining gap, and monthly contribution needed.
- `Agent Inbox` presents the recommended action and its approval route.
- `Supervisor Dashboard` displays liquidity, known 30-day outflows, and before/after safety margins.
- `Insights`, `Explainability`, and `Proposal impact` expose the evidence behind the recommendation.
- `Chat` answers grounded questions with tool calling when an LLM provider is configured.
- `Sandbox Settings` lets reviewers change balances, expenses, and risk thresholds without touching real systems.

## Architecture

The prototype keeps reasoning, authorization, execution, and audit separate.

- FastAPI serves the API and the static frontend.
- SQLite is the local system of record, seeded from JSON data.
- Deterministic read models calculate balances, cash-flow outlook, goal progress, and proposal impact.
- Pydantic tool schemas validate agent tool arguments.
- Guardrails decide whether a transfer is allowed, approval-gated, step-up-gated, or blocked.
- JSON audit logs preserve local demo traces for review.

The dashboard, proposal flow, guardrails, and transfer execution work without external services. The chat experience needs one configured LLM key in `.env` or the shell environment:

```bash
GROQ_API_KEY=""
OPENAI_API_KEY=""
GEMINI_API_KEY=""
```

Only one key is required; if more than one is present, the backend auto-selects and falls back across configured providers.

## Quick Start

Use the `Makefile` as the operational entry point. It creates an isolated `.venv`
inside the project and always starts the app with that same environment, so local
Python tools installed elsewhere on the machine do not affect the demo.

### First Run From The Zip

```bash
cd enterprise-agentic-banking
make setup
make run
```

Then open:

```text
http://127.0.0.1:8000
```

Prerequisites:

- Python 3.11 or newer available as `python3`
- `make` available in the terminal
- A modern browser

If `python3` points to a different interpreter than the one you want, pass it
explicitly:

```bash
make setup PYTHON=/path/to/python3
make run
```

### Without Make

These commands are equivalent and are useful on machines without `make`:

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn src.backend.api_server:app --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn src.backend.api_server:app --host 127.0.0.1 --port 8000
```

### Later Runs

After `make setup` has completed once:

```bash
make run
```

If port `8000` is busy:

```bash
PORT=8001 make run
```

Then open `http://127.0.0.1:8001`.

### Optional LLM Chat

The dashboard, recommendation, approval, execution, reset, and audit flows run with
local data only. The contextual chat becomes available when at least one LLM API key
is present in `.env` or in the shell environment. To configure it:

```bash
cp .env.example .env
```

Then set one provider key in `.env`. If no key is configured, only the chat reports
that the assistant is unavailable; the rest of the prototype still works.

Useful commands:

```bash
make help
make doctor
make smoke
make reset-data
make package
make stop
```

`make doctor` prints which Python interpreter the Makefile will use. `make smoke`
runs the backend/API and frontend syntax checks used for a quick local verification.

The generated SQLite database and audit log are local demo state. Use
`make reset-data` to restore the seeded scenario.

### Preparing The Submission Zip

To create a clean folder archive for review:

```bash
make package
```

The zip is written to `dist/enterprise-agentic-banking.zip`. It excludes `.git`,
`.venv`, `.env`, Python caches, and generated SQLite files, while keeping the
prototype source, seed JSON, README, assessment docs, and prebuilt HTML files.

## Try This

- Approve the proposed transfer toward `Emergency_Fund`.
- Change the proposal amount and preview the updated route.
- Set the amount to EUR 750 to trigger the step-up path.
- Open `Insights` to inspect historical balances and spending used for grounding.
- Open `Explainability` and `Proposal impact` from the inbox.
- Ask the chat: `How much have I spent on sports recently?`
- Ask the chat: `Can you tell me the risk of my mortgage?`

## Documentation

Submission material lives in `docs/`:

- `part_B-architecture_system_design.md`
- `part_B-architecture_system_design.html`
- `part_C-process_decision.md`
- `part_C-process_decision.html`

## Code Map

- `src/backend/api_server.py`: FastAPI routes and frontend mount.
- `src/backend/banking_demo_application.py`: application wiring and use cases.
- `src/backend/storage/`: SQLite schema, seed, reads, writes, reset, and idempotency.
- `src/backend/intelligence/`: deterministic planning, cash-flow math, read models, and proposal explainability.
- `src/backend/application/`: dashboard state, chat service, approval workflow, audit, and environment helpers.
- `src/backend/agentic_system/`: LLM orchestration, tools, schemas, retrieval, provider selection, and guardrails.
- `src/frontend/`: static HTML, CSS, and JavaScript UI.

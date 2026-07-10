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

The dashboard, proposal flow, guardrails, and transfer execution work without external services. The chat experience requires an OpenAI-compatible LLM provider in `.env` or the shell environment.

## Quick Start

Use the `Makefile` as the operational entry point:

```bash
make help
```

It contains setup, run, dev, smoke-test, reset, docs, stop, restart, compile, and clean commands.

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

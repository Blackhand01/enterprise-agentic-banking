# Backend Module Map

This folder is organized by functional responsibility. The guiding principle is to separate verified data, deterministic intelligence, LLM orchestration, application workflows, and the API boundary.

## Module Map

| Path | Responsibility | Contents |
| --- | --- | --- |
| `api_server.py` | API boundary | FastAPI routes, request schemas, static frontend mount. |
| `banking_demo_application.py` | Application facade | Dependency wiring and use cases exposed to the API. |
| `storage/` | Local system of record | SQLite, schema, seed/reset, read-only queries, write commands, idempotency. |
| `intelligence/` | Deterministic bank intelligence | Emergency-fund planner, cashflow formulas, read models, explainability, proposal payloads. |
| `application/` | Application workflows | Dashboard state, chat service, approval workflow, JSON audit, env/trace helpers. |
| `agentic_system/` | LLM orchestration | Provider-agnostic agent, prompt/policy support, tool schemas, semantic retrieval, guardrails. |

## Recommended Reading

1. `api_server.py`: REST APIs exposed to the frontend.
2. `banking_demo_application.py`: service composition.
3. `storage/sqlite_banking_store.py`: local database facade.
4. `storage/customer_banking_read_store.py`: balances, transactions, scheduled payments, and snapshots.
5. `storage/customer_banking_write_store.py`: mutation commands.
6. `storage/transfer_commands.py`: internal transfers with idempotency.
7. `storage/commands.py`: shared helpers and sandbox state injection.
8. `intelligence/emergency_fund_recommendation_planner.py`: plan selection and agentic proposal.
9. `intelligence/emergency_fund_planning_math.py`: cashflow, buffer, and anti-oscillation math.
10. `intelligence/emergency_fund_proposal_payload.py`: proposal payload, evidence, and reasoning trace.
11. `intelligence/read_models.py`: dashboard read-model facade.
12. `application/services.py`: audit trail and approval workflow.
13. `application/customer_services.py`: dashboard state builder and customer chat service.
14. `agentic_system/agent.py`: LLM loop and tool calling.
15. `agentic_system/tools.py`: validated local tools that read/write the store.
16. `agentic_system/guardrails.py`: risk routing and output sanitization.

## Architectural Boundaries

- The language model is not the system of record.
- Balances, transactions, and operational state come from SQLite through `storage/`.
- Financial proposals are calculated in `intelligence/`; they are not invented by the model.
- Transfers pass through tool schema validataon, guardrails, approval, and idempotency.
- Demo audit is stored as local JSON through `JsonAuditTrail` in `application/services.py`.
- The sandbox only mutates local demo state; it does not simulate real authentication or real core banking.

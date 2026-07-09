# Backend Module Map

Questa cartella e organizzata per responsabilita funzionale, non per tipo tecnico generico.

| Path | Responsabilita | Cosa contiene |
| --- | --- | --- |
| `main.py` | API boundary | FastAPI routes, request schema e static frontend mount. |
| `part_a_banking_demo_application.py` | Application facade | Wiring delle dipendenze e use case esposti alle API. |
| `storage/` | System of record locale | Repository SQLite, schema, seed/reset, transazioni reali, idempotenza. |
| `intelligence/` | Bank intelligence deterministica | Planner delle proposte, formule obiettivo, read model, cashflow forecast. |
| `application/` | Workflow mutativi | Trasferimenti approvati dal cliente, scenari evento, audit trace. |
| `agentic_system/` | LLM orchestration | Groq agent, prompt, tool schema, retrieval policy e guardrail LLM/tool. |
| `observability/` | Auditability | Audit log append-only JSON per demo e pannello AI Engineering. |

## Lettura Consigliata

1. `main.py` per vedere le API esposte.
2. `part_a_banking_demo_application.py` per capire come sono collegati i componenti.
3. `intelligence/emergency_fund_recommendation_planner.py` per la raccomandazione.
4. `intelligence/emergency_fund_goal_projection_read_model.py` per l'obiettivo.
5. `intelligence/cashflow_forecast_read_model.py` per il cashflow.
6. `storage/sqlite_banking_store.py` per il facade dello storage.
7. `storage/internal_transfer_command.py` per il trasferimento reale.
8. `storage/external_expense_command.py` per gli eventi spesa.
9. `application/customer_transfer_approval_workflow.py` per approvazione/esecuzione.
10. `application/scenario_event_simulator.py` per scenari e replanning.
7. `agentic_system/agent.py` per il loop LLM + tool calling.

## Regola Architetturale

Il modello linguistico non e il system of record e non decide la safety. Saldi, esecuzione, idempotenza, route di rischio e formule finanziarie sono implementati in codice deterministico e ispezionabile.

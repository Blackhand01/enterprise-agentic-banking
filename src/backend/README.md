# Backend Module Map

Questa cartella è organizzata per responsabilità funzionale. Il principio guida è separare dati verificati, intelligenza deterministica, orchestrazione LLM, workflow applicativi e boundary API.

## Mappa Moduli

| Path | Responsabilità | Cosa contiene |
| --- | --- | --- |
| `api_server.py` | API boundary | FastAPI routes, request schema, mount del frontend statico. |
| `banking_demo_application.py` | Application facade | Wiring delle dipendenze e use case esposti alle API. |
| `storage/` | System of record locale | SQLite, schema, seed/reset, query read-only, comandi write, idempotenza. |
| `intelligence/` | Bank intelligence deterministica | Planner fondo emergenze, formule cashflow, read model, explainability e proposal payload. |
| `application/` | Workflow applicativi | Dashboard state, chat service, approval workflow, audit JSON, env/trace helpers. |
| `agentic_system/` | LLM orchestration | Agent provider-agnostic, prompt/policy support, tool schema, retrieval semantico, guardrail. |

## Lettura Consigliata

1. `api_server.py`: API REST esposte al frontend.
2. `banking_demo_application.py`: composizione dei servizi.
3. `storage/sqlite_banking_store.py`: facciata del database locale.
4. `storage/customer_banking_read_store.py`: query su saldi, transazioni, scheduled payments e snapshot.
5. `storage/customer_banking_write_store.py`: comandi mutativi.
6. `storage/transfer_commands.py`: trasferimenti interni con idempotenza.
7. `storage/commands.py`: helper condivisi e sandbox state injection.
8. `intelligence/emergency_fund_recommendation_planner.py`: selezione del piano e proposta agentica.
9. `intelligence/emergency_fund_planning_math.py`: calcoli cashflow, buffer e anti-oscillazione.
10. `intelligence/emergency_fund_proposal_payload.py`: payload proposta, evidence e reasoning trace.
11. `intelligence/read_models.py`: facade dei read model dashboard.
12. `application/services.py`: audit trail e approval workflow.
13. `application/customer_services.py`: dashboard state builder e customer chat service.
14. `agentic_system/agent.py`: loop LLM + tool calling.
15. `agentic_system/tools.py`: tool locali validati che leggono/scrivono sullo store.
16. `agentic_system/guardrails.py`: route di rischio e sanitizzazione output.

## Confini Architetturali

- Il modello linguistico non è il system of record.
- Saldi, transazioni e stato operativo arrivano da SQLite tramite `storage/`.
- Le proposte finanziarie sono calcolate in `intelligence/`, non inventate dal modello.
- I trasferimenti passano da tool schema, guardrail, approvazione e idempotenza.
- L'audit della demo è JSON locale tramite `JsonAuditTrail` in `application/services.py`.
- La sandbox modifica solo lo stato demo locale, non simula autenticazione reale o core banking reale.

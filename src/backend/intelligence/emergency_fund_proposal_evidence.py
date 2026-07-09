"""Evidence rows shown in the AI Engineering inspector for a proposal."""

from __future__ import annotations

from typing import Any


def build_emergency_fund_proposal_evidence(
    *,
    checking: dict[str, Any],
    emergency: dict[str, Any],
    upcoming: float,
    amount: float,
    route: dict[str, Any],
    action_type: str,
) -> list[dict[str, Any]]:
    already_executed = route["route"] == "ALREADY_EXECUTED"
    new_money_movement = 0.0 if already_executed or action_type != "TRANSFER" else amount
    projected_balance = round(checking["available_balance"] - new_money_movement, 2)
    projected_emergency = round(emergency["balance"] + new_money_movement, 2)

    return [
        _evidence_row(
            group="Contesto bancario fornito all'agente",
            label="Saldo disponibile conto corrente",
            value=checking["available_balance"],
            source="Read model conti cliente",
            purpose="Usato dall'agente per valutare se esiste liquidita disponibile.",
        ),
        _evidence_row(
            group="Contesto bancario fornito all'agente",
            label="Spese pianificate prossimi 30 giorni",
            value=round(upcoming, 2),
            source="Pagamenti pianificati",
            purpose="Usato dall'agente per evitare proposte che scoprano spese imminenti.",
        ),
        _evidence_row(
            group="Contesto bancario fornito all'agente",
            label="Fondo emergenze attuale",
            value=emergency["balance"],
            source="Read model obiettivi risparmio",
            purpose="Usato dall'agente per verificare che il fondo sia sotto obiettivo.",
        ),
        _evidence_row(
            group="Verifiche deterministiche prima dell'esecuzione",
            label="Saldo previsto dopo proposta",
            value=projected_balance,
            source="Controllo saldo post-azione",
            purpose="Calcolo deterministico per verificare l'impatto prima di mostrare la proposta.",
        ),
        _evidence_row(
            group="Verifiche deterministiche prima dell'esecuzione",
            label="Fondo emergenze dopo proposta",
            value=projected_emergency,
            source="Controllo obiettivo risparmio",
            purpose="Calcolo deterministico dell'impatto sul saving pot.",
        ),
        _evidence_row(
            group="Piano proposto dall'agente",
            label="Importo proposto",
            value=amount,
            source="Piano agente basato sul contesto verificato",
            purpose="Azione candidata: spostare liquidita verso una destinazione fidata.",
        ),
        {
            "group": "Decisione Safety and Approval",
            "label": "Route di rischio",
            "value": route["route"],
            "unit": "route",
            "source": "Risk engine deterministico",
            "purpose": "Il modello non decide l'autorizzazione: la route e calcolata da regole testabili.",
        },
    ]


def _evidence_row(
    *,
    group: str,
    label: str,
    value: float,
    source: str,
    purpose: str,
) -> dict[str, Any]:
    return {
        "group": group,
        "label": label,
        "value": value,
        "unit": "EUR",
        "source": source,
        "purpose": purpose,
    }

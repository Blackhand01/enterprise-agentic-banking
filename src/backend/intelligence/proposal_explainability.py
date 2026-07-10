"""Evidence and customer-visible reasoning for emergency-fund proposals."""

from __future__ import annotations

from typing import Any


# emergency_fund_proposal_evidence.py
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
    checking_delta = _checking_delta(action_type, amount, already_executed)
    emergency_delta = _emergency_delta(action_type, amount, already_executed)
    projected_balance = round(checking["available_balance"] + checking_delta, 2)
    projected_emergency = round(emergency["balance"] + emergency_delta, 2)
    action_purpose = (
        "Azione candidata: recuperare liquidita dal fondo emergenze."
        if action_type == "TRANSFER_REVERSE"
        else "Azione candidata: spostare liquidita verso una destinazione fidata."
    )

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
            purpose=action_purpose,
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


def _checking_delta(action_type: str, amount: float, already_executed: bool) -> float:
    if already_executed:
        return 0.0
    if action_type == "TRANSFER":
        return -amount
    if action_type == "TRANSFER_REVERSE":
        return amount
    return 0.0


def _emergency_delta(action_type: str, amount: float, already_executed: bool) -> float:
    if already_executed:
        return 0.0
    if action_type == "TRANSFER":
        return amount
    if action_type == "TRANSFER_REVERSE":
        return -amount
    return 0.0


# emergency_fund_reasoning_trace.py
def build_emergency_fund_reasoning_trace(
    *,
    checking: dict[str, Any],
    emergency: dict[str, Any],
    goal: dict[str, Any],
    upcoming: float,
    amount: float,
    plan: dict[str, Any],
    route: dict[str, Any],
    projected_balance: float,
    projected_expense_buffer: float,
    projected_emergency_balance: float,
) -> list[dict[str, Any]]:
    """Return an auditable, customer-visible reasoning summary."""

    target_balance = float(emergency.get("target_balance", 10000.0))
    current_gap = max(target_balance - float(emergency["balance"]), 0.0)
    projected_gap = max(target_balance - projected_emergency_balance, 0.0)

    return [
        {
            "step": "Analisi_Contesto",
            "title": "Analisi contesto",
            "summary": (
                "Ho letto saldo conto corrente, fondo emergenze e spese pianificate "
                "prima di proporre qualsiasi movimento."
            ),
            "facts": [
                _money_fact("Saldo disponibile", checking["available_balance"]),
                _money_fact("Spese note 30 giorni", upcoming),
                _money_fact("Fondo emergenze attuale", emergency["balance"]),
            ],
        },
        {
            "step": "Valutazione_Obiettivo",
            "title": "Valutazione obiettivo",
            "summary": goal.get(
                "description",
                "Costruire il fondo emergenze mantenendo liquidita sufficiente.",
            ),
            "facts": [
                _money_fact("Obiettivo fondo", target_balance),
                _money_fact("Gap attuale", current_gap),
                _money_fact("Gap dopo proposta", projected_gap),
            ],
        },
        {
            "step": "Logica_Decisionale",
            "title": "Logica decisionale",
            "summary": plan["recommended_action"],
            "facts": [
                {"label": "Azione", "value": plan["action_type"]},
                _money_fact("Importo", amount),
                _money_fact("Saldo previsto conto", projected_balance),
            ],
        },
        {
            "step": "Verifica_Compliance",
            "title": "Verifica safety",
            "summary": route["reason"],
            "facts": [
                {"label": "Route rischio", "value": route["route"]},
                {"label": "Prossimo passo", "value": route["required_next_step"]},
                _money_fact("Margine dopo spese note", projected_expense_buffer),
            ],
        },
    ]


def _money_fact(label: str, value: float) -> dict[str, Any]:
    return {
        "label": label,
        "value": round(float(value), 2),
        "unit": "EUR",
    }

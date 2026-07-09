"""Customer-facing action templates for emergency-fund planning."""

from __future__ import annotations

from typing import Any


def transfer_to_emergency_fund_plan(amount: float, goal: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": "TRANSFER",
        "route": "APPROVAL_REQUIRED",
        "required_next_step": "CUSTOMER_APPROVAL",
        "reason": "Spostamento coerente con obiettivo cliente e margine cashflow.",
        "reason_codes": ["goal_aligned_savings", "known_expenses_covered"],
        "amount": amount,
        "title": "Aumenta il fondo emergenze",
        "summary": f"L'obiettivo attivo e: {goal['description']}",
        "recommended_action": (
            f"Spostare {amount:.2f} EUR dal conto corrente al fondo emergenze, "
            "mantenendo il margine di sicurezza configurato."
        ),
        "rationale": [
            "Il planner ha ricalcolato l'importo dal saldo corrente e dalle spese pianificate.",
            "L'importo non e fisso: viene limitato dal margine minimo scelto dal cliente.",
            "La destinazione e il fondo emergenze, coerente con l'obiettivo dichiarato.",
        ],
    }


def cashflow_review_plan(goal: dict[str, Any], *, reason: str) -> dict[str, Any]:
    if reason == "goal_buffer":
        title = "Mantieni liquidita sul conto"
        recommended_action = (
            "Non spostare fondi ora: il margine minimo configurato dal cliente "
            "assorbe la liquidita disponibile dopo le spese note."
        )
        rationale = [
            "L'obiettivo cliente richiede un margine minimo elevato sul conto corrente.",
            "Dopo le spese pianificate non resta surplus sufficiente per un trasferimento utile.",
            "La prossima azione e conservare liquidita e rivalutare al prossimo evento.",
        ]
        reason_codes = ["goal_cash_buffer_priority", "no_available_surplus"]
    else:
        title = "Rivedi il piano dopo l'imprevisto"
        recommended_action = (
            "Mettere in pausa nuovi trasferimenti automatici e verificare il margine "
            "dopo le spese note prima di decidere una nuova azione."
        )
        rationale = [
            "E stata rilevata una spesa imprevista recente nel ledger.",
            "Prima di proporre altro risparmio, l'agente deve proteggere liquidita e spese imminenti.",
            "La prossima azione utile e una revisione, non un trasferimento precompilato.",
        ]
        reason_codes = ["unexpected_expense_detected", "goal_replanning_required"]

    return {
        "action_type": "REVIEW_CASHFLOW",
        "route": "REVIEW_REQUIRED",
        "required_next_step": "CUSTOMER_REVIEW",
        "reason": "Il contesto e cambiato: serve rivalutare il cashflow prima di muovere liquidita.",
        "reason_codes": reason_codes,
        "amount": 0.0,
        "title": title,
        "summary": f"L'obiettivo attivo resta: {goal['description']}",
        "recommended_action": recommended_action,
        "rationale": rationale,
    }


def maintain_pace_plan(goal: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": "MAINTAIN_PACE",
        "route": "INFO",
        "required_next_step": "NO_ACTION",
        "reason": "Il cliente e gia allineato al ritmo necessario per raggiungere l'obiettivo.",
        "reason_codes": ["goal_pace_on_track", "no_extra_transfer_needed"],
        "amount": 0.0,
        "title": "Mantieni il ritmo di risparmio",
        "summary": f"L'obiettivo attivo resta: {goal['description']}",
        "recommended_action": (
            "Sei perfettamente allineato al tuo piano di risparmio. "
            "Non sono necessari trasferimenti extra questo mese."
        ),
        "rationale": [
            "La media storica dei versamenti copre il contributo mensile richiesto.",
            "Proporre altri trasferimenti sarebbe ridondante e aumenterebbe il carico decisionale.",
            "L'agente continuera a monitorare il piano e rivalutera solo se il contesto cambia.",
        ],
    }


def subscription_review_plan(goal: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": "REVIEW_SUBSCRIPTION",
        "route": "REVIEW_REQUIRED",
        "required_next_step": "CUSTOMER_REVIEW",
        "reason": "Possibile costo ricorrente non coerente con l'obiettivo cliente.",
        "reason_codes": ["unused_subscription_detected", "expense_optimization"],
        "amount": 0.0,
        "title": "Verifica abbonamento inutilizzato",
        "summary": f"L'obiettivo attivo e: {goal['description']}",
        "recommended_action": (
            "Controllare l'abbonamento CloudStorage Premium e decidere se mantenerlo "
            "o disdirlo prima del prossimo rinnovo."
        ),
        "rationale": [
            "Lo scenario segnala un costo ricorrente potenzialmente evitabile.",
            "L'azione non muove denaro: richiede solo revisione e conferma del cliente.",
            "Ridurre costi ricorrenti migliora il margine disponibile per l'obiettivo.",
        ],
    }

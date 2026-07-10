"""Emergency-fund action templates and safety route helpers."""

from __future__ import annotations

from typing import Any


# emergency_fund_action_templates.py
def transfer_to_emergency_fund_plan(
    amount: float, goal: dict[str, Any]
) -> dict[str, Any]:
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
            "mantenendo buffer e margine anti-oscillazione sul conto corrente."
        ),
        "rationale": [
            "Il planner sposta l'eccesso sopra spese note, buffer e margine anti-oscillazione.",
            "L'importo non e frazionato in micro-proposte successive.",
            "La destinazione e il fondo emergenze, coerente con l'obiettivo dichiarato.",
        ],
    }


def transfer_from_emergency_fund_plan(
    amount: float, goal: dict[str, Any]
) -> dict[str, Any]:
    return {
        "action_type": "TRANSFER_REVERSE",
        "route": "APPROVAL_REQUIRED",
        "required_next_step": "CUSTOMER_APPROVAL",
        "reason": "Le spese note superano la liquidita disponibile e il buffer minimo.",
        "reason_codes": [
            "checking_deficit_detected",
            "emergency_fund_rescue_available",
        ],
        "amount": amount,
        "title": "🔴 Allerta Liquidita: Necessario Recupero",
        "summary": f"L'obiettivo attivo resta: {goal['description']}",
        "recommended_action": (
            f"Le spese note superano la liquidita attuale. Propongo di ritirare "
            f"{amount:.2f} EUR dal Fondo Emergenze per riportare il conto in una banda stabile."
        ),
        "rationale": [
            "Il conto corrente non copre spese pianificate e buffer minimo configurato.",
            "Il recupero non si ferma al minimo: include un margine per evitare ping-pong tra conti.",
            "Il trasferimento richiede approvazione cliente e viene eseguito solo dopo conferma.",
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


# proposal_safety_routes.py
def known_expenses_would_not_be_covered(
    *,
    already_executed: bool,
    action_type: str,
    route: dict[str, Any],
    projected_expense_buffer: float,
) -> bool:
    return (
        not already_executed
        and action_type == "TRANSFER"
        and route["route"] == "APPROVAL_REQUIRED"
        and projected_expense_buffer < 0
    )


def already_executed_route() -> dict[str, Any]:
    return {
        "route": "ALREADY_EXECUTED",
        "reason": "Questa proposta e gia stata eseguita sul sistema di record.",
        "required_next_step": "NO_ACTION",
        "reason_codes": ["idempotency_key_consumed"],
    }


def known_expenses_blocked_route() -> dict[str, Any]:
    return {
        "route": "BLOCKED",
        "reason": (
            "Le spese pianificate dei prossimi 30 giorni non restano coperte "
            "dopo lo spostamento proposto."
        ),
        "required_next_step": "REVIEW_CASHFLOW",
        "reason_codes": ["known_expenses_not_covered_after_action"],
    }

"""Route helpers for emergency-fund proposal safety decisions."""

from __future__ import annotations

from typing import Any


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

"""Emergency-fund action templates and safety route helpers."""

from __future__ import annotations

from typing import Any


def transfer_to_emergency_fund_plan(
    amount: float, goal: dict[str, Any]
) -> dict[str, Any]:
    return {
        "action_type": "TRANSFER",
        "route": "APPROVAL_REQUIRED",
        "required_next_step": "CUSTOMER_APPROVAL",
        "reason": "Movement aligned with customer goal and cashflow margin.",
        "reason_codes": ["goal_aligned_savings", "known_expenses_covered"],
        "amount": amount,
        "title": "Increase the emergency fund",
        "summary": f"The active goal is: {goal['description']}",
        "recommended_action": (
            f"Move {amount:.2f} EUR from checking to the emergency fund, "
            "while preserving buffer and anti-oscillation margin in checking."
        ),
        "rationale": [
            "The planner moves the excess above known expenses, buffer, and anti-oscillation margin.",
            "The amount is not split into successive micro-proposals.",
            "The destination is the emergency fund, aligned with the declared goal.",
        ],
    }


def transfer_from_emergency_fund_plan(
    amount: float, goal: dict[str, Any]
) -> dict[str, Any]:
    return {
        "action_type": "TRANSFER_REVERSE",
        "route": "APPROVAL_REQUIRED",
        "required_next_step": "CUSTOMER_APPROVAL",
        "reason": "Known expenses exceed available liquidity and the minimum buffer.",
        "reason_codes": [
            "checking_deficit_detected",
            "emergency_fund_rescue_available",
        ],
        "amount": amount,
        "title": "Liquidity alert: recovery needed",
        "summary": f"The active goal remains: {goal['description']}",
        "recommended_action": (
            "Known expenses exceed current liquidity. I propose withdrawing "
            f"{amount:.2f} EUR from the Emergency Fund to bring the account back into a stable band."
        ),
        "rationale": [
            "Checking does not cover scheduled expenses and the configured minimum buffer.",
            "The recovery does not stop at the minimum: it includes margin to avoid account ping-pong.",
            "The transfer requires customer approval and is executed only after confirmation.",
        ],
    }


def cashflow_review_plan(goal: dict[str, Any], *, reason: str) -> dict[str, Any]:
    if reason == "goal_buffer":
        title = "Preserve liquidity in checking"
        recommended_action = (
            "Do not move funds now: the customer-configured minimum margin "
            "absorbs available liquidity after known expenses."
        )
        rationale = [
            "The customer goal requires a high minimum margin in checking.",
            "After scheduled expenses, no useful transfer surplus remains.",
            "The next action is to preserve liquidity and reassess at the next event.",
        ]
        reason_codes = ["goal_cash_buffer_priority", "no_available_surplus"]
    else:
        title = "Review the plan after the unexpected expense"
        recommended_action = (
            "Pause new automatic transfers and verify the margin after known expenses "
            "before deciding a new action."
        )
        rationale = [
            "A recent unexpected expense was detected in the ledger.",
            "Before proposing more savings, the agent must protect liquidity and upcoming expenses.",
            "The next useful action is a review, not a prefilled transfer.",
        ]
        reason_codes = ["unexpected_expense_detected", "goal_replanning_required"]

    return {
        "action_type": "REVIEW_CASHFLOW",
        "route": "REVIEW_REQUIRED",
        "required_next_step": "CUSTOMER_REVIEW",
        "reason": "The context changed: cashflow must be reassessed before moving liquidity.",
        "reason_codes": reason_codes,
        "amount": 0.0,
        "title": title,
        "summary": f"The active goal remains: {goal['description']}",
        "recommended_action": recommended_action,
        "rationale": rationale,
    }


def maintain_pace_plan(goal: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": "MAINTAIN_PACE",
        "route": "INFO",
        "required_next_step": "NO_ACTION",
        "reason": "The customer is already aligned with the pace required to reach the goal.",
        "reason_codes": ["goal_pace_on_track", "no_extra_transfer_needed"],
        "amount": 0.0,
        "title": "Maintain savings pace",
        "summary": f"The active goal remains: {goal['description']}",
        "recommended_action": (
            "You are fully aligned with your savings plan. "
            "No extra transfers are needed this month."
        ),
        "rationale": [
            "The historical average contribution covers the required monthly contribution.",
            "Proposing additional transfers would be redundant and increase decision load.",
            "The agent will keep monitoring the plan and reassess only if context changes.",
        ],
    }


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
        "reason": "This proposal has already been executed on the system of record.",
        "required_next_step": "NO_ACTION",
        "reason_codes": ["idempotency_key_consumed"],
    }


def known_expenses_blocked_route() -> dict[str, Any]:
    return {
        "route": "BLOCKED",
        "reason": (
            "Scheduled expenses for the next 30 days would no longer be covered "
            "after the proposed movement."
        ),
        "required_next_step": "REVIEW_CASHFLOW",
        "reason_codes": ["known_expenses_not_covered_after_action"],
    }

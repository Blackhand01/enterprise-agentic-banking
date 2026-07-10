"""Evidence and customer-visible reasoning for emergency-fund proposals."""

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
    checking_delta = _checking_delta(action_type, amount, already_executed)
    emergency_delta = _emergency_delta(action_type, amount, already_executed)
    projected_balance = round(checking["available_balance"] + checking_delta, 2)
    projected_emergency = round(emergency["balance"] + emergency_delta, 2)
    action_purpose = (
        "Candidate action: recover liquidity from the emergency fund."
        if action_type == "TRANSFER_REVERSE"
        else "Candidate action: move liquidity to a trusted destination."
    )

    return [
        _evidence_row(
            group="Banking context provided to the agent",
            label="Checking available balance",
            value=checking["available_balance"],
            source="Customer accounts read model",
            purpose="Used by the agent to assess available liquidity.",
        ),
        _evidence_row(
            group="Banking context provided to the agent",
            label="Scheduled expenses next 30 days",
            value=round(upcoming, 2),
            source="Scheduled payments",
            purpose="Used by the agent to avoid proposals that would leave upcoming expenses uncovered.",
        ),
        _evidence_row(
            group="Banking context provided to the agent",
            label="Current emergency fund",
            value=emergency["balance"],
            source="Savings goals read model",
            purpose="Used by the agent to verify the fund is below target.",
        ),
        _evidence_row(
            group="Deterministic checks before execution",
            label="Projected balance after proposal",
            value=projected_balance,
            source="Post-action balance check",
            purpose="Deterministic calculation to verify impact before showing the proposal.",
        ),
        _evidence_row(
            group="Deterministic checks before execution",
            label="Emergency fund after proposal",
            value=projected_emergency,
            source="Savings goal check",
            purpose="Deterministic calculation of impact on the savings pot.",
        ),
        _evidence_row(
            group="Plan proposed by the agent",
            label="Proposed amount",
            value=amount,
            source="Agent plan based on verified context",
            purpose=action_purpose,
        ),
        {
            "group": "Safety and Approval decision",
            "label": "Risk route",
            "value": route["route"],
            "unit": "route",
            "source": "Deterministic risk engine",
            "purpose": "The model does not decide authorization: the route is calculated by testable rules.",
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
            "step": "Context_Analysis",
            "title": "Context analysis",
            "summary": (
                "I read checking balance, emergency fund, and scheduled expenses "
                "before proposing any movement."
            ),
            "facts": [
                _money_fact("Available balance", checking["available_balance"]),
                _money_fact("Known expenses 30 days", upcoming),
                _money_fact("Current emergency fund", emergency["balance"]),
            ],
        },
        {
            "step": "Goal_Evaluation",
            "title": "Goal evaluation",
            "summary": goal.get(
                "description",
                "Build the emergency fund while preserving sufficient liquidity.",
            ),
            "facts": [
                _money_fact("Fund target", target_balance),
                _money_fact("Current gap", current_gap),
                _money_fact("Gap after proposal", projected_gap),
            ],
        },
        {
            "step": "Decision_Logic",
            "title": "Decision logic",
            "summary": plan["recommended_action"],
            "facts": [
                {"label": "Action", "value": plan["action_type"]},
                _money_fact("Amount", amount),
                _money_fact("Projected checking balance", projected_balance),
            ],
        },
        {
            "step": "Compliance_Check",
            "title": "Safety check",
            "summary": route["reason"],
            "facts": [
                {"label": "Risk route", "value": route["route"]},
                {"label": "Next step", "value": route["required_next_step"]},
                _money_fact("Margin after known expenses", projected_expense_buffer),
            ],
        },
    ]


def _money_fact(label: str, value: float) -> dict[str, Any]:
    return {
        "label": label,
        "value": round(float(value), 2),
        "unit": "EUR",
    }

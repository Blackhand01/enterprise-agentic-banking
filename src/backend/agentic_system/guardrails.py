"""Deterministic guardrails for the agentic banking prototype.

Keep safety decisions here, outside the LLM and outside orchestration code.
The agent may propose an action, but these functions decide whether local code
is allowed to expose policy context or simulate execution.
"""

from __future__ import annotations

import json
from typing import Any


# Product/risk threshold for this prototype.
# Keeping it here makes the execution limit explicit, testable, and independent
# from prompt wording or model behavior.
TRANSFER_AUTONOMOUS_LIMIT_EUR = 500.0


def filter_active_policies(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove stale policy documents before they can reach the LLM context."""

    active_policies: list[dict[str, Any]] = []
    for policy in policies:
        # Malformed documents are ignored instead of being passed downstream.
        # A retrieval layer should fail closed when document shape is uncertain.
        if not isinstance(policy, dict):
            continue

        # This is the key retrieval guardrail: stale policies are removed before
        # prompt construction, so the model cannot reason over obsolete rules.
        if policy.get("is_stale") is True:
            continue

        active_policies.append(policy)

    return active_policies


def evaluate_transfer_guardrail(recipient: str, amount: Any) -> dict[str, Any]:
    """Return the deterministic execution decision for a transfer request."""

    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        # Invalid amounts should never reach simulated execution. Return a
        # structured tool result so the agent can ask the user to correct input.
        return {
            "status": "ERROR",
            "reason": "INVALID_AMOUNT",
            "action_required": "FIX_INPUT",
        }

    # Zero and negative transfers are invalid regardless of model confidence.
    if numeric_amount <= 0:
        return {
            "status": "ERROR",
            "reason": "NON_POSITIVE_AMOUNT",
            "action_required": "FIX_INPUT",
        }

    # High-risk movement of money is blocked by code, not by prompt compliance.
    # In production this route would trigger strong authentication or human
    # approval before execution.
    if numeric_amount > TRANSFER_AUTONOMOUS_LIMIT_EUR:
        return {
            "status": "BLOCKED",
            "reason": "HIGH_RISK_AMOUNT",
            "action_required": "REQUEST_MFA",
        }

    # "ALLOWED" is not a model decision; it is the deterministic result of this
    # guardrail evaluation. The execution adapter can now simulate the transfer.
    return {
        "status": "ALLOWED",
        "recipient": recipient,
        "amount": numeric_amount,
        "currency": "EUR",
    }


def transfer_decision_to_tool_result(decision: dict[str, Any]) -> str:
    """Serialize a transfer decision as the JSON tool result expected by the LLM."""

    # Errors and blocks are returned as-is. The LLM should only format them for
    # the customer; it must not reinterpret them as successful execution.
    if decision.get("status") != "ALLOWED":
        return json.dumps(decision)

    # This prototype has no real payment rail. We expose a simulated success only
    # after the deterministic guardrail has returned ALLOWED.
    return json.dumps(
        {
            "status": "EXECUTED",
            "recipient": decision["recipient"],
            "amount": decision["amount"],
            "currency": decision["currency"],
            "execution_mode": "SIMULATED",
        },
        ensure_ascii=False,
    )

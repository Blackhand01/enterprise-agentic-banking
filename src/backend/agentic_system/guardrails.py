"""Deterministic guardrails for the agentic banking prototype.

Keep safety decisions here, outside the LLM and outside orchestration code.
The agent may propose an action, but these functions decide whether local code
is allowed to expose policy context or commit an action through the local adapter.
"""

from __future__ import annotations
import re
from typing import Any

CUSTOMER_UNSAFE_OUTPUT_PATTERNS = (
    r"<\s*/?\s*function\b",
    r"\bfetch_transactions\b",
    r"\bexecute_transfer\b",
    r"\bget_balance_summary\b",
    r"\bget_customer_context\b",
    r"\bget_total_balance\b",
    r"\bget_account_list\b",
    r"\bget_account_balance\b",
    r"\bBank Data APIs?\b",
    r"\bpolicyDB\b",
    r"\bdoc_[a-zA-Z0-9_]+\b",
)


def evaluate_action_route(
    *,
    amount: Any,
    autonomous_transfer_limit_eur: float,
    recipient_status: str = "existing",
    transfer_scope: str = "internal",
    account_ownership: str = "single",
    auth_level: str = "mfa_verified",
    data_freshness: str = "fresh",
) -> dict[str, Any]:
    """Return the deterministic route for a proposed banking action."""
    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        return _route(
            route="INVALID_INPUT",
            reason="Invalid amount.",
            required_next_step="FIX_AMOUNT",
            reason_codes=["invalid_amount"],
        )
    if numeric_amount <= 0:
        return _route(
            route="INVALID_INPUT",
            reason="The amount must be greater than zero.",
            required_next_step="FIX_AMOUNT",
            reason_codes=["non_positive_amount"],
        )
    if data_freshness != "fresh":
        return _route(
            route="BLOCKED",
            reason="Banking data is not fresh enough to authorize the action.",
            required_next_step="REFRESH_CONTEXT",
            reason_codes=["stale_or_unavailable_bank_context"],
        )
    if account_ownership == "shared":
        return _route(
            route="CO_APPROVAL_REQUIRED",
            reason="The shared account requires approval from the second account holder.",
            required_next_step="REQUEST_CO_APPROVAL",
            reason_codes=["shared_account", "multi_principal_authorization"],
        )
    if recipient_status == "new":
        return _route(
            route="STEP_UP_REQUIRED",
            reason="The new beneficiary requires step-up verification.",
            required_next_step="REQUEST_MFA",
            reason_codes=["new_beneficiary"],
        )
    if transfer_scope == "external":
        return _route(
            route="STEP_UP_REQUIRED",
            reason="The external transfer requires step-up verification.",
            required_next_step="REQUEST_MFA",
            reason_codes=["external_transfer"],
        )
    if auth_level != "mfa_verified":
        return _route(
            route="STEP_UP_REQUIRED",
            reason="The customer context does not have a recent MFA verification.",
            required_next_step="REQUEST_MFA",
            reason_codes=["missing_recent_mfa"],
        )
    if numeric_amount > float(autonomous_transfer_limit_eur):
        return _route(
            route="STEP_UP_REQUIRED",
            reason="The amount exceeds the autonomous transfer limit.",
            required_next_step="REQUEST_MFA",
            reason_codes=["amount_above_autonomous_limit"],
        )
    return _route(
        route="APPROVAL_REQUIRED",
        reason="Movement toward an existing trusted internal destination.",
        required_next_step="CUSTOMER_APPROVAL",
        reason_codes=["money_movement", "trusted_existing_internal_target"],
    )


def _route(
    *,
    route: str,
    reason: str,
    required_next_step: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    return {
        "route": route,
        "reason": reason,
        "required_next_step": required_next_step,
        "reason_codes": reason_codes,
    }


def response_has_customer_unsafe_content(text: str) -> bool:
    """Detect internal implementation leakage in a customer-facing answer."""
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in CUSTOMER_UNSAFE_OUTPUT_PATTERNS
    )


def sanitize_customer_response(text: str) -> str:
    """Return a safe fallback when the model exposes internals or fake tools."""
    if not response_has_customer_unsafe_content(text):
        return text
    return (
        "I can help using only verified data from your banking context. "
        "I cannot show internal technical details or unavailable tools. "
        "Tell me what you want to verify, such as total balance, accounts, "
        "spending by category, or proposal impact."
    )


def filter_active_policies(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove stale policy documents before they can reach the LLM context."""
    active_policies: list[dict[str, Any]] = []
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        if policy.get("is_stale") is True:
            continue
        active_policies.append(policy)
    return active_policies


def evaluate_transfer_guardrail(
    recipient: str,
    amount: Any,
    *,
    autonomous_transfer_limit_eur: float,
    auth_level: str = "mfa_verified",
) -> dict[str, Any]:
    """Return the deterministic execution decision for a transfer request."""
    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        return {
            "status": "ERROR",
            "reason": "INVALID_AMOUNT",
            "action_required": "FIX_INPUT",
        }
    if numeric_amount <= 0:
        return {
            "status": "ERROR",
            "reason": "NON_POSITIVE_AMOUNT",
            "action_required": "FIX_INPUT",
        }
    if (
        numeric_amount > float(autonomous_transfer_limit_eur)
        and auth_level != "mfa_verified"
    ):
        return {
            "status": "BLOCKED",
            "reason": "HIGH_RISK_AMOUNT",
            "action_required": "REQUEST_MFA",
        }
    return {
        "status": "ALLOWED",
        "recipient": recipient,
        "amount": numeric_amount,
        "currency": "EUR",
    }

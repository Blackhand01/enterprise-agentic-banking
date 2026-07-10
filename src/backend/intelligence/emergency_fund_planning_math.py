"""Cashflow and projection helpers for emergency-fund planning."""

from __future__ import annotations
import math
from typing import Any

try:
    from .proposal_support import (
        known_expenses_blocked_route,
        known_expenses_would_not_be_covered,
    )
except ImportError:
    from proposal_support import (
        known_expenses_blocked_route,
        known_expenses_would_not_be_covered,
    )


def project_emergency_fund_plan(
    *,
    checking: dict[str, Any],
    emergency: dict[str, Any],
    action_type: str,
    amount: float,
    upcoming: float,
    already_executed: bool,
) -> dict[str, Any]:
    checking_delta = checking_delta_for_plan(
        action_type=action_type,
        amount=amount,
        already_executed=already_executed,
    )
    emergency_delta = emergency_delta_for_plan(
        action_type=action_type,
        amount=amount,
        already_executed=already_executed,
    )
    target_balance = emergency.get("target_balance", 10000.0)
    projected_balance = round(checking["available_balance"] + checking_delta, 2)
    source, recipient = accounts_for_plan(action_type)
    return {
        "projected_balance": projected_balance,
        "projected_expense_buffer": round(projected_balance - upcoming, 2),
        "projected_savings": round(emergency["balance"] + emergency_delta, 2),
        "target_balance": target_balance,
        "source": source,
        "recipient": recipient,
    }


def guard_route_against_known_expenses(
    *,
    route: dict[str, Any],
    plan: dict[str, Any],
    projection: dict[str, Any],
    already_executed: bool,
) -> dict[str, Any]:
    if known_expenses_would_not_be_covered(
        already_executed=already_executed,
        action_type=plan["action_type"],
        route=route,
        projected_expense_buffer=projection["projected_expense_buffer"],
    ):
        return known_expenses_blocked_route()
    return route


def cashflow_stability_margin(financial_rules: dict[str, Any]) -> float:
    minimum_buffer = float(financial_rules["minimum_cash_buffer_eur"])
    rounding_increment = float(financial_rules["transfer_rounding_increment_eur"])
    raw_margin = max(minimum_buffer * 0.25, rounding_increment * 5)
    return round_up_to_increment(raw_margin, rounding_increment)


def cashflow_activation_margin(financial_rules: dict[str, Any]) -> float:
    return cashflow_stability_margin(financial_rules)


def round_down_to_increment(amount: float, increment: float) -> float:
    if increment <= 0:
        return round(amount, 2)
    return round(math.floor((amount + 1e-9) / increment) * increment, 2)


def round_up_to_increment(amount: float, increment: float) -> float:
    if increment <= 0:
        return round(amount, 2)
    return round(math.ceil((amount - 1e-9) / increment) * increment, 2)


def checking_delta_for_plan(
    *,
    action_type: str,
    amount: float,
    already_executed: bool,
) -> float:
    if already_executed:
        return 0.0
    if action_type == "TRANSFER":
        return -amount
    if action_type == "TRANSFER_REVERSE":
        return amount
    return 0.0


def emergency_delta_for_plan(
    *,
    action_type: str,
    amount: float,
    already_executed: bool,
) -> float:
    if already_executed:
        return 0.0
    if action_type == "TRANSFER":
        return amount
    if action_type == "TRANSFER_REVERSE":
        return -amount
    return 0.0


def accounts_for_plan(action_type: str) -> tuple[str, str]:
    if action_type == "TRANSFER_REVERSE":
        return "Emergency_Fund", "Checking"
    return "Checking", "Emergency_Fund"

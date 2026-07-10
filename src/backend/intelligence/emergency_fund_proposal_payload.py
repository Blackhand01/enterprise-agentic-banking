"""Emergency-fund proposal payload assembly."""

from __future__ import annotations
from typing import Any

try:
    from .proposal_explainability import (
        build_emergency_fund_proposal_evidence,
        build_emergency_fund_reasoning_trace,
    )
except ImportError:
    from proposal_explainability import (
        build_emergency_fund_proposal_evidence,
        build_emergency_fund_reasoning_trace,
    )


def build_emergency_fund_proposal_payload(
    *,
    trace_id: str,
    salary: dict[str, Any] | None,
    context: dict[str, Any],
    plan: dict[str, Any],
    route: dict[str, Any],
    projection: dict[str, Any],
    proposal_id: str,
    planned_amount: float,
    executed_operation: Any,
    already_executed: bool,
) -> dict[str, Any]:
    return {
        **_proposal_identity_fields(
            trace_id=trace_id,
            salary=salary,
            proposal_id=proposal_id,
            plan=plan,
            projection=projection,
            goal=context["goal"],
            amount=planned_amount,
            executed_operation=executed_operation,
            already_executed=already_executed,
        ),
        **_proposal_balance_fields(context, projection),
        **_proposal_route_fields(route),
        "trusted_target": True,
        **_proposal_explainability_fields(
            context=context,
            plan=plan,
            route=route,
            projection=projection,
            amount=planned_amount,
        ),
        "rationale": plan["rationale"],
    }


def _proposal_identity_fields(
    *,
    trace_id: str,
    salary: dict[str, Any] | None,
    proposal_id: str,
    plan: dict[str, Any],
    projection: dict[str, Any],
    goal: dict[str, Any],
    amount: float,
    executed_operation: Any,
    already_executed: bool,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "trace_id": trace_id,
        "action_type": plan["action_type"],
        "title": plan["title"],
        "summary": plan["summary"],
        "recommended_action": _recommended_action(plan, amount),
        "goal": goal,
        "source": projection["source"],
        "recipient": projection["recipient"],
        "amount": amount,
        "currency": "EUR",
        "already_executed": already_executed,
        "executed_operation": executed_operation,
        "salary_detected": salary,
    }


def _proposal_balance_fields(
    context: dict[str, Any],
    projection: dict[str, Any],
) -> dict[str, Any]:
    emergency = context["emergency"]
    target_balance = projection["target_balance"]
    projected_savings = projection["projected_savings"]
    return {
        "upcoming_expenses_30d": round(context["upcoming"], 2),
        "available_balance": context["checking"]["available_balance"],
        "projected_checking_balance": projection["projected_balance"],
        "projected_expense_buffer": projection["projected_expense_buffer"],
        "emergency_balance": emergency["balance"],
        "projected_emergency_balance": projected_savings,
        "target_balance": target_balance,
        "financial_rules": context["financial_rules"],
        "goal_progress": round((emergency["balance"] / target_balance) * 100),
        "projected_goal_progress": round((projected_savings / target_balance) * 100),
    }


def _proposal_route_fields(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": route["route"],
        "reason": route["reason"],
        "reason_codes": route.get("reason_codes", []),
        "required_next_step": route["required_next_step"],
    }


def _proposal_explainability_fields(
    *,
    context: dict[str, Any],
    plan: dict[str, Any],
    route: dict[str, Any],
    projection: dict[str, Any],
    amount: float,
) -> dict[str, Any]:
    return {
        "evidence": build_emergency_fund_proposal_evidence(
            checking=context["checking"],
            emergency=context["emergency"],
            upcoming=context["upcoming"],
            amount=amount,
            route=route,
            action_type=plan["action_type"],
        ),
        "reasoning_trace": build_emergency_fund_reasoning_trace(
            checking=context["checking"],
            emergency=context["emergency"],
            goal=context["goal"],
            upcoming=context["upcoming"],
            amount=amount,
            plan=plan,
            route=route,
            projected_balance=projection["projected_balance"],
            projected_expense_buffer=projection["projected_expense_buffer"],
            projected_emergency_balance=projection["projected_savings"],
        ),
    }


def _recommended_action(plan: dict[str, Any], amount: float) -> str:
    if plan["action_type"] == "TRANSFER_REVERSE":
        return (
            "Le spese note superano la liquidita attuale. Propongo di ritirare "
            f"{amount:.2f} EUR dal Fondo Emergenze per riportare il conto in una banda stabile."
        )
    if plan["action_type"] != "TRANSFER":
        return plan["recommended_action"]
    return (
        f"Spostare {amount:.2f} EUR dal conto corrente al fondo emergenze, "
        "mantenendo buffer e margine anti-oscillazione sul conto corrente."
    )

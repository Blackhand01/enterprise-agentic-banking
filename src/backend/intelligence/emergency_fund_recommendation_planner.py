"""Planner for the proactive emergency-fund recommendation."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

try:
    from ..agentic_system.guardrails import evaluate_action_route
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from agentic_system.guardrails import evaluate_action_route
    from storage.sqlite_banking_store import SQLiteBankingStore

from .customer_emergency_goal import default_emergency_fund_goal
from .emergency_fund_action_templates import (
    cashflow_review_plan,
    maintain_pace_plan,
    subscription_review_plan,
    transfer_to_emergency_fund_plan,
)
from .emergency_fund_proposal_evidence import build_emergency_fund_proposal_evidence
from .proposal_safety_routes import (
    already_executed_route,
    event_scenario,
    known_expenses_blocked_route,
    known_expenses_would_not_be_covered,
)


class EmergencyFundRecommendationPlanner:
    """Builds grounded emergency-fund proposals from verified banking data."""

    def __init__(
        self,
        banking_store: SQLiteBankingStore,
        trace_id_factory: Callable[[], str],
        goal_provider: Callable[[], dict[str, Any]] | None = None,
        event_provider: Callable[[], dict[str, Any] | None] | None = None,
    ) -> None:
        self.banking_store = banking_store
        self.trace_id_factory = trace_id_factory
        self.goal_provider = goal_provider or (lambda: default_emergency_fund_goal())
        self.event_provider = event_provider or (lambda: None)

    def build(self, amount: float | None = None) -> dict[str, Any]:
        checking = self.banking_store.account_by_name("Checking")
        emergency = self.banking_store.account_by_name("Emergency_Fund")
        financial_rules = self.banking_store.financial_rule_config()
        goal = self.goal_provider()
        plan = self._select_plan(
            checking=checking,
            emergency=emergency,
            goal=goal,
            financial_rules=financial_rules,
        )
        planned_amount = float(amount if amount is not None else plan["amount"])
        proposal_id = self.proposal_id(planned_amount, plan["action_type"])
        executed_operation = self.banking_store.operation_status(proposal_id)
        upcoming = abs(sum(tx["amount"] for tx in self.banking_store.scheduled_transactions()))
        already_executed = executed_operation is not None
        route = self._route_for_plan(
            plan=plan,
            planned_amount=planned_amount,
            financial_rules=financial_rules,
        )
        if already_executed:
            route = already_executed_route()

        new_money_movement = (
            planned_amount
            if plan["action_type"] == "TRANSFER" and not already_executed
            else 0.0
        )
        projected_balance = round(checking["available_balance"] - new_money_movement, 2)
        projected_expense_buffer = round(projected_balance - upcoming, 2)
        if known_expenses_would_not_be_covered(
            already_executed=already_executed,
            action_type=plan["action_type"],
            route=route,
            projected_expense_buffer=projected_expense_buffer,
        ):
            route = known_expenses_blocked_route()

        target_balance = emergency.get("target_balance", 10000.0)
        projected_savings = round(emergency["balance"] + new_money_movement, 2)

        return {
            "proposal_id": proposal_id,
            "trace_id": self.trace_id_factory(),
            "action_type": plan["action_type"],
            "title": plan["title"],
            "summary": plan["summary"],
            "recommended_action": _recommended_action(plan, planned_amount),
            "goal": goal,
            "source": "Checking",
            "recipient": "Emergency_Fund",
            "amount": planned_amount,
            "currency": "EUR",
            "already_executed": already_executed,
            "executed_operation": executed_operation,
            "salary_detected": self.banking_store.latest_salary(),
            "upcoming_expenses_30d": round(upcoming, 2),
            "available_balance": checking["available_balance"],
            "projected_checking_balance": projected_balance,
            "projected_expense_buffer": projected_expense_buffer,
            "emergency_balance": emergency["balance"],
            "projected_emergency_balance": projected_savings,
            "target_balance": target_balance,
            "financial_rules": financial_rules,
            "goal_progress": round((emergency["balance"] / target_balance) * 100),
            "projected_goal_progress": round((projected_savings / target_balance) * 100),
            "trusted_target": True,
            "route": route["route"],
            "reason": route["reason"],
            "reason_codes": route.get("reason_codes", []),
            "required_next_step": route["required_next_step"],
            "evidence": build_emergency_fund_proposal_evidence(
                checking=checking,
                emergency=emergency,
                upcoming=upcoming,
                amount=planned_amount,
                route=route,
                action_type=plan["action_type"],
            ),
            "rationale": plan["rationale"],
        }

    def preview_transfer(self, amount: float) -> dict[str, Any]:
        financial_rules = self.banking_store.financial_rule_config()
        return evaluate_action_route(
            amount=amount,
            autonomous_transfer_limit_eur=financial_rules["autonomous_transfer_limit_eur"],
        )

    def proposal_id(self, amount: float, action_type: str = "TRANSFER") -> str:
        salary = self.banking_store.latest_salary() or {}
        anchor = salary.get("transaction_id", "no_salary_anchor")
        cents = int(round(float(amount) * 100))
        return f"prop_{action_type.lower()}_{anchor}_checking_to_emergency_{cents}"

    def _select_plan(
        self,
        *,
        checking: dict[str, Any],
        emergency: dict[str, Any],
        goal: dict[str, Any],
        financial_rules: dict[str, Any],
    ) -> dict[str, Any]:
        if event_scenario(self.event_provider()) == "unused_subscription":
            return subscription_review_plan(goal)

        if self._has_recent_unexpected_expense():
            return cashflow_review_plan(goal, reason="unexpected_expense")

        if self._is_goal_pace_on_track(emergency=emergency, goal=goal):
            return maintain_pace_plan(goal)

        amount = self._suggest_transfer_amount(checking, emergency, financial_rules)
        if amount <= 0:
            return cashflow_review_plan(goal, reason="goal_buffer")

        return transfer_to_emergency_fund_plan(amount, goal)

    def _suggest_transfer_amount(
        self,
        checking: dict[str, Any],
        emergency: dict[str, Any],
        financial_rules: dict[str, Any],
    ) -> float:
        upcoming = abs(sum(tx["amount"] for tx in self.banking_store.scheduled_transactions()))
        minimum_buffer = float(financial_rules["minimum_cash_buffer_eur"])
        surplus_ratio = float(financial_rules["surplus_investment_ratio"])
        transfer_limit = float(financial_rules["autonomous_transfer_limit_eur"])
        rounding_increment = float(financial_rules["transfer_rounding_increment_eur"])
        available_surplus = checking["available_balance"] - upcoming - minimum_buffer
        target_gap = max(float(emergency.get("target_balance", 0)) - emergency["balance"], 0)
        raw_amount = min(available_surplus * surplus_ratio, target_gap, transfer_limit)
        return max(0.0, round(raw_amount / rounding_increment) * rounding_increment)

    def _has_recent_unexpected_expense(self) -> bool:
        today = date.today().isoformat()
        return any(
            tx.get("date") == today
            for tx in self.banking_store.transactions_by_category("imprevisti")
        )

    def _is_goal_pace_on_track(
        self,
        *,
        emergency: dict[str, Any],
        goal: dict[str, Any],
    ) -> bool:
        target_balance = float(emergency.get("target_balance", 10000.0))
        current_balance = float(emergency["balance"])
        target_months = int(goal.get("target_months", 18))
        if target_months <= 0:
            return current_balance >= target_balance

        current_gap = max(target_balance - current_balance, 0.0)
        if current_gap <= 0:
            return True

        required_monthly = round(current_gap / target_months, 2)
        historical_monthly = self._historical_monthly_savings()
        return historical_monthly >= required_monthly

    def _historical_monthly_savings(self) -> float:
        snapshots = self.banking_store.monthly_snapshots(limit=12)
        if not snapshots:
            return 0.0
        values = [
            max(float(snapshot.get("savings_transfer_eur", 0.0)), 0.0)
            for snapshot in snapshots
        ]
        return round(sum(values) / len(values), 2)

    def _route_for_plan(
        self,
        *,
        plan: dict[str, Any],
        planned_amount: float,
        financial_rules: dict[str, Any],
    ) -> dict[str, Any]:
        if plan["action_type"] == "TRANSFER":
            return evaluate_action_route(
                amount=planned_amount,
                autonomous_transfer_limit_eur=financial_rules["autonomous_transfer_limit_eur"],
            )

        return {
            "route": plan["route"],
            "reason": plan["reason"],
            "required_next_step": plan["required_next_step"],
            "reason_codes": plan["reason_codes"],
        }


def _recommended_action(plan: dict[str, Any], amount: float) -> str:
    if plan["action_type"] != "TRANSFER":
        return plan["recommended_action"]
    return (
        f"Spostare {amount:.2f} EUR dal conto corrente al fondo emergenze, "
        "mantenendo il margine di sicurezza configurato."
    )

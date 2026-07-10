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
from .proposal_support import (
    already_executed_route,
    cashflow_review_plan,
    maintain_pace_plan,
    transfer_from_emergency_fund_plan,
    transfer_to_emergency_fund_plan,
)
from .customer_emergency_goal import default_emergency_fund_goal
from .emergency_fund_planning_math import (
    cashflow_activation_margin,
    cashflow_stability_margin,
    guard_route_against_known_expenses,
    project_emergency_fund_plan,
    round_down_to_increment,
    round_up_to_increment,
)
from .emergency_fund_proposal_payload import build_emergency_fund_proposal_payload


class EmergencyFundRecommendationPlanner:
    """Builds grounded emergency-fund proposals from verified banking data."""

    def __init__(
        self,
        banking_store: SQLiteBankingStore,
        trace_id_factory: Callable[[], str],
        goal_provider: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.banking_store = banking_store
        self.trace_id_factory = trace_id_factory
        self.goal_provider = goal_provider or (lambda: default_emergency_fund_goal())

    def build(self, amount: float | None = None) -> dict[str, Any]:
        context = self._planning_context()
        plan = self._select_plan(
            checking=context["checking"],
            emergency=context["emergency"],
            goal=context["goal"],
            financial_rules=context["financial_rules"],
        )
        planned_amount = self._planned_amount(amount, plan)
        proposal_id = self.proposal_id(planned_amount, plan["action_type"])
        executed_operation = self.banking_store.operation_status(proposal_id)
        already_executed = executed_operation is not None
        route = self._route_for_execution(
            plan=plan,
            planned_amount=planned_amount,
            financial_rules=context["financial_rules"],
            already_executed=already_executed,
        )
        projection = project_emergency_fund_plan(
            checking=context["checking"],
            emergency=context["emergency"],
            action_type=plan["action_type"],
            amount=planned_amount,
            upcoming=context["upcoming"],
            already_executed=already_executed,
        )
        route = guard_route_against_known_expenses(
            route=route,
            plan=plan,
            projection=projection,
            already_executed=already_executed,
        )
        return build_emergency_fund_proposal_payload(
            trace_id=self.trace_id_factory(),
            salary=self.banking_store.latest_salary(),
            context=context,
            plan=plan,
            route=route,
            projection=projection,
            proposal_id=proposal_id,
            planned_amount=planned_amount,
            executed_operation=executed_operation,
            already_executed=already_executed,
        )

    def _planning_context(self) -> dict[str, Any]:
        checking = self.banking_store.account_by_name("Checking")
        emergency = self.banking_store.account_by_name("Emergency_Fund")
        financial_rules = self.banking_store.financial_rule_config()
        goal = self.goal_provider()
        upcoming = abs(
            sum(tx["amount"] for tx in self.banking_store.scheduled_transactions())
        )
        return {
            "checking": checking,
            "emergency": emergency,
            "financial_rules": financial_rules,
            "goal": goal,
            "upcoming": upcoming,
        }

    @staticmethod
    def _planned_amount(amount: float | None, plan: dict[str, Any]) -> float:
        return float(amount if amount is not None else plan["amount"])

    def _route_for_execution(
        self,
        *,
        plan: dict[str, Any],
        planned_amount: float,
        financial_rules: dict[str, Any],
        already_executed: bool,
    ) -> dict[str, Any]:
        if already_executed:
            return already_executed_route()
        return self._route_for_plan(
            plan=plan,
            planned_amount=planned_amount,
            financial_rules=financial_rules,
        )

    def preview_transfer(self, amount: float) -> dict[str, Any]:
        financial_rules = self.banking_store.financial_rule_config()
        return evaluate_action_route(
            amount=amount,
            autonomous_transfer_limit_eur=financial_rules[
                "autonomous_transfer_limit_eur"
            ],
        )

    def proposal_id(self, amount: float, action_type: str = "TRANSFER") -> str:
        salary = self.banking_store.latest_salary() or {}
        anchor = salary.get("transaction_id", "no_salary_anchor")
        cents = int(round(float(amount) * 100))
        direction = (
            "emergency_to_checking"
            if action_type == "TRANSFER_REVERSE"
            else "checking_to_emergency"
        )
        return f"prop_{action_type.lower()}_{anchor}_{direction}_{cents}"

    def _select_plan(
        self,
        *,
        checking: dict[str, Any],
        emergency: dict[str, Any],
        goal: dict[str, Any],
        financial_rules: dict[str, Any],
    ) -> dict[str, Any]:
        rescue_amount = self._suggest_rescue_amount(
            checking, emergency, financial_rules
        )
        if rescue_amount > 0:
            return transfer_from_emergency_fund_plan(rescue_amount, goal)
        if self._has_recent_unexpected_expense():
            return cashflow_review_plan(goal, reason="unexpected_expense")
        if self._is_goal_pace_on_track(emergency=emergency, goal=goal):
            return maintain_pace_plan(goal)
        amount = self._suggest_transfer_amount(checking, emergency, financial_rules)
        if amount <= 0:
            return cashflow_review_plan(goal, reason="goal_buffer")
        return transfer_to_emergency_fund_plan(amount, goal)

    def _suggest_rescue_amount(
        self,
        checking: dict[str, Any],
        emergency: dict[str, Any],
        financial_rules: dict[str, Any],
    ) -> float:
        upcoming = abs(
            sum(tx["amount"] for tx in self.banking_store.scheduled_transactions())
        )
        minimum_buffer = float(financial_rules["minimum_cash_buffer_eur"])
        rounding_increment = float(financial_rules["transfer_rounding_increment_eur"])
        stability_margin = cashflow_stability_margin(financial_rules)
        activation_margin = cashflow_activation_margin(financial_rules)
        deficit = upcoming + minimum_buffer - float(checking["available_balance"])
        emergency_balance = float(emergency["balance"])
        if deficit < activation_margin or emergency_balance <= 0:
            return 0.0
        stable_recovery_amount = (
            upcoming
            + minimum_buffer
            + stability_margin
            - float(checking["available_balance"])
        )
        rounded_amount = round_up_to_increment(
            stable_recovery_amount, rounding_increment
        )
        return round(min(rounded_amount, emergency_balance), 2)

    def _suggest_transfer_amount(
        self,
        checking: dict[str, Any],
        emergency: dict[str, Any],
        financial_rules: dict[str, Any],
    ) -> float:
        upcoming = abs(
            sum(tx["amount"] for tx in self.banking_store.scheduled_transactions())
        )
        minimum_buffer = float(financial_rules["minimum_cash_buffer_eur"])
        rounding_increment = float(financial_rules["transfer_rounding_increment_eur"])
        stability_margin = cashflow_stability_margin(financial_rules)
        activation_margin = cashflow_activation_margin(financial_rules)
        stable_cash_floor = upcoming + minimum_buffer + stability_margin
        available_surplus = float(checking["available_balance"]) - stable_cash_floor
        target_gap = max(
            float(emergency.get("target_balance", 0)) - emergency["balance"], 0
        )
        if available_surplus < activation_margin:
            return 0.0
        raw_amount = min(available_surplus, target_gap)
        return max(0.0, round_down_to_increment(raw_amount, rounding_increment))

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
        if plan["action_type"] == "TRANSFER_REVERSE":
            return {
                "route": plan["route"],
                "reason": plan["reason"],
                "required_next_step": plan["required_next_step"],
                "reason_codes": plan["reason_codes"],
            }
        if plan["action_type"] == "TRANSFER":
            return evaluate_action_route(
                amount=planned_amount,
                autonomous_transfer_limit_eur=financial_rules[
                    "autonomous_transfer_limit_eur"
                ],
            )
        return {
            "route": plan["route"],
            "reason": plan["reason"],
            "required_next_step": plan["required_next_step"],
            "reason_codes": plan["reason_codes"],
        }

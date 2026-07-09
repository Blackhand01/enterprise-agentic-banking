"""Builds the complete `/api/state` response for the frontend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from ..intelligence.dashboard_read_model_builder import CustomerDashboardReadModelBuilder
    from ..intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from ..observability.json_audit_trail import JsonAuditTrail
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from intelligence.dashboard_read_model_builder import CustomerDashboardReadModelBuilder
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from observability.json_audit_trail import JsonAuditTrail
    from storage.sqlite_banking_store import SQLiteBankingStore


class DashboardStateResponseBuilder:
    """Assembles customer data, proposal data, policy state and audit state."""

    def __init__(
        self,
        *,
        users_path: Path,
        policy_path: Path,
        banking_store: SQLiteBankingStore,
        emergency_fund_planner: EmergencyFundRecommendationPlanner,
        dashboard_read_models: CustomerDashboardReadModelBuilder,
        audit_trail: JsonAuditTrail,
        user_goal_provider: Callable[[], dict[str, Any]],
        last_event_provider: Callable[[], dict[str, Any] | None],
    ) -> None:
        self.users_path = users_path
        self.policy_path = policy_path
        self.banking_store = banking_store
        self.emergency_fund_planner = emergency_fund_planner
        self.dashboard_read_models = dashboard_read_models
        self.audit_trail = audit_trail
        self.user_goal_provider = user_goal_provider
        self.last_event_provider = last_event_provider

    def build(self) -> dict[str, Any]:
        user = _read_json(self.users_path)[0]
        policies = _read_json(self.policy_path)
        user_goal = self.user_goal_provider()
        proposal = self.emergency_fund_planner.build()
        financial_rules = proposal.get("financial_rules", {})
        user = _with_runtime_risk_thresholds(user, financial_rules)

        return {
            "user": user,
            "user_goal": user_goal,
            "accounts": self.banking_store.accounts(),
            "transactions": self.banking_store.transactions(limit=12),
            "customer_activity": self.banking_store.customer_activity(limit=8),
            "monthly_snapshots": self.banking_store.monthly_snapshots(limit=12),
            "scheduled_transactions": self.banking_store.scheduled_transactions(),
            "proposal": proposal,
            "cashflow_forecast": self.dashboard_read_models.cashflow_forecast(proposal),
            "emergency_goal_projection": self.dashboard_read_models.emergency_goal_projection(
                proposal=proposal,
                goal=user_goal,
            ),
            "agent_inbox": self.dashboard_read_models.agent_inbox(proposal),
            "last_event": self.last_event_provider(),
            "policies": _partition_policies(policies),
            "audit": self.audit_trail.list_events(),
        }


def _partition_policies(policies: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "active": [policy for policy in policies if not policy.get("is_stale")],
        "stale": [policy for policy in policies if policy.get("is_stale")],
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _with_runtime_risk_thresholds(
    user: dict[str, Any],
    financial_rules: dict[str, Any],
) -> dict[str, Any]:
    synced_user = dict(user)
    risk_thresholds = dict(synced_user.get("risk_thresholds", {}))
    if "autonomous_transfer_limit_eur" in financial_rules:
        risk_thresholds["autonomous_transfer_limit_eur"] = financial_rules[
            "autonomous_transfer_limit_eur"
        ]
    synced_user["risk_thresholds"] = risk_thresholds
    return synced_user

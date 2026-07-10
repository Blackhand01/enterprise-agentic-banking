"""Customer dashboard read-model facade."""

from __future__ import annotations
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:
    from storage.sqlite_banking_store import SQLiteBankingStore

try:
    from .cashflow_forecast_read_model import CashflowForecastReadModel
    from .customer_emergency_goal import (
        add_months,
        default_emergency_fund_goal,
        default_user_goal,
        month_label,
    )
    from .emergency_fund_goal_projection_read_model import (
        EmergencyFundGoalProjectionReadModel,
    )
except ImportError:
    from cashflow_forecast_read_model import CashflowForecastReadModel
    from customer_emergency_goal import (
        add_months,
        default_emergency_fund_goal,
        default_user_goal,
        month_label,
    )
    from emergency_fund_goal_projection_read_model import (
        EmergencyFundGoalProjectionReadModel,
    )

__all__ = [
    "CashflowForecastReadModel",
    "CustomerDashboardReadModelBuilder",
    "EmergencyFundGoalProjectionReadModel",
    "add_months",
    "build_agent_inbox_items",
    "default_emergency_fund_goal",
    "default_user_goal",
    "month_label",
]


def build_agent_inbox_items(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    status = "completed" if proposal.get("already_executed") else "pending_approval"
    if proposal["route"] == "BLOCKED":
        status = "blocked"

    return [
        {
            "id": proposal["proposal_id"],
            "title": proposal["title"],
            "summary": proposal["recommended_action"],
            "status": status,
            "route": proposal["route"],
            "required_next_step": proposal["required_next_step"],
            "evidence": {
                "known_expenses_30d": proposal["upcoming_expenses_30d"],
                "projected_checking_balance": proposal["projected_checking_balance"],
                "projected_emergency_balance": proposal["projected_emergency_balance"],
            },
        }
    ]


class CustomerDashboardReadModelBuilder:
    """Builds read-only state slices used by the frontend dashboard."""

    def __init__(self, banking_store: SQLiteBankingStore) -> None:
        self.cashflow = CashflowForecastReadModel(banking_store)
        self.emergency_goal = EmergencyFundGoalProjectionReadModel(banking_store)

    def cashflow_forecast(
        self, proposal: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.cashflow.build(proposal)

    def emergency_goal_projection(
        self,
        *,
        proposal: dict[str, Any],
        goal: dict[str, Any],
    ) -> dict[str, Any]:
        return self.emergency_goal.build(proposal=proposal, goal=goal)

    @staticmethod
    def agent_inbox(proposal: dict[str, Any]) -> list[dict[str, Any]]:
        return build_agent_inbox_items(proposal)

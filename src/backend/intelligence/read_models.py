"""Customer dashboard read-model facade."""

from __future__ import annotations
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:
    from storage.sqlite_banking_store import SQLiteBankingStore

try:
    from .agent_inbox_read_model import build_agent_inbox_items
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
    from agent_inbox_read_model import build_agent_inbox_items
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

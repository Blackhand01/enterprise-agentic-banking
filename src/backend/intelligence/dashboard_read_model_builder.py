"""Facade for customer-facing dashboard read models."""

from __future__ import annotations

from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from storage.sqlite_banking_store import SQLiteBankingStore

from .agent_inbox_read_model import build_agent_inbox_items
from .cashflow_forecast_read_model import CashflowForecastReadModel
from .emergency_fund_goal_projection_read_model import EmergencyFundGoalProjectionReadModel


class CustomerDashboardReadModelBuilder:
    """Builds read-only state slices used by the frontend dashboard."""

    def __init__(self, banking_store: SQLiteBankingStore) -> None:
        self.cashflow = CashflowForecastReadModel(banking_store)
        self.emergency_goal = EmergencyFundGoalProjectionReadModel(banking_store)

    def cashflow_forecast(self, proposal: dict[str, Any] | None = None) -> dict[str, Any]:
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

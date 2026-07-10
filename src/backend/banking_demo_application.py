"""Application facade for the banking demo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .agentic_system.tools import BankingToolExecutor
    from .application.services import (
        CustomerChatService,
        CustomerTransferApprovalWorkflow,
        DashboardStateResponseBuilder,
        JsonAuditTrail,
        iso_now,
        load_local_env_file,
        new_trace_id,
    )
    from .intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from .intelligence.read_models import (
        CustomerDashboardReadModelBuilder,
        default_user_goal,
    )
    from .storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from agentic_system.tools import BankingToolExecutor
    from application.services import (
        CustomerChatService,
        CustomerTransferApprovalWorkflow,
        DashboardStateResponseBuilder,
        JsonAuditTrail,
        iso_now,
        load_local_env_file,
        new_trace_id,
    )
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from intelligence.read_models import (
        CustomerDashboardReadModelBuilder,
        default_user_goal,
    )
    from storage.sqlite_banking_store import SQLiteBankingStore


class BankingDemoApplication:
    """Coordinates API use cases for the banking demo prototype."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.ledger_path = self.data_dir / "ledger.json"
        self.db_path = self.data_dir / "banking.db"
        self.users_path = self.data_dir / "users.json"
        self.policy_path = self.data_dir / "policyDB.json"
        self.audit_path = self.data_dir / "audit_log.json"

        load_local_env_file(self.data_dir.parents[1] / ".env")
        self.user_goal = default_user_goal()
        self._last_event: dict[str, Any] | None = None

        self.banking_store = SQLiteBankingStore(self.db_path, self.ledger_path)
        self.repository = self.banking_store
        self.tool_executor = BankingToolExecutor(self.db_path, self.ledger_path)
        self.audit_trail = JsonAuditTrail(self.audit_path)
        self.audit_log = self.audit_trail

        self.emergency_fund_planner = EmergencyFundRecommendationPlanner(
            self.banking_store,
            new_trace_id,
            goal_provider=lambda: self.user_goal,
        )
        self.proposals = self.emergency_fund_planner
        self.dashboard_read_models = CustomerDashboardReadModelBuilder(
            self.banking_store
        )
        self.read_models = self.dashboard_read_models

        self.dashboard_state_builder = DashboardStateResponseBuilder(
            users_path=self.users_path,
            policy_path=self.policy_path,
            banking_store=self.banking_store,
            emergency_fund_planner=self.emergency_fund_planner,
            dashboard_read_models=self.dashboard_read_models,
            audit_trail=self.audit_trail,
            user_goal_provider=lambda: self.user_goal,
            last_event_provider=lambda: self._last_event,
        )
        self.transfer_workflow = CustomerTransferApprovalWorkflow(
            proposal_builder=self.emergency_fund_planner,
            tool_executor=self.tool_executor,
            audit_log=self.audit_trail,
            trace_id_factory=new_trace_id,
            now_factory=iso_now,
        )
        self.chat_service = CustomerChatService(
            policy_db_path=self.policy_path,
            db_path=self.db_path,
            ledger_seed_path=self.ledger_path,
        )

    @property
    def _banking_agent(self) -> Any:
        return self.chat_service._banking_agent

    @_banking_agent.setter
    def _banking_agent(self, agent: Any) -> None:
        self.chat_service._banking_agent = agent

    def dashboard_state(self) -> dict[str, Any]:
        return self.dashboard_state_builder.build()

    def build_liquidity_proposal(self, amount: float | None = None) -> dict[str, Any]:
        return self.emergency_fund_planner.build(amount)

    def build_current_proposal(self) -> dict[str, Any]:
        return self.emergency_fund_planner.build()

    def preview_transfer(self, amount: float) -> dict[str, Any]:
        return self.emergency_fund_planner.preview_transfer(amount)

    def update_financial_rules(
        self,
        *,
        autonomous_transfer_limit_eur: float | None = None,
        minimum_cash_buffer_eur: float | None = None,
        surplus_investment_ratio: float | None = None,
        transfer_rounding_increment_eur: float | None = None,
    ) -> dict[str, Any]:
        return self.banking_store.update_financial_rule_config(
            autonomous_transfer_limit_eur=autonomous_transfer_limit_eur,
            minimum_cash_buffer_eur=minimum_cash_buffer_eur,
            surplus_investment_ratio=surplus_investment_ratio,
            transfer_rounding_increment_eur=transfer_rounding_increment_eur,
        )

    def submit_transfer(
        self,
        amount: float,
        action_type: str | None = None,
    ) -> dict[str, Any]:
        return self.transfer_workflow.submit_transfer(amount, action_type=action_type)

    def cashflow_forecast(
        self, proposal: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.dashboard_read_models.cashflow_forecast(proposal)

    def agent_inbox(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        return self.dashboard_read_models.agent_inbox(proposal)

    def inject_sandbox_state(
        self,
        *,
        checking_balance: float,
        emergency_balance: float,
        upcoming_expenses: float,
    ) -> dict[str, Any]:
        result = self.banking_store.inject_sandbox_state(
            checking_balance=checking_balance,
            emergency_balance=emergency_balance,
            upcoming_expenses=upcoming_expenses,
        )
        self._last_event = None
        self.chat_service.reset_agent()
        return {
            "status": result["status"],
            "mutation": result,
            "state": self.dashboard_state(),
        }

    def chat(self, message: str) -> dict[str, Any]:
        return self.chat_service.chat(message)

    def list_audit_events(self) -> list[dict[str, Any]]:
        return self.audit_trail.list_events()

    def reset_audit(self) -> None:
        self.audit_trail.reset()

    def reset_data(self) -> None:
        self.banking_store.reset_from_seed()
        self.chat_service.reset_agent()
        self._last_event = None
        self.user_goal = default_user_goal()

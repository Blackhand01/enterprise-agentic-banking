"""Customer-facing application services."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

try:
    from ..agentic_system.agent import BankingAgent
    from ..intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from ..intelligence.read_models import CustomerDashboardReadModelBuilder
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:
    from agentic_system.agent import BankingAgent
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from intelligence.read_models import CustomerDashboardReadModelBuilder
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
        audit_trail: Any,
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


def _partition_policies(
    policies: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
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


class CustomerChatService:
    """Creates the banking agent lazily and formats API chat responses."""

    def __init__(
        self,
        *,
        policy_db_path: Path,
        db_path: Path,
        ledger_seed_path: Path,
    ) -> None:
        self.policy_db_path = policy_db_path
        self.db_path = db_path
        self.ledger_seed_path = ledger_seed_path
        self._banking_agent: BankingAgent | None = None
        self._lock = threading.Lock()

    def chat(self, message: str) -> dict[str, Any]:
        with self._lock:
            return self._chat_locked(message)

    def _chat_locked(self, message: str) -> dict[str, Any]:
        try:
            agent = self._agent()
            last_tool_call_id = latest_tool_call_id(agent.history)
            answer = agent.chat(message)
        except RuntimeError as exc:
            return {
                "answer": _assistant_unavailable_message(str(exc)),
                "tool_result": {
                    "status": "AI_ASSISTANT_UNAVAILABLE",
                    "reason": str(exc),
                },
            }
        tool_result = latest_tool_result_after(agent.history, last_tool_call_id)
        return {
            "answer": customer_safe_answer_for_tool_result(answer, tool_result),
            "tool_result": tool_result,
            "history": agent.history,
        }

    def reset_agent(self) -> None:
        self._banking_agent = None

    def _agent(self) -> BankingAgent:
        if self._banking_agent is None:
            self._banking_agent = BankingAgent(
                policy_db_path=self.policy_db_path,
                db_path=self.db_path,
                ledger_seed_path=self.ledger_seed_path,
            )
        return self._banking_agent


def latest_tool_result(history: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(history):
        if message.get("role") != "tool":
            continue
        try:
            parsed = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            return {"status": "INVALID_TOOL_RESULT"}
        return parsed if isinstance(parsed, dict) else {"status": "INVALID_TOOL_RESULT"}
    return {"status": "NO_TOOL_CALL"}


def latest_tool_call_id(history: list[dict[str, Any]]) -> str | None:
    for message in reversed(history):
        if message.get("role") != "tool":
            continue
        tool_call_id = message.get("tool_call_id")
        return tool_call_id if isinstance(tool_call_id, str) else None
    return None


def latest_tool_result_after(
    history: list[dict[str, Any]],
    previous_tool_call_id: str | None,
) -> dict[str, Any]:
    for message in reversed(history):
        if message.get("role") != "tool":
            continue
        if (
            previous_tool_call_id
            and message.get("tool_call_id") == previous_tool_call_id
        ):
            break
        try:
            parsed = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            return {"status": "INVALID_TOOL_RESULT"}
        return parsed if isinstance(parsed, dict) else {"status": "INVALID_TOOL_RESULT"}
    return {"status": "NO_TOOL_CALL"}


def customer_safe_answer_for_tool_result(
    answer: str,
    tool_result: dict[str, Any],
) -> str:
    if tool_result.get("status") != "NO_DATA":
        return answer
    return "I found no transactions in your current profile for this request."


def _assistant_unavailable_message(reason: str) -> str:
    lowered = reason.lower()
    if "invalid_api_key" in lowered or "invalid api key" in lowered or "401" in lowered:
        return (
            "AI assistant unavailable: the configured LLM key is invalid. "
            "Check LLM_PROVIDER and the related API key in .env, then restart the server."
        )
    if "rate_limit" in lowered or "rate limit" in lowered or "429" in lowered:
        return (
            "AI assistant temporarily unavailable: the LLM provider usage limit was reached. "
            "Try again in a few minutes or use a key with available quota."
        )
    if "API_KEY" in reason or "LLM_PROVIDER" in reason or "LLM_BASE_URL" in reason:
        return (
            "AI assistant unavailable in this environment. "
            "Configure an LLM provider in .env to enable agentic chat with tool calling."
        )
    if "sentence-transformers" in reason:
        return (
            "AI assistant unavailable: the local embedding engine is missing. "
            "Run python3 -m pip install -r requirements.txt and restart the server."
        )
    return (
        "AI assistant temporarily unavailable. "
        "Check the technical detail in the inspection panel."
    )

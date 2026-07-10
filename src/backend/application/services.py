"""Application services, audit trail, and runtime helpers."""

from __future__ import annotations
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

try:
    from ..agentic_system.tools import BankingToolExecutor
    from ..intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
except ImportError:
    from agentic_system.tools import BankingToolExecutor
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )

try:
    from .customer_services import (
        CustomerChatService,
        DashboardStateResponseBuilder,
        _assistant_unavailable_message,
    )
except ImportError:
    from customer_services import (
        CustomerChatService,
        DashboardStateResponseBuilder,
        _assistant_unavailable_message,
    )

__all__ = [
    "CustomerChatService",
    "CustomerTransferApprovalWorkflow",
    "DashboardStateResponseBuilder",
    "JsonAuditTrail",
    "_assistant_unavailable_message",
    "audit_metrics",
    "iso_now",
    "load_local_env_file",
    "new_trace_id",
]

SUCCESSFUL_TOOL_STATUSES = {
    "EXECUTED",
    "BLOCKED",
    "DUPLICATE",
    "EVENT_PROCESSED",
    "RECORDED",
}


def audit_metrics(
    *,
    latency_ms: int,
    tool_calls: int,
    tool_result_status: str,
    trace_id: str,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "latency_ms": latency_ms,
        "tokens_estimated": 0,
        "tool_calls": tool_calls,
        "tool_failures": 0 if tool_result_status in SUCCESSFUL_TOOL_STATUSES else 1,
        "timed_out": False,
    }


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class JsonAuditTrail:
    """Persists lightweight audit traces in a local JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def list_events(self, limit: int = 10) -> list[dict[str, Any]]:
        events = self._read()
        return list(reversed(events[-limit:]))

    def append(self, trace: dict[str, Any]) -> None:
        events = self._read()
        events.append(trace)
        self._write(events)

    def reset(self) -> None:
        self._write([])

    def _read(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: list[dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


class CustomerTransferApprovalWorkflow:
    """Executes a transfer only after customer approval and guardrail routing."""

    def __init__(
        self,
        *,
        proposal_builder: EmergencyFundRecommendationPlanner,
        tool_executor: BankingToolExecutor,
        audit_log: JsonAuditTrail,
        trace_id_factory: Callable[[], str],
        now_factory: Callable[[], str],
    ) -> None:
        self.proposal_builder = proposal_builder
        self.tool_executor = tool_executor
        self.audit_log = audit_log
        self.trace_id_factory = trace_id_factory
        self.now_factory = now_factory

    def submit_transfer(
        self,
        amount: float,
        action_type: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        trace_id = self.trace_id_factory()
        proposal = self.proposal_builder.build(amount)
        tool_result = self._execute_or_block(amount, trace_id, proposal, action_type)
        trace = self._trace(
            trace_id=trace_id,
            amount=amount,
            proposal=proposal,
            tool_result=tool_result,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
        self.audit_log.append(trace)
        return trace

    def _execute_or_block(
        self,
        amount: float,
        trace_id: str,
        proposal: dict[str, Any],
        requested_action_type: str | None,
    ) -> dict[str, Any]:
        blocked_result = _blocked_approval_result(proposal, requested_action_type)
        if blocked_result is not None:
            return blocked_result
        return self._execute_approved_transfer(amount, trace_id, proposal)

    def _execute_approved_transfer(
        self,
        amount: float,
        trace_id: str,
        proposal: dict[str, Any],
    ) -> dict[str, Any]:
        if proposal.get("action_type") == "TRANSFER_REVERSE":
            return self.tool_executor.repository.execute_internal_transfer(
                trace_id=trace_id,
                operation_id=proposal["proposal_id"],
                source_name="Emergency_Fund",
                target_name="Checking",
                amount=amount,
            )
        return json.loads(
            self.tool_executor.execute_transfer(
                recipient="Emergency_Fund",
                amount=amount,
                trace_id=trace_id,
                operation_id=proposal["proposal_id"],
            )
        )

    def _trace(
        self,
        *,
        trace_id: str,
        amount: float,
        proposal: dict[str, Any],
        tool_result: dict[str, Any],
        latency_ms: int,
    ) -> dict[str, Any]:
        return {
            "trace_id": trace_id,
            "timestamp": self.now_factory(),
            "layer_events": _approval_trace_events(amount, proposal, tool_result),
            "proposal": proposal,
            "tool_result": tool_result,
            "metrics": audit_metrics(
                latency_ms=latency_ms,
                tool_calls=1,
                tool_result_status=tool_result["status"],
                trace_id=trace_id,
            ),
        }


def _blocked_approval_result(
    proposal: dict[str, Any],
    requested_action_type: str | None,
) -> dict[str, Any] | None:
    action_type = proposal.get("action_type")
    if action_type not in {"TRANSFER", "TRANSFER_REVERSE"}:
        return {
            "status": "BLOCKED",
            "reason": "ACTION_NOT_EXECUTABLE",
            "action_required": proposal["required_next_step"],
        }
    if requested_action_type is not None and requested_action_type != action_type:
        return {
            "status": "BLOCKED",
            "reason": "ACTION_TYPE_MISMATCH",
            "action_required": "REFRESH_PROPOSAL",
            "requested_action_type": requested_action_type,
            "current_action_type": action_type,
        }
    if proposal["route"] == "BLOCKED":
        return {
            "status": "BLOCKED",
            "reason": "KNOWN_EXPENSES_NOT_COVERED",
            "action_required": proposal["required_next_step"],
        }
    if proposal["route"] == "INVALID_INPUT":
        return {
            "status": "ERROR",
            "reason": "INVALID_INPUT",
            "action_required": proposal["required_next_step"],
        }
    return None


def _approval_trace_events(
    amount: float,
    proposal: dict[str, Any],
    tool_result: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "layer": "App customer",
            "event": f"Il customer ha approvato EUR {amount:.2f}",
        },
        {"layer": "Agent AI", "event": f"proposta: {proposal['title']}"},
        {"layer": "Contesto bancario", "event": "contesto letto da SQLite"},
        {
            "layer": "Idempotency",
            "event": f"operation_id: {proposal['proposal_id']}",
        },
        {
            "layer": "Safety and approval",
            "event": f"route: {proposal['route']}",
        },
        {
            "layer": "Banking action gateway",
            "event": f"tool result: {tool_result['status']}",
        },
        {"layer": "Audit log", "event": "event persisted"},
    ]


def load_local_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def new_trace_id() -> str:
    return f"trc_{int(time.time() * 1000):x}"

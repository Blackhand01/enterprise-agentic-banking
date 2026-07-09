"""Customer-approved transfer execution workflow."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

try:
    from ..agentic_system.tools import BankingToolExecutor
    from ..intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from ..observability.json_audit_trail import JsonAuditTrail
except ImportError:  # Allows direct script-style imports during prototyping.
    from agentic_system.tools import BankingToolExecutor
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from observability.json_audit_trail import JsonAuditTrail

from .audit_trace_metrics import audit_metrics


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

    def submit_transfer(self, amount: float) -> dict[str, Any]:
        started = time.perf_counter()
        trace_id = self.trace_id_factory()
        proposal = self.proposal_builder.build(amount)
        tool_result = self._execute_or_block(amount, trace_id, proposal)
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
    ) -> dict[str, Any]:
        if proposal.get("action_type") != "TRANSFER":
            return {
                "status": "BLOCKED",
                "reason": "ACTION_NOT_EXECUTABLE",
                "action_required": proposal["required_next_step"],
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
            "layer_events": [
                {"layer": "App cliente", "event": f"Il cliente ha approvato EUR {amount:.2f}"},
                {"layer": "Agente AI", "event": f"proposta: {proposal['title']}"},
                {"layer": "Contesto bancario", "event": "contesto letto da SQLite"},
                {"layer": "Idempotenza", "event": f"operation_id: {proposal['proposal_id']}"},
                {"layer": "Sicurezza e approvazione", "event": f"percorso: {proposal['route']}"},
                {"layer": "Gateway azioni bancarie", "event": f"risultato tool: {tool_result['status']}"},
                {"layer": "Audit log", "event": "evento persistito"},
            ],
            "proposal": proposal,
            "tool_result": tool_result,
            "metrics": audit_metrics(
                latency_ms=latency_ms,
                tool_calls=1,
                tool_result_status=tool_result["status"],
                trace_id=trace_id,
            ),
        }

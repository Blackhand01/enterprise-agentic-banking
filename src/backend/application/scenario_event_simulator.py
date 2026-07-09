"""Scenario-trigger simulator used to demonstrate proactive replanning."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

try:
    from ..intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from ..observability.json_audit_trail import JsonAuditTrail
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from intelligence.emergency_fund_recommendation_planner import (
        EmergencyFundRecommendationPlanner,
    )
    from observability.json_audit_trail import JsonAuditTrail
    from storage.sqlite_banking_store import SQLiteBankingStore

from .audit_trace_metrics import audit_metrics


class ScenarioEventSimulator:
    """Processes controlled business scenarios and records audit traces."""

    def __init__(
        self,
        *,
        banking_store: SQLiteBankingStore,
        proposal_builder: EmergencyFundRecommendationPlanner,
        audit_log: JsonAuditTrail,
        trace_id_factory: Callable[[], str],
        now_factory: Callable[[], str],
    ) -> None:
        self.banking_store = banking_store
        self.proposal_builder = proposal_builder
        self.audit_log = audit_log
        self.trace_id_factory = trace_id_factory
        self.now_factory = now_factory

    def simulate_event(self, scenario: str) -> dict[str, Any]:
        trace_id = self.trace_id_factory()
        normalized = scenario.strip().lower()
        result = self._process_scenario(normalized, trace_id)
        trace = self._trace(trace_id=trace_id, scenario=normalized, result=result)
        self.audit_log.append(trace)
        return trace

    def _process_scenario(self, scenario: str, trace_id: str) -> dict[str, Any]:
        if scenario == "salary_arrival":
            return self._record_salary_arrival(trace_id, scenario)
        if scenario == "high_unexpected_expense":
            return self._record_high_expense(trace_id, scenario)
        if scenario == "unused_subscription":
            return {
                "status": "EVENT_PROCESSED",
                "scenario": scenario,
                "title": "Abbonamento inutilizzato",
                "summary": (
                    "Scenario di prodotto: l'agente segnala un costo ricorrente da far "
                    "confermare al cliente prima di una disdetta."
                ),
                "merchant": "CloudStorage Premium",
                "amount": 12.99,
                "route": "APPROVAL_REQUIRED",
            }
        return {"status": "ERROR", "reason": "UNKNOWN_SCENARIO", "scenario": scenario}

    def _record_salary_arrival(self, trace_id: str, scenario: str) -> dict[str, Any]:
        result = self.banking_store.record_external_income(
            trace_id=trace_id,
            operation_id=f"event_{scenario}_{date.today().isoformat()}",
            account_name="Checking",
            merchant="Tata Innovation Hub Payroll",
            amount=3200.0,
            category="stipendio",
            display_name="Stipendio Tata Innovation Hub",
        )
        result.update(
            {
                "scenario": scenario,
                "title": (
                    "Stipendio gia elaborato"
                    if result["status"] == "DUPLICATE"
                    else "Stipendio accreditato"
                ),
                "summary": (
                    "Questo scenario era gia stato applicato: nessun nuovo accredito e stato creato."
                    if result["status"] == "DUPLICATE"
                    else (
                        "Lo stipendio e stato registrato nel ledger SQLite. L'agente rivaluta "
                        "liquidita inattiva, spese note e obiettivo fondo emergenze."
                    )
                ),
            }
        )
        return result

    def _record_high_expense(self, trace_id: str, scenario: str) -> dict[str, Any]:
        result = self.banking_store.record_external_expense(
            trace_id=trace_id,
            operation_id=f"event_{scenario}_{date.today().isoformat()}",
            account_name="Checking",
            merchant="Riparazione auto imprevista",
            amount=1200.0,
            category="imprevisti",
            display_name="Spesa imprevista alta",
        )
        result.update(
            {
                "scenario": scenario,
                "title": (
                    "Spesa imprevista alta gia elaborata"
                    if result["status"] == "DUPLICATE"
                    else "Spesa imprevista alta"
                ),
                "summary": (
                    "Questo scenario era gia stato applicato: nessun nuovo movimento e stato creato."
                    if result["status"] == "DUPLICATE"
                    else (
                        "La spesa e stata registrata nel ledger. L'agente deve rivalutare "
                        "il cashflow prima di proporre nuove azioni."
                    )
                ),
            }
        )
        return result

    def _trace(
        self,
        *,
        trace_id: str,
        scenario: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "trace_id": trace_id,
            "timestamp": self.now_factory(),
            "layer_events": [
                {"layer": "Motore eventi", "event": f"scenario: {scenario}"},
                {"layer": "Ledger SQLite", "event": f"risultato: {result['status']}"},
                {"layer": "Agente AI", "event": "inbox e proposta rivalutate dal nuovo contesto"},
                {"layer": "Audit log", "event": "evento persistito"},
            ],
            "proposal": self.proposal_builder.build(),
            "tool_result": result,
            "metrics": audit_metrics(
                latency_ms=0,
                tool_calls=0,
                tool_result_status=result["status"],
                trace_id=trace_id,
            ),
        }

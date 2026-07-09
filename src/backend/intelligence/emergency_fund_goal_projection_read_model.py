"""Emergency-fund goal projection read model."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
    from storage.sqlite_banking_store import SQLiteBankingStore

from .month_labels import add_months, month_label


class EmergencyFundGoalProjectionReadModel:
    """Calculates progress, required savings pace and timeline labels."""

    def __init__(self, banking_store: SQLiteBankingStore) -> None:
        self.banking_store = banking_store

    def build(self, *, proposal: dict[str, Any], goal: dict[str, Any]) -> dict[str, Any]:
        emergency = self.banking_store.account_by_name("Emergency_Fund")
        snapshots = self.banking_store.monthly_snapshots(limit=12)
        today = date.today()
        target_balance = float(emergency.get("target_balance", 10000.0))
        current_balance = float(emergency["balance"])
        target_months = int(goal.get("target_months", 18))
        target_date = add_months(today, target_months)
        current_gap = max(target_balance - current_balance, 0.0)
        historical_monthly = _average_monthly_savings(snapshots)
        historical_months = _months_to_target(current_gap, historical_monthly)
        action_amount = _proposal_transfer_amount(proposal)
        balance_after_action = min(target_balance, current_balance + action_amount)
        gap_after_action = max(target_balance - balance_after_action, 0.0)
        required_monthly = _safe_monthly(current_gap, target_months)
        required_after_action = _safe_monthly(gap_after_action, target_months)
        revised_target_date = _revised_target_date(target_date, proposal)
        is_behind_plan = _is_behind_plan(
            historical_monthly=historical_monthly,
            required_monthly=required_monthly,
            historical_eta_months=historical_months,
            target_months=target_months,
        )

        return {
            "goal_name": "Fondo emergenze",
            "target_balance": target_balance,
            "current_balance": current_balance,
            "balance_after_agent_action": balance_after_action,
            "current_progress": round((current_balance / target_balance) * 100),
            "projected_progress": round((balance_after_action / target_balance) * 100),
            "gap": round(current_gap, 2),
            "gap_after_agent_action": round(gap_after_action, 2),
            "target_months": target_months,
            "target_date": target_date.isoformat(),
            "target_label": month_label(target_date),
            "historical_monthly_savings": historical_monthly,
            "historical_eta_months": historical_months,
            "historical_eta_label": _historical_eta_label(today, historical_months),
            "required_monthly_savings": required_monthly,
            "required_monthly_after_agent_action": required_after_action,
            "monthly_savings_gap": round(max(required_monthly - historical_monthly, 0.0), 2),
            "is_behind_plan": is_behind_plan,
            "status_summary": _status_summary(
                is_behind_plan=is_behind_plan,
                historical_monthly=historical_monthly,
                required_monthly=required_monthly,
                required_after_action=required_after_action,
                target_label=month_label(target_date),
                proposal=proposal,
            ),
            "agent_timeline_label": month_label(revised_target_date),
            "agent_timeline_note": _timeline_note(proposal),
            "agent_action_amount": action_amount,
        }


def _proposal_transfer_amount(proposal: dict[str, Any]) -> float:
    if proposal.get("already_executed"):
        return 0.0
    if proposal.get("action_type") == "TRANSFER":
        return float(proposal["amount"])
    return 0.0


def _average_monthly_savings(snapshots: list[dict[str, Any]]) -> float:
    if not snapshots:
        return 0.0
    values = [max(float(snapshot.get("savings_transfer_eur", 0.0)), 0.0) for snapshot in snapshots]
    return round(sum(values) / len(values), 2)


def _months_to_target(gap: float, monthly_savings: float) -> int | None:
    if gap <= 0:
        return 0
    if monthly_savings <= 0:
        return None
    return int(math.ceil(gap / monthly_savings))


def _safe_monthly(gap: float, months: int) -> float:
    if months <= 0:
        return round(gap, 2)
    return round(gap / months, 2)


def _is_behind_plan(
    *,
    historical_monthly: float,
    required_monthly: float,
    historical_eta_months: int | None,
    target_months: int,
) -> bool:
    if required_monthly <= 0:
        return False
    if historical_eta_months is None:
        return True
    return historical_monthly < required_monthly or historical_eta_months > target_months


def _status_summary(
    *,
    is_behind_plan: bool,
    historical_monthly: float,
    required_monthly: float,
    required_after_action: float,
    target_label: str,
    proposal: dict[str, Any],
) -> str:
    if is_behind_plan:
        prefix = (
            f"Al ritmo storico stai accantonando {historical_monthly:.2f} EUR/mese, "
            f"ma per arrivare entro {target_label} servono {required_monthly:.2f} EUR/mese."
        )
    else:
        prefix = (
            f"Il ritmo storico di {historical_monthly:.2f} EUR/mese copre il piano "
            f"richiesto di {required_monthly:.2f} EUR/mese."
        )

    if proposal.get("action_type") == "TRANSFER" and float(proposal.get("amount", 0.0)) > 0:
        return (
            f"{prefix} Se approvi l'azione proposta, il contributo mensile ancora "
            f"necessario scende a {required_after_action:.2f} EUR/mese."
        )
    return prefix


def _revised_target_date(target_date: date, proposal: dict[str, Any]) -> date:
    reason_codes = proposal.get("reason_codes", [])
    if "unexpected_expense_detected" in reason_codes:
        return add_months(target_date, 1)
    return target_date


def _timeline_note(proposal: dict[str, Any]) -> str:
    reason_codes = proposal.get("reason_codes", [])
    if proposal.get("action_type") == "TRANSFER":
        return "Approvando l'azione, il contributo mensile richiesto diminuisce."
    if "unexpected_expense_detected" in reason_codes:
        return "Dopo l'imprevisto l'agente mette in pausa il trasferimento e sposta la timeline di un mese."
    return "L'agente preserva liquidita e richiede revisione prima di muovere fondi."


def _historical_eta_label(today: date, historical_months: int | None) -> str:
    if historical_months is None:
        return "Non stimabile"
    return month_label(add_months(today, historical_months))

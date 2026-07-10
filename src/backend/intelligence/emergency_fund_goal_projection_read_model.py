"""Emergency-fund goal projection read model."""

from __future__ import annotations
import math
from datetime import date
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:
    from storage.sqlite_banking_store import SQLiteBankingStore

try:
    from .customer_emergency_goal import add_months, month_label
except ImportError:
    from customer_emergency_goal import add_months, month_label


class EmergencyFundGoalProjectionReadModel:
    """Calculates progress, required savings pace and timeline labels."""

    def __init__(self, banking_store: SQLiteBankingStore) -> None:
        self.banking_store = banking_store

    def build(
        self, *, proposal: dict[str, Any], goal: dict[str, Any]
    ) -> dict[str, Any]:
        emergency = self.banking_store.account_by_name("Emergency_Fund")
        snapshots = self.banking_store.monthly_snapshots(limit=12)
        metrics = _emergency_goal_metrics(
            emergency=emergency,
            snapshots=snapshots,
            proposal=proposal,
            goal=goal,
            today=date.today(),
        )
        return _emergency_goal_payload(metrics, proposal)


def _emergency_goal_metrics(
    *,
    emergency: dict[str, Any],
    snapshots: list[dict[str, Any]],
    proposal: dict[str, Any],
    goal: dict[str, Any],
    today: date,
) -> dict[str, Any]:
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
    return {
        "today": today,
        "target_balance": target_balance,
        "current_balance": current_balance,
        "target_months": target_months,
        "target_date": target_date,
        "current_gap": current_gap,
        "historical_monthly": historical_monthly,
        "historical_months": historical_months,
        "action_amount": action_amount,
        "balance_after_action": balance_after_action,
        "gap_after_action": gap_after_action,
        "required_monthly": required_monthly,
        "required_after_action": required_after_action,
        "revised_target_date": _revised_target_date(target_date, proposal),
        "is_behind_plan": _is_behind_plan(
            historical_monthly=historical_monthly,
            required_monthly=required_monthly,
            historical_eta_months=historical_months,
            target_months=target_months,
        ),
    }


def _emergency_goal_payload(
    metrics: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    target_label = month_label(metrics["target_date"])
    return {
        "goal_name": "Fondo emergenze",
        "target_balance": metrics["target_balance"],
        "current_balance": metrics["current_balance"],
        "balance_after_agent_action": metrics["balance_after_action"],
        "current_progress": _progress_percent(
            metrics["current_balance"], metrics["target_balance"]
        ),
        "projected_progress": _progress_percent(
            metrics["balance_after_action"], metrics["target_balance"]
        ),
        "gap": round(metrics["current_gap"], 2),
        "gap_after_agent_action": round(metrics["gap_after_action"], 2),
        "target_months": metrics["target_months"],
        "target_date": metrics["target_date"].isoformat(),
        "target_label": target_label,
        "historical_monthly_savings": metrics["historical_monthly"],
        "historical_eta_months": metrics["historical_months"],
        "historical_eta_label": _historical_eta_label(
            metrics["today"], metrics["historical_months"]
        ),
        "required_monthly_savings": metrics["required_monthly"],
        "required_monthly_after_agent_action": metrics["required_after_action"],
        "monthly_savings_gap": round(
            max(metrics["required_monthly"] - metrics["historical_monthly"], 0.0), 2
        ),
        "is_behind_plan": metrics["is_behind_plan"],
        "status_summary": _status_summary(
            is_behind_plan=metrics["is_behind_plan"],
            historical_monthly=metrics["historical_monthly"],
            required_monthly=metrics["required_monthly"],
            required_after_action=metrics["required_after_action"],
            target_label=target_label,
            proposal=proposal,
        ),
        "agent_timeline_label": month_label(metrics["revised_target_date"]),
        "agent_timeline_note": _timeline_note(proposal),
        "agent_action_amount": metrics["action_amount"],
    }


def _progress_percent(current_balance: float, target_balance: float) -> int:
    return round((current_balance / target_balance) * 100)


def _proposal_transfer_amount(proposal: dict[str, Any]) -> float:
    if proposal.get("already_executed"):
        return 0.0
    if proposal.get("action_type") == "TRANSFER":
        return float(proposal["amount"])
    return 0.0


def _average_monthly_savings(snapshots: list[dict[str, Any]]) -> float:
    if not snapshots:
        return 0.0
    values = [
        max(float(snapshot.get("savings_transfer_eur", 0.0)), 0.0)
        for snapshot in snapshots
    ]
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
    return (
        historical_monthly < required_monthly or historical_eta_months > target_months
    )


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
    if (
        proposal.get("action_type") == "TRANSFER"
        and float(proposal.get("amount", 0.0)) > 0
    ):
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

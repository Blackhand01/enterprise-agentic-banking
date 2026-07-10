"""Cashflow forecast read model."""

from __future__ import annotations
from datetime import date, timedelta
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:
    from storage.sqlite_banking_store import SQLiteBankingStore


class CashflowForecastReadModel:
    """Builds historical and 30-day projected cashflow points."""

    def __init__(self, banking_store: SQLiteBankingStore) -> None:
        self.banking_store = banking_store

    def build(self, proposal: dict[str, Any] | None = None) -> dict[str, Any]:
        checking = self.banking_store.account_by_name("Checking")
        scheduled = self.banking_store.scheduled_transactions()
        snapshots = self.banking_store.monthly_snapshots(limit=12)
        today = date.today()
        action_amount = _proposal_checking_outflow_amount(proposal)
        future_points, known_expenses_total = _future_cashflow_points(
            scheduled=scheduled,
            current_balance=float(checking["available_balance"]),
            action_amount=action_amount,
            today=today,
        )
        return {
            "horizon_days": 30,
            "known_expenses_total": round(known_expenses_total, 2),
            "proposed_action_amount": action_amount,
            "proposed_action_type": proposal.get("action_type") if proposal else None,
            "past_points": _past_cashflow_points(snapshots),
            "future_points": future_points,
        }


def _past_cashflow_points(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": f"{snapshot['month']}-28",
            "label": snapshot["month_label"],
            "balance": snapshot["checking_end_balance_eur"],
            "kind": "storico",
        }
        for snapshot in snapshots
    ]


def _future_cashflow_points(
    *,
    scheduled: list[dict[str, Any]],
    current_balance: float,
    action_amount: float,
    today: date,
) -> tuple[list[dict[str, Any]], float]:
    horizon_end = today + timedelta(days=30)
    running_balance = current_balance
    running_after_action = round(current_balance - action_amount, 2)
    points = [_opening_cashflow_point(today, running_balance, running_after_action)]
    known_expenses_total = 0.0
    for item in scheduled:
        if not _is_within_horizon(item["date"], today, horizon_end):
            continue
        running_balance = round(running_balance + float(item["amount"]), 2)
        running_after_action = round(running_after_action + float(item["amount"]), 2)
        known_expenses_total += abs(float(item["amount"]))
        points.append(
            _scheduled_cashflow_point(item, running_balance, running_after_action)
        )
    return points, known_expenses_total


def _opening_cashflow_point(
    today: date,
    balance: float,
    balance_after_action: float,
) -> dict[str, Any]:
    return {
        "date": today.isoformat(),
        "label": "Oggi",
        "balance": balance,
        "balance_after_action": balance_after_action,
        "kind": "previsione",
        "event": "Available balance attuale",
        "amount": 0.0,
    }


def _scheduled_cashflow_point(
    item: dict[str, Any],
    balance: float,
    balance_after_action: float,
) -> dict[str, Any]:
    return {
        "date": item["date"],
        "label": item["merchant"],
        "balance": balance,
        "balance_after_action": balance_after_action,
        "kind": "previsione",
        "event": f"{item['merchant']} ({item['category']})",
        "amount": item["amount"],
    }


def _is_within_horizon(value: str, start: date, end: date) -> bool:
    item_date = date.fromisoformat(value)
    return start <= item_date <= end


def _proposal_checking_outflow_amount(proposal: dict[str, Any] | None) -> float:
    if proposal and proposal.get("already_executed"):
        return 0.0
    if proposal and proposal.get("action_type") == "TRANSFER":
        return float(proposal.get("amount", 0.0))
    if proposal and proposal.get("action_type") == "TRANSFER_REVERSE":
        return -float(proposal.get("amount", 0.0))
    return 0.0

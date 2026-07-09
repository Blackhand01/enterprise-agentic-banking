"""Cashflow read model for the customer supervisor dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
except ImportError:  # Allows direct script-style imports during prototyping.
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
        horizon_end = today + timedelta(days=30)

        past_points = [
            {
                "date": f"{snapshot['month']}-28",
                "label": snapshot["month_label"],
                "balance": snapshot["checking_end_balance_eur"],
                "kind": "storico",
            }
            for snapshot in snapshots
        ]

        action_amount = _proposal_transfer_amount(proposal)
        running_balance = float(checking["available_balance"])
        running_after_action = round(running_balance - action_amount, 2)
        future_points = [
            {
                "date": today.isoformat(),
                "label": "Oggi",
                "balance": running_balance,
                "balance_after_action": running_after_action,
                "kind": "previsione",
                "event": "Saldo disponibile attuale",
                "amount": 0.0,
            }
        ]

        known_expenses_total = 0.0
        for item in scheduled:
            item_date = date.fromisoformat(item["date"])
            if not today <= item_date <= horizon_end:
                continue
            running_balance = round(running_balance + float(item["amount"]), 2)
            running_after_action = round(running_after_action + float(item["amount"]), 2)
            known_expenses_total += abs(float(item["amount"]))
            future_points.append(
                {
                    "date": item["date"],
                    "label": item["merchant"],
                    "balance": running_balance,
                    "balance_after_action": running_after_action,
                    "kind": "previsione",
                    "event": f"{item['merchant']} ({item['category']})",
                    "amount": item["amount"],
                }
            )

        return {
            "horizon_days": 30,
            "known_expenses_total": round(known_expenses_total, 2),
            "proposed_action_amount": action_amount,
            "past_points": past_points,
            "future_points": future_points,
        }


def _proposal_transfer_amount(proposal: dict[str, Any] | None) -> float:
    if proposal and proposal.get("already_executed"):
        return 0.0
    if proposal and proposal.get("action_type") == "TRANSFER":
        return float(proposal.get("amount", 0.0))
    return 0.0

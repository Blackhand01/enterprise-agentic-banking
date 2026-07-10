"""Read-only SQLite queries for the customer banking context."""

from __future__ import annotations
from typing import Any
from .schema_seed import SQLiteConnectionProvider


class CustomerBankingReadStore:
    """Queries accounts, transactions, schedules and monthly snapshots."""

    def __init__(self, connection_provider: SQLiteConnectionProvider) -> None:
        self.connection_provider = connection_provider

    def accounts(self) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT account_id, user_id, name, type, iban_alias,
                       balance, available_balance, target_balance
                FROM accounts
                ORDER BY CASE name WHEN 'Checking' THEN 0 ELSE 1 END, name
                """
            ).fetchall()
        return [_drop_nulls(dict(row)) for row in rows]

    def balance_summary(self) -> dict[str, Any]:
        accounts = self.accounts()
        normalized_accounts = [
            {
                "name": account["name"],
                "type": account["type"],
                "balance": account["balance"],
                "available_balance": account.get(
                    "available_balance", account["balance"]
                ),
                **(
                    {"target_balance": account["target_balance"]}
                    if "target_balance" in account
                    else {}
                ),
            }
            for account in accounts
        ]
        return {
            "status": "OK",
            "currency": "EUR",
            "accounts": normalized_accounts,
            "total_balance": round(sum(account["balance"] for account in accounts), 2),
            "total_available": round(
                sum(
                    account.get("available_balance", account["balance"])
                    for account in accounts
                ),
                2,
            ),
        }

    def customer_context_summary(self) -> dict[str, Any]:
        return {
            "status": "OK",
            "currency": "EUR",
            "balance_summary": self.balance_summary(),
            "latest_salary": self.latest_salary(),
            "scheduled_transactions": self.scheduled_transactions(),
            "recent_transactions": self.transactions(limit=8),
            "monthly_snapshots": self.monthly_snapshots(limit=12),
        }

    def account_by_name(self, name: str) -> dict[str, Any]:
        with self.connection_provider.connect() as connection:
            row = connection.execute(
                """
                SELECT account_id, user_id, name, type, iban_alias,
                       balance, available_balance, target_balance
                FROM accounts
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Account not found: {name}")
        return _drop_nulls(dict(row))

    def transactions(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, transfer_id, account_id, date, merchant,
                       amount, category, display_name, direction
                FROM transactions
                ORDER BY date DESC, created_at DESC, transaction_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_drop_nulls(dict(row)) for row in rows]

    def transactions_by_category(self, category: str) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, transfer_id, account_id, date, merchant,
                       amount, category, display_name, retrieval_text, direction
                FROM transactions
                WHERE lower(category) = lower(?)
                ORDER BY date DESC, created_at DESC, transaction_id DESC
                """,
                (category,),
            ).fetchall()
        return [_drop_nulls(dict(row)) for row in rows]

    def transactions_for_semantic_search(
        self, limit: int = 200
    ) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, transfer_id, account_id, date, merchant,
                       amount, category, display_name, retrieval_text, direction
                FROM transactions
                WHERE amount < 0
                  AND category != 'risparmio'
                ORDER BY date DESC, created_at DESC, transaction_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_drop_nulls(dict(row)) for row in rows]

    def scheduled_transactions(self) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT scheduled_id, account_id, date, merchant, amount, category
                FROM scheduled_transactions
                ORDER BY date
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def monthly_snapshots(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT month, month_label, income_eur, rent_eur, utilities_eur,
                       groceries_eur, sport_eur, discretionary_eur, savings_transfer_eur,
                       checking_end_balance_eur, emergency_fund_balance_eur
                FROM monthly_snapshots
                ORDER BY month DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def latest_salary(self) -> dict[str, Any] | None:
        with self.connection_provider.connect() as connection:
            row = connection.execute(
                """
                SELECT transaction_id, account_id, date, merchant, amount, category
                FROM transactions
                WHERE category = 'stipendio'
                ORDER BY date DESC, created_at DESC
                LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def customer_activity(self, limit: int = 8) -> list[dict[str, Any]]:
        checking = self.account_by_name("Checking")
        with self.connection_provider.connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, transfer_id, date, merchant, amount,
                       category, display_name, direction
                FROM transactions
                WHERE account_id = ?
                ORDER BY date DESC, created_at DESC, transaction_id DESC
                LIMIT ?
                """,
                (checking["account_id"], limit),
            ).fetchall()
        return [_activity_row(dict(row)) for row in rows]

    def operation_status(self, operation_id: str) -> dict[str, Any] | None:
        with self.connection_provider.connect() as connection:
            row = connection.execute(
                """
                SELECT operation_id, trace_id, status, created_at
                FROM executed_operations
                WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()
        return dict(row) if row else None

    def financial_rule_config(self) -> dict[str, Any]:
        with self.connection_provider.connect() as connection:
            row = connection.execute(
                """
                SELECT profile_id, surplus_investment_ratio, minimum_cash_buffer_eur,
                       autonomous_transfer_limit_eur, transfer_rounding_increment_eur
                FROM financial_rule_config
                WHERE config_id = 'default'
                """
            ).fetchone()
        if row is None:
            raise ValueError("Financial rule configuration not found")
        return dict(row)


def _activity_row(item: dict[str, Any]) -> dict[str, Any]:
    is_internal_saving = (
        item.get("category") == "risparmio"
        and item.get("transfer_id")
        and item.get("direction") == "out"
    )
    return {
        "activity_id": item["transaction_id"],
        "date": item["date"],
        "title": (
            item.get("display_name")
            if is_internal_saving
            else item.get("display_name") or item["merchant"]
        ),
        "subtitle": (
            "Conto corrente -> Fondo emergenze"
            if is_internal_saving
            else item["category"]
        ),
        "amount": item["amount"],
        "category": item["category"],
    }


def _drop_nulls(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}

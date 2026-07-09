"""Load the JSON demo ledger into the SQLite banking store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .sqlite_connection import SQLiteConnectionProvider, now_iso


def is_banking_store_empty(connection_provider: SQLiteConnectionProvider) -> bool:
    with connection_provider.connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()
        return int(row["count"]) == 0


def is_financial_rule_config_missing(connection_provider: SQLiteConnectionProvider) -> bool:
    with connection_provider.connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM financial_rule_config"
        ).fetchone()
        return int(row["count"]) == 0


def reset_banking_store_from_seed(
    connection_provider: SQLiteConnectionProvider,
    seed_path: str | Path,
) -> None:
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    created_at = now_iso()

    with connection_provider.connect() as connection:
        connection.executescript(
            """
            DELETE FROM transactions;
            DELETE FROM scheduled_transactions;
            DELETE FROM monthly_snapshots;
            DELETE FROM executed_operations;
            DELETE FROM financial_rule_config;
            DELETE FROM accounts;
            """
        )
        connection.execute(
            """
            INSERT INTO financial_rule_config (
                config_id, profile_id, surplus_investment_ratio,
                minimum_cash_buffer_eur, autonomous_transfer_limit_eur,
                transfer_rounding_increment_eur
            )
            VALUES (
                'default', :profile_id, :surplus_investment_ratio,
                :minimum_cash_buffer_eur, :autonomous_transfer_limit_eur,
                :transfer_rounding_increment_eur
            )
            """,
            seed["financial_rule_config"],
        )
        connection.executemany(
            """
            INSERT INTO accounts (
                account_id, user_id, name, type, iban_alias,
                balance, available_balance, target_balance
            )
            VALUES (
                :account_id, :user_id, :name, :type, :iban_alias,
                :balance, :available_balance, :target_balance
            )
            """,
            [_account_seed_row(account) for account in seed["accounts"]],
        )
        connection.executemany(
            """
            INSERT INTO transactions (
                transaction_id, transfer_id, account_id, date, merchant,
                amount, category, display_name, direction, created_at
            )
            VALUES (
                :transaction_id, :transfer_id, :account_id, :date, :merchant,
                :amount, :category, :display_name, :direction, :created_at
            )
            """,
            [_transaction_seed_row(tx, created_at) for tx in seed["transactions"]],
        )
        connection.executemany(
            """
            INSERT INTO scheduled_transactions (
                scheduled_id, account_id, date, merchant, amount, category
            )
            VALUES (
                :scheduled_id, :account_id, :date, :merchant, :amount, :category
            )
            """,
            seed.get("scheduled_transactions", []),
        )
        connection.executemany(
            """
            INSERT INTO monthly_snapshots (
                month, month_label, income_eur, rent_eur, utilities_eur,
                groceries_eur, sport_eur, discretionary_eur, savings_transfer_eur,
                checking_end_balance_eur, emergency_fund_balance_eur
            )
            VALUES (
                :month, :month_label, :income_eur, :rent_eur, :utilities_eur,
                :groceries_eur, :sport_eur, :discretionary_eur, :savings_transfer_eur,
                :checking_end_balance_eur, :emergency_fund_balance_eur
            )
            """,
            seed.get("monthly_snapshots", []),
        )


def _account_seed_row(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_id": account["account_id"],
        "user_id": account["user_id"],
        "name": account["name"],
        "type": account["type"],
        "iban_alias": account["iban_alias"],
        "balance": account["balance"],
        "available_balance": account.get("available_balance"),
        "target_balance": account.get("target_balance"),
    }


def _transaction_seed_row(
    transaction: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    return {
        "transaction_id": transaction["transaction_id"],
        "transfer_id": transaction.get("transfer_id"),
        "account_id": transaction["account_id"],
        "date": transaction["date"],
        "merchant": transaction["merchant"],
        "amount": transaction["amount"],
        "category": transaction["category"],
        "display_name": transaction.get("display_name"),
        "direction": transaction.get("direction"),
        "created_at": created_at,
    }

"""SQLite connection, schema and seed loading for the banking store."""

from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


class SQLiteConnectionProvider:
    """Owns database path and transaction-scoped SQLite connections."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


BANKING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    iban_alias TEXT NOT NULL,
    balance REAL NOT NULL,
    available_balance REAL,
    target_balance REAL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    transfer_id TEXT,
    account_id TEXT NOT NULL,
    date TEXT NOT NULL,
    merchant TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    display_name TEXT,
    retrieval_text TEXT,
    direction TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS scheduled_transactions (
    scheduled_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    date TEXT NOT NULL,
    merchant TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS monthly_snapshots (
    month TEXT PRIMARY KEY,
    month_label TEXT NOT NULL,
    income_eur REAL NOT NULL,
    rent_eur REAL NOT NULL,
    utilities_eur REAL NOT NULL,
    groceries_eur REAL NOT NULL,
    sport_eur REAL NOT NULL,
    discretionary_eur REAL NOT NULL,
    savings_transfer_eur REAL NOT NULL,
    checking_end_balance_eur REAL NOT NULL,
    emergency_fund_balance_eur REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS executed_operations (
    operation_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_rule_config (
    config_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    surplus_investment_ratio REAL NOT NULL,
    minimum_cash_buffer_eur REAL NOT NULL,
    autonomous_transfer_limit_eur REAL NOT NULL,
    transfer_rounding_increment_eur REAL NOT NULL
);
"""


def ensure_banking_schema(connection_provider: SQLiteConnectionProvider) -> None:
    with connection_provider.connect() as connection:
        connection.executescript(BANKING_SCHEMA_SQL)
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(transactions)").fetchall()
        }
        if "retrieval_text" not in existing_columns:
            connection.execute(
                "ALTER TABLE transactions ADD COLUMN retrieval_text TEXT"
            )


def is_banking_store_empty(connection_provider: SQLiteConnectionProvider) -> bool:
    with connection_provider.connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()
        return int(row["count"]) == 0


def is_financial_rule_config_missing(
    connection_provider: SQLiteConnectionProvider,
) -> bool:
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
                amount, category, display_name, retrieval_text, direction, created_at
            )
            VALUES (
                :transaction_id, :transfer_id, :account_id, :date, :merchant,
                :amount, :category, :display_name, :retrieval_text, :direction, :created_at
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
        "retrieval_text": transaction.get("retrieval_text"),
        "direction": transaction.get("direction"),
        "created_at": created_at,
    }

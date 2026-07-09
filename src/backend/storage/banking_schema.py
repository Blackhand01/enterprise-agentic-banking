"""SQLite schema for the prototype banking ledger."""

from __future__ import annotations

from .sqlite_connection import SQLiteConnectionProvider


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

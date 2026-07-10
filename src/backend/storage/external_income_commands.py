"""SQLite command for external customer ledger income."""

from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import Any
from .commands import (
    account_for_update,
    duplicate_result,
    operation_status,
    record_executed_operation,
)
from .schema_seed import SQLiteConnectionProvider, now_iso


def record_external_income(
    *,
    connection_provider: SQLiteConnectionProvider,
    trace_id: str,
    operation_id: str | None = None,
    account_name: str,
    merchant: str,
    amount: float,
    category: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    numeric_amount = round(float(amount), 2)
    if numeric_amount <= 0:
        return {
            "status": "ERROR",
            "reason": "NON_POSITIVE_AMOUNT",
            "action_required": "FIX_INPUT",
        }

    created_at = now_iso()
    today = datetime.now().date().isoformat()
    suffix = trace_id.replace("trc_", "")
    transaction_id = f"txn_{today}_{category}_{suffix}"
    stable_operation_id = operation_id or trace_id

    with connection_provider.connect() as connection:
        existing_operation = operation_status(connection, stable_operation_id)
        if existing_operation is not None:
            return duplicate_result(existing_operation, "EVENT_ALREADY_PROCESSED")

        account = account_for_update(connection, account_name)
        _add_external_income(
            connection=connection,
            account_id=account["account_id"],
            transaction_id=transaction_id,
            merchant=merchant,
            amount=numeric_amount,
            category=category,
            display_name=display_name or merchant,
            created_at=created_at,
            today=today,
        )
        record_executed_operation(
            connection=connection,
            operation_id=stable_operation_id,
            trace_id=trace_id,
            status="RECORDED",
            created_at=created_at,
        )

    return {
        "status": "RECORDED",
        "transaction_id": transaction_id,
        "trace_id": trace_id,
        "operation_id": stable_operation_id,
        "merchant": merchant,
        "amount": numeric_amount,
        "currency": "EUR",
        "execution_mode": "SQLITE_COMMITTED",
    }


def _add_external_income(
    *,
    connection: sqlite3.Connection,
    account_id: str,
    transaction_id: str,
    merchant: str,
    amount: float,
    category: str,
    display_name: str,
    created_at: str,
    today: str,
) -> None:
    connection.execute(
        """
        UPDATE accounts
        SET balance = balance + ?, available_balance = available_balance + ?
        WHERE account_id = ?
        """,
        (amount, amount, account_id),
    )
    connection.execute(
        """
        INSERT INTO transactions (
            transaction_id, transfer_id, account_id, date, merchant,
            amount, category, display_name, direction, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction_id,
            None,
            account_id,
            today,
            merchant,
            amount,
            category,
            display_name,
            "in",
            created_at,
        ),
    )
    connection.execute(
        """
        UPDATE monthly_snapshots
        SET checking_end_balance_eur = checking_end_balance_eur + ?,
            income_eur = income_eur + ?
        WHERE month = (
            SELECT month FROM monthly_snapshots ORDER BY month DESC LIMIT 1
        )
        """,
        (amount, amount),
    )

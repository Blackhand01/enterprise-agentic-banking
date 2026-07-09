"""SQLite command that commits an internal transfer between customer accounts."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from .ledger_write_helpers import (
    account_for_update,
    duplicate_result,
    operation_status,
    record_executed_operation,
)
from .sqlite_connection import SQLiteConnectionProvider, now_iso


def execute_internal_transfer(
    *,
    connection_provider: SQLiteConnectionProvider,
    trace_id: str,
    operation_id: str | None = None,
    source_name: str,
    target_name: str,
    amount: float,
) -> dict[str, Any]:
    numeric_amount = round(float(amount), 2)
    created_at = now_iso()
    today = datetime.now().date().isoformat()
    suffix = trace_id.replace("trc_", "")
    stable_operation_id = operation_id or trace_id

    with connection_provider.connect() as connection:
        existing_operation = operation_status(connection, stable_operation_id)
        if existing_operation is not None:
            return duplicate_result(existing_operation, "OPERATION_ALREADY_EXECUTED")

        source = account_for_update(connection, source_name)
        target = account_for_update(connection, target_name)
        if float(source["available_balance"]) < numeric_amount:
            return {
                "status": "BLOCKED",
                "reason": "INSUFFICIENT_FUNDS",
                "action_required": "LOWER_AMOUNT",
            }

        _move_balance_between_accounts(
            connection=connection,
            source_account_id=source["account_id"],
            target_account_id=target["account_id"],
            amount=numeric_amount,
        )
        debit_id, credit_id = _insert_transfer_transactions(
            connection=connection,
            trace_id=trace_id,
            suffix=suffix,
            today=today,
            source_account_id=source["account_id"],
            target_account_id=target["account_id"],
            amount=numeric_amount,
            created_at=created_at,
        )
        record_executed_operation(
            connection=connection,
            operation_id=stable_operation_id,
            trace_id=trace_id,
            status="EXECUTED",
            created_at=created_at,
        )
        _apply_transfer_to_latest_monthly_snapshot(connection, numeric_amount)

    return {
        "status": "EXECUTED",
        "recipient": target_name,
        "amount": numeric_amount,
        "currency": "EUR",
        "execution_mode": "SQLITE_COMMITTED",
        "operation_id": stable_operation_id,
        "transfer_id": trace_id,
        "debit_transaction_id": debit_id,
        "credit_transaction_id": credit_id,
    }


def _move_balance_between_accounts(
    *,
    connection: sqlite3.Connection,
    source_account_id: str,
    target_account_id: str,
    amount: float,
) -> None:
    connection.execute(
        """
        UPDATE accounts
        SET balance = balance - ?, available_balance = available_balance - ?
        WHERE account_id = ?
        """,
        (amount, amount, source_account_id),
    )
    connection.execute(
        """
        UPDATE accounts
        SET balance = balance + ?
        WHERE account_id = ?
        """,
        (amount, target_account_id),
    )


def _insert_transfer_transactions(
    *,
    connection: sqlite3.Connection,
    trace_id: str,
    suffix: str,
    today: str,
    source_account_id: str,
    target_account_id: str,
    amount: float,
    created_at: str,
) -> tuple[str, str]:
    debit_id = f"txn_{today}_agent_savings_out_{suffix}"
    credit_id = f"txn_{today}_agent_savings_in_{suffix}"
    connection.executemany(
        """
        INSERT INTO transactions (
            transaction_id, transfer_id, account_id, date, merchant,
            amount, category, display_name, direction, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                debit_id,
                trace_id,
                source_account_id,
                today,
                "Fondo emergenze",
                -amount,
                "risparmio",
                "Trasferimento al fondo emergenze",
                "out",
                created_at,
            ),
            (
                credit_id,
                trace_id,
                target_account_id,
                today,
                "Conto corrente",
                amount,
                "risparmio",
                "Trasferimento dal conto corrente",
                "in",
                created_at,
            ),
        ],
    )
    return debit_id, credit_id


def _apply_transfer_to_latest_monthly_snapshot(
    connection: sqlite3.Connection,
    amount: float,
) -> None:
    connection.execute(
        """
        UPDATE monthly_snapshots
        SET checking_end_balance_eur = checking_end_balance_eur - ?,
            emergency_fund_balance_eur = emergency_fund_balance_eur + ?,
            savings_transfer_eur = savings_transfer_eur + ?
        WHERE month = (
            SELECT month FROM monthly_snapshots ORDER BY month DESC LIMIT 1
        )
        """,
        (amount, amount, amount),
    )

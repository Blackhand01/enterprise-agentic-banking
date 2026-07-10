"""SQLite command that commits internal transfers between customer accounts."""

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
        if _available_funds(source) < numeric_amount:
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
            source_name=source_name,
            target_name=target_name,
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
        _apply_transfer_to_latest_monthly_snapshot(
            connection,
            source_name=source_name,
            target_name=target_name,
            amount=numeric_amount,
        )
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
        SET balance = balance - ?,
            available_balance = CASE
                WHEN available_balance IS NULL THEN NULL
                ELSE available_balance - ?
            END
        WHERE account_id = ?
        """,
        (amount, amount, source_account_id),
    )
    connection.execute(
        """
        UPDATE accounts
        SET balance = balance + ?,
            available_balance = CASE
                WHEN available_balance IS NULL THEN NULL
                ELSE available_balance + ?
            END
        WHERE account_id = ?
        """,
        (amount, amount, target_account_id),
    )


def _available_funds(account: dict[str, Any]) -> float:
    available_balance = account["available_balance"]
    return (
        float(available_balance)
        if available_balance is not None
        else float(account["balance"])
    )


def _insert_transfer_transactions(
    *,
    connection: sqlite3.Connection,
    trace_id: str,
    suffix: str,
    today: str,
    source_name: str,
    target_name: str,
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
                target_name,
                -amount,
                "risparmio",
                _outgoing_transfer_display_name(target_name),
                "out",
                created_at,
            ),
            (
                credit_id,
                trace_id,
                target_account_id,
                today,
                source_name,
                amount,
                "risparmio",
                _incoming_transfer_display_name(source_name),
                "in",
                created_at,
            ),
        ],
    )
    return debit_id, credit_id


def _outgoing_transfer_display_name(target_name: str) -> str:
    if target_name == "Emergency_Fund":
        return "Trasferimento al fondo emergenze"
    if target_name == "Checking":
        return "Trasferimento al conto corrente"
    return f"Trasferimento verso {target_name}"


def _incoming_transfer_display_name(source_name: str) -> str:
    if source_name == "Emergency_Fund":
        return "Recupero dal fondo emergenze"
    if source_name == "Checking":
        return "Trasferimento dal conto corrente"
    return f"Trasferimento da {source_name}"


def _apply_transfer_to_latest_monthly_snapshot(
    connection: sqlite3.Connection,
    *,
    source_name: str,
    target_name: str,
    amount: float,
) -> None:
    checking_delta = _snapshot_delta("Checking", source_name, target_name, amount)
    emergency_delta = _snapshot_delta(
        "Emergency_Fund", source_name, target_name, amount
    )
    savings_delta = amount if target_name == "Emergency_Fund" else -amount
    connection.execute(
        """
        UPDATE monthly_snapshots
        SET checking_end_balance_eur = checking_end_balance_eur + ?,
            emergency_fund_balance_eur = emergency_fund_balance_eur + ?,
            savings_transfer_eur = savings_transfer_eur + ?
        WHERE month = (
            SELECT month FROM monthly_snapshots ORDER BY month DESC LIMIT 1
        )
        """,
        (checking_delta, emergency_delta, savings_delta),
    )


def _snapshot_delta(
    account_name: str, source_name: str, target_name: str, amount: float
) -> float:
    if account_name == source_name:
        return -amount
    if account_name == target_name:
        return amount
    return 0.0

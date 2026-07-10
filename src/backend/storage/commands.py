"""Shared SQLite write helpers and sandbox state command."""

from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from typing import Any
from .schema_seed import SQLiteConnectionProvider


def operation_status(
    connection: sqlite3.Connection,
    operation_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT operation_id, trace_id, status, created_at
        FROM executed_operations
        WHERE operation_id = ?
        """,
        (operation_id,),
    ).fetchone()


def duplicate_result(operation: sqlite3.Row, reason: str) -> dict[str, Any]:
    return {
        "status": "DUPLICATE",
        "reason": reason,
        "action_required": "NO_ACTION",
        "operation_id": operation["operation_id"],
        "original_trace_id": operation["trace_id"],
        "created_at": operation["created_at"],
    }


def account_for_update(connection: sqlite3.Connection, name: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT account_id, name, balance, available_balance
        FROM accounts
        WHERE name = ?
        """,
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Account not found: {name}")
    return row


def record_executed_operation(
    *,
    connection: sqlite3.Connection,
    operation_id: str,
    trace_id: str,
    status: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO executed_operations (
            operation_id, trace_id, status, created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (operation_id, trace_id, status, created_at),
    )


def inject_sandbox_state(
    *,
    connection_provider: SQLiteConnectionProvider,
    checking_balance: float,
    emergency_balance: float,
    upcoming_expenses: float,
) -> dict[str, Any]:
    """Overwrite dashboard-driving banking state with exact demo values."""

    checking_value = round(float(checking_balance), 2)
    emergency_value = round(float(emergency_balance), 2)
    upcoming_value = round(float(upcoming_expenses), 2)
    if checking_value < 0 or emergency_value < 0 or upcoming_value < 0:
        return {
            "status": "ERROR",
            "reason": "NEGATIVE_SANDBOX_VALUE",
            "action_required": "FIX_INPUT",
        }

    scheduled_date = (date.today() + timedelta(days=7)).isoformat()
    with connection_provider.connect() as connection:
        checking = account_for_update(connection, "Checking")
        emergency = account_for_update(connection, "Emergency_Fund")

        connection.execute(
            """
            UPDATE accounts
            SET balance = ?, available_balance = ?
            WHERE account_id = ?
            """,
            (checking_value, checking_value, checking["account_id"]),
        )
        connection.execute(
            """
            UPDATE accounts
            SET balance = ?
            WHERE account_id = ?
            """,
            (emergency_value, emergency["account_id"]),
        )

        connection.execute("DELETE FROM scheduled_transactions")
        if upcoming_value > 0:
            connection.execute(
                """
                INSERT INTO scheduled_transactions (
                    scheduled_id, account_id, date, merchant, amount, category
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "sandbox_upcoming_expenses",
                    checking["account_id"],
                    scheduled_date,
                    "Spese note sandbox",
                    -upcoming_value,
                    "sandbox",
                ),
            )

        connection.execute("DELETE FROM executed_operations")
        connection.execute(
            """
            UPDATE monthly_snapshots
            SET checking_end_balance_eur = ?,
                emergency_fund_balance_eur = ?
            WHERE month = (
                SELECT month FROM monthly_snapshots ORDER BY month DESC LIMIT 1
            )
            """,
            (checking_value, emergency_value),
        )

    return {
        "status": "SANDBOX_STATE_INJECTED",
        "checking_balance": checking_value,
        "emergency_balance": emergency_value,
        "upcoming_expenses": upcoming_value,
        "scheduled_date": scheduled_date if upcoming_value > 0 else None,
    }


from .external_expense_commands import record_external_expense  # noqa: E402
from .external_income_commands import record_external_income  # noqa: E402
from .transfer_commands import execute_internal_transfer  # noqa: E402

__all__ = [
    "account_for_update",
    "duplicate_result",
    "execute_internal_transfer",
    "inject_sandbox_state",
    "operation_status",
    "record_executed_operation",
    "record_external_expense",
    "record_external_income",
]

"""Shared helpers for SQLite ledger write commands."""

from __future__ import annotations

import sqlite3
from typing import Any


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

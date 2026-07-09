"""Facade over the SQLite customer banking store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .banking_schema import ensure_banking_schema
from .customer_banking_read_store import CustomerBankingReadStore
from .customer_banking_write_store import CustomerBankingWriteStore
from .seed_ledger_loader import (
    is_banking_store_empty,
    is_financial_rule_config_missing,
    reset_banking_store_from_seed,
)
from .sqlite_connection import SQLiteConnectionProvider


class SQLiteBankingStore:
    """Customer banking system of record used by the prototype."""

    def __init__(self, db_path: str | Path, seed_path: str | Path) -> None:
        self.seed_path = Path(seed_path)
        self.connection_provider = SQLiteConnectionProvider(db_path)
        ensure_banking_schema(self.connection_provider)
        if is_banking_store_empty(self.connection_provider) or is_financial_rule_config_missing(
            self.connection_provider
        ):
            self.reset_from_seed()

        self.read = CustomerBankingReadStore(self.connection_provider)
        self.write = CustomerBankingWriteStore(self.connection_provider)

    def reset_from_seed(self) -> None:
        reset_banking_store_from_seed(self.connection_provider, self.seed_path)

    def accounts(self) -> list[dict[str, Any]]:
        return self.read.accounts()

    def balance_summary(self) -> dict[str, Any]:
        return self.read.balance_summary()

    def customer_context_summary(self) -> dict[str, Any]:
        return self.read.customer_context_summary()

    def account_by_name(self, name: str) -> dict[str, Any]:
        return self.read.account_by_name(name)

    def transactions(self, limit: int = 12) -> list[dict[str, Any]]:
        return self.read.transactions(limit)

    def transactions_by_category(self, category: str) -> list[dict[str, Any]]:
        return self.read.transactions_by_category(category)

    def scheduled_transactions(self) -> list[dict[str, Any]]:
        return self.read.scheduled_transactions()

    def monthly_snapshots(self, limit: int = 12) -> list[dict[str, Any]]:
        return self.read.monthly_snapshots(limit)

    def latest_salary(self) -> dict[str, Any] | None:
        return self.read.latest_salary()

    def customer_activity(self, limit: int = 8) -> list[dict[str, Any]]:
        return self.read.customer_activity(limit)

    def operation_status(self, operation_id: str) -> dict[str, Any] | None:
        return self.read.operation_status(operation_id)

    def financial_rule_config(self) -> dict[str, Any]:
        return self.read.financial_rule_config()

    def update_financial_rule_config(
        self,
        *,
        autonomous_transfer_limit_eur: float | None = None,
        minimum_cash_buffer_eur: float | None = None,
        surplus_investment_ratio: float | None = None,
        transfer_rounding_increment_eur: float | None = None,
    ) -> dict[str, Any]:
        return self.write.update_financial_rule_config(
            autonomous_transfer_limit_eur=autonomous_transfer_limit_eur,
            minimum_cash_buffer_eur=minimum_cash_buffer_eur,
            surplus_investment_ratio=surplus_investment_ratio,
            transfer_rounding_increment_eur=transfer_rounding_increment_eur,
        )

    def execute_internal_transfer(
        self,
        *,
        trace_id: str,
        operation_id: str | None = None,
        source_name: str,
        target_name: str,
        amount: float,
    ) -> dict[str, Any]:
        return self.write.execute_internal_transfer(
            trace_id=trace_id,
            operation_id=operation_id,
            source_name=source_name,
            target_name=target_name,
            amount=amount,
        )

    def record_external_expense(
        self,
        *,
        trace_id: str,
        operation_id: str | None = None,
        account_name: str,
        merchant: str,
        amount: float,
        category: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        return self.write.record_external_expense(
            trace_id=trace_id,
            operation_id=operation_id,
            account_name=account_name,
            merchant=merchant,
            amount=amount,
            category=category,
            display_name=display_name,
        )

    def record_external_income(
        self,
        *,
        trace_id: str,
        operation_id: str | None = None,
        account_name: str,
        merchant: str,
        amount: float,
        category: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        return self.write.record_external_income(
            trace_id=trace_id,
            operation_id=operation_id,
            account_name=account_name,
            merchant=merchant,
            amount=amount,
            category=category,
            display_name=display_name,
        )

    def inject_sandbox_state(
        self,
        *,
        checking_balance: float,
        emergency_balance: float,
        upcoming_expenses: float,
    ) -> dict[str, Any]:
        return self.write.inject_sandbox_state(
            checking_balance=checking_balance,
            emergency_balance=emergency_balance,
            upcoming_expenses=upcoming_expenses,
        )

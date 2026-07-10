"""Facade for customer banking write commands."""

from __future__ import annotations

from typing import Any

from .commands import (
    execute_internal_transfer,
    inject_sandbox_state,
    record_external_expense,
    record_external_income,
)
from .schema_seed import SQLiteConnectionProvider


class CustomerBankingWriteStore:
    """Delegates ledger mutations to explicit command modules."""

    def __init__(self, connection_provider: SQLiteConnectionProvider) -> None:
        self.connection_provider = connection_provider

    def execute_internal_transfer(
        self,
        *,
        trace_id: str,
        operation_id: str | None = None,
        source_name: str,
        target_name: str,
        amount: float,
    ) -> dict[str, Any]:
        return execute_internal_transfer(
            connection_provider=self.connection_provider,
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
        return record_external_expense(
            connection_provider=self.connection_provider,
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
        return record_external_income(
            connection_provider=self.connection_provider,
            trace_id=trace_id,
            operation_id=operation_id,
            account_name=account_name,
            merchant=merchant,
            amount=amount,
            category=category,
            display_name=display_name,
        )

    def update_financial_rule_config(
        self,
        *,
        autonomous_transfer_limit_eur: float | None = None,
        minimum_cash_buffer_eur: float | None = None,
        surplus_investment_ratio: float | None = None,
        transfer_rounding_increment_eur: float | None = None,
    ) -> dict[str, Any]:
        with self.connection_provider.connect() as connection:
            current = connection.execute(
                """
                SELECT profile_id, surplus_investment_ratio, minimum_cash_buffer_eur,
                       autonomous_transfer_limit_eur, transfer_rounding_increment_eur
                FROM financial_rule_config
                WHERE config_id = 'default'
                """
            ).fetchone()
            if current is None:
                raise ValueError("Financial rule configuration not found")

            updated = dict(current)
            if autonomous_transfer_limit_eur is not None:
                updated["autonomous_transfer_limit_eur"] = float(
                    autonomous_transfer_limit_eur
                )
            if minimum_cash_buffer_eur is not None:
                updated["minimum_cash_buffer_eur"] = float(minimum_cash_buffer_eur)
            if surplus_investment_ratio is not None:
                updated["surplus_investment_ratio"] = float(surplus_investment_ratio)
            if transfer_rounding_increment_eur is not None:
                updated["transfer_rounding_increment_eur"] = float(
                    transfer_rounding_increment_eur
                )

            connection.execute(
                """
                UPDATE financial_rule_config
                SET surplus_investment_ratio = :surplus_investment_ratio,
                    minimum_cash_buffer_eur = :minimum_cash_buffer_eur,
                    autonomous_transfer_limit_eur = :autonomous_transfer_limit_eur,
                    transfer_rounding_increment_eur = :transfer_rounding_increment_eur
                WHERE config_id = 'default'
                """,
                updated,
            )
            return updated

    def inject_sandbox_state(
        self,
        *,
        checking_balance: float,
        emergency_balance: float,
        upcoming_expenses: float,
    ) -> dict[str, Any]:
        return inject_sandbox_state(
            connection_provider=self.connection_provider,
            checking_balance=checking_balance,
            emergency_balance=emergency_balance,
            upcoming_expenses=upcoming_expenses,
        )

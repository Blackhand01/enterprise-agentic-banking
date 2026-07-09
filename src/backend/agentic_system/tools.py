"""Local tool implementations for the banking agent."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

try:
    from ..storage.sqlite_banking_store import SQLiteBankingStore
    from .guardrails import evaluate_transfer_guardrail
    from .schemas import validate_tool_arguments
    from .semantic_transaction_retriever import SemanticTransactionRetriever
except ImportError:  # Allows direct script-style imports during prototyping.
    from guardrails import evaluate_transfer_guardrail
    from schemas import validate_tool_arguments
    from semantic_transaction_retriever import SemanticTransactionRetriever
    from storage.sqlite_banking_store import SQLiteBankingStore


class BankingToolExecutor:
    """Executes local tools after schema validation and deterministic guardrails."""

    def __init__(
        self,
        db_path: str | Path = "banking.db",
        seed_path: str | Path = "ledger.json",
    ) -> None:
        self.repository = SQLiteBankingStore(db_path, seed_path)

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        try:
            validated_args = validate_tool_arguments(tool_name, arguments)
        except Exception as exc:
            return json.dumps(
                {
                    "status": "ERROR",
                    "reason": "INVALID_TOOL_ARGUMENTS",
                    "details": str(exc),
                }
            )

        if tool_name == "fetch_transactions":
            return self.fetch_transactions(
                category=validated_args.category,
                search_query=validated_args.search_query,
            )

        if tool_name == "get_balance_summary":
            return self.get_balance_summary()

        if tool_name == "get_customer_context":
            return self.get_customer_context()

        if tool_name == "execute_transfer":
            return self.execute_transfer(
                recipient=validated_args.recipient,
                amount=validated_args.amount,
                operation_id=validated_args.operation_id,
            )

        return json.dumps({"status": "ERROR", "reason": "UNKNOWN_TOOL", "tool": tool_name})

    def get_balance_summary(self) -> str:
        """Return customer account balances from the SQLite system of record."""

        return json.dumps(self.repository.balance_summary(), ensure_ascii=False)

    def get_customer_context(self) -> str:
        """Return verified customer context for planning and explanation."""

        return json.dumps(self.repository.customer_context_summary(), ensure_ascii=False)

    def fetch_transactions(self, category: str, search_query: str | None = None) -> str:
        """Grounded semantic ledger lookup by transaction category and query intent."""

        normalized_category = category.strip().lower()
        matches = self.repository.transactions_by_category(normalized_category)
        retriever = SemanticTransactionRetriever(matches)
        filtered_matches = retriever.semantic_search(search_query)
        status = "OK" if filtered_matches or not search_query else "NO_DATA"

        return json.dumps(
            {
                "status": status,
                "category": category,
                "search_query": search_query,
                "count": len(filtered_matches),
                "unfiltered_count": len(matches),
                "similarity_threshold": retriever.threshold,
                "transactions": filtered_matches,
            },
            ensure_ascii=False,
        )

    def execute_transfer(
        self,
        recipient: str,
        amount: float,
        trace_id: str | None = None,
        operation_id: str | None = None,
    ) -> str:
        """Execute a committed SQLite transfer behind deterministic guardrails."""

        financial_rules = self.repository.financial_rule_config()
        decision = evaluate_transfer_guardrail(
            recipient=recipient,
            amount=amount,
            autonomous_transfer_limit_eur=financial_rules["autonomous_transfer_limit_eur"],
        )
        if decision.get("status") != "ALLOWED":
            return json.dumps(decision)

        result = self.repository.execute_internal_transfer(
            trace_id=trace_id or f"trc_tool_{int(time.time() * 1000):x}",
            operation_id=operation_id,
            source_name="Checking",
            target_name=recipient,
            amount=amount,
        )
        return json.dumps(result, ensure_ascii=False)

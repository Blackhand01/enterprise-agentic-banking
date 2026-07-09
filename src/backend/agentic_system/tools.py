"""Local tool implementations for the banking agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .guardrails import evaluate_transfer_guardrail, transfer_decision_to_tool_result
    from .schemas import validate_tool_arguments
except ImportError:  # Allows direct script-style imports during prototyping.
    from guardrails import evaluate_transfer_guardrail, transfer_decision_to_tool_result
    from schemas import validate_tool_arguments


class BankingToolExecutor:
    """Executes local tools after schema validation and deterministic guardrails."""

    def __init__(self, ledger_path: str | Path = "ledger.json") -> None:
        self.ledger_path = Path(ledger_path)

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
            return self.fetch_transactions(category=validated_args.category)

        if tool_name == "execute_transfer":
            return self.execute_transfer(
                recipient=validated_args.recipient,
                amount=validated_args.amount,
            )

        return json.dumps({"status": "ERROR", "reason": "UNKNOWN_TOOL", "tool": tool_name})

    def fetch_transactions(self, category: str) -> str:
        """Grounded ledger lookup by transaction category."""

        if not self.ledger_path.exists():
            return json.dumps(
                {
                    "status": "ERROR",
                    "reason": "LEDGER_FILE_NOT_FOUND",
                    "path": str(self.ledger_path),
                }
            )

        try:
            ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return json.dumps({"status": "ERROR", "reason": "INVALID_LEDGER_JSON"})

        transactions = ledger.get("transactions", [])
        normalized_category = category.strip().lower()
        matches = [
            tx
            for tx in transactions
            if str(tx.get("category", "")).strip().lower() == normalized_category
        ]

        return json.dumps(
            {
                "status": "OK",
                "category": category,
                "count": len(matches),
                "transactions": matches,
            },
            ensure_ascii=False,
        )

    def execute_transfer(self, recipient: str, amount: float) -> str:
        """Simulated transfer execution behind deterministic guardrails."""

        decision = evaluate_transfer_guardrail(recipient=recipient, amount=amount)
        return transfer_decision_to_tool_result(decision)

"""Customer chat facade around the Groq-powered banking agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from ..agentic_system.agent import BankingAgent
except ImportError:  # Allows direct script-style imports during prototyping.
    from agentic_system.agent import BankingAgent


class CustomerChatService:
    """Creates the banking agent lazily and formats API chat responses."""

    def __init__(
        self,
        *,
        policy_db_path: Path,
        db_path: Path,
        ledger_seed_path: Path,
    ) -> None:
        self.policy_db_path = policy_db_path
        self.db_path = db_path
        self.ledger_seed_path = ledger_seed_path
        self._banking_agent: BankingAgent | None = None

    def chat(self, message: str) -> dict[str, Any]:
        try:
            agent = self._agent()
            answer = agent.chat(message)
        except RuntimeError as exc:
            return {
                "answer": (
                    "Assistente AI non disponibile in questo ambiente. "
                    "Configura GROQ_API_KEY per abilitare la chat agentica con tool calling."
                ),
                "tool_result": {
                    "status": "AI_ASSISTANT_UNAVAILABLE",
                    "reason": str(exc),
                },
            }

        return {
            "answer": answer,
            "tool_result": latest_tool_result(agent.history),
            "history": agent.history,
        }

    def reset_agent(self) -> None:
        self._banking_agent = None

    def _agent(self) -> BankingAgent:
        if self._banking_agent is None:
            self._banking_agent = BankingAgent(
                policy_db_path=self.policy_db_path,
                db_path=self.db_path,
                ledger_seed_path=self.ledger_seed_path,
            )
        return self._banking_agent


def latest_tool_result(history: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(history):
        if message.get("role") != "tool":
            continue
        try:
            parsed = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            return {"status": "INVALID_TOOL_RESULT"}
        return parsed if isinstance(parsed, dict) else {"status": "INVALID_TOOL_RESULT"}
    return {"status": "NO_TOOL_CALL"}

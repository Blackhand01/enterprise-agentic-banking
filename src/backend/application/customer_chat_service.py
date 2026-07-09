"""Customer chat facade around the provider-agnostic banking agent."""

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
            history_before_turn = len(agent.history)
            answer = agent.chat(message)
        except RuntimeError as exc:
            return {
                "answer": _assistant_unavailable_message(str(exc)),
                "tool_result": {
                    "status": "AI_ASSISTANT_UNAVAILABLE",
                    "reason": str(exc),
                },
            }

        turn_messages = agent.history[history_before_turn:]
        return {
            "answer": answer,
            "tool_result": latest_tool_result(turn_messages),
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


def _assistant_unavailable_message(reason: str) -> str:
    lowered = reason.lower()
    if "invalid_api_key" in lowered or "invalid api key" in lowered or "401" in lowered:
        return (
            "Assistente AI non disponibile: la chiave LLM configurata non e valida. "
            "Verifica LLM_PROVIDER e la relativa chiave API in .env, poi riavvia il server."
        )
    if "rate_limit" in lowered or "rate limit" in lowered or "429" in lowered:
        return (
            "Assistente AI temporaneamente non disponibile: limite di utilizzo del provider LLM raggiunto. "
            "Riprova tra qualche minuto o usa una chiave con quota disponibile."
        )
    if "API_KEY" in reason or "LLM_PROVIDER" in reason or "LLM_BASE_URL" in reason:
        return (
            "Assistente AI non disponibile in questo ambiente. "
            "Configura un provider LLM in .env per abilitare la chat agentica con tool calling."
        )
    if "sentence-transformers" in reason:
        return (
            "Assistente AI non disponibile: manca il motore di embedding locale. "
            "Esegui python3 -m pip install -r requirements.txt e riavvia il server."
        )
    return (
        "Assistente AI temporaneamente non disponibile. "
        "Controlla il dettaglio tecnico nel pannello di ispezione."
    )

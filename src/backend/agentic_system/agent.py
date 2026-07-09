"""Groq-powered banking agent orchestration.

This module keeps orchestration thin: prompt construction, chat history,
tool execution and schema validation live in dedicated modules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from groq import Groq
except ImportError:  # Allows tests/imports without the optional dependency.
    Groq = None  # type: ignore[assignment]

try:
    from .chat_history import SlidingWindowChatHistory
    from .prompts import build_system_prompt
    from .retrieval import PolicyRetriever
    from .schemas import groq_tool_definitions
    from .tools import BankingToolExecutor
except ImportError:  # Allows direct script-style imports during prototyping.
    from chat_history import SlidingWindowChatHistory
    from prompts import build_system_prompt
    from retrieval import PolicyRetriever
    from schemas import groq_tool_definitions
    from tools import BankingToolExecutor


class BankingAgent:
    """Coordinates Groq chat completions and local tool execution."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        *,
        groq_client: Any | None = None,
        model: str = DEFAULT_MODEL,
        history_window: int = 10,
        policy_db_path: str | Path = "policyDB.json",
        ledger_path: str | Path = "ledger.json",
    ) -> None:
        self.model = model
        self.chat_history = SlidingWindowChatHistory(history_window)
        self.policy_retriever = PolicyRetriever(policy_db_path)
        self.tool_executor = BankingToolExecutor(ledger_path)
        self.groq_client = groq_client or self._build_groq_client()

    @property
    def history(self) -> list[dict[str, Any]]:
        """Expose a copy of the current sliding-window history for inspection."""

        return self.chat_history.messages

    @property
    def tools(self) -> list[dict[str, Any]]:
        return groq_tool_definitions()

    def chat(self, user_input: str) -> str:
        """Send a user message through the agent loop and return final text."""

        self._append_user_message(user_input)
        assistant_message = self._request_assistant_message(use_tools=True)

        if not self._has_tool_calls(assistant_message):
            return self._store_and_return_assistant_text(assistant_message)

        self._store_assistant_tool_request(assistant_message)
        self._execute_and_store_tool_calls(assistant_message.tool_calls)

        final_message = self._request_assistant_message(use_tools=False)
        return self._store_and_return_assistant_text(final_message)

    def fetch_transactions(self, category: str) -> str:
        """Compatibility wrapper for the local fetch_transactions tool."""

        return self.tool_executor.execute(
            "fetch_transactions",
            {"category": category},
        )

    def execute_transfer(self, recipient: str, amount: float) -> str:
        """Compatibility wrapper for the local execute_transfer tool."""

        return self.tool_executor.execute(
            "execute_transfer",
            {"recipient": recipient, "amount": amount},
        )

    def _build_groq_client(self) -> Any:
        if Groq is None:
            raise RuntimeError(
                "The 'groq' package is not installed. Install it with: pip install groq"
            )

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY environment variable.")

        return Groq(api_key=api_key)

    def _system_prompt(self) -> str:
        return build_system_prompt(self.policy_retriever)

    def _messages_for_api(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self._system_prompt()}] + self.history

    def _append_user_message(self, content: str) -> None:
        self._append_message({"role": "user", "content": content})

    def _append_message(self, message: dict[str, Any]) -> None:
        self.chat_history.append(message)

    def _request_assistant_message(self, *, use_tools: bool) -> Any:
        response = self._create_completion(self._messages_for_api(), use_tools=use_tools)
        return response.choices[0].message

    def _create_completion(self, messages: list[dict[str, Any]], *, use_tools: bool) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        if use_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        try:
            return self.groq_client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"Groq API call failed: {exc}") from exc

    @staticmethod
    def _has_tool_calls(assistant_message: Any) -> bool:
        return bool(getattr(assistant_message, "tool_calls", None))

    def _store_and_return_assistant_text(self, assistant_message: Any) -> str:
        final_text = getattr(assistant_message, "content", None) or ""
        self._append_message({"role": "assistant", "content": final_text})
        return final_text

    def _store_assistant_tool_request(self, assistant_message: Any) -> None:
        self._append_message(
            {
                "role": "assistant",
                "content": getattr(assistant_message, "content", None) or "",
                "tool_calls": [
                    self._serialize_tool_call(call)
                    for call in assistant_message.tool_calls
                ],
            }
        )

    @staticmethod
    def _serialize_tool_call(call: Any) -> dict[str, Any]:
        return {
            "id": call.id,
            "type": "function",
            "function": {
                "name": call.function.name,
                "arguments": call.function.arguments,
            },
        }

    def _execute_and_store_tool_calls(self, tool_calls: list[Any]) -> None:
        for call in tool_calls:
            self._append_message(self._run_tool_call(call))

    def _run_tool_call(self, call: Any) -> dict[str, Any]:
        tool_name = call.function.name
        arguments = self._parse_tool_arguments(call.function.arguments)
        tool_result = self.tool_executor.execute(tool_name, arguments)

        return {
            "role": "tool",
            "tool_call_id": call.id,
            "name": tool_name,
            "content": tool_result,
        }

    @staticmethod
    def _parse_tool_arguments(raw_arguments: str | None) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError:
            return {}

        return parsed if isinstance(parsed, dict) else {}

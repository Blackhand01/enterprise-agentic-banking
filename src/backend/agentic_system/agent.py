"""Provider-agnostic banking agent orchestration.

This module keeps orchestration thin: prompt construction, chat history,
tool execution and schema validation live in dedicated modules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .chat_history import SlidingWindowChatHistory
    from .guardrails import (
        response_has_customer_unsafe_content,
        sanitize_customer_response,
    )
    from .llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )
    from .prompts import build_system_prompt
    from .retrieval import PolicyRetriever
    from .schemas import llm_tool_definitions
    from .tools import BankingToolExecutor
except ImportError:  # Allows direct script-style imports during prototyping.
    from chat_history import SlidingWindowChatHistory
    from guardrails import response_has_customer_unsafe_content, sanitize_customer_response
    from llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )
    from prompts import build_system_prompt
    from retrieval import PolicyRetriever
    from schemas import llm_tool_definitions
    from tools import BankingToolExecutor


class BankingAgent:
    """Coordinates LLM chat completions and local tool execution."""

    DEFAULT_MODEL = ""

    def __init__(
        self,
        *,
        groq_client: Any | None = None,
        llm_client: Any | None = None,
        model: str = DEFAULT_MODEL,
        history_window: int = 10,
        policy_db_path: str | Path = "policyDB.json",
        db_path: str | Path = "banking.db",
        ledger_seed_path: str | Path = "ledger.json",
    ) -> None:
        self.model = model
        self.chat_history = SlidingWindowChatHistory(history_window)
        self.policy_retriever = PolicyRetriever(policy_db_path)
        self.tool_executor = BankingToolExecutor(db_path, ledger_seed_path)
        self.llm_client = llm_client or groq_client
        self.llm_provider = "custom"
        self._fallback_provider_configs: list[LLMProviderConfig] = []
        if self.llm_client is None:
            self.llm_client, provider_config = build_chat_client()
            self.llm_provider = provider_config.provider
            if not self.model:
                self.model = provider_config.model
            self._fallback_provider_configs = fallback_provider_configs(provider_config)

    @property
    def history(self) -> list[dict[str, Any]]:
        """Expose a copy of the current sliding-window history for inspection."""

        return self.chat_history.messages

    @property
    def tools(self) -> list[dict[str, Any]]:
        return llm_tool_definitions()

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
            return self.llm_client.chat.completions.create(**kwargs)
        except Exception as exc:
            try:
                fallback_response = self._try_fallback_completion(
                    kwargs,
                    original_provider=self.llm_provider,
                    original_error=exc,
                )
            except RuntimeError:
                raise
            if fallback_response is not None:
                return fallback_response
            raise RuntimeError(f"{self.llm_provider} LLM API call failed: {exc}") from exc

    def _try_fallback_completion(
        self,
        kwargs: dict[str, Any],
        *,
        original_provider: str,
        original_error: Exception,
    ) -> Any | None:
        if not self._is_retryable_provider_error(original_error):
            return None

        errors = [f"{original_provider}: {original_error}"]
        for config in self._fallback_provider_configs:
            fallback_kwargs = dict(kwargs)
            fallback_kwargs["model"] = config.model
            try:
                client = build_chat_client_for_config(config)
                response = client.chat.completions.create(**fallback_kwargs)
            except Exception as exc:
                errors.append(f"{config.provider}: {exc}")
                if not self._is_retryable_provider_error(exc):
                    continue
                continue

            self.llm_client = client
            self.llm_provider = config.provider
            self.model = config.model
            self._fallback_provider_configs = [
                candidate
                for candidate in self._fallback_provider_configs
                if candidate.provider != config.provider
            ]
            return response

        raise RuntimeError("All configured LLM providers failed: " + " | ".join(errors))

    @staticmethod
    def _is_retryable_provider_error(error: Exception) -> bool:
        lowered = str(error).lower()
        return any(
            marker in lowered
            for marker in (
                "401",
                "403",
                "408",
                "409",
                "429",
                "500",
                "502",
                "503",
                "504",
                "invalid_api_key",
                "rate_limit",
                "rate limit",
                "timeout",
                "temporarily unavailable",
                "service unavailable",
            )
        )

    @staticmethod
    def _has_tool_calls(assistant_message: Any) -> bool:
        return bool(getattr(assistant_message, "tool_calls", None))

    def _store_and_return_assistant_text(self, assistant_message: Any) -> str:
        final_text = getattr(assistant_message, "content", None) or ""
        final_text = self._customer_safe_text(final_text)
        self._append_message({"role": "assistant", "content": final_text})
        return final_text

    def _customer_safe_text(self, text: str) -> str:
        if not response_has_customer_unsafe_content(text):
            return text

        tool_fallback = self._format_latest_tool_result_for_customer()
        if tool_fallback:
            return tool_fallback

        return sanitize_customer_response(text)

    def _format_latest_tool_result_for_customer(self) -> str | None:
        for message in reversed(self.history):
            if message.get("role") != "tool":
                continue
            tool_name = message.get("name")
            payload = self._parse_tool_payload(message.get("content"))
            if tool_name == "get_balance_summary":
                return self._format_balance_summary(payload)
            if tool_name == "get_customer_context":
                balance_summary = payload.get("balance_summary", {})
                return self._format_balance_summary(balance_summary)
            if tool_name == "fetch_transactions":
                return self._format_transaction_summary(payload)
            return None
        return None

    @staticmethod
    def _parse_tool_payload(content: Any) -> dict[str, Any]:
        try:
            parsed = json.loads(content or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _format_balance_summary(payload: dict[str, Any]) -> str | None:
        if payload.get("status") != "OK":
            return None

        currency = payload.get("currency", "EUR")
        accounts = payload.get("accounts", [])
        total = payload.get("total_balance")
        if total is None or not isinstance(accounts, list):
            return None

        account_parts = []
        for account in accounts:
            name = account.get("name")
            balance = account.get("balance")
            if name is None or balance is None:
                continue
            account_parts.append(
                f"{name}: {BankingAgent._format_money(float(balance), currency)}"
            )

        details = "; ".join(account_parts)
        return (
            "In questa banca hai "
            f"{BankingAgent._format_money(float(total), currency)} in totale. "
            f"Dettaglio conti: {details}."
        )

    @staticmethod
    def _format_transaction_summary(payload: dict[str, Any]) -> str | None:
        category = payload.get("category", "richiesta")
        if payload.get("status") == "NO_DATA":
            search_query = payload.get("search_query") or category
            return (
                "Non ho accesso ai dati relativi a "
                f"{search_query} nel tuo profilo attuale."
            )
        if payload.get("status") != "OK":
            return None

        transactions = payload.get("transactions", [])
        if not isinstance(transactions, list):
            return None

        total = abs(round(sum(float(tx.get("amount", 0)) for tx in transactions), 2))
        return (
            f"Ho trovato {len(transactions)} transazioni per la categoria {category}. "
            f"Il totale considerato e {BankingAgent._format_money(total, 'EUR')}."
        )

    @staticmethod
    def _format_money(value: float, currency: str) -> str:
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} {currency}"

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

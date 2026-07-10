"""Private runtime helpers for BankingAgent."""

from __future__ import annotations
import json
from typing import Any

try:
    from .agent_support import _extract_month_range, _is_temporal_follow_up
    from .guardrails import (
        response_has_customer_unsafe_content,
        sanitize_customer_response,
    )
    from .llm_provider import build_chat_client_for_config
except ImportError:
    from agent_support import _extract_month_range, _is_temporal_follow_up
    from guardrails import (
        response_has_customer_unsafe_content,
        sanitize_customer_response,
    )
    from llm_provider import build_chat_client_for_config


class AgentRuntimeMixin:
    def _create_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        use_tools: bool,
        require_tool: bool = False,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if use_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "required" if require_tool else "auto"
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
            raise RuntimeError(
                f"{self.llm_provider} LLM API call failed: {exc}"
            ) from exc

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
            if tool_name == "get_spending_summary":
                return self._format_spending_summary(payload)
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
                f"{name}: {AgentRuntimeMixin._format_money(float(balance), currency)}"
            )
        details = "; ".join(account_parts)
        return (
            "In questa banca hai "
            f"{AgentRuntimeMixin._format_money(float(total), currency)} in totale. "
            f"Dettaglio conti: {details}."
        )

    @staticmethod
    def _format_transaction_summary(payload: dict[str, Any]) -> str | None:
        category = payload.get("category") or "richiesta"
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
            f"Il totale considerato e {AgentRuntimeMixin._format_money(total, 'EUR')}."
        )

    @staticmethod
    def _format_spending_summary(payload: dict[str, Any]) -> str | None:
        if payload.get("status") != "OK":
            return None
        currency = payload.get("currency", "EUR")
        total_spent = payload.get("total_spent")
        transactions = payload.get("transactions", [])
        if total_spent is None or not isinstance(transactions, list):
            return None
        details = []
        for transaction in transactions[:5]:
            merchant = transaction.get("merchant")
            amount = transaction.get("amount")
            if merchant is None or amount is None:
                continue
            details.append(
                f"{merchant}: {AgentRuntimeMixin._format_money(abs(float(amount)), currency)}"
            )
        detail_text = "; ".join(details)
        return (
            "Nelle transazioni recenti hai speso "
            f"{AgentRuntimeMixin._format_money(float(total_spent), currency)}. "
            f"Principali uscite: {detail_text}."
        )

    @staticmethod
    def _format_money(value: float, currency: str) -> str:
        formatted = (
            f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
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
        if tool_name == "fetch_transactions":
            arguments = self._with_temporal_context(arguments)
            arguments = self._with_customer_query_context(arguments)
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

    def _with_customer_query_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        latest_user_message = self._latest_user_message()
        search_query = arguments.get("search_query")
        category = arguments.get("category")
        if not latest_user_message:
            return arguments
        if not isinstance(search_query, str) or not search_query.strip():
            if isinstance(category, str) and category.strip():
                return arguments
            arguments["search_query"] = latest_user_message
            return arguments
        normalized_user_message = latest_user_message.strip()
        normalized_search_query = search_query.strip()
        if normalized_search_query.lower() in normalized_user_message.lower():
            arguments["search_query"] = normalized_user_message
            return arguments
        arguments["search_query"] = (
            f"{normalized_user_message} {normalized_search_query}"
        )
        return arguments

    def _with_temporal_context(self, arguments: dict[str, Any]) -> dict[str, Any]:
        latest_user_message = self._latest_user_message() or ""
        date_range = _extract_month_range(latest_user_message)
        if date_range:
            arguments.setdefault("date_from", date_range[0])
            arguments.setdefault("date_to", date_range[1])
        if not arguments.get("date_from") and not arguments.get("date_to"):
            return arguments
        latest_payload = self._latest_fetch_transactions_payload()
        if not latest_payload:
            return arguments
        if _is_temporal_follow_up(latest_user_message):
            arguments["category"] = latest_payload.get("category")
            arguments["search_query"] = latest_payload.get("search_query")
        else:
            arguments.setdefault("category", latest_payload.get("category"))
            arguments.setdefault("search_query", latest_payload.get("search_query"))
        return {key: value for key, value in arguments.items() if value is not None}

    def _latest_user_message(self) -> str | None:
        for message in reversed(self.history):
            if message.get("role") == "user":
                content = message.get("content")
                return content if isinstance(content, str) else None
        return None

    def _latest_fetch_transactions_payload(self) -> dict[str, Any] | None:
        for message in reversed(self.history):
            if (
                message.get("role") != "tool"
                or message.get("name") != "fetch_transactions"
            ):
                continue
            payload = self._parse_tool_payload(message.get("content"))
            return payload if payload else None
        return None

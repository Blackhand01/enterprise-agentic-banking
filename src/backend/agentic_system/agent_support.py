"""Support primitives for the provider-agnostic banking agent."""

from __future__ import annotations
import calendar
import json
import re
from pathlib import Path
from typing import Any, Callable, ClassVar, Protocol

try:
    from .guardrails import filter_active_policies
    from .llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )
except ImportError:
    from guardrails import filter_active_policies
    from llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )


class RetrievalQueryTranslator:
    """LLM-backed zero-shot translator for semantic retrieval queries."""

    _cache: ClassVar[dict[str, str]] = {}
    _override: ClassVar[Callable[[str], str] | None] = None

    @classmethod
    def set_override(cls, translator: Callable[[str], str] | None) -> None:
        cls._override = translator
        cls._cache = {}

    @classmethod
    def translate(cls, query: str) -> str:
        normalized = query.strip()
        if not normalized:
            return normalized
        if cls._override is not None:
            return cls._override(normalized).strip() or normalized
        cache_key = normalized.lower()
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        response = cls._translate_with_configured_provider(normalized)
        translated = (response.choices[0].message.content or "").strip()
        translated = _clean_translation(translated) or normalized
        cls._cache[cache_key] = translated
        return translated

    @staticmethod
    def _translation_messages(query: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "Translate the user's short semantic retrieval query to English for "
                    "a bank transaction search about customer purchases, merchants and activities. "
                    "Resolve ambiguous terms using that transaction-search context. "
                    "Return only the translated search phrase, with no explanation."
                ),
            },
            {"role": "user", "content": query},
        ]

    @classmethod
    def _translate_with_configured_provider(cls, query: str):
        client, primary_config = build_chat_client()
        kwargs = {
            "model": primary_config.model,
            "messages": cls._translation_messages(query),
            "temperature": 0,
            "max_tokens": 24,
        }
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            return cls._translate_with_fallbacks(
                kwargs=kwargs,
                primary_config=primary_config,
                original_error=exc,
            )

    @staticmethod
    def _translate_with_fallbacks(
        *,
        kwargs: dict,
        primary_config: LLMProviderConfig,
        original_error: Exception,
    ):
        if not _is_retryable_provider_error(original_error):
            raise original_error
        errors = [f"{primary_config.provider}: {original_error}"]
        for config in fallback_provider_configs(primary_config):
            fallback_kwargs = dict(kwargs)
            fallback_kwargs["model"] = config.model
            try:
                client = build_chat_client_for_config(config)
                return client.chat.completions.create(**fallback_kwargs)
            except Exception as exc:
                errors.append(f"{config.provider}: {exc}")
                continue
        raise RuntimeError(
            "All configured LLM providers failed during retrieval query translation: "
            + " | ".join(errors)
        )


def _clean_translation(value: str) -> str:
    return value.replace("\n", " ").strip().strip('"').strip("'").strip()


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


class SlidingWindowChatHistory:
    """Stores only the most recent messages needed for the agent context."""

    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._messages: list[dict[str, Any]] = []

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def append(self, message: dict[str, Any]) -> None:
        self._messages.append(message)
        self._messages = self._messages[-self.window_size :]

    def extend(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            self.append(message)


class PolicyLookup(Protocol):
    def get_policies_by_category(self, category: str) -> str: ...


def build_system_prompt(policy_retriever: PolicyLookup) -> str:
    """Build the system prompt with active, non-stale policies injected."""
    transfer_policy = policy_retriever.get_policies_by_category(
        "payments_and_transfers"
    )
    grounding_policy = policy_retriever.get_policies_by_category("grounding")
    return f"""
            You are the TCS Agentic Bank Assistant.

            Your task:
            - Understand the customer's request.
            - Use available functions when the answer depends on account data, transactions, policies, or banking actions.
            - Retrieve relevant context before giving financial guidance or proposing an operation.
            - Produce clear customer answers with facts, rationale, and the proposed next step.
            - Never invent balances, transactions, beneficiaries, policies, or execution results.
            - If requested data is not available in the current profile, state that concisely and stop.
            - If an operation cannot be completed, explain only the customer-side next step. Do not discuss implementation details.
            - Never say money was moved unless a function result confirms the operation.

            Customer conversation rules:
            - Always answer in English.
            - Never show function names, tool calls, <function=...> tags, policy IDs, document IDs, or internal technical details.
            - Do not invent unavailable functions. If a tool does not exist, do not mention it.
            - When the customer asks about balances, total available, accounts, planned expenses, or overall context, first retrieve verified context with the available tools.
            - When the customer asks about history, use the available tools to retrieve verified data instead of answering from memory.
            - If a tool returns transactions, say the data was found and summarize only those transactions. Do not say the data is missing.
            - If a tool returns NO_DATA, answer with one concise sentence. Do not add generic offers of help.
            - If the customer asks what a merchant is, describe only what appears in the customer profile: date, amount, category, and merchant name. Do not infer the business type beyond available data.
            - When the customer asks what you can do, describe only actually supported capabilities: check balances and customer context, analyze transactions by category, explain proposals, prepare transfers to supported destinations with safety controls.
            - If the customer asks for other customers' data or all bank accounts, refuse briefly and explain that you can use only their verified banking context.

            Strict Compliance Rule:
            - If the customer asks about financial information or products that are not present in retrieved context, such as mortgages, loans, credit lines, or unloaded products, explicitly state that the data is missing.
            - Do not offer manual risk calculations.
            - Do not ask the customer to manually provide missing data.
            - Do not offer general financial advice.
            - For missing data, use this exact format: "I do not have access to data about [topic] in your current profile."

            Active transfer policy:
            {transfer_policy}

            Active grounding policy:
            {grounding_policy}
        """.strip()


class PolicyRetriever:
    """Loads active bank policies and formats them for prompt grounding."""

    def __init__(self, db_path: str | Path = "policyDB.json") -> None:
        self.db_path = Path(db_path)
        self._policies = self._load_active_policies()

    def _load_active_policies(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Policy database not found: {self.db_path}")
        try:
            raw = json.loads(self.db_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in policy database: {self.db_path}"
            ) from exc
        if not isinstance(raw, list):
            raise ValueError("Policy database must be a list of policy objects.")
        return filter_active_policies(raw)

    def get_policies_by_category(self, category: str) -> str:
        """Return active policies for a category as prompt-ready text."""
        normalized_category = category.strip().lower()
        matches = [
            policy
            for policy in self._policies
            if str(policy.get("category", "")).strip().lower() == normalized_category
        ]
        if not matches:
            return f"No active policy found for category: {category}"
        formatted: list[str] = []
        for policy in matches:
            policy_id = policy.get("id", "unknown_policy")
            title = policy.get("title", policy_id)
            version = policy.get("version", "unspecified")
            body = policy.get("body", "")
            formatted.append(
                "\n".join(
                    [
                        f"Policy ID: {policy_id}",
                        f"Title: {title}",
                        f"Category: {policy.get('category', category)}",
                        f"Version: {version}",
                        f"Body: {body}",
                    ]
                )
            )
        return "\n\n---\n\n".join(formatted)


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _extract_month_range(text: str) -> tuple[str, str] | None:
    lowered = text.lower()
    match = re.search(
        r"\b(" + "|".join(_MONTHS) + r")\s+(\d{4})\b",
        lowered,
    )
    if not match:
        return None
    month = _MONTHS[match.group(1)]
    year = int(match.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _is_temporal_follow_up(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return False
    month_pattern = "|".join(_MONTHS)
    return bool(
        re.fullmatch(
            r"(and\s+)?(in)?\s*(" + month_pattern + r")\s+\d{4}\s*\??", lowered
        )
    )

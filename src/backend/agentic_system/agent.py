"""Provider-agnostic banking agent orchestration."""

from __future__ import annotations
from pathlib import Path
from typing import Any

try:
    from .agent_runtime import AgentRuntimeMixin
    from .agent_support import (
        PolicyRetriever,
        SlidingWindowChatHistory,
        _extract_month_range,
        _is_temporal_follow_up,
        build_system_prompt,
    )
    from .llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        fallback_provider_configs,
    )
    from .schemas import llm_tool_definitions
    from .tools import BankingToolExecutor
except ImportError:
    from agent_runtime import AgentRuntimeMixin
    from agent_support import (
        PolicyRetriever,
        SlidingWindowChatHistory,
        _extract_month_range,
        _is_temporal_follow_up,
        build_system_prompt,
    )
    from llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        fallback_provider_configs,
    )
    from schemas import llm_tool_definitions
    from tools import BankingToolExecutor

__all__ = [
    "BankingAgent",
    "_extract_month_range",
    "_is_temporal_follow_up",
]


class BankingAgent(AgentRuntimeMixin):
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
        assistant_message = self._request_assistant_message(
            use_tools=True,
            require_tool=True,
        )
        if not self._has_tool_calls(assistant_message):
            return self._store_and_return_assistant_text(assistant_message)
        self._store_assistant_tool_request(assistant_message)
        self._execute_and_store_tool_calls(assistant_message.tool_calls)
        final_message = self._request_assistant_message(use_tools=False)
        return self._store_and_return_assistant_text(final_message)

    def fetch_transactions(
        self,
        category: str | None = None,
        search_query: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> str:
        """Compatibility wrapper for the local fetch_transactions tool."""
        arguments = {
            key: value
            for key, value in {
                "category": category,
                "search_query": search_query,
                "date_from": date_from,
                "date_to": date_to,
            }.items()
            if value is not None
        }
        return self.tool_executor.execute("fetch_transactions", arguments)

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

    def _request_assistant_message(
        self,
        *,
        use_tools: bool,
        require_tool: bool = False,
    ) -> Any:
        response = self._create_completion(
            self._messages_for_api(),
            use_tools=use_tools,
            require_tool=require_tool,
        )
        return response.choices[0].message

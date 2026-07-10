"""Centralized Pydantic schemas for OpenAI-compatible agent tool contracts.

The agent exposes these schemas to the selected LLM provider for tool calling
and uses the same models to validate tool arguments before executing local
Python functions.
"""

from __future__ import annotations
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FetchTransactionsArgs(BaseModel):
    """Arguments for the fetch_transactions tool."""

    model_config = ConfigDict(extra="forbid")
    category: str | None = Field(
        default=None,
        description=(
            "Banking macro-category, if the customer provides it. Leave empty "
            "when the search is conceptual."
        ),
    )
    search_query: str | None = Field(
        default=None,
        description=(
            "Natural phrase or semantic concept searched by the customer. Prefer "
            "the full relevant part of the customer request over isolated tokens, "
            "so the backend can resolve ambiguity through local embedding search."
        ),
    )
    date_from: str | None = Field(
        default=None,
        description="Optional start date in YYYY-MM-DD format.",
    )
    date_to: str | None = Field(
        default=None,
        description="Optional end date in YYYY-MM-DD format.",
    )

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("search_query")
    @classmethod
    def normalize_search_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("date_from", "date_to")
    @classmethod
    def normalize_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            raise ValueError("date filters must use YYYY-MM-DD")
        return normalized

    @model_validator(mode="after")
    def require_category_or_search_query(self) -> "FetchTransactionsArgs":
        if not self.category and not self.search_query:
            raise ValueError("category or search_query is required")
        return self


class NoArgs(BaseModel):
    """Empty argument contract for read-only tools without parameters."""

    model_config = ConfigDict(extra="forbid")


class ExecuteTransferArgs(BaseModel):
    """Arguments for the execute_transfer tool."""

    model_config = ConfigDict(extra="forbid")
    recipient: str = Field(
        ...,
        min_length=1,
        description="Transfer beneficiary or savings pot name.",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount in EUR.",
    )
    operation_id: str | None = Field(
        default=None,
        description="Idempotent operation identifier, if available.",
    )

    @field_validator("recipient")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("recipient cannot be blank")
        return normalized

    @field_validator("operation_id")
    @classmethod
    def normalize_operation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "get_balance_summary": NoArgs,
    "get_customer_context": NoArgs,
    "get_spending_summary": NoArgs,
    "fetch_transactions": FetchTransactionsArgs,
    "execute_transfer": ExecuteTransferArgs,
}


def llm_tool_definitions() -> list[dict[str, Any]]:
    """Return OpenAI-compatible tool definitions from the central Pydantic models."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_balance_summary",
                "description": (
                    "Retrieve the customer's local bank accounts, balances, "
                    "and total balance in EUR."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_context",
                "description": (
                    "Retrieve verified customer context: accounts, balances, "
                    "latest salary, scheduled payments, recent transactions, "
                    "and monthly history."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_spending_summary",
                "description": (
                    "Deterministically calculate total recent outflows "
                    "using only negative-amount customer transactions."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_transactions",
                "description": (
                    "Retrieve the customer's banking transaction history. "
                    "Supports macro-category filters and semantic searches over "
                    "specific concepts through embeddings. Supports structured "
                    "date filters with date_from and date_to."
                ),
                "parameters": FetchTransactionsArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_transfer",
                "description": "Submit a transfer request to a beneficiary or savings pot.",
                "parameters": ExecuteTransferArgs.model_json_schema(),
            },
        },
    ]


def groq_tool_definitions() -> list[dict[str, Any]]:
    """Backward-compatible alias kept for older imports/tests."""
    return llm_tool_definitions()


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> BaseModel:
    """Validate raw tool-call arguments against the matching Pydantic model."""
    model = TOOL_ARG_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return model.model_validate(arguments)

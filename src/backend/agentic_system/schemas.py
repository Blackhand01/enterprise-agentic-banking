"""Centralized Pydantic schemas for agent tool contracts.

The agent exposes these schemas to Groq for tool calling and uses the same
models to validate tool arguments before executing local Python functions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FetchTransactionsArgs(BaseModel):
    """Arguments for the fetch_transactions tool."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(
        ...,
        min_length=1,
        description="Transaction category, e.g. sport, bollette, stipendio.",
    )

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("category cannot be blank")
        return normalized


class ExecuteTransferArgs(BaseModel):
    """Arguments for the execute_transfer tool."""

    model_config = ConfigDict(extra="forbid")

    recipient: str = Field(
        ...,
        min_length=1,
        description="Transfer recipient or savings pot name.",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount in EUR.",
    )

    @field_validator("recipient")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("recipient cannot be blank")
        return normalized


TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "fetch_transactions": FetchTransactionsArgs,
    "execute_transfer": ExecuteTransferArgs,
}


def groq_tool_definitions() -> list[dict[str, Any]]:
    """Return Groq-compatible tool definitions from the central Pydantic models."""

    return [
        {
            "type": "function",
            "function": {
                "name": "fetch_transactions",
                "description": "Fetch grounded ledger transactions by category.",
                "parameters": FetchTransactionsArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_transfer",
                "description": "Submit a transfer request to a recipient or savings pot.",
                "parameters": ExecuteTransferArgs.model_json_schema(),
            },
        },
    ]


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> BaseModel:
    """Validate raw tool-call arguments against the matching Pydantic model."""

    model = TOOL_ARG_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return model.model_validate(arguments)
